"""Normalize product titles for feeds, shipping manifests, and SEO."""

from __future__ import annotations

import re

from app.config import settings

_brand = re.escape((settings.BRAND_NAME or "Chairvala").strip())
PRODUCT_NAME_BRAND_SUFFIX_RE = re.compile(
    rf"\s*[|\u2013\u2014-]\s*(?:shree\s*(?:krishna|ram)\s*steel|{_brand}(?:\.com)?)\s*$",
    re.I,
)


def strip_product_name_brand_suffix(name: str | None) -> str:
    return PRODUCT_NAME_BRAND_SUFFIX_RE.sub("", (name or "")).strip()
