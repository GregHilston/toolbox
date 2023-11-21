"""Sends this device's ipv4, ipv6, and hostname to desired email address"""

import argparse

import utils

def parse_args() -> dict[str, any]:
    """Parse arguments

    Returns:
        parsed arguments
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--from_email_address",
        "-f",
        type=str,
    )
    parser.add_argument(
        "--to_email_address",
        "-t",
        type=str,
    )
    return vars(parser.parse_args())

if __name__ == "__main__":
    args = parse_args()

    body = ''
    body += f'IPV4 Address = {utils.get_ipv4_address()}'
    body += f'IPV6 Address = {utils.get_ipv6_address()}'
    body +=  f'hostname = {utils.get_host_name()}'

    subject = f'{utils.get_host_name()} powered on with internet'

    utils.send_email(args['from_email_address'], args['to_email_address'], subject, body)
