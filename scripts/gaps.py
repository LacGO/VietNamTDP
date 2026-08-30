#!/usr/bin/env python3
"""In danh sách phường/xã còn thiếu dữ liệu TDP đúng mốc 01/7/2026."""
import csv
import glob
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
wards = list(csv.DictReader(open(ROOT / "data" / "wards.csv", encoding="utf-8")))
have = {}
for f in glob.glob(str(ROOT / "sources" / "tdp" / "*" / "*.json")):
    d = json.load(open(f))
    have[d["ward_code"]] = d.get("arrangement", "?")

only = sys.argv[1] if len(sys.argv) > 1 else None
n = 0
for w in wards:
    if only and w["province_code"] != only:
        continue
    st = have.get(w["ward_code"])
    if st == "2026_07":
        continue
    n += 1
    tag = "MISSING" if st is None else f"OLD({st})"
    print(f"{w['province_code']} {w['ward_code']} {w['unit_type']:<7} {w['name']:<24} {tag}")
print(f"\n{n} phường/xã cần bổ sung")
