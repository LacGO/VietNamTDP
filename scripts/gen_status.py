#!/usr/bin/env python3
"""Generate docs/STATUS.md — TDP collection coverage tracker."""
import csv
import datetime
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = ROOT / "docs" / "STATUS.md"


def load(n):
    return list(csv.DictReader(open(DATA / n, encoding="utf-8")))


def main():
    wards = load("wards.csv")
    meta = {m["ward_code"]: m for m in load("tdp_ward_meta.csv")}
    prov = {p["province_code"]: p for p in load("provinces.csv")}

    lines = [
        "# Tình trạng thu thập dữ liệu Tổ dân phố / Thôn",
        "",
        f"_Cập nhật: {datetime.date.today().isoformat()} — sinh tự động bằng `scripts/gen_status.py`._",
        "",
        "Mức xác minh: `primary` = trích từ nghị quyết HĐND cấp xã / công báo tỉnh · "
        "`partial` = báo chí / Wikipedia dẫn nguồn · `unverified` = cần đối chiếu · "
        "`pending` = chưa có dữ liệu.",
        "",
    ]

    for pc in ("01", "25"):
        pw = [w for w in wards if w["province_code"] == pc]
        listed = [w for w in pw if int(meta.get(w["ward_code"], {}).get("tdp_count", 0)) > 0]
        cur = [w for w in listed if meta[w["ward_code"]].get("arrangement") == "2026_07"]
        count_only = [w for w in pw if w["ward_code"] in meta and w not in listed]
        n_tdp = sum(int(meta[w["ward_code"]]["tdp_count"]) for w in listed)
        n_cur = sum(int(meta[w["ward_code"]]["tdp_count"]) for w in cur)
        lines += [
            f"## {prov[pc]['full_name']} (`{pc}`)",
            "",
            f"- Phường/xã: **{len(pw)}**",
            f"- Có **danh mục tên** TDP: **{len(listed)}/{len(pw)}** — {n_tdp} đơn vị",
            f"- **Đúng mốc 01/7/2026** (có tên): **{len(cur)}/{len(pw)}** — {n_cur} TDP",
            f"- Mới có số lượng, chưa có tên: {len(count_only)} · chưa có gì: {len(pw)-len(listed)-len(count_only)}",
            "",
            "| Mã | Phường/Xã | Loại | Số TDP | Mốc | Xác minh | Nguồn |",
            "|----|-----------|------|-------:|-----|----------|-------|",
        ]
        for w in sorted(pw, key=lambda x: x["ward_code"]):
            m = meta.get(w["ward_code"])
            if m:
                arr = "✅ 01/7/2026" if m.get("arrangement") == "2026_07" else "⚠️ trước 01/7/2026"
                src = (m["resolution"] or m["source_keys"] or "")[:70]
                cnt = m["tdp_count"]
                if cnt == "0" and m.get("approx_count"):
                    cnt = f"~{m['approx_count']} (chưa có tên)"
                    arr = "⛔ chưa có danh mục"
                lines.append(
                    f"| {w['ward_code']} | {w['name']} | {w['unit_type']} | "
                    f"{cnt} | {arr} | {m['verified']} | {src} |"
                )
            else:
                lines.append(
                    f"| {w['ward_code']} | {w['name']} | {w['unit_type']} | — | — | pending | |"
                )
        lines.append("")

    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"-> {OUT}")


if __name__ == "__main__":
    main()
