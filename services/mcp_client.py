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
                return resp.json()
    except Exception:
        pass
    return []


def fire_and_forget_ping():
    """Schedule a background health ping without blocking the request."""
    try:
        asyncio.create_task(ping_mcp())
    except RuntimeError:
        pass
