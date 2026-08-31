#!/usr/bin/env python3
"""
Sinh file Markdown danh sách Tổ dân phố / Thôn, chia theo phường/xã của từng tỉnh:
  docs/danh-sach-tdp/ha-noi.md
  docs/danh-sach-tdp/phu-tho.md
  docs/danh-sach-tdp/README.md   (mục lục)
"""
import csv
import datetime
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = ROOT / "docs" / "danh-sach-tdp"
OUT.mkdir(parents=True, exist_ok=True)


def load(n):
    return list(csv.DictReader(open(DATA / n, encoding="utf-8")))


def main():
    provinces = {p["province_code"]: p for p in load("provinces.csv")}
    wards = load("wards.csv")
    tdp = load("tdp.csv")
    meta = {m["ward_code"]: m for m in load("tdp_ward_meta.csv")}
    sources = {s["source_key"]: s for s in load("tdp_sources.csv")}

    tdp_by_ward = {}
    for t in tdp:
        tdp_by_ward.setdefault(t["ward_code"], []).append(t)

    today = datetime.date.today().isoformat()
    index = ["# Danh sách Tổ dân phố / Thôn theo phường/xã", "",
             f"_Sinh tự động bằng `scripts/gen_tdp_lists.py` — cập nhật {today}._", ""]

    for pc in ("01", "25"):
        p = provinces[pc]
        pw = [w for w in wards if w["province_code"] == pc]
        fname = p["code_name"].replace("_", "-") + ".md"
        done = [w for w in pw if w["ward_code"] in meta]
        cur = [w for w in done if meta[w["ward_code"]].get("arrangement") == "2026_07"]
        n_tdp = sum(len(tdp_by_ward.get(w["ward_code"], [])) for w in pw)

        L = [
            f"# Danh sách Tổ dân phố / Thôn — {p['full_name']}", "",
            f"_Cập nhật {today}. Mốc: ✅ = đúng bộ máy 01/7/2026 · ⚠️ = hiện trạng trước 01/7/2026 · ⛔ = chưa có._",
            "",
            f"- Phường/xã: **{len(pw)}** · có dữ liệu: **{len(done)}** · đúng mốc 01/7/2026: **{len(cur)}** · tổng đơn vị: **{n_tdp}**",
            "",
            "## Mục lục", "",
            "| Mã | Phường/Xã | Loại | Số | Mốc |",
            "|----|-----------|------|---:|-----|",
        ]
        for w in sorted(pw, key=lambda x: x["ward_code"]):
            m = meta.get(w["ward_code"])
            cnt = len(tdp_by_ward.get(w["ward_code"], []))
            mark = "⛔" if not m else ("✅" if m.get("arrangement") == "2026_07" else "⚠️")
            anchor = w["ward_code"]
            L.append(f"| [{w['ward_code']}](#{anchor}) | {w['name']} | {w['unit_type']} | "
                     f"{cnt if cnt else '—'} | {mark} |")
        L.append("")

        for w in sorted(pw, key=lambda x: x["ward_code"]):
            wc = w["ward_code"]
            m = meta.get(wc)
            items = tdp_by_ward.get(wc, [])
            L.append(f'<a id="{wc}"></a>')
            L.append(f"## {w['unit_type']} {w['name']} — `{wc}`")
            L.append("")
            if not m:
                L += ["> ⛔ **Chưa có dữ liệu tổ dân phố.** Chưa tìm thấy nghị quyết HĐND cấp xã công bố công khai.", ""]
                continue
            arr = "✅ đúng bộ máy 01/7/2026" if m.get("arrangement") == "2026_07" \
                else "⚠️ danh mục hiện trạng TRƯỚC 01/7/2026 (chờ nghị quyết mới)"
            L.append(f"- **Số lượng:** {m['tdp_count']}  ·  **Mốc:** {arr}  ·  **Mức xác minh:** `{m['verified']}`")
            if m.get("resolution"):
                L.append(f"- **Văn bản:** {m['resolution']}")
            for sk in (m.get("source_keys") or "").split(";"):
                s = sources.get(sk)
                if s and s.get("url"):
                    L.append(f"- **Nguồn:** [{s.get('title') or sk}]({s['url']})")
            if m.get("note"):
                L.append(f"- _{m['note']}_")
            L.append("")
            if items:
                L.append("| # | Tên đầy đủ | Định danh | Mã |")
                L.append("|--:|-----------|-----------|----|")
                for t in items:
                    L.append(f"| {t['seq']} | {t['full_name']} | {t['name']} | `{t['tdp_code']}` |")
                L.append("")

        (OUT / fname).write_text("\n".join(L) + "\n", encoding="utf-8")
        index.append(f"- [{p['full_name']}]({fname}) — {len(pw)} phường/xã, {n_tdp} đơn vị "
                     f"(đúng mốc 01/7/2026: {len(cur)})")
        print(f"-> docs/danh-sach-tdp/{fname}")

    (OUT / "README.md").write_text("\n".join(index) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
