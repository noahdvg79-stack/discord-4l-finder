# Discord 4L Username Finder

A GitHub Actions scanner that generates valid 4-character Discord usernames,
checks them through Namecheckly's API, and sends confirmed available names
to a Discord incoming webhook.

## Discord username rules

This project uses the current Discord username rules:

- 2–32 characters
- lowercase `a-z`
- numbers `0-9`
- `_`
- `.`
- no consecutive periods (`..`)

Discord's official documentation gives `.a.b.` as an example of a valid
pattern, so this scanner does **not** incorrectly reject a period at the
beginning or end.

## 1. Create the GitHub repository

1. Go to GitHub.
2. Click **New repository**.
3. Give it a name such as `discord-4l-finder`.
4. Public or private is fine; **private is preferable** because the project
   contains automation configuration.
5. Create the repository.

Upload these files/folders:

```text
discord-4l-finder/
├── .github/
│   └── workflows/
│       └── scanner.yml
├── requirements.txt
├── scanner.py
└── README.md
```

## 2. Create a Discord webhook

In the Discord server/channel where you want alerts:

1. Open the channel settings.
2. Go to **Integrations**.
3. Open **Webhooks**.
4. Create a webhook.
5. Copy its webhook URL.

Treat this URL like a password. Do not put it directly into `scanner.py`
or `scanner.yml`.

## 3. Get a Namecheckly API key

Namecheckly documents its developer API at:

https://namecheckly.com/developers

The API documentation currently says public queries are limited to
5 requests/minute and authenticated requests can use up to 100 requests/minute.

Use your API key as a GitHub Actions secret.

## 4. Add GitHub secrets

In your repository:

**Settings → Secrets and variables → Actions → New repository secret**

Create:

### `NAMECHECKLY_API_KEY`

Value:

```text
YOUR_NAMECHECKLY_API_KEY
```

### `DISCORD_WEBHOOK_URL`

Value:

```text
YOUR_DISCORD_WEBHOOK_URL
```

Do not add quotes around the values.

## 5. Enable Actions

Go to:

**Actions → Find 4L Discord Usernames**

If GitHub asks you to enable workflows, enable it.

You can then click:

**Run workflow**

to test it immediately.

The workflow also runs every 5 minutes.

## 6. How the scanner works

Each run:

1. Generates random valid 4-character usernames.
2. Avoids duplicate candidates within the run.
3. Checks candidates against Namecheckly.
4. Uses concurrent requests for speed.
5. Limits the average request rate to 90/minute, below Namecheckly's
   documented 100/minute authenticated limit.
6. Sends each confirmed available username to the Discord webhook.

Example notification:

```text
🎉 4L Discord username found: `a7_q`
```

## Speed

There are 38 allowed characters:

```text
abcdefghijklmnopqrstuvwxyz
0123456789
_.
```

There are therefore roughly 2 million possible 4-character combinations
before applying the `..` restriction.

The scanner samples the space randomly rather than walking it sequentially.
That means it does not have to start at `aaaa` and slowly work upward.

The GitHub runner does the work, so your computer does not need to stay on.

## Important

An "available" result from Namecheckly should be treated as a candidate to
claim promptly, not a reservation. Availability can change between checking
the name and attempting to claim it on Discord.

Also respect Namecheckly's API limits and terms. Do not increase the request
rate above the documented limit.

If Namecheckly changes its API response format, the `is_available()` function
in `scanner.py` may need to be adjusted.
