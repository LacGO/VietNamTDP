#!/usr/bin/env python3
"""Shared helpers for the VietNamTDP build scripts."""
import re
import unicodedata

# Vietnamese tone-mark placement variants (old "kiểu cũ" vs new orthography).
# Chỉ dời dấu khi "oa/oe/uy" là âm cuối của âm tiết (hoà→hòa, thuỷ→thủy);
# GIỮ NGUYÊN khi còn phụ âm cuối (hoàng, xoàng, quýnh) — dấu đã đúng chỗ.
_PAIRS_O = [
    ("oà", "òa"), ("oá", "óa"), ("oả", "ỏa"), ("oã", "õa"), ("oạ", "ọa"),
    ("oè", "òe"), ("oé", "óe"), ("oẻ", "ỏe"), ("oẽ", "õe"), ("oẹ", "ọe"),
]
_PAIRS_U = [
    ("uỳ", "ùy"), ("uý", "úy"), ("uỷ", "ủy"), ("uỹ", "ũy"), ("uỵ", "ụy"),
]
_AFTER = r"(?![A-Za-zÀ-ỹ])"          # âm tiết kết thúc ở đây (không phụ âm cuối)
_RX = [(re.compile(re.escape(a) + _AFTER, re.I), a, b) for a, b in _PAIRS_O]
# "uy": bỏ qua khi đứng ngay sau "q" (quý, quỳ… vốn đã đúng)
_RX += [(re.compile(r"(?<![Qq])" + re.escape(a) + _AFTER, re.I), a, b) for a, b in _PAIRS_U]


def _swapcase_match(orig_lower_pair, repl_lower, matched):
    # giữ hoa/thường theo ký tự đầu của cụm khớp
    return repl_lower[0].upper() + repl_lower[1:] if matched[0].isupper() else repl_lower


def canon_tone(s: str) -> str:
    """Canonicalise tone-mark placement to the 'new' orthography (an toàn)."""
    s = unicodedata.normalize("NFC", s)
    for rx, a, b in _RX:
        s = rx.sub(lambda m: _swapcase_match(a, b, m.group(0)), s)
    return s


def norm_name(s: str) -> str:
    """Loose key for matching unit names across sources."""
    s = canon_tone(s).lower().strip()
    s = re.sub(r"\s+", " ", s)
    return s


def slugify(s: str) -> str:
    s = canon_tone(s)
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.replace("Đ", "D").replace("đ", "d")
    s = re.sub(r"[^A-Za-z0-9]+", "_", s).strip("_").lower()
    return s
