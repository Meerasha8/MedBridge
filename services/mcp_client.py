import asyncio
import time
import httpx
from fastapi import HTTPException

import config

_HEADERS = {"X-MCP-Key": config.MCP_SECRET_KEY, "Content-Type": "application/json"}


async def call_tool(tool_name: str, payload: dict) -> dict | list:
    url = f"{config.MCP_SERVER_URL}/tools/{tool_name}"
    async with httpx.AsyncClient(timeout=config.MCP_HTTP_TIMEOUT) as client:
        try:
            resp = await client.post(url, headers=_HEADERS, json=payload)
        except httpx.TimeoutException:
            await asyncio.sleep(5)
            try:
                resp = await client.post(url, headers=_HEADERS, json=payload)
            except httpx.TimeoutException:
                raise HTTPException(
                    status_code=503,
                    detail="Health service is starting up. Please try again in 30 seconds.",
                )
        if resp.status_code != 200:
            try:
                detail = resp.json()
            except Exception:
                detail = resp.text
            raise HTTPException(status_code=resp.status_code, detail=f"MCP error: {detail}")
        return resp.json()


async def ping_mcp() -> float:
    start = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=config.MCP_HTTP_TIMEOUT) as client:
            await client.get(f"{config.MCP_SERVER_URL}/health", headers=_HEADERS)
        return time.monotonic() - start
    except Exception:
        return 999.0


async def fetch_tool_schemas() -> list:
    try:
        async with httpx.AsyncClient(timeout=config.MCP_HTTP_TIMEOUT) as client:
            resp = await client.get(f"{config.MCP_SERVER_URL}/tools", headers=_HEADERS)
            if resp.status_code == 200:
                data = resp.json()
                return _normalize_tool_list(data)
    except Exception:
        pass
    return []


def _normalize_tool_list(data) -> list:
    """The MCP server's /tools endpoint might return a bare list, or a dict
    wrapping the list under a key like "tools"/"data"/"results". Handle all
    of those shapes so callers always get a clean list of tool-schema dicts."""
    if isinstance(data, list):
        return [t for t in data if isinstance(t, dict)]
    if isinstance(data, dict):
        for key in ("tools", "data", "results", "items"):
            value = data.get(key)
            if isinstance(value, list):
                return [t for t in value if isinstance(t, dict)]
        # Maybe the dict itself is a single tool schema.
        if "name" in data or "tool_name" in data:
            return [data]
    return []


def fire_and_forget_ping():
    """Schedule a background health ping without blocking the request."""
    try:
        asyncio.create_task(ping_mcp())
    except RuntimeError:
        pass
