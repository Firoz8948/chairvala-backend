"""
Import products from docs/chairvala-production-products.csv (Chairvala export format).

Prerequisites:
  - Categories exist with slugs matching category_slugs in the CSV (reels optional).
  - Metafield definitions optional (values stored on products either way).
  - Image URLs in CSV must already work (e.g. Bunny CDN).

Usage (from backend root, with DATABASE_URL in .env):

  python scripts/import_production_csv.py --csv /path/to/chairvala-production-products.csv
  python scripts/import_production_csv.py --csv ... --dry-run
  python scripts/import_production_csv.py --csv ... --skip-existing

On EC2:

  docker compose exec backend python scripts/import_production_csv.py \\
    --csv /opt/backend/import/chairvala-production-products.csv
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from app.admin.service import _clean_option_data
from app.categories import service as category_service
from app.database import AsyncSessionLocal
from app.models import Category, Product, ProductImage, ProductVariant, ProductVariantOption


def _parse_bool(val: str | None) -> bool:
    if not val:
        return False
    return str(val).strip().lower() in {"true", "1", "yes"}


def _parse_float(val: str | None) -> float | None:
    if val is None or str(val).strip() == "":
        return None
    try:
        return float(val)
    except ValueError:
        return None


def _parse_int(val: str | None, default: int = 0) -> int:
    if val is None or str(val).strip() == "":
        return default
    try:
        return int(float(val))
    except ValueError:
        return default


def _parse_json(val: str | None, default):
    if not val or not str(val).strip():
        return default
    try:
        return json.loads(val)
    except json.JSONDecodeError:
        return default


def _image_urls(row: dict) -> list[str]:
    pipe = (row.get("images_pipe") or "").strip()
    if pipe:
        return [u.strip() for u in pipe.split("|") if u.strip()][:12]
    urls = []
    for i in range(1, 9):
        u = (row.get(f"image_{i}") or "").strip()
        if u:
            urls.append(u)
    return urls[:12]


async def load_category_map(db) -> dict[str, Category]:
    rows = (await db.execute(select(Category))).scalars().all()
    return {c.slug: c for c in rows if c.slug}


async def import_row(
    db,
    row: dict,
    slug_map: dict[str, Category],
    *,
    dry_run: bool,
    skip_existing: bool,
) -> str:
    slug = (row.get("slug") or "").strip()[:300]
    if not slug:
        return "skip:empty-slug"

    existing = (
        await db.execute(select(Product).where(Product.slug == slug))
    ).scalar_one_or_none()
    if existing:
        return "skip:exists" if skip_existing else "error:duplicate-slug"

    slugs_raw = (row.get("category_slugs") or row.get("category_slug") or "").strip()
    cat_slugs = [s.strip() for s in slugs_raw.split("|") if s.strip()]
    primary_slug = (row.get("category_slug") or (cat_slugs[0] if cat_slugs else "")).strip()
    category_ids = []
    for s in cat_slugs:
        cat = slug_map.get(s)
        if cat and cat.id not in category_ids:
            category_ids.append(cat.id)
    if not category_ids and primary_slug:
        cat = slug_map.get(primary_slug)
        if cat:
            category_ids = [cat.id]

    missing = [s for s in cat_slugs if s not in slug_map and s != "reels"]
    if missing and not category_ids:
        return f"error:unknown-category:{missing[0]}"

    primary_id = slug_map[primary_slug].id if primary_slug in slug_map else (
        category_ids[0] if category_ids else None
    )
    primary_cat = slug_map.get(primary_slug) or (
        slug_map.get(cat_slugs[0]) if cat_slugs else None
    )

    name = (row.get("name") or "").strip()[:255]
    if not name:
        return "skip:empty-name"

    product_fields = {
        "name": name,
        "description": row.get("description") or None,
        "price": float(row.get("price") or 0),
        "mrp": float(row.get("mrp") or 0),
        "stock": _parse_int(row.get("stock")),
        "unit": (row.get("unit") or "piece").strip()[:50] or "piece",
        "weight": _parse_float(row.get("weight")),
        "length_cm": _parse_float(row.get("length_cm")),
        "breadth_cm": _parse_float(row.get("breadth_cm")),
        "height_cm": _parse_float(row.get("height_cm")),
        "is_featured": _parse_bool(row.get("is_featured")),
        "is_active": _parse_bool(row.get("is_active")),
        "metafields": _parse_json(row.get("metafields_json"), {}),
        "colors": _parse_json(row.get("colors_json"), []),
        "color_group_id": (row.get("color_group_id") or "").strip() or None,
        "seo_title": (row.get("seo_title") or "").strip()[:200] or None,
        "seo_description": (row.get("seo_description") or "").strip()[:320] or None,
        "category": primary_cat.name[:100] if primary_cat else (row.get("primary_category_name") or "Uncategorised")[:100],
        "category_id": primary_id,
        "tags": [],
    }

    variants = _parse_json(row.get("variants_json"), [])
    images = _image_urls(row)

    if dry_run:
        return f"ok:dry-run:{slug}"

    product = Product(slug=slug, **product_fields)
    db.add(product)
    await db.flush()

    await category_service.sync_product_categories(
        db, product, category_ids, primary_id=primary_id
    )

    for pos, url in enumerate(images):
        db.add(ProductImage(product_id=product.id, url=url[:500], position=pos))

    for var_data in variants or []:
        if not isinstance(var_data, dict):
            continue
        var_name = (var_data.get("name") or "").strip()[:100]
        if not var_name:
            continue
        variant = ProductVariant(product_id=product.id, name=var_name)
        db.add(variant)
        await db.flush()
        for opt_data in var_data.get("options") or []:
            if not isinstance(opt_data, dict):
                continue
            cleaned = _clean_option_data(opt_data)
            db.add(ProductVariantOption(variant_id=variant.id, **cleaned))

    return f"ok:{slug}"


async def run(csv_path: Path, *, dry_run: bool, skip_existing: bool) -> int:
    if not csv_path.is_file():
        print(f"CSV not found: {csv_path}", file=sys.stderr)
        return 1

    async with AsyncSessionLocal() as db:
        slug_map = await load_category_map(db)
        print(f"Categories in DB: {len(slug_map)}")

        stats = {"ok": 0, "skip": 0, "error": 0}
        with csv_path.open(encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                result = await import_row(
                    db,
                    row,
                    slug_map,
                    dry_run=dry_run,
                    skip_existing=skip_existing,
                )
                if result.startswith("ok:"):
                    stats["ok"] += 1
                    print(result)
                elif result.startswith("skip:"):
                    stats["skip"] += 1
                    print(result)
                else:
                    stats["error"] += 1
                    print(result, file=sys.stderr)

        if dry_run:
            await db.rollback()
            print("Dry run — rolled back.")
        else:
            await db.commit()
            print("Committed.")

    print(f"Done: {stats}")
    return 1 if stats["error"] else 0


def main():
    parser = argparse.ArgumentParser(description="Import Chairvala production CSV")
    parser.add_argument(
        "--csv",
        type=Path,
        default=Path(__file__).resolve().parents[2]
        / "docs"
        / "chairvala-production-products.csv",
        help="Path to export CSV",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skip-existing", action="store_true", default=True)
    parser.add_argument("--no-skip-existing", action="store_false", dest="skip_existing")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(run(args.csv, dry_run=args.dry_run, skip_existing=args.skip_existing)))


if __name__ == "__main__":
    main()