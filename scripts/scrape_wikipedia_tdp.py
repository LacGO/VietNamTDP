#!/usr/bin/env python3
"""
Thu thập danh mục tổ dân phố / thôn từ Wikipedia tiếng Việt cho từng phường/xã.

Với mỗi phường/xã trong data/wards.csv:
  - thử vài tiêu đề ứng viên, tải wikitext (action=raw)
  - xác thực bằng "mã hành chính = <ward_code>" trong infobox
  - trích bảng "Danh sách các <đơn vị> thuộc <tên>" hoặc câu "được chia thành N ..."
  - trích 1-3 nguồn <ref> gần đó (ưu tiên nghị quyết / cổng TTĐT phường)
  - ghi sources/tdp/<mã tỉnh>/<mã xã>_<slug>.json

Chạy:  python3 scripts/scrape_wikipedia_tdp.py [--only 01] [--limit N] [--refresh]
Wikitext thô được cache tại sources/raw/wiki/<ward_code>.wikitext
"""
import argparse
import csv
import json
import pathlib
import re
import sys
import time
import urllib.parse
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import slugify, canon_tone  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
WIKI_CACHE = ROOT / "sources" / "raw" / "wiki"
OUT = ROOT / "sources" / "tdp"
WIKI_CACHE.mkdir(parents=True, exist_ok=True)

UA = "VietNamTDP-dataset/0.1 (open data; https://github.com/)"
API = "https://vi.wikipedia.org/w/index.php"


def _get(title: str) -> str:
    q = urllib.parse.urlencode({"title": title, "action": "raw"})
    req = urllib.request.Request(f"{API}?{q}", headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            if r.status != 200:
                return ""
            return r.read().decode("utf-8", "replace")
    except Exception:
        return ""


def fetch_raw(title: str) -> str:
    wt = _get(title)
    m = re.match(r"#(?:đổi|ĐỔI|REDIRECT)\s*\[\[([^\]]+)\]\]", wt.strip(), re.I)
    if m:
        return _get(m.group(1).split("|")[0].strip())
    return wt


def candidates(name: str, unit_type: str):
    kind = "phường" if unit_type == "Phường" else "xã"
    seen = []
    for base in {name.strip(), canon_tone(name).strip()}:
        for t in (f"{base} ({kind})", base, f"{base} ({kind}, Hà Nội)",
                  f"{base} ({kind}, Phú Thọ)", f"{base}, Hà Nội", f"{base}, Phú Thọ",
                  f"{base} (định hướng)"):
            if t not in seen:
                seen.append(t)
    return seen


REF_RE = re.compile(r"<ref[^>]*>\{\{[Cc]hú thích web\s*\|(.+?)\}\}</ref>", re.S)


def parse_ref(block: str):
    def field(key):
        m = re.search(r"\b" + key + r"\s*=\s*([^|}]+)", block)
        return m.group(1).strip() if m else ""
    return {
        "title": field("title") or field("tiêu đề"),
        "url": field("url"),
        "date": field("date") or field("ngày"),
        "archive_url": field("archive-url"),
    }


UNIT_ALT = r"(tổ dân phố|thôn|khu phố|khu dân cư|khu|bản|xóm|làng)"


def extract_tdp(wt: str, ward_name: str):
    """Return (list_of_names, unit_type, mode)."""
    wt = canon_tone(wt)
    cn = canon_tone(ward_name)
    unit = "tổ dân phố"

    # 1) explicit list table: "! ... |Danh sách các <unit> thuộc <ward>"
    hdr = re.search(
        r"Danh sách các " + UNIT_ALT + r"[^\n|]*?thuộc\s+(?:phường|xã)?\s*"
        + re.escape(cn) + r"\b", wt)
    if hdr:
        unit = hdr.group(1)
        tail = wt[hdr.end():]
        # stop at next section heading or a clearly different "Danh sách" table
        stop = re.search(r"\n==+ | Danh sách các " + UNIT_ALT + r" thuộc ", tail)
        seg = tail[: stop.start()] if stop else tail[:12000]
        names = [m.group(1).strip()
                 for m in re.finditer(r"\n\|\s*align=\"left\"\s*\|\s*([^\n|]+)", seg)]
        names = [n for n in names if n and not n.lower().startswith(("tên", "stt"))]
        if names:
            return dedupe(names), unit, "table"

    # 2) narrative "được chia thành N <unit>: A, B ... và Z."
    #    Có thể có NHIỀU danh sách (hiện trạng + lịch sử). Chấm điểm để chọn danh sách mới nhất:
    #    +2 nếu đơn vị là "tổ dân phố" (thuật ngữ chuẩn NĐ 185/2026)
    #    -3 mỗi lần xuất hiện "... cũ)" (danh sách mô tả theo đơn vị cũ = hiện trạng chuyển tiếp)
    #    +2 nếu nằm ngay sau tiêu đề "== Hành chính =="
    cands = []
    for nm in re.finditer(
        r"(?:được chia thành|gồm)\s+(\d+)\s+" + UNIT_ALT + r"\s*:\s*(.+?)\.\s*(?:<ref|\n|$)", wt):
        u = nm.group(2)
        body = nm.group(3)
        parts = re.split(r",\s*|\s+và\s+", body)
        names = [re.sub(r"<ref.*|\([^)]*\)", "", p).strip() for p in parts if p.strip()]
        names = [n for n in names if n and not re.fullmatch(r"\d+[A-Za-z]?", n)]
        if not names:
            continue
        score = 0
        if "tổ dân phố" in u:
            score += 2
        score -= 3 * len(re.findall(r"cũ\)", body))
        pre = wt[max(0, nm.start() - 400):nm.start()]
        if "== Hành chính" in pre:
            score += 2
        cands.append((score, -nm.start(), names, u))
    if cands:
        cands.sort(reverse=True)
        sc, _, names, u = cands[0]
        return dedupe(names), u, "narrative" + ("" if sc >= 0 else "!old")

    # 3) numbered only: "được chia thành N <unit>, đánh số từ a đến b"
    num = re.search(
        r"(?:được chia thành|gồm)\s+(\d+)\s+" + UNIT_ALT
        + r"[^\n.]*?đánh số từ\s+(\d+)\s+đến\s+(\d+)", wt)
    if num:
        unit = num.group(2)
        a, b = int(num.group(3)), int(num.group(4))
        label = "Tổ dân phố" if "tổ dân phố" in unit else unit.capitalize()
        return [f"{label} {i}" for i in range(a, b + 1)], unit, "numbered"

    return [], unit, "none"


def dedupe(names):
    out, seen = [], set()
    for n in names:
        n = re.sub(r"\s+", " ", n).strip(" .;")
        k = n.lower()
        if n and k not in seen:
            seen.add(k)
            out.append(n)
    return out


def pick_sources(wt: str, list_pos: int):
    """Grab up to 3 chú-thích-web refs, preferring nghị quyết / cổng phường."""
    refs = []
    for m in REF_RE.finditer(wt):
        r = parse_ref(m.group(1))
        if not (r["title"] or r["url"]):
            continue
        score = 0
        blob = (r["title"] + " " + r["url"]).lower()
        if "nghị quyết" in blob or "nghi-quyet" in blob:
            score += 3
        if "hdnd" in blob or "hội đồng nhân dân" in blob:
            score += 2
        if ".gov.vn" in blob:
            score += 2
        if "sắp xếp" in blob and "tổ dân phố" in blob:
            score += 2
        if "2026" in (r["date"] or ""):
            score += 1
        refs.append((score, abs(m.start() - list_pos), r))
    refs.sort(key=lambda x: (-x[0], x[1]))
    picked, seen = [], set()
    for _, _, r in refs:
        key = r["url"] or r["title"]
        if key in seen:
            continue
        seen.add(key)
        picked.append(r)
        if len(picked) >= 3:
            break
    return picked


_D26 = r"(?:năm 2026|tháng \d+ năm 2026|1/7/2026|01/7/2026)"
_ACT = (r"(?:thành lập|sắp xếp|tổ chức lại|đổi tên|sáp nhập)[^\n.]{0,90}"
        r"(?:tổ dân phố|thôn|khu)(?:\s+mới)?")
EST_2026 = re.compile(
    r"(?:" + _D26 + r"[^\n.]{0,90}" + _ACT + r")"
    r"|(?:" + _ACT + r"[^\n.]{0,90}" + _D26 + r")"
    r"|(?:được chia thành[^.]{0,200}?<ref[^>]*>\{\{[^}]*?" + _D26 + r")")


def arrangement_of(wt: str, mode: str, unit: str, pc: str):
    """Trả về ('2026_07' | 'truoc_2026_07', effective_date)."""
    if mode.endswith("!old"):
        return "truoc_2026_07", ""
    if EST_2026.search(wt):
        return "2026_07", "2026-07-01"
    # Phú Thọ: hệ cũ dùng "khu"; danh sách "tổ dân phố" là hệ mới NĐ 185/2026
    if pc == "25" and unit == "tổ dân phố":
        return "2026_07", "2026-07-01"
    return "truoc_2026_07", ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="province_code filter, e.g. 01")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--refresh", action="store_true", help="ignore wikitext cache (refetch)")
    ap.add_argument("--reextract", action="store_true",
                    help="reprocess from wikitext cache, overwrite existing outputs")
    ap.add_argument("--sleep", type=float, default=0.5)
    args = ap.parse_args()

    wards = list(csv.DictReader(open(DATA / "wards.csv", encoding="utf-8")))
    if args.only:
        wards = [w for w in wards if w["province_code"] == args.only]
    if args.limit:
        wards = wards[: args.limit]

    report = []
    for w in wards:
        wc, pc = w["ward_code"], w["province_code"]
        existing = list((OUT / pc).glob(f"{wc}_*.json"))
        if existing and not args.refresh and not args.reextract:
            report.append((wc, w["name"], "skip(exists)", 0))
            continue
        cache = WIKI_CACHE / f"{wc}.wikitext"
        wt, used_title = "", ""
        if cache.exists() and not args.refresh:
            wt = cache.read_text(encoding="utf-8")
            used_title = "(cache)"
        else:
            prov_name = "thành phố Hà Nội" if pc == "01" else "tỉnh Phú Thọ"
            for t in candidates(w["name"], w["unit_type"]):
                raw = fetch_raw(t)
                time.sleep(args.sleep)
                if "Thông tin đơn vị hành chính Việt Nam" not in raw:
                    continue
                code_ok = re.search(r"mã hành chính\s*=\s*" + wc + r"\b", raw)
                cn = canon_tone(w["name"])
                name_ok = re.search(
                    r"'''" + re.escape(cn) + r"'''\s+(?:là|,)\s.{0,40}?"
                    r"(?:\[\[)?(?:một |)(?:xã|phường|Phường|Xã)", canon_tone(raw))
                kind_vn = "phường" if w["unit_type"] == "Phường" else "xã"
                title_ok = f"({kind_vn})" in t and cn.lower() in canon_tone(t).lower()
                prov_ok = prov_name in raw
                if code_ok or ((name_ok or title_ok) and prov_ok):
                    wt, used_title = raw, t
                    break
            if wt:
                cache.write_text(wt, encoding="utf-8")
        if not wt:
            report.append((wc, w["name"], "NO-WIKI", 0))
            continue

        names, unit, mode = extract_tdp(wt, w["name"])
        if not names:
            report.append((wc, w["name"], f"no-list({mode})", 0))
            continue
        lp = canon_tone(wt).find("Danh sách các")
        srcs = pick_sources(wt, lp if lp > 0 else 0)
        arr, eff = arrangement_of(wt, mode, unit, pc)
        note = ("Trích tự động từ Wikipedia tiếng Việt (mode={m}). "
                "Cần đối chiếu nghị quyết HĐND phường/xã.").format(m=mode)
        if arr == "truoc_2026_07":
            note += (" ⚠️ Danh mục có thể là hiện trạng TRƯỚC sắp xếp thôn/TDP 01/7/2026 "
                     "— Wikipedia chưa cập nhật nghị quyết mới.")
        obj = {
            "ward_code": wc,
            "ward_name": w["name"],
            "province_code": pc,
            "resolution": "",
            "arrangement": arr,
            "effective_date": eff,
            "verified": "unverified",
            "extraction": {"source": "vi.wikipedia.org", "title": used_title, "mode": mode},
            "sources": [
                {
                    "key": f"wiki-{wc}-{i+1}",
                    "title": s["title"],
                    "url": s["url"] or s["archive_url"],
                    "date": s["date"],
                    "type": "wikipedia-ref",
                }
                for i, s in enumerate(srcs)
            ],
            "note": note,
            "tdp": [{"name": n, "type": unit} for n in names],
        }
        (OUT / pc).mkdir(parents=True, exist_ok=True)
        (OUT / pc / f"{wc}_{slugify(w['name'])}.json").write_text(
            json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        report.append((wc, w["name"], f"OK({mode})", len(names)))

    ok = sum(1 for r in report if r[2].startswith("OK"))
    tot_tdp = sum(r[3] for r in report)
    print(f"\n{ok}/{len(report)} phường/xã có danh sách — tổng {tot_tdp} TDP/thôn")
    for wc, nm, st, n in report:
        if not st.startswith("skip"):
            print(f"  {wc} {nm:<22} {st:<16} {n}")


if __name__ == "__main__":
    main()
