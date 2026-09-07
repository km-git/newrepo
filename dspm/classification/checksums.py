"""AU TFN, AU ABN, and UK NHS checksum helpers used by custom_types + classification."""

from __future__ import annotations

import re


def digits_only(value: str) -> str:
    return re.sub(r"\D", "", value or "")


def tfn_plausible(value: str) -> bool:
    n = digits_only(value)
    return len(n) in {8, 9}


def abn_checksum_ok(value: str) -> bool:
    n = digits_only(value)
    if len(n) != 11:
        return False
    weights = (10, 1, 3, 5, 7, 9, 11, 13, 15, 17, 19)
    digits = [int(ch) for ch in n]
    digits[0] -= 1
    total = sum(d * w for d, w in zip(digits, weights, strict=True))
    return total % 89 == 0


def nhs_checksum_ok(value: str) -> bool:
    n = digits_only(value)
    if len(n) != 10:
        return False
    total = sum(int(n[i]) * (10 - i) for i in range(9))
    remainder = total % 11
    check = 11 - remainder
    if check == 11:
        check = 0
    if check == 10:
        return False
    return check == int(n[9])
