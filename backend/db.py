"""Async Postgres (Supabase) connection helpers for Gestor360.

The FastAPI backend connects with SUPABASE_DB_URL using the pooled service-role
connection string. That bypasses RLS by design — the backend is responsible for
enforcing `WHERE company_id = $1` in every tenant-scoped query.
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any, Iterable, Optional

import asyncpg
from fastapi import HTTPException

logger = logging.getLogger(__name__)

_pool: Optional[asyncpg.Pool] = None


async def _init_connection(conn: asyncpg.Connection) -> None:
    """Register JSONB codecs so we can pass/receive Python dicts/lists directly."""
    await conn.set_type_codec(
        "jsonb",
        encoder=json.dumps,
        decoder=json.loads,
        schema="pg_catalog",
    )
    await conn.set_type_codec(
        "json",
        encoder=json.dumps,
        decoder=json.loads,
        schema="pg_catalog",
    )


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        dsn = os.environ.get("SUPABASE_DB_URL")
        if not dsn:
            raise HTTPException(
                status_code=503,
                detail="Banco não configurado (SUPABASE_DB_URL ausente).",
            )
        try:
            _pool = await asyncpg.create_pool(
                dsn=dsn,
                min_size=1,
                max_size=int(os.environ.get("DB_POOL_MAX", "10")),
                init=_init_connection,
                statement_cache_size=0,  # required for pgBouncer (Supabase pooler)
            )
        except Exception as exc:
            logger.error("Failed to open Supabase pool: %s", exc)
            raise HTTPException(status_code=503, detail="Falha ao conectar no banco")
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


async def fetch(query: str, *args: Any) -> list[asyncpg.Record]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetch(query, *args)


async def fetchrow(query: str, *args: Any) -> Optional[asyncpg.Record]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchrow(query, *args)


async def fetchval(query: str, *args: Any) -> Any:
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchval(query, *args)


async def execute(query: str, *args: Any) -> str:
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.execute(query, *args)


def row_to_dict(row: Optional[asyncpg.Record]) -> Optional[dict]:
    if row is None:
        return None
    d = dict(row)
    # Coerce Decimal → float for JSON friendliness.
    for k, v in list(d.items()):
        if hasattr(v, "is_finite") and not isinstance(v, float):
            try:
                d[k] = float(v)
            except Exception:
                pass
    return d


def rows_to_list(rows: Iterable[asyncpg.Record]) -> list[dict]:
    return [row_to_dict(r) for r in rows]
