"""Based on the official Push Over documentation https://support.pushover.net/i44-example-code-and-pushover-libraries"""
import argparse
import http.client
import os
import requests
import urllib

def send_notification_requests(message: str="Hello World"):
    response = requests.post(
            "https://api.pushover.net/1/messages.json",
        data = {
            "user": os.environ["PUSHOVER_USER_KEY"],
            "token": os.environ["PUSHOVER_WORK_API_KEY"],
            "message": message
        }
    )
    return response

def send_notification_urllib(message: str="Hello World"):
    conn = http.client.HTTPSConnection("api.pushover.net:443")
    conn.request(
        "POST",
        "/1/messages.json",
        urllib.parse.urlencode(
            {
                "user": os.environ["PUSHOVER_USER_KEY"],
                "token": os.environ["PUSHOVER_WORK_API_KEY"],
                "message": message
            }
        ),
        {
            "Content-type": "application/x-www-form-urlencoded"
        }
    )

    return conn.getresponse().read()

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--message",
        "-m",
        type=str,
    )
    return vars(parser.parse_args())

if __name__ == "__main__":
    args = parse_args()

    response = send_notification_requests(args["message"])
    print(response)