#!/usr/bin/env python3
"""Generate customer-facing delivery proposal Word document (v3.5)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from generate_customer_docx_pack import build_main_proposal  # noqa: E402


def main() -> None:
    out = build_main_proposal()
    if len(sys.argv) > 1:
        # Legacy: custom output path — build then copy
        dest = Path(sys.argv[1])
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(out.read_bytes())
        print(f"Wrote {dest}")
    else:
        print(f"Wrote {out}")


if __name__ == "__main__":
    main()
