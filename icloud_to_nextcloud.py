#!/usr/bin/env python3
import argparse
import configparser
import logging
import sys
import urllib.parse

import requests

from pyicloud import PyiCloudService
from requests.auth import HTTPBasicAuth


###############
# Main script #
###############

def load_config(config_str=None):
    """
    Load and parse config from string provided. Defaults to reading from stdin.
    """
    if not config_str:
        config_str = sys.stdin.read()
    config = configparser.ConfigParser()
    config.read_string(config_str)
    return config


def get_icloud_location(config):
    """
    Fetch latest iPhone location from iCloud
    """
    email = config['apple']['email']
    password = config['apple']['password']
    code_2fa = config['apple'].get('code_2fa')
    
    api = PyiCloudService(email, password=password, cookie_directory=config['apple']['cookie_directory'])

    if api.requires_2fa:
        print("Two-factor authentication required.")
        if not code_2fa:
            code_2fa = input('code_2fa?')
        result = api.validate_2fa_code(code_2fa)
        print("Code validation result: %s" % result)

        if not result:
            print("Failed to verify security code")
            sys.exit(1)

        if not api.is_trusted_session:
            print("Session is not trusted. Requesting trust...")
            result = api.trust_session()
            print("Session trust result %s" % result)

            if not result:
                print("Failed to request trust. You will likely be prompted for the code again in the coming weeks")
    elif api.requires_2sa:
        import click
        print("Two-step authentication required. Your trusted devices are:")

        devices = api.trusted_devices
        for i, device in enumerate(devices):
            print(
                "  %s: %s" % (i, device.get('deviceName',
                "SMS to %s" % device.get('phoneNumber')))
            )

        device = click.prompt('Which device would you like to use?', default=0)
        device = devices[device]
        if not api.send_verification_code(device):
            print("Failed to send verification code")
            sys.exit(1)

        code = click.prompt('Please enter validation code')
        if not api.validate_verification_code(device, code):
            print("Failed to verify verification code")
            sys.exit(1)

    iphone = next(
            device
            for device in api.devices.values()
            if config['apple']['iPhone_name'] in device.status()['name']
        )
    iphone_location = iphone.location
    iphone_status = iphone.status()

    return iphone_location, iphone_status


def store_location_in_nextcloud(config, iphone_location, iphone_status):
    """
    Store provided iPhone location to Nextcloud.
    """
    if iphone_location is None:
        print('Could not retrieved iPhone location. Try again.')
        sys.exit(1)

    nextcloud_location_args = {
        "user_agent": iphone_status['name'],
        "lat": iphone_location['latitude'],
        "lng": iphone_location['longitude'],
        "accuracy": iphone_location['horizontalAccuracy'],
        "timestamp": iphone_location['timeStamp'] // 1000,
        "altitude": iphone_location['altitude'],
        "battery": iphone_status['batteryLevel'],
    }
    logging.info('Got location data from iCloud: %s.', nextcloud_location_args)
    logging.debug(
        "curl -X POST -u '%s:%s' '%s'",
        config['nextcloud']['user'],
        config['nextcloud']['password'],
        (
            '%s?%s' % (
                urllib.parse.urljoin(
                    config['nextcloud']['server'], '/apps/maps/api/1.0/devices'
                ),
                urllib.parse.urlencode(nextcloud_location_args),
            )
        ),
    )
    r = requests.post(
        urllib.parse.urljoin(
            config['nextcloud']['server'], '/apps/maps/api/1.0/devices'
        ),
        params=nextcloud_location_args,
        auth=HTTPBasicAuth(
            config['nextcloud']['user'], config['nextcloud']['password']
        )
    )
    r.raise_for_status()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog='icloud2Nextcloud')
    parser.add_argument('--config')
    args = parser.parse_args()

    config_str = None
    if args.config is not None:
        with open(args.config, 'r') as fh:
            config_str = fh.read()

    logging.basicConfig(level=logging.INFO)
    config = load_config(config_str)
    iphone_location, iphone_status = get_icloud_location(config)
    store_location_in_nextcloud(config, iphone_location, iphone_status)
