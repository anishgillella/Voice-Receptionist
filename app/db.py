"""Async Postgres helpers for Supabase persistence."""

from typing import Any, Dict

import asyncpg

from .config import get_settings


async def get_connection() -> asyncpg.Connection:
    settings = get_settings()
    return await asyncpg.connect(settings.supabase_database_url)


async def ensure_tables_exist() -> None:
    conn = await get_connection()
    try:
        await conn.execute(
            """
            create table if not exists sessions (
              id uuid primary key default gen_random_uuid(),
              phone_number text,
              status text default 'active',
              started_at timestamptz default now(),
              ended_at timestamptz,
              metadata jsonb
            );
            """
        )
        await conn.execute(
            """
            create table if not exists transcripts (
              id bigserial primary key,
              session_id uuid references sessions(id) on delete cascade,
              role text check (role in ('user','assistant','system','tool')),
              message text,
              metadata jsonb,
              created_at timestamptz default now()
            );
            """
        )
        await conn.execute(
            """
            create table if not exists calendar_actions (
              id bigserial primary key,
              session_id uuid references sessions(id),
              action text check (action in ('create','update','delete')),
              event_id text,
              summary text,
              start_time timestamptz,
              end_time timestamptz,
              stylist text,
              service text,
              created_at timestamptz default now()
            );
            """
        )
    finally:
        await conn.close()


async def upsert_session(session_id: str, metadata: Dict[str, Any]) -> None:
    conn = await get_connection()
    try:
        await conn.execute(
            """
            insert into sessions (id, phone_number, metadata)
            values ($1, $2, $3)
            on conflict (id) do update
              set metadata = sessions.metadata || EXCLUDED.metadata
            """,
            session_id,
            metadata.get("phone_number"),
            metadata,
        )
    finally:
        await conn.close()


async def insert_transcript(session_id: str, role: str, message: str, metadata: Dict[str, Any]) -> None:
    conn = await get_connection()
    try:
        await conn.execute(
            """
            insert into transcripts (session_id, role, message, metadata)
            values ($1, $2, $3, $4)
            """,
            session_id,
            role,
            message,
            metadata,
        )
    finally:
        await conn.close()


async def insert_calendar_action(
    session_id: str,
    action: str,
    event_id: str | None,
    summary: str | None,
    start_time: str | None,
    end_time: str | None,
    stylist: str | None,
    service: str | None,
) -> None:
    conn = await get_connection()
    try:
        await conn.execute(
            """
            insert into calendar_actions (
              session_id, action, event_id, summary, start_time, end_time, stylist, service
            ) values ($1,$2,$3,$4,$5,$6,$7,$8)
            """,
            session_id,
            action,
            event_id,
            summary,
            start_time,
            end_time,
            stylist,
            service,
        )
    finally:
        await conn.close()


async def fetch_transcript(session_id: str) -> list[asyncpg.Record]:
    conn = await get_connection()
    try:
        rows = await conn.fetch(
            """
            select role, message, metadata, created_at
            from transcripts
            where session_id = $1
            order by created_at asc
            """,
            session_id,
        )
        return rows
    finally:
        await conn.close()

