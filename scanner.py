import itertools
import json
import os
import string
import time

import requests


# ============================================================
# CONFIG
# ============================================================

APIFY_TOKEN = os.environ["APIFY_TOKEN"]
DISCORD_WEBHOOK = os.environ["DISCORD_WEBHOOK"]

# Apify actor
ACTOR_ID = "neverempty~discord-username-checker"

# Number of usernames sent to Apify per request.
#
# 100 is a good balance between speed and the 5-minute
# synchronous API timeout.
BATCH_SIZE = 100

# Delay between batches.
BATCH_DELAY = 2

# 4-character Discord username alphabet.
#
# Discord allows:
# a-z
# 0-9
# _
# .
CHARACTERS = (
    string.ascii_lowercase
    + string.digits
    + "_."
)

USERNAME_LENGTH = 4

# Don't generate these.
# We keep the generator conservative.
FORBIDDEN_SUBSTRINGS = {
    "..",
}


# ============================================================
# APIFY API
# ============================================================

APIFY_URL = (
    "https://api.apify.com/v2/actors/"
    f"{ACTOR_ID}/run-sync-get-dataset-items"
)


# ============================================================
# VALIDATION
# ============================================================

def valid_username(username):
    if len(username) != 4:
        return False

    if any(
        character not in CHARACTERS
        for character in username
    ):
        return False

    for forbidden in FORBIDDEN_SUBSTRINGS:
        if forbidden in username:
            return False

    # Conservative generation:
    # don't start/end with a period.
    if username.startswith("."):
        return False

    if username.endswith("."):
        return False

    return True


# ============================================================
# GENERATE ALL VALID 4L USERNAMES
# ============================================================

def username_generator():

    for characters in itertools.product(
        CHARACTERS,
        repeat=USERNAME_LENGTH
    ):

        username = "".join(characters)

        if valid_username(username):
            yield username


# ============================================================
# DISCORD WEBHOOK
# ============================================================

def send_to_discord(username):

    payload = {
        "content": (
            "🎉 **4L DISCORD USERNAME FOUND**\n"
            f"```{username}```"
        )
    }

    try:

        response = requests.post(
            DISCORD_WEBHOOK,
            json=payload,
            timeout=15
        )

        if response.status_code in (200, 204):

            print(
                f"[WEBHOOK] Sent: {username}",
                flush=True
            )

        else:

            print(
                f"[WEBHOOK ERROR] "
                f"HTTP {response.status_code}",
                flush=True
            )

    except Exception as error:

        print(
            f"[WEBHOOK ERROR] {error}",
            flush=True
        )


# ============================================================
# CHECK A BATCH
# ============================================================

def check_batch(usernames):

    payload = {
        "usernames": usernames
    }

    headers = {
        "Authorization":
            f"Bearer {APIFY_TOKEN}",

        "Content-Type":
            "application/json"
    }

    print(
        f"[APIFY] Checking "
        f"{len(usernames)} usernames...",
        flush=True
    )

    try:

        response = requests.post(
            APIFY_URL,
            headers=headers,
            json=payload,
            timeout=290
        )

    except requests.RequestException as error:

        print(
            f"[APIFY ERROR] {error}",
            flush=True
        )

        return []

    if response.status_code != 200:

        print(
            f"[APIFY ERROR] "
            f"HTTP {response.status_code}",
            flush=True
        )

        print(
            response.text[:1000],
            flush=True
        )

        return []

    try:

        results = response.json()

    except json.JSONDecodeError:

        print(
            "[APIFY ERROR] "
            "Response wasn't JSON.",
            flush=True
        )

        return []

    if not isinstance(results, list):

        print(
            "[APIFY ERROR] "
            "Unexpected response:",
            flush=True
        )

        print(
            results,
            flush=True
        )

        return []

    return results


# ============================================================
# PROCESS RESULTS
# ============================================================

def process_results(results):

    found = 0

    for result in results:

        if not isinstance(result, dict):
            continue

        username = str(
            result.get(
                "username",
                ""
            )
        ).lower()

        available = result.get(
            "available"
        )

        status = result.get(
            "status",
            ""
        )

        # ----------------------------------------------------
        # AVAILABLE
        # ----------------------------------------------------

        if available is True:

            print(
                "",
                flush=True
            )

            print(
                "======================================",
                flush=True
            )

            print(
                f"🎉 AVAILABLE: {username}",
                flush=True
            )

            print(
                "======================================",
                flush=True
            )

            send_to_discord(
                username
            )

            found += 1

        # ----------------------------------------------------
        # TAKEN
        # ----------------------------------------------------

        elif status == "taken":

            print(
                f"[TAKEN] {username}",
                flush=True
            )

        # ----------------------------------------------------
        # INVALID
        # ----------------------------------------------------

        elif status == "invalid":

            print(
                f"[INVALID] {username}",
                flush=True
            )

        # ----------------------------------------------------
        # RATE LIMITED / NOT CHECKED
        # ----------------------------------------------------

        else:

            print(
                f"[NOT CHECKED] "
                f"{username} "
                f"status={status}",
                flush=True
            )

    return found


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "=" * 60,
        flush=True
    )

    print(
        "DISCORD 4L FINDER - APIFY EDITION",
        flush=True
    )

    print(
        "=" * 60,
        flush=True
    )

    print(
        f"Batch size: {BATCH_SIZE}",
        flush=True
    )

    print(
        "Generating valid 4-character usernames...",
        flush=True
    )

    generator = username_generator()

    checked = 0
    found = 0
    batch_number = 0

    while True:

        batch = list(
            itertools.islice(
                generator,
                BATCH_SIZE
            )
        )

        # We've reached the end of the
        # generated username space.
        if not batch:

            print(
                "",
                flush=True
            )

            print(
                "======================================",
                flush=True
            )

            print(
                "FINISHED THE ENTIRE 4L SEARCH SPACE",
                flush=True
            )

            print(
                f"Checked: {checked}",
                flush=True
            )

            print(
                f"Found: {found}",
                flush=True
            )

            print(
                "======================================",
                flush=True
            )

            break

        batch_number += 1

        print(
            "",
            flush=True
        )

        print(
            f"========== BATCH {batch_number} ==========",
            flush=True
        )

        print(
            f"First: {batch[0]}",
            flush=True
        )

        print(
            f"Last:  {batch[-1]}",
            flush=True
        )

        results = check_batch(
            batch
        )

        checked += len(batch)

        found += process_results(
            results
        )

        print(
            "",
            flush=True
        )

        print(
            f"[PROGRESS] "
            f"Checked: {checked} | "
            f"Found: {found}",
            flush=True
        )

        time.sleep(
            BATCH_DELAY
        )


if __name__ == "__main__":

    main()
