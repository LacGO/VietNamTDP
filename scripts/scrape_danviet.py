#!/usr/bin/env python3
"""
Trích danh mục thôn/TDP mới từ bài Báo Dân Việt (danviet.vn) — chuyên mục
"Sáp nhập thôn, tổ dân phố". Các bài này thường nhúng TOÀN VĂN nghị quyết HĐND cấp xã.

  python3 scripts/scrape_danviet.py <ward_code> <danviet_url> [--dry] [--verified primary]
"""
import argparse
import csv
import html
import json
import pathlib
import re
import sys
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import slugify, canon_tone  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "sources" / "tdp"
UA = "Mozilla/5.0 (VietNamTDP)"

U = r"(thôn|tổ dân phố|khu phố)"
PATTERNS = [
    re.compile(r"để thành lập " + U + r"\s+([^;.\n]+?)[;.\n]", re.I),
    re.compile(r"thành lập " + U + r"\s+([^;.\n]+?)\s+trên cơ sở", re.I),
    re.compile(r"[Đđ]ổi tên (?:xóm|khu|thôn|khu phố|tổ dân phố)[^;\n]+? thành " + U + r"\s+([^;.\n]+?)[;.\n]", re.I),
    re.compile(r"giữ nguyên (?:xóm|khu|thôn)[^;\n]+?,?\s*(?:đổi tên (?:thành )?)?" + U + r"\s+([^;.\n]+?)[;.\n]", re.I),
    re.compile(r"(?:xóm|khu)[^;\n]+? nay mang tên " + U + r"\s+([^;.\n]+?)[;.\n]", re.I),
]
STOP = re.compile(r"(sau (?:khi )?sắp xếp|trên cơ sở|hiện có|trước sắp xếp|cũ\b)", re.I)


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    return urllib.request.urlopen(req, timeout=45).read().decode("utf-8", "replace")


def article_text(htmltext):
    b = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", htmltext, flags=re.S)
    b = re.sub(r"<[^>]+>", "\n", b)
    b = html.unescape(b)
    b = re.sub(r"[ \t]+", " ", b)
    lines = [l.strip() for l in b.splitlines() if l.strip()]
    # vùng nghị quyết: từ "QUYẾT NGHỊ" / "Điều 1" đến "Điều 2"/"Điều 3"/"Nơi nhận"
    s = next((i for i, l in enumerate(lines)
              if re.search(r"QUYẾT NGHỊ|^Điều 1\.", l)), 0)
    e = next((i for i, l in enumerate(lines[s + 1:], s + 1)
              if re.search(r"^Điều [2-9]\.|Nơi nhận:|TM\. HỘI ĐỒNG", l)), min(len(lines), s + 120))
    return "\n".join(lines[s:e]) if s else "\n".join(lines)


def extract(txt):
    names = []
    for rx in PATTERNS:
        for m in rx.finditer(txt):
            n = m.group(2).strip(" ,.;\"'()")
            n = re.split(r"\s+(?:với|và|trên|thuộc)\b", n)[0].strip()
            if n and not STOP.search(n) and len(n) <= 40:
                names.append(n)
    # dedupe giữ thứ tự
    seen, out = set(), []
    for n in names:
        k = canon_tone(n).lower()
        if k not in seen:
            seen.add(k)
            out.append(n)
    return out


def res_no(txt):
    m = re.search(r"Nghị quyết số\s+([\dA-Za-zĐ/\-]+)[^\n]{0,50}?ngày\s+(\d+)"
                  r"[^\n]{0,6}tháng\s+(\d+)[^\n]{0,6}năm\s+(\d+)", txt)
    if m:
        return f"Nghị quyết số {m.group(1)} ngày {int(m.group(2)):02d}/{int(m.group(3)):02d}/{m.group(4)} HĐND cấp xã"
    m = re.search(r"Đề án số\s+([\dA-Za-zĐ/\-]+)[^\n]{0,40}?ngày\s+(\d+)[^\n]{0,6}tháng\s+(\d+)[^\n]{0,6}năm\s+(\d+)", txt)
    if m:
        return f"Đề án số {m.group(1)} ngày {int(m.group(2)):02d}/{int(m.group(3)):02d}/{m.group(4)} UBND cấp xã"
    return ""


def target_count(txt):
    m = re.search(r"thành lập\s+(\d+)\s+" + U, txt, re.I) or \
        re.search(r"còn\s+(\d+)\s+" + U, txt, re.I) or \
        re.search(r"(\d+)\s+" + U + r"\s+(?:mới|trên địa bàn)", txt, re.I)
    return int(m.group(1)) if m else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ward_code")
    ap.add_argument("url")
    ap.add_argument("--verified", default="primary")
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    wards = {w["ward_code"]: w for w in csv.DictReader(open(ROOT / "data" / "wards.csv", encoding="utf-8"))}
    w = wards[a.ward_code]
    pc = w["province_code"]

    raw = fetch(a.url)
    txt = article_text(raw)
    names = extract(txt)
    tgt = target_count(txt)
    unit = "tổ dân phố" if ("tổ dân phố" in txt[:400].lower() and w["unit_type"] == "Phường") else \
           ("tổ dân phố" if w["unit_type"] == "Phường" else "thôn")
    print(f"{w['full_name']}: trích {len(names)} {unit} (mục tiêu ~{tgt}) | {res_no(txt)!r}")
    print("  ", names)
    if tgt and abs(len(names) - tgt) > 2:
        print(f"  ⚠️ lệch mục tiêu ({len(names)} vs {tgt}) — kiểm tra thủ công")
    if a.dry or not names:
        return
    obj = {
        "ward_code": a.ward_code, "ward_name": w["name"], "province_code": pc,
        "resolution": res_no(txt), "arrangement": "2026_07",
        "effective_date": "2026-07-01", "verified": a.verified,
        "extraction": {"source": "danviet.vn", "url": a.url, "mode": "danviet-fulltext"},
        "sources": [{"key": f"danviet-{a.ward_code}",
                     "title": f"Sáp nhập thôn/TDP — {w['full_name']} (Báo Dân Việt)",
                     "url": a.url, "date": "2026", "type": "bao"}],
        "note": f"{len(names)} {unit} sau sắp xếp 01/7/2026; trích từ toàn văn nghị quyết HĐND cấp xã đăng trên Báo Dân Việt.",
        "tdp": [{"name": n, "type": unit} for n in names],
    }
    (OUT / pc).mkdir(parents=True, exist_ok=True)
    p = OUT / pc / f"{a.ward_code}_{slugify(w['name'])}.json"
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("  ->", p)


if __name__ == "__main__":
    main()
