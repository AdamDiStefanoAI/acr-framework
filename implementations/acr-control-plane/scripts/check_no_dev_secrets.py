#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

DEV_SECRET_PATTERNS = {
    "dev_jwt_secret_change_in_production",
    "killswitch_dev_secret_change_me",
    "dev_operator_session_secret_change_me",
    "dev-operator-key",
    "acr_dev_password",
}

SCAN_PATHS = (
    Path("deploy"),
    Path(".env.production.example"),
    Path("docs"),
)

ALLOWLIST_FILES = {
    Path("docs/configuration.md"),
    Path("README.md"),
    Path(".env.example"),
    Path("docker-compose.yml"),
}


def main() -> int:
    failures: list[str] = []
    for scan_path in SCAN_PATHS:
        if not scan_path.exists():
            continue
        files = [scan_path] if scan_path.is_file() else [p for p in scan_path.rglob("*") if p.is_file()]
        for file_path in files:
            if file_path in ALLOWLIST_FILES:
                continue
            text = file_path.read_text(encoding="utf-8")
            for pattern in DEV_SECRET_PATTERNS:
                if pattern in text:
                    failures.append(f"{file_path}: contains forbidden dev secret pattern '{pattern}'")

    if failures:
        print("Dev secret leakage check failed:")
        for failure in failures:
            print(f" - {failure}")
        return 1

    print("No forbidden dev secret patterns found in production-facing paths.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
