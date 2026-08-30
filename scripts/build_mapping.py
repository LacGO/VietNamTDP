#!/usr/bin/env python3
"""
Parse the UBTVQH resolutions (NQ 1656 – Hà Nội, NQ 1676 – Phú Thọ) into a
machine-readable "đơn vị cũ -> đơn vị mới" mapping at commune/ward level.

Input : sources/raw/nq1656_hanoi_mapping.txt
        sources/raw/nq1676_phutho_mapping.txt
Output: data/ward_mapping.csv / .json
        (new_ward_name, new_ward_type, province_code, relation, old_unit_type,
         old_unit_name, old_unit_qualifier, provision_no, source)

`relation` values:
  toan_bo            - toàn bộ diện tích + dân số
  mot_phan          - một phần diện tích + dân số
  mot_phan_dt       - một phần diện tích tự nhiên (of area only)
  mot_phan_dt_toanbo_ds - một phần diện tích, toàn bộ dân số
  phan_con_lai      - phần còn lại (sau khi sắp xếp ...)
"""
import csv
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import norm_name  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "sources" / "raw"
DATA = ROOT / "data"

FILES = [
    ("01", RAW / "nq1656_hanoi_mapping.txt", "NQ 1656/NQ-UBTVQH15"),
    ("25", RAW / "nq1676_phutho_mapping.txt", "NQ 1676/NQ-UBTVQH15"),
]

# markers ordered so longer/more specific patterns match first
MARKERS = [
    ("mot_phan_dt_toanbo_ds", "một phần diện tích tự nhiên, toàn bộ quy mô dân số của"),
    ("mot_phan", "một phần diện tích tự nhiên, quy mô dân số của"),
    ("mot_phan", "một phần diện tích tự nhiên quy mô dân số của"),
    ("mot_phan_dt", "một phần diện tích tự nhiên của"),
    ("toan_bo", "toàn bộ diện tích tự nhiên, quy mô dân số của"),
    ("toan_bo", "toàn bộ diện tích tự nhiên quy mô dân số của"),
    ("phan_con_lai", "phần còn lại của"),
]

NEW_NAME_RE = re.compile(
    r"thành (phường|xã) mới có tên gọi là (?:phường|xã)\s+(.+?)\.\s*$"
)
UNIT_RE = re.compile(
    r"(?:^|\s)(thị trấn|phường|xã)\s+([A-ZĐÀ-Ỹ][^,\.]*?)(?=\s+(?:và |các |một |toàn |phần |thành |sau |thị trấn |phường |xã )|,|\.|$)"
)


def clean_segment(seg: str) -> str:
    # drop trailing "sau khi sắp xếp theo quy định tại ... Điều này"
    seg = re.split(r"\s+sau khi sắp xếp theo quy định", seg)[0]
    return seg.strip(" ,")


def parse_units(segment: str):
    """Yield (unit_type, name, qualifier) from a component segment."""
    seg = clean_segment(segment)
    # Normalise "các xã A, B và C" / "các phường ..." → distribute the type
    results = []
    # capture explicit "(quận X)" / "(huyện Y)" qualifiers inline
    # First, split into chunks that each start with an optional type keyword
    # Strategy: tokenise on ', ' and ' và '
    parts = re.split(r",\s*|\s+và\s+", seg)
    current_type = None
    for p in parts:
        p = p.strip()
        if not p:
            continue
        m = re.match(r"^(các\s+)?(thị trấn|phường|xã)\s+(.*)$", p)
        if m:
            current_type = m.group(2)
            name = m.group(3).strip()
        else:
            name = p
        qualifier = ""
        qm = re.search(r"\(([^)]+)\)", name)
        if qm:
            qualifier = qm.group(1).strip()
            name = re.sub(r"\s*\([^)]*\)", "", name).strip()
        # strip leftover leading/trailing words
        name = re.sub(r"^(các|một phần|toàn bộ|phần còn lại)\s+", "", name).strip()
        name = re.sub(r"\s+(và|thành|sau)$", "", name).strip()
        if name and not re.match(r"^(diện tích|quy mô|dân số)", name):
            results.append((current_type or "", name, qualifier))
    return results


def parse_provision(line: str):
    m = NEW_NAME_RE.search(line)
    if not m:
        return None
    new_type, new_name = m.group(1), m.group(2).strip()
    body = line[: m.start()]
    body = re.sub(r"^\d+\.\s*", "", body)
    body = re.sub(r"^Sắp xếp\s+", "", body)

    # find all marker positions
    hits = []
    low = body.lower()
    for rel, phrase in MARKERS:
        start = 0
        while True:
            idx = low.find(phrase, start)
            if idx == -1:
                break
            hits.append((idx, idx + len(phrase), rel, phrase))
            start = idx + len(phrase)
    hits.sort()
    # remove overlapping shorter matches (e.g. inside a longer phrase)
    filtered = []
    for h in hits:
        if filtered and h[0] < filtered[-1][1]:
            continue
        filtered.append(h)

    comps = []
    for i, (s, e, rel, phrase) in enumerate(filtered):
        seg_end = filtered[i + 1][0] if i + 1 < len(filtered) else len(body)
        segment = body[e:seg_end]
        for utype, uname, qual in parse_units(segment):
            comps.append((rel, utype, uname, qual))
    return new_type, new_name, comps


def main():
    rows = []
    for province_code, path, src in FILES:
        text = path.read_text(encoding="utf-8")
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not re.match(r"^\d+\.\s", line):
                continue
            prov_no = int(line.split(".", 1)[0])
            parsed = parse_provision(line)
            if not parsed:
                continue
            new_type, new_name, comps = parsed
            new_name = re.sub(r"\s+(và|thành)$", "", new_name).strip()
            for rel, utype, uname, qual in comps:
                rows.append(
                    {
                        "province_code": province_code,
                        "new_ward_name": new_name,
                        "new_ward_type": new_type,
                        "relation": rel,
                        "old_unit_type": utype,
                        "old_unit_name": uname,
                        "old_unit_qualifier": qual,
                        "provision_no": prov_no,
                        "source": src,
                    }
                )
    # 2 communes of Phú Thọ kept unchanged (not in the numbered provisions)
    for name in ("Thu Cúc", "Trung Sơn"):
        rows.append(
            {
                "province_code": "25",
                "new_ward_name": name,
                "new_ward_type": "xã",
                "relation": "giu_nguyen",
                "old_unit_type": "xã",
                "old_unit_name": name,
                "old_unit_qualifier": "",
                "provision_no": 0,
                "source": "NQ 1676/NQ-UBTVQH15",
            }
        )

    # attach the official new-ward code (join by normalised name within province)
    wards = list(csv.DictReader(open(DATA / "wards.csv", encoding="utf-8")))
    widx = {}
    for w in wards:
        widx[(w["province_code"], norm_name(w["name"]))] = w["ward_code"]
    unmatched = set()
    for r in rows:
        key = (r["province_code"], norm_name(r["new_ward_name"]))
        r["new_ward_code"] = widx.get(key, "")
        if not r["new_ward_code"]:
            unmatched.add((r["province_code"], r["new_ward_name"]))
    if unmatched:
        print(f"WARNING: {len(unmatched)} new wards without code: {sorted(unmatched)}")

    fieldnames = [
        "province_code", "new_ward_code", "new_ward_name", "new_ward_type",
        "relation", "old_unit_type", "old_unit_name", "old_unit_qualifier",
        "provision_no", "source",
    ]
    with open(DATA / "ward_mapping.csv", "w", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, fieldnames=fieldnames)
        wr.writeheader()
        wr.writerows(rows)
    (DATA / "ward_mapping.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    # quick sanity report
    from collections import defaultdict

    by_new = defaultdict(set)
    for r in rows:
        by_new[(r["province_code"], r["new_ward_name"])].add(r["provision_no"])
    print(f"mapping rows: {len(rows)}")
    print(f"distinct new wards covered: {len(by_new)}")
    for pc in ("01", "25"):
        n = len({k for k in by_new if k[0] == pc})
        print(f"  province {pc}: {n} new wards")
    # show one sample
    sample = [r for r in rows if r["new_ward_name"] == "Hoàn Kiếm"]
    for r in sample:
        print("   ", r["relation"], r["old_unit_type"], r["old_unit_name"], r["old_unit_qualifier"])


if __name__ == "__main__":
    main()
