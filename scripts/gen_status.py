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
        done = [w for w in pw if w["ward_code"] in meta]
        cur = [w for w in done if meta[w["ward_code"]].get("arrangement") == "2026_07"]
        n_tdp = sum(int(meta[w["ward_code"]]["tdp_count"]) for w in done)
        n_cur = sum(int(meta[w["ward_code"]]["tdp_count"]) for w in cur)
        lines += [
            f"## {prov[pc]['full_name']} (`{pc}`)",
            "",
            f"- Phường/xã: **{len(pw)}**",
            f"- Có dữ liệu TDP: **{len(done)}/{len(pw)}** ({100*len(done)//len(pw)}%) — {n_tdp} đơn vị",
            f"- **Đúng mốc 01/7/2026**: **{len(cur)}/{len(pw)}** phường/xã — {n_cur} TDP",
            "",
            "| Mã | Phường/Xã | Loại | Số TDP | Mốc | Xác minh | Nguồn |",
            "|----|-----------|------|-------:|-----|----------|-------|",
        ]
        for w in sorted(pw, key=lambda x: x["ward_code"]):
            m = meta.get(w["ward_code"])
            if m:
                arr = "✅ 01/7/2026" if m.get("arrangement") == "2026_07" else "⚠️ trước 01/7/2026"
                src = (m["resolution"] or m["source_keys"] or "")[:70]
                lines.append(
                    f"| {w['ward_code']} | {w['name']} | {w['unit_type']} | "
                    f"{m['tdp_count']} | {arr} | {m['verified']} | {src} |"
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
