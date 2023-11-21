"""
Based on the official Push Over documentation
https://support.pushover.net/i44-example-code-and-pushover-libraries
"""
import argparse

from utils import send_pushover_notification

def parse_args() -> dict[str, any]:
    """Parse arguments

    Returns:
        parsed arguments
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--message",
        "-m",
        type=str,
    )
    return vars(parser.parse_args())

if __name__ == "__main__":
    args = parse_args()

    response = send_pushover_notification(args["message"])
    print(response)