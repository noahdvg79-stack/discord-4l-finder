import asyncio
import os
import random
import string
import aiohttp

# ============================================================
# CONFIG
# ============================================================

WEBHOOK_URL = os.environ["https://discord.com/api/webhooks/1554879248651518053/ob6LqXxWjZuC9S884yUvWwWf5VyqT-5TZNZBYs8qKPC_i-TY1YqInBrbhLnK0aJf4gGO"]

# Number of simultaneous requests.
# Start with 5. The program automatically backs off on 429s.
CONCURRENCY = 5

# 4-character usernames
LENGTH = 4

# Discord username characters
CHARACTERS = string.ascii_lowercase + string.digits + "_."

# ============================================================
# USERNAME GENERATOR
# ============================================================

def valid_username(username):
    if len(username) != 4:
        return False

    if any(c not in CHARACTERS for c in username):
        return False

    # Don't allow consecutive periods
    if ".." in username:
        return False

    # Don't allow periods at either end
    if username.startswith(".") or username.endswith("."):
        return False

    return True


def generate_username():
    while True:
        username = "".join(
            random.choice(CHARACTERS)
            for _ in range(LENGTH)
        )

        if valid_username(username):
            return username


# ============================================================
# DISCORD AVAILABILITY CHECK
# ============================================================

URL = (
    "https://discord.com/api/v9/"
    "unique-username/username-attempt-unauthed"
)


async def check_username(session, username):

    payload = {
        "username": username
    }

    try:

        async with session.post(
            URL,
            json=payload,
            timeout=aiohttp.ClientTimeout(total=15)
        ) as response:

            # Rate limited
            if response.status == 429:

                try:
                    data = await response.json()

                    retry_after = float(
                        data.get("retry_after", 5)
                    )

                except Exception:
                    retry_after = 5

                print(
                    f"[RATE LIMIT] Waiting "
                    f"{retry_after:.1f}s"
                )

                return username, "rate_limit", retry_after

            # Successful request
            if response.status == 200:

                try:
                    data = await response.json()
                except Exception:
                    return username, "unknown", 0

                print(
                    f"[CHECK] {username} -> {data}"
                )

                # Discord's response normally contains
                # a boolean indicating whether the username
                # can be used.
                if data.get("taken") is False:
                    return username, "available", 0

                if data.get("taken") is True:
                    return username, "taken", 0

                # Some responses use username_exists
                if data.get("username_exists") is False:
                    return username, "available", 0

                if data.get("username_exists") is True:
                    return username, "taken", 0

                return username, "unknown", 0

            print(
                f"[HTTP {response.status}] "
                f"{username}"
            )

            return username, "unknown", 0

    except asyncio.TimeoutError:

        print(
            f"[TIMEOUT] {username}"
        )

        return username, "unknown", 0

    except Exception as e:

        print(
            f"[ERROR] {username}: {e}"
        )

        return username, "unknown", 0


# ============================================================
# DISCORD WEBHOOK
# ============================================================

async def send_webhook(session, username):

    payload = {
        "content":
            f"🎉 **4L AVAILABLE**\n"
            f"```{username}```\n"
            f"Grab it immediately!"
    }

    try:

        async with session.post(
            WEBHOOK_URL,
            json=payload,
            timeout=aiohttp.ClientTimeout(total=15)
        ) as response:

            if response.status in (200, 204):

                print(
                    f"[FOUND] {username} "
                    f"-> sent to Discord"
                )

            else:

                print(
                    f"[WEBHOOK ERROR] "
                    f"HTTP {response.status}"
                )

    except Exception as e:

        print(
            f"[WEBHOOK ERROR] {e}"
        )


# ============================================================
# CONTINUOUS SCANNER
# ============================================================

async def worker(
    session,
    semaphore,
    checked
):

    while True:

        username = generate_username()

        # Avoid checking the same name repeatedly
        # during this runner session.
        if username in checked:
            continue

        checked.add(username)

        async with semaphore:

            result = await check_username(
                session,
                username
            )

        username, status, retry_after = result

        if status == "available":

            print(
                f"\n🎉🎉🎉 AVAILABLE: "
                f"{username}\n"
            )

            await send_webhook(
                session,
                username
            )

        elif status == "taken":

            print(
                f"[TAKEN] {username}"
            )

        elif status == "rate_limit":

            # Everyone waits when Discord tells us
            # to slow down.
            await asyncio.sleep(
                max(retry_after, 1)
            )

        else:

            print(
                f"[UNKNOWN] {username}"
            )


# ============================================================
# MAIN
# ============================================================

async def main():

    print("=" * 60)
    print("DISCORD 4L USERNAME FINDER")
    print("Continuous mode")
    print("=" * 60)

    print(
        f"Concurrency: {CONCURRENCY}"
    )

    print(
        "Press Cancel workflow in GitHub "
        "to stop it."
    )

    connector = aiohttp.TCPConnector(
        limit=CONCURRENCY
    )

    semaphore = asyncio.Semaphore(
        CONCURRENCY
    )

    checked = set()

    async with aiohttp.ClientSession(
        connector=connector
    ) as session:

        workers = [
            asyncio.create_task(
                worker(
                    session,
                    semaphore,
                    checked
                )
            )
            for _ in range(CONCURRENCY)
        ]

        await asyncio.gather(
            *workers
        )


if __name__ == "__main__":

    try:
        asyncio.run(main())

    except KeyboardInterrupt:

        print(
            "\nScanner stopped."
        )
