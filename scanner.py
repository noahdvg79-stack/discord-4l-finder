import asyncio
import json
import os
import random
import string
from typing import Any

import aiohttp

NAMECHECKLY_URL = "https://namecheckly.com/api/check"

# Discord username rules: lowercase a-z, 0-9, "_" and ".";
# no consecutive periods. Discord says leading/trailing periods are allowed.
CHARS = string.ascii_lowercase + string.digits + "_."
LENGTH = 4

# Stay below Namecheckly's documented 100 requests/minute authenticated limit.
# 90 checks/minute gives a little headroom.
REQUESTS_PER_MINUTE = int(os.getenv("REQUESTS_PER_MINUTE", "90"))
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "15"))
MAX_RUN_MINUTES = int(os.getenv("MAX_RUN_MINUTES", "5"))

API_KEY = os.environ["NAMECHECKLY_API_KEY"]
WEBHOOK_URL = os.environ["DISCORD_WEBHOOK_URL"]


def valid_username(name: str) -> bool:
    return (
        len(name) == LENGTH
        and all(c in CHARS for c in name)
        and ".." not in name
    )


def random_candidate() -> str:
    while True:
        candidate = "".join(random.choices(CHARS, k=LENGTH))
        if valid_username(candidate):
            return candidate


def is_available(payload: Any) -> bool:
    """Handle a few plausible API response shapes without assuming one exact schema."""
    if not isinstance(payload, dict):
        return False

    # Expected documented shape is socials[].status / socials[].available.
    socials = payload.get("socials")
    if isinstance(socials, list):
        for item in socials:
            if not isinstance(item, dict):
                continue
            platform = str(item.get("platform", "")).lower()
            if platform and platform != "discord":
                continue

            if item.get("available") is True:
                return True

            status = str(item.get("status", "")).lower()
            if status in {"available", "free"}:
                return True

            # Some APIs use boolean "taken".
            if item.get("taken") is False:
                return True

    # Fallback shapes.
    discord = payload.get("discord")
    if isinstance(discord, dict):
        if discord.get("available") is True:
            return True
        if str(discord.get("status", "")).lower() in {"available", "free"}:
            return True
        if discord.get("taken") is False:
            return True

    return False


async def check(session: aiohttp.ClientSession, username: str) -> tuple[str, bool, str]:
    params = {
        "name": username,
        "platforms": "discord",
    }
    headers = {
        "x-api-key": API_KEY,
        "Accept": "application/json",
    }

    try:
        async with session.get(
            NAMECHECKLY_URL,
            params=params,
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=15),
        ) as response:
            body = await response.text()

            if response.status != 200:
                return username, False, f"HTTP {response.status}: {body[:200]}"

            try:
                data = json.loads(body)
            except json.JSONDecodeError:
                return username, False, "Invalid JSON response"

            return username, is_available(data), ""
    except Exception as exc:
        return username, False, repr(exc)


async def send_webhook(session: aiohttp.ClientSession, username: str) -> None:
    payload = {
        "content": f"🎉 **4L Discord username found:** `{username}`",
        "allowed_mentions": {"parse": []},
    }

    async with session.post(
        WEBHOOK_URL,
        json=payload,
        timeout=aiohttp.ClientTimeout(total=15),
    ) as response:
        if response.status >= 300:
            body = await response.text()
            raise RuntimeError(f"Discord webhook failed: HTTP {response.status}: {body[:300]}")


async def main() -> None:
    # 90/minute by default. We run in batches so the runner doesn't hammer the API.
    delay = 60.0 / max(1, REQUESTS_PER_MINUTE)
    deadline = asyncio.get_running_loop().time() + (MAX_RUN_MINUTES * 60)

    checked: set[str] = set()
    connector = aiohttp.TCPConnector(limit=BATCH_SIZE)
    async with aiohttp.ClientSession(connector=connector) as session:
        while asyncio.get_running_loop().time() < deadline:
            candidates = []
            while len(candidates) < BATCH_SIZE:
                name = random_candidate()
                if name not in checked:
                    checked.add(name)
                    candidates.append(name)

            results = await asyncio.gather(
                *(check(session, name) for name in candidates)
            )

            for username, available, error in results:
                if error:
                    print(f"[WARN] {username}: {error}")
                elif available:
                    print(f"[FOUND] {username}")
                    await send_webhook(session, username)

            # Keep average request rate below the configured ceiling.
            await asyncio.sleep(delay * len(candidates))

    print(f"Checked {len(checked)} unique 4-character candidates this run.")


if __name__ == "__main__":
    asyncio.run(main())
