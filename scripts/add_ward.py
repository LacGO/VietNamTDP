#!/usr/bin/env python3
"""
Thêm/cập nhật dữ liệu TDP cho 1 phường/xã từ 1 URL (trang bài hoặc PDF trực tiếp).

  python3 scripts/add_ward.py <ward_code> <url> [--pdf <pdf_url>] [--title "..."]
        [--resolution "..."] [--verified primary|partial] [--unit "tổ dân phố"|"thôn"]
        [--names "A;B;C"]  [--range N]  [--dry]

- Không có --pdf/--names: tự tải <url>, nếu là PDF thì parse; nếu là HTML thì tìm link .pdf
  đầu tiên khớp "thôn/tổ dân phố" + "sắp xếp/đổi tên".
- --range N: sinh "1".."N".
"""
import argparse
import csv
import json
import pathlib
import re
import sys
import urllib.parse
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import slugify, canon_tone  # noqa: E402

try:
    import fitz
except ImportError:
    fitz = None

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "sources" / "tdp"
UA = "Mozilla/5.0 (VietNamTDP)"

SKIP = re.compile(r"(trước sắp xếp|trước đổi tên|sau sắp xếp|sau đổi tên|giữ nguyên,|"
                  r"^tên (thôn|tổ)|^stt|chưa sắp xếp|^ghi chú)", re.I)
NAME = re.compile(r"^(Thôn|Tổ dân phố|Tổ dân phố số|Khu phố)\s+([^\n,]{1,55})$")


def get(url, binary=False):
    u = urllib.parse.quote(url, safe=":/?&=%#")
    req = urllib.request.Request(u, headers={"User-Agent": UA})
    d = urllib.request.urlopen(req, timeout=60).read()
    return d if binary else d.decode("utf-8", "replace")


def parse_text(txt):
    out = []
    for ln in txt.splitlines():
        ln = ln.strip()
        if " khu " in ln.lower() or ln.lower().startswith("khu "):
            continue
        m = NAME.match(ln)
        if m and not SKIP.search(ln):
            nm = re.sub(r"\s+", " ", m.group(2)).strip(" .;,")
            if nm and not re.fullmatch(r"\d+[A-Za-z]?", nm):
                out.append(nm)
    if not out:
        g = re.search(r"(tổ dân phố|thôn)\s*(?:số\s*)?1\s*đến\s*(?:tổ dân phố|thôn)?\s*(?:số\s*)?(\d+)",
                      canon_tone(txt), re.I)
        if g and 4 <= int(g.group(2)) <= 90:
            out = [str(i) for i in range(1, int(g.group(2)) + 1)]
    # dedupe
    seen, res = set(), []
    for n in out:
        k = canon_tone(n).lower()
        if k not in seen:
            seen.add(k)
            res.append(n)
    return res


def resno(txt):
    m = re.search(r"(Nghị quyết|Đề án|Thông báo)\s+số\s+([\dA-Za-zĐ/\-]+)[^\n]{0,50}?"
                  r"ngày\s+(\d+)\s+tháng\s+(\d+)\s+năm\s+(\d+)", txt)
    if m:
        return f"{m.group(1)} số {m.group(2)} ngày {int(m.group(3)):02d}/{int(m.group(4)):02d}/{m.group(5)}"
    return ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ward_code")
    ap.add_argument("url")
    ap.add_argument("--pdf")
    ap.add_argument("--title", default="")
    ap.add_argument("--resolution", default="")
    ap.add_argument("--verified", default="partial")
    ap.add_argument("--unit", default="")
    ap.add_argument("--names", default="")
    ap.add_argument("--range", type=int, default=0)
    ap.add_argument("--date", default="2026")
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()

    wards = {w["ward_code"]: w for w in csv.DictReader(open(ROOT / "data" / "wards.csv", encoding="utf-8"))}
    w = wards[a.ward_code]
    pc = w["province_code"]
    txt = ""
    src_pdf = a.pdf or ""

    if a.range:
        names = [str(i) for i in range(1, a.range + 1)]
    elif a.names:
        names = [x.strip() for x in re.split(r"[;|]", a.names) if x.strip()]
    else:
        if a.pdf:
            blob = get(a.pdf, binary=True)
        else:
            raw = get(a.url, binary=True)
            if raw[:4] == b"%PDF":
                blob, src_pdf = raw, a.url
            else:
                html = raw.decode("utf-8", "replace")
                cands = re.findall(r'(https?://[^"\s]+\.(?:pdf|PDF))', html)
                cands += [urllib.parse.urljoin(a.url, h)
                          for h in re.findall(r'href="([^"]+\.(?:pdf|PDF))"', html)]
                blob = b""
                for c in dict.fromkeys(cands):
                    try:
                        b = get(c, binary=True)
                    except Exception:
                        continue
                    if b[:4] == b"%PDF":
                        t = "\n".join(p.get_text() for p in fitz.open(stream=b, filetype="pdf"))
                        if canon_tone(w["name"]).lower() in canon_tone(t).lower() and \
                           re.search(r"(sắp xếp|đổi tên|sử dụng tên).{0,40}(thôn|tổ dân phố)", canon_tone(t), re.I):
                            blob, src_pdf, txt = b, c, t
                            break
        if not txt and blob[:4] == b"%PDF":
            txt = "\n".join(p.get_text() for p in fitz.open(stream=blob, filetype="pdf"))
        names = parse_text(txt)

    if not names:
        print("!! Không tìm được danh sách. Dùng --names hoặc --range.")
        sys.exit(2)

    unit = a.unit or ("tổ dân phố" if w["unit_type"] == "Phường" else "thôn")
    obj = {
        "ward_code": a.ward_code, "ward_name": w["name"], "province_code": pc,
        "resolution": a.resolution or resno(txt),
        "arrangement": "2026_07", "effective_date": "2026-07-01",
        "verified": a.verified,
        "extraction": {"source": urllib.parse.urlparse(a.url).netloc, "url": src_pdf or a.url,
                       "mode": "add_ward"},
        "sources": [{"key": f"portal-{a.ward_code}",
                     "title": a.title or f"Nghị quyết/Đề án sắp xếp {unit} {w['full_name']}",
                     "url": a.url, "date": a.date, "type": "cong_ttdt"}],
        "note": f"{len(names)} {unit} sau sắp xếp 01/7/2026.",
        "tdp": [{"name": n, "type": unit} for n in names],
    }
    print(f"{w['full_name']}: {len(names)} {unit} | res={obj['resolution']!r}")
    print("  ", names[:12], "..." if len(names) > 12 else "")
    if not a.dry:
        (OUT / pc).mkdir(parents=True, exist_ok=True)
        p = OUT / pc / f"{a.ward_code}_{slugify(w['name'])}.json"
        p.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("  ->", p)


if __name__ == "__main__":
    main()
