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
        key = "PUSHOVER_USER_KEY"
        logger.warning(f"pushover_user_key not provided, falling back to ${key}")
        pushover_user_key = os.environ[key]

    if not pushover_work_api_key:
        key = "PUSHOVER_WORK_API_KEY"
        logger.warning(f"pushover_work_api_key not provided, falling back to ${key}")
        pushover_work_api_key = os.environ[key]

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
