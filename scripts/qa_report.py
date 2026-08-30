#!/usr/bin/env python3
"""Kiểm tra chất lượng dữ liệu TDP đã thu thập."""
import csv
import json
import pathlib
import collections

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
SRC = ROOT / "sources" / "tdp"

# Con số dự kiến (theo báo chí / kế hoạch tỉnh) để đối chiếu độ phủ
EXPECTED = {"01": 2755, "25": 1722}


def main():
    wards = list(csv.DictReader(open(DATA / "wards.csv", encoding="utf-8")))
    tdp = list(csv.DictReader(open(DATA / "tdp.csv", encoding="utf-8")))
    by_ward = collections.Counter(r["ward_code"] for r in tdp)

    issues = []
    for fp in sorted(SRC.glob("*/*.json")):
        d = json.loads(fp.read_text(encoding="utf-8"))
        names = [t["name"] for t in d["tdp"]]
        wc = d["ward_code"]
        dup = [n for n, c in collections.Counter(names).items() if c > 1]
        if dup:
            issues.append(f"{wc} {d['ward_name']}: TDP trùng tên: {dup}")
        if not d.get("sources"):
            issues.append(f"{wc} {d['ward_name']}: thiếu nguồn")
        if d.get("arrangement") != "2026_07":
            issues.append(f"{wc} {d['ward_name']}: danh mục TRƯỚC 01/7/2026 ({len(names)} đơn vị) — cần cập nhật theo nghị quyết HĐND xã")
        if any(len(n) > 40 for n in names):
            issues.append(f"{wc} {d['ward_name']}: tên TDP bất thường (quá dài)")

    meta = {m["ward_code"]: m for m in csv.DictReader(open(DATA / "tdp_ward_meta.csv", encoding="utf-8"))}
    for pc in ("01", "25"):
        pw = [w for w in wards if w["province_code"] == pc]
        cov = [w for w in pw if w["ward_code"] in by_ward]
        n = sum(by_ward[w["ward_code"]] for w in cov)
        cur = [w for w in cov if meta.get(w["ward_code"], {}).get("arrangement") == "2026_07"]
        ncur = sum(by_ward[w["ward_code"]] for w in cur)
        print(f"[{pc}] {len(cov)}/{len(pw)} phường/xã có dữ liệu · {n} đơn vị")
        print(f"     trong đó ĐÚNG mốc 01/7/2026: {len(cur)}/{len(pw)} phường/xã · {ncur} TDP "
              f"(dự kiến ~{EXPECTED[pc]}, đạt {100*ncur//EXPECTED[pc]}%)")

    print(f"\n{len(issues)} cảnh báo:")
    for i in issues:
        print("  -", i)


if __name__ == "__main__":
    main()
