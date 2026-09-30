import asyncio
import os
import random
import string
import aiohttp

# ============================================================
# CONFIGURATION
# ============================================================

WEBHOOK_URL = os.environ["DISCORD_WEBHOOK"]

# Number of simultaneous checks.
#
# Start at 5. If Discord returns 429 rate limits, the program
# automatically waits for the requested amount of time.
CONCURRENCY = 5

# We only want 4-character usernames.
USERNAME_LENGTH = 4

# Discord username characters.
CHARACTERS = (
    string.ascii_lowercase
    + string.digits
    + "_."
)

# Discord's username availability endpoint.
DISCORD_URL = (
    "https://discord.com/api/v9/"
    "unique-username/username-attempt-unauthed"
)


# ============================================================
# USERNAME VALIDATION
# ============================================================

def valid_username(username: str) -> bool:
    """
    Check whether a generated username follows the basic
    Discord username character rules.
    """

    # Exactly 4 characters.
    if len(username) != USERNAME_LENGTH:
        return False

    # Only allowed characters.
    if any(
        character not in CHARACTERS
        for character in username
    ):
        return False

    # Discord doesn't allow consecutive periods.
    if ".." in username:
        return False

    # Don't generate leading/trailing periods.
    # This keeps the generated pool conservative.
    if username.startswith("."):
        return False

    if username.endswith("."):
        return False

    return True


def generate_username() -> str:
    """
    Generate a random valid 4-character username.
    """

    while True:

        username = "".join(
            random.choice(CHARACTERS)
            for _ in range(USERNAME_LENGTH)
        )

        if valid_username(username):
            return username


# ============================================================
# DISCORD CHECK
# ============================================================

async def check_username(
    session: aiohttp.ClientSession,
    username: str
):
    """
    Ask Discord whether a username is taken.

    Returns:

        ("available", retry_after)
        ("taken", 0)
        ("rate_limit", retry_after)
        ("error", retry_after)
    """

    payload = {
        "username": username
    }

    try:

        async with session.post(
            DISCORD_URL,
            json=payload,
            headers={
                "Content-Type": "application/json"
            },
            timeout=aiohttp.ClientTimeout(
                total=10,
                connect=5
            )
        ) as response:

            # ------------------------------------------------
            # RATE LIMIT
            # ------------------------------------------------

            if response.status == 429:

                try:
                    data = await response.json()

                    retry_after = float(
                        data.get(
                            "retry_after",
                            5
                        )
                    )

                except Exception:

                    retry_after = 5

                print(
                    f"[429] Discord rate limit "
                    f"for {username}; "
                    f"waiting {retry_after:.2f}s",
                    flush=True
                )

                return (
                    "rate_limit",
                    retry_after
                )

            # ------------------------------------------------
            # SUCCESS
            # ------------------------------------------------

            if response.status == 200:

                try:

                    data = await response.json()

                except Exception:

                    print(
                        f"[ERROR] Invalid JSON "
                        f"for {username}",
                        flush=True
                    )

                    return (
                        "error",
                        0
                    )

                print(
                    f"[CHECK] {username} -> {data}",
                    flush=True
                )

                # Discord endpoint returns:
                #
                # {"taken": true}
                #
                # or
                #
                # {"taken": false}

                if data.get("taken") is False:

                    return (
                        "available",
                        0
                    )

                if data.get("taken") is True:

                    return (
                        "taken",
                        0
                    )

                # Some implementations/API versions can return
                # an alternative field.
                if data.get(
                    "username_exists"
                ) is False:

                    return (
                        "available",
                        0
                    )

                if data.get(
                    "username_exists"
                ) is True:

                    return (
                        "taken",
                        0
                    )

                print(
                    f"[UNKNOWN] Unexpected response "
                    f"for {username}: {data}",
                    flush=True
                )

                return (
                    "error",
                    0
                )

            # ------------------------------------------------
            # OTHER HTTP STATUS
            # ------------------------------------------------

            body = await response.text()

            print(
                f"[HTTP {response.status}] "
                f"{username}: "
                f"{body[:300]}",
                flush=True
            )

            return (
                "error",
                0
            )

    except asyncio.TimeoutError:

        print(
            f"[TIMEOUT] {username}",
            flush=True
        )

        return (
            "error",
            0
        )

    except aiohttp.ClientError as error:

        print(
            f"[NETWORK ERROR] "
            f"{username}: {error}",
            flush=True
        )

        return (
            "error",
            0
        )

    except Exception as error:

        print(
            f"[ERROR] "
            f"{username}: {error}",
            flush=True
        )

        return (
            "error",
            0
        )


# ============================================================
# DISCORD WEBHOOK
# ============================================================

async def send_webhook(
    session: aiohttp.ClientSession,
    username: str
):

    payload = {
        "content": (
            "🎉 **4L DISCORD USERNAME FOUND**\n"
            f"```{username}```"
        )
    }

    try:

        async with session.post(
            WEBHOOK_URL,
            json=payload,
            timeout=aiohttp.ClientTimeout(
                total=10
            )
        ) as response:

            if response.status in (
                200,
                204
            ):

                print(
                    f"[WEBHOOK] Sent {username}",
                    flush=True
                )

            else:

                body = await response.text()

                print(
                    f"[WEBHOOK ERROR] "
                    f"HTTP {response.status}: "
                    f"{body[:300]}",
                    flush=True
                )

    except Exception as error:

        print(
            f"[WEBHOOK ERROR] "
            f"{error}",
            flush=True
        )


# ============================================================
# WORKER
# ============================================================

async def worker(
    session: aiohttp.ClientSession,
    worker_id: int,
    checked: set,
    checked_lock: asyncio.Lock
):

    while True:

        # ---------------------------------------------
        # Generate a username that hasn't been checked
        # by another worker.
        # ---------------------------------------------

        while True:

            username = generate_username()

            async with checked_lock:

                if username not in checked:

                    checked.add(username)

                    break

        print(
            f"[WORKER {worker_id}] "
            f"Testing {username}",
            flush=True
        )

        # ---------------------------------------------
        # Check Discord
        # ---------------------------------------------

        status, retry_after = (
            await check_username(
                session,
                username
            )
        )

        # ---------------------------------------------
        # AVAILABLE
        # ---------------------------------------------

        if status == "available":

            print(
                "",
                flush=True
            )

            print(
                "🎉🎉🎉🎉🎉🎉🎉🎉",
                flush=True
            )

            print(
                f"AVAILABLE: {username}",
                flush=True
            )

            print(
                "🎉🎉🎉🎉🎉🎉🎉🎉",
                flush=True
            )

            print(
                "",
                flush=True
            )

            await send_webhook(
                session,
                username
            )

        # ---------------------------------------------
        # TAKEN
        # ---------------------------------------------

        elif status == "taken":

            print(
                f"[TAKEN] {username}",
                flush=True
            )

        # ---------------------------------------------
        # RATE LIMITED
        # ---------------------------------------------

        elif status == "rate_limit":

            # Discord has told us how long to wait.
            await asyncio.sleep(
                max(
                    retry_after,
                    1
                )
            )

        # ---------------------------------------------
        # ERROR
        # ---------------------------------------------

        else:

            # Small pause so a temporary network error
            # doesn't create a tight loop.
            await asyncio.sleep(1)


# ============================================================
# MAIN
# ============================================================

async def main():

    print(
        "=" * 60,
        flush=True
    )

    print(
        "DISCORD 4L USERNAME FINDER",
        flush=True
    )

    print(
        "CONTINUOUS MODE",
        flush=True
    )

    print(
        "=" * 60,
        flush=True
    )

    print(
        f"Workers: {CONCURRENCY}",
        flush=True
    )

    print(
        "Checking Discord directly.",
        flush=True
    )

    print(
        "The scanner will continue until "
        "the GitHub job is stopped.",
        flush=True
    )

    print(
        "=" * 60,
        flush=True
    )

    checked = set()

    checked_lock = asyncio.Lock()

    connector = aiohttp.TCPConnector(
        limit=CONCURRENCY,
        limit_per_host=CONCURRENCY,
        ttl_dns_cache=300
    )

    async with aiohttp.ClientSession(
        connector=connector
    ) as session:

        workers = []

        for worker_id in range(
            1,
            CONCURRENCY + 1
        ):

            task = asyncio.create_task(
                worker(
                    session,
                    worker_id,
                    checked,
                    checked_lock
                )
            )

            workers.append(task)

        await asyncio.gather(
            *workers
        )


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    try:

        asyncio.run(
            main()
        )

    except KeyboardInterrupt:

        print(
            "",
            flush=True
        )

        print(
            "Scanner stopped.",
            flush=True
        )
