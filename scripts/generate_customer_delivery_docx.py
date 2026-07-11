#!/usr/bin/env python3
"""Generate customer-facing delivery proposal Word document (v3.5)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from customer_md_to_docx import convert_markdown_file  # noqa: E402
from generate_customer_docx_pack import DOCS, MAIN_OUT  # noqa: E402


def main() -> None:
    md = DOCS / "ARIA-报价助手-正式版交付方案与报价（客户版）.md"
    out = convert_markdown_file(md, MAIN_OUT)
    if len(sys.argv) > 1:
        dest = Path(sys.argv[1])
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(out.read_bytes())
        print(f"Wrote {dest}")
    else:
        print(f"Wrote {out}")


if __name__ == "__main__":
    main()
