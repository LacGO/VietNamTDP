#!/usr/bin/env python3
"""
Build cấp tỉnh + cấp phường/xã tables from the raw source snapshot
(sources/raw/prov_*.json, extracted from GSO / thanglequoc dataset).

Outputs:
  data/provinces.csv, data/provinces.json
  data/wards.csv,     data/wards.json
"""
import csv
import json
import pathlib
import unicodedata

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "sources" / "raw"
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)

PROV_CODES = ["01", "25"]  # Hà Nội, Phú Thọ (mới)


def slugify(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.replace("Đ", "D").replace("đ", "d")
    return "_".join(s.lower().split())


def load():
    provinces, wards = [], []
    for code in PROV_CODES:
        p = json.loads((RAW / f"prov_{code}.json").read_text(encoding="utf-8"))
        provinces.append(
            {
                "province_code": p["Code"],
                "name": p["Name"],
                "full_name": p["FullName"],
                "name_en": p["NameEn"],
                "full_name_en": p["FullNameEn"],
                "code_name": p["CodeName"],
                "unit_type": p["AdministrativeUnitFullName"],
                "postal_prefix": p.get("PostalCodePrefix", ""),
                "ward_count": len(p["Wards"]),
            }
        )
        for w in p["Wards"]:
            wards.append(
                {
                    "ward_code": w["Code"],
                    "province_code": p["Code"],
                    "name": w["Name"],
                    "full_name": w["FullName"],
                    "name_en": w["NameEn"],
                    "full_name_en": w["FullNameEn"],
                    "code_name": w["CodeName"],
                    "unit_type": w["AdministrativeUnitShortName"],  # Phường / Xã
                    "postal_code": w.get("PostalCode", ""),
                }
            )
    wards.sort(key=lambda x: x["ward_code"])
    return provinces, wards


def write_csv(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        wr.writeheader()
        wr.writerows(rows)


def main():
    provinces, wards = load()
    write_csv(DATA / "provinces.csv", provinces)
    write_csv(DATA / "wards.csv", wards)
    (DATA / "provinces.json").write_text(
        json.dumps(provinces, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (DATA / "wards.json").write_text(
        json.dumps(wards, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"provinces: {len(provinces)}")
    for p in provinces:
        print(f"  {p['province_code']} {p['full_name']}: {p['ward_count']} phường/xã")
    print(f"wards: {len(wards)}")


if __name__ == "__main__":
    main()
