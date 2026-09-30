import random
import string
import time
import requests

# =========================
# CONFIG
# =========================

DISCORD_WEBHOOK = "PASTE_YOUR_DISCORD_WEBHOOK_HERE"

# Namecheckly public API
API_URL = "https://namecheckly.com/api/check"

# Discord allows lowercase letters, numbers, "_" and "."
CHARACTERS = string.ascii_lowercase + string.digits + "."

# How many names to check each GitHub Actions run
CHECKS_PER_RUN = 5

# Public Namecheckly limit = 5 requests/minute.
# 12 seconds between requests keeps us at <= 5/minute.
DELAY = 12


# =========================
# USERNAME GENERATOR
# =========================

def generate_username():
    while True:
        username = "".join(
            random.choice(CHARACTERS)
            for _ in range(4)
        )

        # Discord username rules
        if len(username) != 4:
            continue

        # No consecutive periods
        if ".." in username:
            continue

        return username


# =========================
# NAMECHECKLY
# =========================

def check_username(username):

    params = {
        "name": username
    }

    try:
        response = requests.get(
            API_URL,
            params=params,
            timeout=20
        )

        print(
            f"Checking {username} | "
            f"HTTP {response.status_code}"
        )

        if response.status_code != 200:
            print(response.text[:500])
            return False

        data = response.json()

        print(data)

        # Try to locate Discord information in the response.
        #
        # Namecheckly can return social-platform results in
        # different structures, so we inspect the returned JSON.

        if isinstance(data, dict):

            # Common structure:
            socials = data.get("socials")

            if isinstance(socials, list):
                for item in socials:

                    if not isinstance(item, dict):
                        continue

                    platform = str(
                        item.get("platform", "")
                    ).lower()

                    if platform == "discord":

                        if item.get("available") is True:
                            return True

                        if str(
                            item.get("status", "")
                        ).lower() in {
                            "available",
                            "free"
                        }:
                            return True

            # Alternative Discord structure
            discord = data.get("discord")

            if isinstance(discord, dict):

                if discord.get("available") is True:
                    return True

                if str(
                    discord.get("status", "")
                ).lower() in {
                    "available",
                    "free"
                }:
                    return True

        return False

    except Exception as e:

        print(
            f"Error checking {username}: {e}"
        )

        return False


# =========================
# DISCORD WEBHOOK
# =========================

def send_to_discord(username):

    message = {
        "content":
            f"🎉 **4L Discord username found!**\n"
            f"`{username}`"
    }

    try:

        response = requests.post(
            DISCORD_WEBHOOK,
            json=message,
            timeout=20
        )

        if response.status_code in (200, 204):

            print(
                f"✅ Sent {username} to Discord"
            )

        else:

            print(
                f"❌ Discord webhook error: "
                f"{response.status_code}"
            )

    except Exception as e:

        print(
            f"Webhook error: {e}"
        )


# =========================
# MAIN
# =========================

def main():

    print(
        "Starting Discord 4L username scanner..."
    )

    checked = set()

    for i in range(CHECKS_PER_RUN):

        username = generate_username()

        while username in checked:
            username = generate_username()

        checked.add(username)

        print(
            f"\n[{i + 1}/{CHECKS_PER_RUN}] "
            f"Testing {username}"
        )

        available = check_username(
            username
        )

        if available:

            print(
                f"🎉 AVAILABLE: {username}"
            )

            send_to_discord(
                username
            )

        else:

            print(
                f"❌ Taken: {username}"
            )

        # Don't wait after the final request
        if i < CHECKS_PER_RUN - 1:

            print(
                f"Waiting {DELAY} seconds..."
            )

            time.sleep(DELAY)


if __name__ == "__main__":
    main()
