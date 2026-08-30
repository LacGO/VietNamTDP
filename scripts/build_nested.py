#!/usr/bin/env python3
"""Build nested tree JSON per province: json/<code_name>.json  (tỉnh > phường/xã > TDP)."""
import csv
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = ROOT / "json"
OUT.mkdir(exist_ok=True)


def load(name):
    return list(csv.DictReader(open(DATA / name, encoding="utf-8")))


def main():
    provinces = load("provinces.csv")
    wards = load("wards.csv")
    tdp = load("tdp.csv")

    tdp_by_ward = {}
    for t in tdp:
        tdp_by_ward.setdefault(t["ward_code"], []).append(
            {"tdp_code": t["tdp_code"], "name": t["name"], "unit_type": t["unit_type"]}
        )

    wards_by_prov = {}
    for w in wards:
        wards_by_prov.setdefault(w["province_code"], []).append(w)

    index = []
    for p in provinces:
        node = {
            "province_code": p["province_code"],
            "name": p["name"],
            "full_name": p["full_name"],
            "name_en": p["name_en"],
            "wards": [],
        }
        for w in wards_by_prov.get(p["province_code"], []):
            node["wards"].append(
                {
                    "ward_code": w["ward_code"],
                    "name": w["name"],
                    "full_name": w["full_name"],
                    "unit_type": w["unit_type"],
                    "tdp": tdp_by_ward.get(w["ward_code"], []),
                }
            )
        path = OUT / f"{p['code_name']}.json"
        path.write_text(json.dumps(node, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        index.append({"province_code": p["province_code"], "file": path.name,
                      "wards": len(node["wards"]),
                      "tdp": sum(len(w["tdp"]) for w in node["wards"])})
        print(f"{path.name}: {index[-1]['wards']} phường/xã, {index[-1]['tdp']} TDP")
    (OUT / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
