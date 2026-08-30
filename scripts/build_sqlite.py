#!/usr/bin/env python3
"""Build db/vietnam_tdp.sqlite from db/schema.sql + data/*.csv."""
import csv
import pathlib
import sqlite3

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DB = ROOT / "db" / "vietnam_tdp.sqlite"
SCHEMA = ROOT / "db" / "schema.sql"


def rows(name):
    return list(csv.DictReader(open(DATA / name, encoding="utf-8")))


def insert(cur, table, records, cols):
    if not records:
        return
    ph = ",".join("?" * len(cols))
    cur.executemany(
        f"INSERT INTO {table} ({','.join(cols)}) VALUES ({ph})",
        [[r.get(c, "") for c in cols] for r in records],
    )


def main():
    if DB.exists():
        DB.unlink()
    con = sqlite3.connect(DB)
    con.executescript(SCHEMA.read_text(encoding="utf-8"))
    cur = con.cursor()

    insert(cur, "province", rows("provinces.csv"),
           ["province_code", "name", "full_name", "name_en", "full_name_en",
            "code_name", "unit_type", "postal_prefix"])
    insert(cur, "ward", rows("wards.csv"),
           ["ward_code", "province_code", "name", "full_name", "name_en",
            "full_name_en", "code_name", "unit_type", "postal_code"])
    insert(cur, "tdp", rows("tdp.csv"),
           ["tdp_code", "ward_code", "province_code", "name", "unit_type",
            "code_name", "seq", "arrangement", "verified", "effective_date"])
    insert(cur, "tdp_ward_meta", rows("tdp_ward_meta.csv"),
           ["ward_code", "province_code", "tdp_count", "arrangement", "resolution",
            "effective_date", "verified", "source_keys", "note"])
    try:
        insert(cur, "tdp_source", rows("tdp_sources.csv"),
               ["source_key", "title", "url", "date", "type", "via"])
    except FileNotFoundError:
        pass
    insert(cur, "ward_mapping", rows("ward_mapping.csv"),
           ["province_code", "new_ward_code", "new_ward_name", "new_ward_type",
            "relation", "old_unit_type", "old_unit_name", "old_unit_qualifier",
            "provision_no", "source"])

    con.commit()
    for t in ("province", "ward", "tdp", "tdp_ward_meta", "ward_mapping"):
        n = cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f"{t}: {n}")
    con.close()
    print(f"-> {DB}")


if __name__ == "__main__":
    main()
