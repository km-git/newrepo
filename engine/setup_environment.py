"""Auto-install Python libraries, GitHub libs, and gh CLI for the trading system."""

from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import sys
import venv
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent.parent
VENV_DIR = ROOT / ".venv"
LIBS_DIR = ROOT / "libs"

GITHUB_LIBS: Tuple[Tuple[str, str], ...] = (
  ("https://github.com/niall-oc/pyharmonics.git", "pyharmonics"),
  ("https://github.com/drstevendev/ElliottWaveAnalyzer.git", "ElliottWaveAnalyzer"),
  ("https://github.com/DrEdwardPCB/python-taew.git", "python-taew"),
)

PIP_EDITABLE = ("python-taew", "pyharmonics")
VERIFY_IMPORTS = (
  ("taew", "wave2_fibonacci_check"),
  ("pyharmonics.technicals", "OHLCTechnicals"),
)


def _run(cmd: List[str], *, cwd: Optional[Path] = None, input_text: str = "") -> subprocess.CompletedProcess:
  return subprocess.run(
    cmd,
    cwd=str(cwd or ROOT),
    capture_output=True,
    text=True,
    input=input_text,
  )


def venv_python() -> Path:
  if VENV_DIR.exists():
    return VENV_DIR / "bin" / "python"
  return Path(sys.executable)


def ensure_venv() -> Dict[str, Any]:
  if VENV_DIR.exists() and (VENV_DIR / "bin" / "python").exists():
    return {"created": False, "path": str(VENV_DIR)}
  builder = venv.EnvBuilder(with_pip=True, clear=False, upgrade=False)
  builder.create(VENV_DIR)
  return {"created": True, "path": str(VENV_DIR)}


def pip_install(*specs: str, upgrade: bool = False) -> Dict[str, Any]:
  py = venv_python()
  cmd = [str(py), "-m", "pip", "install"]
  if upgrade:
    cmd.append("--upgrade")
  cmd.extend(specs)
  proc = _run(cmd)
  return {
    "ok": proc.returncode == 0,
    "specs": list(specs),
    "stdout": (proc.stdout or "")[-2000:],
    "stderr": (proc.stderr or "")[-2000:],
  }


def clone_github_libs() -> List[Dict[str, Any]]:
  LIBS_DIR.mkdir(parents=True, exist_ok=True)
  results: List[Dict[str, Any]] = []
  for url, name in GITHUB_LIBS:
    dest = LIBS_DIR / name
    if (dest / ".git").exists():
      results.append({"name": name, "action": "exists", "path": str(dest)})
      continue
    proc = _run(["git", "clone", "--depth", "1", url, str(dest)])
    results.append({
      "name": name,
      "action": "cloned" if proc.returncode == 0 else "failed",
      "path": str(dest),
      "stderr": (proc.stderr or "")[-500:],
    })
  readme = LIBS_DIR / "python-taew" / "README.md"
  if not readme.exists() and (LIBS_DIR / "python-taew").exists():
    readme.write_text("# python-taew\n", encoding="utf-8")
  return results


def install_requirements() -> Dict[str, Any]:
  req = ROOT / "requirements.txt"
  if not req.exists():
    return {"ok": False, "error": "requirements.txt missing"}
  py = venv_python()
  _run([str(py), "-m", "pip", "install", "--upgrade", "pip"])
  return pip_install(f"-r{req}")


def install_editable_libs() -> Dict[str, Any]:
  specs = [str(LIBS_DIR / name) for name in PIP_EDITABLE if (LIBS_DIR / name).exists()]
  if not specs:
    return {"ok": False, "error": "no editable libs found — run clone first"}
  return pip_install(*specs)


def install_runtime_extras() -> Dict[str, Any]:
  return pip_install("numba", "plotly", "kaleido")


def install_token_savers() -> Dict[str, Any]:
  try:
    from engine.token_saver_registry import install_missing_libraries, registry_summary

    return {"install": install_missing_libraries(), "registry": registry_summary()}
  except Exception as exc:
    return {"ok": False, "error": str(exc)}


def find_gh() -> Optional[str]:
  for candidate in (
    shutil.which("gh"),
    "/exec-daemon/gh",
    "/usr/bin/gh",
    "/usr/local/bin/gh",
  ):
    if candidate and Path(candidate).exists():
      return candidate
  return None


def install_gh_cli() -> Dict[str, Any]:
  existing = find_gh()
  if existing:
    proc = _run([existing, "--version"])
    return {"installed": True, "path": existing, "version": (proc.stdout or proc.stderr or "").strip()}

  system = platform.system().lower()
  if system != "linux":
    return {"installed": False, "error": f"auto-install gh not supported on {system}"}

  script = ROOT / "scripts" / "install_github_tools.sh"
  if not script.exists():
    return {"installed": False, "error": "install_github_tools.sh missing"}

  proc = subprocess.run(["bash", str(script)], cwd=str(ROOT), capture_output=True, text=True)
  gh = find_gh()
  return {
    "installed": gh is not None,
    "path": gh,
    "stdout": (proc.stdout or "")[-1000:],
    "stderr": (proc.stderr or "")[-1000:],
  }


def configure_gh_auth() -> Dict[str, Any]:
  gh = find_gh()
  if not gh:
    return {"configured": False, "reason": "gh not found"}
  token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
  if not token:
    return {"configured": False, "reason": "no GITHUB_TOKEN/GH_TOKEN"}

  env = os.environ.copy()
  env["GH_TOKEN"] = token
  env["GITHUB_TOKEN"] = token
  status = subprocess.run([gh, "auth", "status"], capture_output=True, text=True, env=env)
  if status.returncode == 0:
    return {"configured": True, "action": "already_authenticated"}

  login = subprocess.run(
    [gh, "auth", "login", "--with-token"],
    input=token,
    capture_output=True,
    text=True,
    env=env,
  )
  return {
    "configured": login.returncode == 0,
    "action": "login",
    "stderr": (login.stderr or "")[-300:],
  }


def verify_imports() -> List[Dict[str, Any]]:
  py = venv_python()
  rows: List[Dict[str, Any]] = []
  for module, symbol in VERIFY_IMPORTS:
    code = f"from {module} import {symbol}; print('ok')"
    proc = _run([str(py), "-c", code])
    rows.append({
      "module": module,
      "symbol": symbol,
      "ok": proc.returncode == 0,
      "error": (proc.stderr or "").strip()[-200:] if proc.returncode != 0 else "",
    })
  return rows


def setup_environment(
  *,
  create_venv: bool = True,
  install_deps: bool = True,
  install_gh: bool = True,
  install_savers: bool = True,
  configure_auth: bool = True,
) -> Dict[str, Any]:
  """Full environment bootstrap for local dev, cloud agents, and CI."""
  result: Dict[str, Any] = {"root": str(ROOT), "steps": {}}

  if create_venv:
    result["steps"]["venv"] = ensure_venv()

  if install_deps:
    result["steps"]["github_libs"] = clone_github_libs()
    result["steps"]["requirements"] = install_requirements()
    result["steps"]["editable_libs"] = install_editable_libs()
    result["steps"]["runtime_extras"] = install_runtime_extras()

  if install_savers:
    result["steps"]["token_savers"] = install_token_savers()

  if install_gh:
    result["steps"]["gh_cli"] = install_gh_cli()

  if configure_auth:
    result["steps"]["gh_auth"] = configure_gh_auth()

  result["steps"]["verify"] = verify_imports()
  result["python"] = str(venv_python())
  result["gh"] = find_gh()
  result["ok"] = all(v.get("ok", True) for v in result["steps"]["verify"])
  return result


def main() -> None:
  upgrade = "--upgrade" in sys.argv
  skip_gh = "--skip-gh" in sys.argv
  skip_auth = "--skip-auth" in sys.argv
  skip_savers = "--skip-savers" in sys.argv

  if upgrade:
    pip_install("--upgrade", f"-r{ROOT / 'requirements.txt'}")

  out = setup_environment(
    install_gh=not skip_gh,
    install_savers=not skip_savers,
    configure_auth=not skip_auth,
  )
  print(json.dumps(out, indent=2))
  if not out.get("ok"):
    sys.exit(1)


if __name__ == "__main__":
  main()
