"""Bundled storefront banners (static files under frontend public/)."""

# Served by Next.js from public/images/banners/
DEFAULT_DESKTOP_BANNER_IMAGE = "/images/banners/chairvala-first-banner.png"
DEFAULT_DESKTOP_BANNER_TITLE = "Chairvala – plastic chairs & steel products"

DEFAULT_MOBILE_BANNER_IMAGE = "/images/banners/chairvala-mobile-banner.png"
DEFAULT_MOBILE_BANNER_TITLE = "Chairvala – mobile hero"


def is_protected_default_banner(
    *,
    device: str | None,
    image_url: str | None,
) -> bool:
    """Bundled heroes with overlay copy — cannot delete or replace image in Admin."""
    if not image_url:
        return False
    url = image_url.strip()
    dev = (device or "").lower()
    if dev == "desktop":
        return url == DEFAULT_DESKTOP_BANNER_IMAGE or url.endswith(
            "chairvala-first-banner.png"
        )
    if dev == "mobile":
        return url == DEFAULT_MOBILE_BANNER_IMAGE or url.endswith(
            "chairvala-mobile-banner.png"
        )
    return False
