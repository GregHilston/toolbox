import json

import requests

from secrets.secrets import grehg_xyz_slack_webhook_url


def send_message_to_grehg_xyz_slack(channel: str, text: str):
    """Sends a message to our Grehg XYZ Slack team"""
    data = {
        "channel": channel,
        "username": "webhookbot",
        "text": text,
        "icon_emoji": "ghost"
    }
    payload = json.dumps(data)
    requests.post(grehg_xyz_slack_webhook_url, data=payload)
