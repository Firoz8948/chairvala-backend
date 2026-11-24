from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.banners.defaults import (
    DEFAULT_DESKTOP_BANNER_IMAGE,
    DEFAULT_DESKTOP_BANNER_TITLE,
    DEFAULT_MOBILE_BANNER_IMAGE,
    DEFAULT_MOBILE_BANNER_TITLE,
)
from app.database import AsyncSessionLocal
from app.models import BannerSlide


async def _ensure_one(
    session: AsyncSession,
    *,
    device: str,
    image_url: str,
    title: str,
    log_label: str,
) -> None:
    existing = (
        await session.execute(
            select(BannerSlide).where(
                BannerSlide.device == device,
                BannerSlide.image_url == image_url,
            )
        )
    ).scalar_one_or_none()

    if existing:
        return

    session.add(
        BannerSlide(
            device=device,
            image_url=image_url,
            title=title,
            link_url="/shop",
            position=0,
            is_active=True,
        )
    )
    await session.commit()
    print(f"Default {log_label} banner seeded ({image_url.rsplit('/', 1)[-1]})")


async def ensure_default_desktop_banner(session: AsyncSession | None = None) -> None:
    """Insert the bundled desktop hero if it is not already in banner_slides."""
    owns_session = session is None
    if owns_session:
        session = AsyncSessionLocal()

    try:
        await _ensure_one(
            session,
            device="desktop",
            image_url=DEFAULT_DESKTOP_BANNER_IMAGE,
            title=DEFAULT_DESKTOP_BANNER_TITLE,
            log_label="desktop",
        )
    finally:
        if owns_session:
            await session.close()


async def ensure_default_mobile_banner(session: AsyncSession | None = None) -> None:
    """Insert the bundled mobile hero if it is not already in banner_slides."""
    owns_session = session is None
    if owns_session:
        session = AsyncSessionLocal()

    try:
        await _ensure_one(
            session,
            device="mobile",
            image_url=DEFAULT_MOBILE_BANNER_IMAGE,
            title=DEFAULT_MOBILE_BANNER_TITLE,
            log_label="mobile",
        )
    finally:
        if owns_session:
            await session.close()


async def ensure_default_banners(session: AsyncSession | None = None) -> None:
    owns_session = session is None
    if owns_session:
        session = AsyncSessionLocal()

    try:
        await _ensure_one(
            session,
            device="desktop",
            image_url=DEFAULT_DESKTOP_BANNER_IMAGE,
            title=DEFAULT_DESKTOP_BANNER_TITLE,
            log_label="desktop",
        )
        await _ensure_one(
            session,
            device="mobile",
            image_url=DEFAULT_MOBILE_BANNER_IMAGE,
            title=DEFAULT_MOBILE_BANNER_TITLE,
            log_label="mobile",
        )
    finally:
        if owns_session:
            await session.close()
