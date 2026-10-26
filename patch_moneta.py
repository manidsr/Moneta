#!/usr/bin/env python3
"""Fix: Blu 'charge' SMS ("... ریال بابت خرید شارژ از حساب شما پرید") was not parsed.

Run from the folder containing moneta_phone (or inside it):
    python patch_fix_charge.py            apply
    python patch_fix_charge.py --undo     restore lib/parser.dart.fixbak
"""
import shutil
import sys
from pathlib import Path

OLD = r"RegExp(r'([\d,]+)\s*ریال\s*(از حساب شما پرید|به حساب شما نشست)')"
NEW = r"RegExp(r'([\d,]+)\s*ریال\s*(?:بابت\s+.+?\s+)?(از حساب شما پرید|به حساب شما نشست)')"


def main() -> int:
    root = Path(".").resolve()
    app = root if (root / "lib" / "parser.dart").exists() else root / "moneta_phone"
    p = app / "lib" / "parser.dart"
    if not p.exists():
        print("ERROR: lib/parser.dart not found. Run from the folder containing moneta_phone.")
        return 1
    bak = p.with_name("parser.dart.fixbak")

    if "--undo" in sys.argv:
        if bak.exists():
            shutil.copy2(bak, p)
            print("restored", p)
            return 0
        print("no backup found")
        return 1

    with open(p, encoding="utf-8", newline="") as f:
        t = f.read()
    if NEW in t:
        print("already fixed, nothing to do")
        return 0
    if OLD not in t:
        print("ERROR: expected regex not found in parser.dart (was patch_moneta.py applied?)")
        return 1
    if not bak.exists():
        shutil.copy2(p, bak)
    with open(p, "w", encoding="utf-8", newline="") as f:
        f.write(t.replace(OLD, NEW))
    print("patched", p)
    print("Next: flutter test test/parser_test.dart")
    return 0


if __name__ == "__main__":
    sys.exit(main())