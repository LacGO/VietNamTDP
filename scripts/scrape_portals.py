#!/usr/bin/env python3
"""
Bổ sung danh mục thôn/TDP đúng mốc 01/7/2026 từ CỔNG THÔNG TIN ĐIỆN TỬ từng phường/xã.

Với mỗi phường/xã còn thiếu dữ liệu 2026_07:
  - xác định host cổng (sources/portal_hosts.json, hoặc đoán từ code_name)
  - tải trang chủ + các trang chuyên mục, tìm bài "... thôn/tổ dân phố ... sắp xếp/đổi tên/
    thành lập/sử dụng tên ..."
  - trong bài: lấy danh sách inline hoặc tải file PDF đính kèm và parse (PyMuPDF)
  - ghi sources/tdp/<pc>/<wc>_<slug>.json  (verified=primary, arrangement=2026_07)

Chạy:  python3 scripts/scrape_portals.py [--only 25] [--codes 08584,07900] [--limit N]
Cache: sources/raw/portal/<host>/*.html , sources/raw/portal_pdf/*.pdf
"""
import argparse
import csv
import glob
import json
import pathlib
import re
import sys
import time
import urllib.parse
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import slugify, canon_tone  # noqa: E402

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = ROOT / "sources" / "tdp"
HTML_CACHE = ROOT / "sources" / "raw" / "portal"
PDF_CACHE = ROOT / "sources" / "raw" / "portal_pdf"
HOSTS = json.loads((ROOT / "sources" / "portal_hosts.json").read_text())
for p in (HTML_CACHE, PDF_CACHE):
    p.mkdir(parents=True, exist_ok=True)

UA = "Mozilla/5.0 (VietNamTDP open-data bot)"
ART_RE = re.compile(
    r"(thôn|tổ dân phố|khu dân cư|khu phố)", re.I)
ACT_RE = re.compile(
    r"(sắp xếp|sáp nhập|đổi tên|thành lập|sử dụng tên gọi|tổ chức lại|danh sách|nghị quyết)", re.I)
SKIP_RE = re.compile(r"(trước sắp xếp|trước đổi tên|sau sắp xếp|sau đổi tên|giữ nguyên,|"
                     r"^tên (thôn|tổ)|chưa sắp xếp)", re.I)
# CHỈ khớp tên đơn vị MỚI (sau sắp xếp): có tiền tố đầy đủ, không chứa dấu phẩy/"khu"
NAME_RE = re.compile(r"^(Thôn|Tổ dân phố|Tổ dân phố số|TDP|Khu phố)\s+([^\n,]{1,55})$")
SECTIONS = ["", "/sap-xep-to-dan-pho", "/thong-tin-sat-nhap-khu-dan-cu",
            "/sap-xep-to-chuc-bo-may-va-don-vi-hanh-chinh", "/tin-tuc-su-kien",
            "/index.php", "/thong-bao", "/van-ban", "/chi-dao-dieu-hanh",
            "/sap-xep-don-vi-hanh-chinh", "/tin-tuc-hoat-dong-cua-ubnd",
            "/tin-tuc-hoat-dong-hdnd", "/van-ban-chi-dao-dieu-hanh"]


def http_get(url, binary=False, timeout=45):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = r.read()
            return data if binary else data.decode("utf-8", "replace")
    except Exception as e:
        return b"" if binary else ""


def abs_url(host, href):
    if href.startswith("http"):
        return href
    return f"https://{host}" + ("" if href.startswith("/") else "/") + href


def links(html):
    for m in re.finditer(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', html, re.S | re.I):
        txt = re.sub(r"<[^>]+>", " ", m.group(2))
        txt = re.sub(r"\s+", " ", txt).strip()
        yield m.group(1), txt


def _score(t):
    tl = canon_tone(t).lower()
    s = 0
    if "sử dụng tên gọi" in tl:
        s += 6
    if "nghị quyết" in tl:
        s += 3
    if "thông báo" in tl:
        s += 1
    if "thành lập" in tl and ("tổ dân phố" in tl or "thôn" in tl):
        s += 3
    if "đổi tên" in tl and ("thôn" in tl or "tổ dân phố" in tl):
        s += 3
    if "danh sách" in tl and ("thôn" in tl or "tổ dân phố" in tl):
        s += 3
    if "sau sắp xếp" in tl:
        s += 2
    for bad in ("hội nghị", "đóng góp ý kiến", "lấy ý kiến", "triển khai",
                "phương án tổng thể", "dự thảo", "quy trình", "hướng dẫn",
                "kế hoạch", "tuyên truyền", "chỉ thị", "sinh hoạt chi bộ"):
        if bad in tl:
            s -= 3
    return s


def find_article_urls(host):
    seen, found = set(), []
    queue = [f"https://{host}{s}" for s in SECTIONS]
    home = http_get(f"https://{host}")
    for href, _ in links(home):
        if re.search(r"(sat-nhap|sap-xep|khu-dan-cu|to-dan-pho|don-vi-hanh-chinh)",
                     href, re.I):
            queue.append(abs_url(host, href))
    for url in list(dict.fromkeys(queue))[:18]:
        html = http_get(url)
        time.sleep(0.15)
        if not html:
            continue
        for href, txt in links(html):
            if not txt or len(txt) < 12:
                continue
            if ART_RE.search(txt) and ACT_RE.search(txt):
                u = abs_url(host, href)
                if u not in seen:
                    seen.add(u)
                    found.append((u, txt))
        if len([f for f in found if _score(f[1]) >= 3]) >= 3:
            break
    found.sort(key=lambda x: -_score(x[1]))
    return [f for f in found if _score(f[1]) > -2][:8]


def parse_pdf_text(txt):
    names, mode = [], "pdf"
    for raw in txt.splitlines():
        line = raw.strip()
        if " khu " in line.lower() or line.lower().startswith("khu "):
            continue
        m = NAME_RE.match(line)
        if m and not SKIP_RE.search(line):
            nm = re.sub(r"\s+", " ", m.group(2)).strip(" .;,")
            if nm and not re.fullmatch(r"\d+[A-Za-z]?", nm):
                names.append(nm)
    # also "gồm ... thôn: A, B và C"
    if not names:
        g = re.search(r"gồm[^\n:]*?(thôn|tổ dân phố)[^:]*:\s*([^\n.]+)", txt, re.I)
        if g:
            names = [x.strip() for x in re.split(r",|;| và ", g.group(2)) if x.strip()]
    return dedupe(names)


def numbered_range(txt):
    """'Tổ dân phố số 1 đến Tổ dân phố số 50' / 'gồm 32 thôn ... đánh số từ 1 đến 32'."""
    t = canon_tone(txt)
    m = re.search(r"(tổ dân phố|thôn)\s*(?:số\s*)?1\s*đến\s*(?:tổ dân phố|thôn)?\s*(?:số\s*)?(\d+)", t, re.I)
    if not m:
        m = re.search(r"(\d+)\s+(tổ dân phố|thôn)[^\n.]{0,40}đánh số (?:từ )?1\s*(?:đến|-)\s*(\d+)", t, re.I)
        if m:
            u = m.group(2)
            b = int(m.group(3))
            return [str(i) for i in range(1, b + 1)]
        return []
    u, b = m.group(1), int(m.group(2))
    if 4 <= b <= 90:
        return [str(i) for i in range(1, b + 1)]
    return []


def parse_html_list(html):
    text = re.sub(r"<script.*?</script>|<style.*?</style>", " ", html, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    import html as _h
    text = _h.unescape(text)
    return parse_pdf_text(text)


def dedupe(names):
    out, seen = [], set()
    for n in names:
        n = re.sub(r"\s+", " ", str(n)).strip(" .;,")
        n = re.sub(r"^(Thôn|Tổ dân phố|TDP|Khu phố|Khu)\s+", "", n)
        k = canon_tone(n).lower()
        if n and 1 < len(n) < 60 and k not in seen and not SKIP_RE.search(n):
            seen.add(k)
            out.append(n)
    return out


def resolution_no(txt):
    m = re.search(r"Nghị quyết\s+số\s+(\d+[/A-Za-zĐ\-]*NQ-HĐND)[^\n]{0,60}?"
                  r"ngày\s+(\d+)\s+tháng\s+(\d+)\s+năm\s+(\d+)", txt)
    if m:
        return f"Nghị quyết số {m.group(1)} ngày {int(m.group(2)):02d}/{int(m.group(3)):02d}/{m.group(4)} HĐND cấp xã"
    m = re.search(r"Nghị quyết\s+số\s+(\d+[/A-Za-zĐ\-]*NQ-HĐND)", txt)
    return f"Nghị quyết số {m.group(1)} HĐND cấp xã" if m else ""


def norm_host(h):
    h = re.sub(r"^https?://", "", h or "").strip().strip("/")
    return h.split("/")[0]


def process_ward(w, sleep):
    wc, pc = w["ward_code"], w["province_code"]
    host = norm_host(HOSTS.get(wc)) or (
        f"{slugify(w['name']).replace('_','')}."
        + ("hanoi.gov.vn" if pc == "01" else "phutho.gov.vn"))
    arts = find_article_urls(host)
    for url, title in arts:
        html = http_get(url)
        time.sleep(sleep)
        if not html:
            continue
        # try PDF attachments first
        pdfs = re.findall(r'href="([^"]+\.(?:pdf|PDF))"', html)
        pdfs += re.findall(r'(https?://[^"\s]+\.(?:pdf|PDF))', html)
        cand = []
        wname = canon_tone(w["name"]).lower()
        for pu in dict.fromkeys(pdfs):
            pu = abs_url(host, pu)
            pu2 = urllib.parse.quote(pu, safe=":/?&=%")
            blob = http_get(pu2, binary=True)
            time.sleep(sleep)
            if blob[:4] != b"%PDF" or not fitz or len(blob) > 8_000_000:
                continue
            try:
                doc = fitz.open(stream=blob, filetype="pdf")
                ptxt = "\n".join(p.get_text() for p in doc)
            except Exception:
                continue
            low = canon_tone(ptxt).lower()
            if wname not in low:
                continue
            if not re.search(r"(sắp xếp|đổi tên|sử dụng tên gọi|thành lập).{0,40}(thôn|tổ dân phố)"
                             r"|(thôn|tổ dân phố).{0,40}(sắp xếp|đổi tên|sau sắp xếp)", low):
                continue
            names = parse_pdf_text(ptxt)
            rng = numbered_range(ptxt)
            if rng and (not names or len(rng) > len(names)):
                names = rng
            if 4 <= len(names) <= 80:
                cand.append((names, resolution_no(ptxt), pu, title, "pdf", len(blob)))
        if not cand:
            names = parse_html_list(html)
            rng = numbered_range(html)
            if rng and len(rng) > len(names):
                names = rng
            if 4 <= len(names) <= 80:
                cand.append((names, resolution_no(html), url, title, "html", 0))
        if cand:
            # ưu tiên: nhiều tên hợp lệ, file nhỏ (văn bản nghị quyết ngắn)
            names, resno, srcurl, title, mode, _ = max(
                cand, key=lambda c: (len(c[0]), -c[5]))
            unit = "tổ dân phố" if pc == "01" or "Phường" == w["unit_type"] else "thôn"
            if re.search(r"tổ dân phố", " ".join(names[:5]) + title, re.I):
                unit = "tổ dân phố"
            obj = {
                "ward_code": wc, "ward_name": w["name"], "province_code": pc,
                "resolution": resno, "arrangement": "2026_07",
                "effective_date": "2026-07-01", "verified": "primary",
                "extraction": {"source": host, "url": srcurl, "mode": f"portal-{mode}"},
                "sources": [{"key": f"portal-{wc}", "title": title,
                             "url": srcurl, "date": "2026", "type": "cong_ttdt"}],
                "note": "Trích từ cổng TTĐT phường/xã (nghị quyết/thông báo HĐND cấp xã).",
                "tdp": [{"name": n, "type": unit} for n in names],
            }
            (OUT / pc).mkdir(parents=True, exist_ok=True)
            (OUT / pc / f"{wc}_{slugify(w['name'])}.json").write_text(
                json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            return f"OK({mode}) {len(names)}  [{host}]"
    return f"MISS  [{host}]"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only")
    ap.add_argument("--codes", help="danh sách mã xã, phẩy ngăn cách")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--sleep", type=float, default=0.25)
    args = ap.parse_args()

    wards = list(csv.DictReader(open(DATA / "wards.csv", encoding="utf-8")))
    have = {}
    for f in glob.glob(str(OUT / "*" / "*.json")):
        d = json.load(open(f))
        have[d["ward_code"]] = d.get("arrangement")

    todo = []
    codes = set(args.codes.split(",")) if args.codes else None
    for w in wards:
        if args.only and w["province_code"] != args.only:
            continue
        if codes and w["ward_code"] not in codes:
            continue
        if not codes and have.get(w["ward_code"]) == "2026_07":
            continue
        todo.append(w)
    if args.limit:
        todo = todo[: args.limit]

    print(f"{len(todo)} phường/xã cần xử lý\n")
    ok = 0
    for w in todo:
        r = process_ward(w, args.sleep)
        if r.startswith("OK"):
            ok += 1
        print(f"  {w['province_code']} {w['ward_code']} {w['name']:<24} {r}", flush=True)
    print(f"\n{ok}/{len(todo)} bổ sung được từ cổng TTĐT")


if __name__ == "__main__":
    main()
