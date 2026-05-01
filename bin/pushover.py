# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "requests",
#     "loguru",
# ]
# ///
"""Send a push notification via the Pushover API"""

import argparse
import os

import requests
from loguru import logger


def send_pushover_notification(
    message: str = "Hello World",
    pushover_user_key: str | None = None,
    pushover_work_api_key: str | None = None,
):
    if not pushover_user_key:
        pushover_user_key = os.environ.get("PUSHOVER_USER_KEY")
    if not pushover_work_api_key:
        pushover_work_api_key = os.environ.get("PUSHOVER_WORK_API_KEY")

    if not pushover_user_key or not pushover_work_api_key:
        logger.error(
            "PUSHOVER_USER_KEY and/or PUSHOVER_WORK_API_KEY not set. "
            "Run `just secrets` in ~/Git/toolbox/nixos to generate secrets from 1Password, "
            "then open a new terminal (secrets are auto-loaded via .zshrc)."
        )
        raise SystemExit(1)

    return requests.post(
        "https://api.pushover.net/1/messages.json",
        data={
            "user": pushover_user_key,
            "token": pushover_work_api_key,
            "message": message,
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Send a Pushover notification")
    parser.add_argument("--message", "-m", type=str, required=True)
    args = parser.parse_args()

    response = send_pushover_notification(args.message)
    print(response)
