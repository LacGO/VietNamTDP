#!/usr/bin/env python3
"""
Compile per-ward TDP source files (sources/tdp/<province_code>/<ward_code>_*.json)
into data/tdp.csv and data/tdp.json, and data/tdp_sources.csv.

Generated code scheme:  <ward_code>.<seq:03d>   e.g. 00070.001
"""
import csv
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import slugify  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "sources" / "tdp"
DATA = ROOT / "data"

VALID_VERIFIED = {"primary", "partial", "unverified", "pending"}


def main():
    wards = {w["ward_code"]: w for w in csv.DictReader(open(DATA / "wards.csv", encoding="utf-8"))}

    tdp_rows, source_rows, meta_rows = [], [], []
    seen_sources = set()
    files = sorted(SRC.glob("*/*.json"))
    for fp in files:
        d = json.loads(fp.read_text(encoding="utf-8"))
        wc = d["ward_code"]
        if wc not in wards:
            raise SystemExit(f"{fp}: unknown ward_code {wc}")
        pc = wards[wc]["province_code"]
        verified = d.get("verified", "pending")
        if verified not in VALID_VERIFIED:
            raise SystemExit(f"{fp}: bad verified={verified}")
        eff = d.get("effective_date", "")
        src_keys = [s["key"] for s in d.get("sources", [])]
        for s in d.get("sources", []):
            if s["key"] not in seen_sources:
                seen_sources.add(s["key"])
                source_rows.append(
                    {
                        "source_key": s["key"],
                        "title": s.get("title", ""),
                        "url": s.get("url", ""),
                        "date": s.get("date", ""),
                        "type": s.get("type", ""),
                        "via": s.get("via", ""),
                    }
                )
        arr = d.get("arrangement", "unknown")
        meta_rows.append(
            {
                "ward_code": wc,
                "province_code": pc,
                "tdp_count": len(d.get("tdp", [])),
                "arrangement": arr,
                "resolution": d.get("resolution", ""),
                "effective_date": eff,
                "verified": verified,
                "source_keys": ";".join(src_keys),
                "note": d.get("note", ""),
            }
        )
        for i, t in enumerate(d.get("tdp", []), start=1):
            unit = t.get("type", "tổ dân phố")
            # name = phần định danh (bỏ tiền tố loại đơn vị nếu có)
            name = re.sub(r"\s*\((?:sắp xếp|sáp nhập|hợp nhất|gồm|trên cơ sở|đổi tên)[^)]*\)",
                          "", t["name"], flags=re.I).strip()
            name = re.sub(r"^(Tổ dân phố|Tổ dân số|Thôn|Khu phố|Khu|Bản|Xóm|Làng)\s+",
                          "", name, flags=re.I).strip()
            name = re.sub(r"^số\s+", "", name).strip() or t["name"]
            full = f"{unit[0].upper()}{unit[1:]} {name}"
            tdp_rows.append(
                {
                    "tdp_code": f"{wc}.{i:03d}",
                    "ward_code": wc,
                    "province_code": pc,
                    "name": name,
                    "full_name": full,
                    "unit_type": unit,
                    "code_name": slugify(name),
                    "seq": i,
                    "arrangement": arr,
                    "verified": verified,
                    "effective_date": eff,
                }
            )

    tdp_rows.sort(key=lambda r: r["tdp_code"])
    meta_rows.sort(key=lambda r: r["ward_code"])
    _write_csv(DATA / "tdp.csv", tdp_rows)
    _write_csv(DATA / "tdp_ward_meta.csv", meta_rows)
    _write_csv(DATA / "tdp_sources.csv", source_rows)
    (DATA / "tdp.json").write_text(
        json.dumps(tdp_rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    covered = {r["ward_code"] for r in tdp_rows}
    for pc in ("01", "25"):
        total = sum(1 for w in wards.values() if w["province_code"] == pc)
        cov = sum(1 for wc in covered if wards[wc]["province_code"] == pc)
        n = sum(1 for r in tdp_rows if r["province_code"] == pc)
        print(f"province {pc}: {n} TDP across {cov}/{total} phường/xã")


def _write_csv(path, rows):
    if not rows:
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        wr.writeheader()
        wr.writerows(rows)


if __name__ == "__main__":
    main()
