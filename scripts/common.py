#!/usr/bin/env python3
"""Shared helpers for the VietNamTDP build scripts."""
import re
import unicodedata

# Vietnamese tone-mark placement variants (old vs new orthography).
# e.g. "Hoà" (old) vs "Hòa" (new); "Thuỷ" vs "Thủy".
_TONE_VARIANTS = {
    "oà": "òa", "oá": "óa", "oả": "ỏa", "oã": "õa", "oạ": "ọa",
    "oè": "òe", "oé": "óe", "oẻ": "ỏe", "oẽ": "õe", "oẹ": "ọe",
    "uỳ": "ùy", "uý": "úy", "uỷ": "ủy", "uỹ": "ũy", "uỵ": "ụy",
    "Oà": "Òa", "Oá": "Óa", "Oả": "Ỏa", "Oã": "Õa", "Oạ": "Ọa",
    "Uỳ": "Ùy", "Uý": "Úy", "Uỷ": "Ủy", "Uỹ": "Ũy", "Uỵ": "Ụy",
}


def canon_tone(s: str) -> str:
    """Canonicalise tone-mark placement to the 'new' orthography."""
    s = unicodedata.normalize("NFC", s)
    for a, b in _TONE_VARIANTS.items():
        s = s.replace(a, b)
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
