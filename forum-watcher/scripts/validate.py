#!/usr/bin/env python3
"""MHVTL + disk-tool smoke suite. Never runs tape tests on GitHub-hosted runners."""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

TAPE_MODULES = frozenset({"tape-ops", "vtl-cloud", "tape-duplicate"})
TIMEOUT = 60
# Full 100 MiB LTO payload only when MHVTL_FULL=1; default 1 MiB for smoke.
LTO_MIB = 100 if os.environ.get("MHVTL_FULL") == "1" else 1


def which(name: str) -> str | None:
    return shutil.which(name)


def run_cmd(argv: list[str], timeout: int = TIMEOUT, cwd: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv,
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=cwd,
        check=False,
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_github_hosted() -> bool:
    labels = os.environ.get("RUNNER_LABELS", "")
    if "self-hosted" in labels or "mhvtl" in labels:
        return False
    if os.environ.get("RUNNER_ENVIRONMENT", "").lower() == "github-hosted":
        return True
    if os.environ.get("RUNNER_NAME", "").startswith("GitHub Actions"):
        return True
    # GitHub-hosted ubuntu-* sets GITHUB_ACTIONS plus ImageOS; self-hosted should set RUNNER_LABELS.
    if os.environ.get("GITHUB_ACTIONS") == "true":
        return True
    return False


def has_sg() -> bool:
    dev = Path("/dev")
    if not dev.exists():
        return False
    return any(dev.glob("sg*")) or Path("/dev/nst0").exists() or Path("/dev/st0").exists()


def result(name: str, status: str, detail: str) -> dict:
    return {"name": name, "status": status, "detail": detail}


def refuse_hosted_tape(name: str) -> dict | None:
    if is_github_hosted():
        return result(
            name,
            "skip",
            "HARD RULE: mhvtl/tape tests never run on a GitHub-hosted runner (no /dev/sg)",
        )
    if not has_sg():
        return result(name, "skip", "no SCSI generic device (/dev/sg* or /dev/nst0)")
    return None


def docker_mhvtl_available() -> str | None:
    image = os.environ.get("MHVTL_DOCKER_IMAGE", "").strip()
    if not image:
        return None
    if is_github_hosted():
        return None
    if not which("docker"):
        return None
    inspect = run_cmd(["docker", "image", "inspect", image], timeout=30)
    if inspect.returncode == 0:
        return image
    pull = run_cmd(["docker", "pull", image], timeout=120)
    if pull.returncode == 0:
        return image
    return None


def test_mhvtl_discovery() -> dict:
    name = "mhvtl discovery"
    blocked = refuse_hosted_tape(name)
    if blocked:
        image = docker_mhvtl_available()
        if image and blocked["detail"].startswith("no SCSI"):
            return result(
                name,
                "skip",
                f"Docker image {image} is present but mhvtl needs the host kernel module; "
                "adrianj/mhvtl does not exist on Docker Hub (404). Use a self-hosted mhvtl runner.",
            )
        return blocked
    mtx = which("mtx")
    if not mtx:
        return result(name, "skip", "mtx not on PATH")
    device = os.environ.get("MHVTL_CHANGER", "/dev/sg13")
    proc = run_cmd([mtx, "-f", device, "status"])
    if proc.returncode != 0:
        # Common: changer is not sg13. Try mtx inquiry on sg devices? Keep honest.
        return result(name, "fail", proc.stderr.strip() or proc.stdout.strip() or f"{mtx} exit {proc.returncode}")
    text = proc.stdout
    if "Storage Element" not in text and "Data Transfer Element" not in text:
        return result(name, "fail", "mtx status did not look like a library:\n" + text[:400])
    return result(name, "pass", f"{device}: library status ok")


def test_lto7_write_read() -> dict:
    name = "LTO-7 write-read"
    blocked = refuse_hosted_tape(name)
    if blocked:
        return blocked
    tape = os.environ.get("MHVTL_TAPE", "/dev/nst0")
    if not Path(tape).exists():
        return result(name, "skip", f"{tape} missing")
    if not which("tar") or not which("mt"):
        return result(name, "skip", "tar or mt not on PATH")
    with tempfile.TemporaryDirectory(prefix="mhvtl-lto-") as tmp:
        src = Path(tmp) / "rand.bin"
        run_cmd(["dd", "if=/dev/urandom", f"of={src}", "bs=1M", f"count={LTO_MIB}"], timeout=TIMEOUT)
        expected = sha256_file(src)
        rewind = run_cmd(["mt", "-f", tape, "rewind"])
        if rewind.returncode != 0:
            return result(name, "fail", rewind.stderr.strip() or "mt rewind failed")
        write = run_cmd(["tar", "-cf", tape, "-C", tmp, src.name], timeout=TIMEOUT)
        if write.returncode != 0:
            return result(name, "fail", write.stderr.strip() or "tar write failed")
        run_cmd(["mt", "-f", tape, "rewind"])
        extract_dir = Path(tmp) / "extract"
        extract_dir.mkdir()
        read = run_cmd(["tar", "-xf", tape, "-C", str(extract_dir)], timeout=TIMEOUT)
        if read.returncode != 0:
            return result(name, "fail", read.stderr.strip() or "tar read failed")
        got = sha256_file(extract_dir / src.name)
        if got != expected:
            return result(name, "fail", f"sha256 mismatch {expected} != {got}")
        return result(name, "pass", f"{LTO_MIB} MiB round-trip {expected[:12]}")


def test_ltfs_format() -> dict:
    name = "LTFS format"
    blocked = refuse_hosted_tape(name)
    if blocked:
        return blocked
    mkltfs = which("mkltfs")
    ltfs = which("ltfs")
    if not mkltfs:
        return result(name, "skip", "mkltfs not on PATH")
    tape = os.environ.get("MHVTL_TAPE", "/dev/nst0")
    if not Path(tape).exists():
        return result(name, "skip", f"{tape} missing")
    fmt = run_cmd([mkltfs, "-f", "-d", tape, "-n", "TEST"], timeout=TIMEOUT)
    if fmt.returncode != 0:
        return result(name, "fail", fmt.stderr.strip() or "mkltfs failed")
    if not ltfs:
        return result(name, "pass", "mkltfs ok; ltfs mount binary missing (format-only)")
    mount = Path("/tmp/ltfs-test")
    mount.mkdir(exist_ok=True)
    mounted = run_cmd([ltfs, "-o", f"devname={tape}", str(mount)], timeout=TIMEOUT)
    if mounted.returncode != 0:
        return result(name, "fail", mounted.stderr.strip() or "ltfs mount failed")
    run_cmd(["umount", str(mount)])
    fsck = which("ltfsfsck")
    if fsck:
        run_cmd([fsck, tape], timeout=TIMEOUT)
    return result(name, "pass", "mkltfs + ltfs mount/umount")


def test_borg_restore() -> dict:
    name = "BorgBackup restore"
    borg = which("borg")
    if not borg:
        return result(name, "skip", "borg not on PATH")
    env = os.environ.copy()
    env["BORG_PASSPHRASE"] = "t2c-mhvtl-smoke"
    with tempfile.TemporaryDirectory(prefix="mhvtl-borg-") as tmp:
        repo = Path(tmp) / "repo"
        src = Path(tmp) / "src"
        src.mkdir()
        payload = src / "payload.bin"
        payload.write_bytes(os.urandom(64 * 1024))
        expected = sha256_file(payload)
        init = subprocess.run(
            [borg, "init", "--encryption=repokey-blake2", str(repo)],
            capture_output=True, text=True, timeout=TIMEOUT, env=env, check=False,
        )
        if init.returncode != 0:
            return result(name, "fail", init.stderr.strip() or "borg init failed")
        create = subprocess.run(
            [borg, "create", f"{repo}::smoke", str(src)],
            capture_output=True, text=True, timeout=TIMEOUT, env=env, check=False,
        )
        if create.returncode != 0:
            return result(name, "fail", create.stderr.strip() or "borg create failed")
        dest = Path(tmp) / "restore"
        dest.mkdir()
        extract = subprocess.run(
            [borg, "extract", f"{repo}::smoke"],
            capture_output=True, text=True, timeout=TIMEOUT, env=env, cwd=str(dest), check=False,
        )
        if extract.returncode != 0:
            return result(name, "fail", extract.stderr.strip() or "borg extract failed")
        restored = dest / src.name / payload.name
        # borg extract restores the absolute/relative path under cwd
        if not restored.exists():
            matches = list(dest.rglob(payload.name))
            if not matches:
                return result(name, "fail", "extracted payload missing")
            restored = matches[0]
        got = sha256_file(restored)
        if got != expected:
            return result(name, "fail", f"sha256 mismatch {expected} != {got}")
        return result(name, "pass", f"round-trip {expected[:12]}")


def test_seaweedfs_s3() -> dict:
    name = "SeaweedFS S3 round-trip"
    weed = which("weed")
    if not weed:
        return result(name, "skip", "weed not on PATH")
    with tempfile.TemporaryDirectory(prefix="mhvtl-weed-") as tmp:
        data_dir = Path(tmp) / "data"
        data_dir.mkdir()
        # Prefer `weed mini` (current SeaweedFS smoke) over `weed server -s3`.
        proc = subprocess.Popen(
            [weed, "mini", "-dir", str(data_dir)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            time.sleep(2)
            if proc.poll() is not None:
                return result(name, "skip", "weed mini exited immediately; try `weed server -s3` on a self-hosted box")
            src = Path(tmp) / "obj.bin"
            src.write_bytes(os.urandom(512 * 1024))
            expected = sha256_file(src)
            dest = Path(tmp) / "obj.out"
            # Default mini S3 is often :8333; use rclone/aws if present, else curl PUT may 403.
            rclone = which("rclone")
            if rclone:
                conf = Path(tmp) / "rclone.conf"
                conf.write_text(
                    "[sw]\ntype = s3\nprovider = Other\naccess_key_id = any\n"
                    "secret_access_key = any\nendpoint = http://127.0.0.1:8333\n"
                    "acl = private\n"
                )
                put = run_cmd(
                    [rclone, "--config", str(conf), "copyto", str(src), "sw:t2c-smoke/obj.bin"],
                    timeout=TIMEOUT,
                )
                if put.returncode != 0:
                    return result(name, "fail", put.stderr.strip() or "rclone put failed")
                get = run_cmd(
                    [rclone, "--config", str(conf), "copyto", "sw:t2c-smoke/obj.bin", str(dest)],
                    timeout=TIMEOUT,
                )
                if get.returncode != 0:
                    return result(name, "fail", get.stderr.strip() or "rclone get failed")
                got = sha256_file(dest)
                if got != expected:
                    return result(name, "fail", f"sha256 mismatch {expected} != {got}")
                return result(name, "pass", f"S3 round-trip {expected[:12]}")
            return result(name, "skip", "weed mini running but rclone missing for S3 PUT/GET")
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()


TESTS = (
    test_mhvtl_discovery,
    test_lto7_write_read,
    test_ltfs_format,
    test_borg_restore,
    test_seaweedfs_s3,
)


def should_run(modules: list[str]) -> bool:
    if not modules:
        return True
    return any(m in TAPE_MODULES for m in modules)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="MHVTL / disk-tool smoke suite")
    parser.add_argument(
        "--modules",
        default=os.environ.get("VALIDATE_MODULES", "tape-ops,vtl-cloud,tape-duplicate"),
        help="Comma-separated module hints from the promoted Discover",
    )
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def run(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    modules = [m.strip() for m in args.modules.split(",") if m.strip()]
    print(f"[validate] modules={modules} github_hosted={is_github_hosted()} sg={has_sg()}")
    if is_github_hosted():
        print("[validate] tape tests will SKIP (GitHub-hosted has no sg)")
        image = os.environ.get("MHVTL_DOCKER_IMAGE", "")
        if image:
            print("[validate] refusing Docker fallback on GitHub-hosted — privileged sg passthrough is not available")
    if not should_run(modules):
        print("[validate] skip: promoted modules are not tape-ops / vtl-cloud / tape-duplicate")
        return 0
    results = []
    for fn in TESTS:
        try:
            results.append(fn())
        except subprocess.TimeoutExpired:
            results.append(result(fn.__name__, "fail", f"timeout {TIMEOUT}s"))
        except Exception as exc:  # noqa: BLE001
            results.append(result(fn.__name__, "fail", str(exc)))
    failed = 0
    for item in results:
        print(f"[{item['status'].upper()}] {item['name']}: {item['detail']}")
        if item["status"] == "fail":
            failed += 1
    if args.json:
        import json

        print(json.dumps(results, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(run())
