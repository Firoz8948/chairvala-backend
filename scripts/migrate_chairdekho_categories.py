"""One-off: seed / replace categories with Shree Krishna Steel product categories via SQL."""
import asyncio
import os
from pathlib import Path
from urllib.parse import unquote, urlparse

import asyncpg
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

NEW = [
    ("Plastic Chairs", "plastic-chairs", 0),
    ("Plastic Stools & Tables", "plastic-stools-tables", 1),
    ("Plastic Household", "plastic-household", 2),
    ("Steel Furniture", "steel-furniture", 3),
    ("Steel Racks & Storage", "steel-racks-storage", 4),
    ("Steel Household", "steel-household", 5),
]


async def main():
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        raise SystemExit("DATABASE_URL not set")
    url = url.replace("postgresql+asyncpg://", "postgresql://")
    parsed = urlparse(url)
    conn = await asyncpg.connect(
        host=parsed.hostname or "localhost",
        port=parsed.port or 5432,
        user=unquote(parsed.username or ""),
        password=unquote(parsed.password or ""),
        database=(parsed.path or "/").lstrip("/") or "postgres",
    )
    try:
        cols = await conn.fetch(
            """
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'categories'
            """
        )
        col_names = {r["column_name"] for r in cols}
        if not col_names:
            raise SystemExit("categories table not found")

        await conn.execute("DELETE FROM categories")
        for name, slug, position in NEW:
            if "position" in col_names and "is_active" in col_names:
                await conn.execute(
                    """
                    INSERT INTO categories (name, slug, position, is_active)
                    VALUES ($1, $2, $3, true)
                    """,
                    name,
                    slug,
                    position,
                )
            elif "position" in col_names:
                await conn.execute(
                    """
                    INSERT INTO categories (name, slug, position)
                    VALUES ($1, $2, $3)
                    """,
                    name,
                    slug,
                    position,
                )
            else:
                await conn.execute(
                    """
                    INSERT INTO categories (name, slug)
                    VALUES ($1, $2)
                    """,
                    name,
                    slug,
                )
        print(f"Seeded {len(NEW)} Shree Krishna Steel categories")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
