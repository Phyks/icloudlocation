#!/usr/bin/env python3
import configparser
import logging
import sys
import urllib.parse

import bottle
import requests

from pyicloud import PyiCloudService
from requests.auth import HTTPBasicAuth


class StoppableCherootServer(bottle.ServerAdapter):
    """
    We need a stoppable HTTP server, which can be stopped from within a route.

    This is not doable out of the box in bottle and is quite hacky using plain
    WSGIRef. This is easier and cleaner with Cheroot (formally CherryPy)
    backend.
    """
    def run(self, handler):  # pragma: no cover
        from cheroot import wsgi
        self.options['bind_addr'] = (self.host, self.port)
        self.options['wsgi_app'] = handler
        self.server = wsgi.Server(**self.options)
        try:
            self.server.start()
        finally:
            self.server.stop()


############################################
# Web app to fetch 2FA code from the user. #
############################################

code_2fa = None  # Global for passing 2FA code from web app to main script
app = bottle.Bottle()
server = None


@app.route('/')
def get_2fa():
    """
    Main HTTP route, display an HTML form to fetch 2FA code from user.
    """
    return """
    <!doctype html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <title>iCloud 2FA protection</title>
</head>
<body>
    <form method="post" action="/2fa">
        <p>
            <label for="2FA">2FA password?</label>
            <input type="text" id="2FA" name="2FA"/>
        </p>
        <input type="submit"/>
    </form>
</body>
</html>"""


@app.post('/2fa')
def set_2fa():
    """
    Handle form submission and store 2FA code to pass along the rest of the
    code.
    """
    global code_2fa
    global server
    code_2fa = bottle.request.forms.get('2FA')
    server.server.stop()
    return "OK"


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
    global server
    global code_2fa
    email = config['apple']['email']
    password = config['apple']['password']
    api = PyiCloudService(email, password=password, cookie_directory=config['apple']['cookie_directory'])

    if api.requires_2fa:
        print(
            "Two-factor authentication required. "
            f"Head over to http://{config['webserver']['host']}:{config['webserver']['port']} and fill-in the 2FA code."
        )
        server = StoppableCherootServer(
            host=config['webserver']['host'],
            port=int(config['webserver']['port'])
        )
        app.run(server=server)
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
                print(
                    "Failed to request trust. "
                    "You will likely be prompted for the code again "
                    "in the coming weeks"
                )
    elif api.requires_2sa:
        import click
        print("Two-step authentication required. Your trusted devices are:")

        devices = api.trusted_devices
        for i, device in enumerate(devices):
            print(
                "  %s: %s" % (
                    i, device.get(
                        'deviceName', "SMS to %s" % device.get('phoneNumber')
                    )
                )
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
        for device in api.devices
        if 'iPhone' in device.status()['name']
    )
    iphone_location = iphone.location()
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
    logging.basicConfig(level=logging.INFO)
    config = load_config()
    iphone_location, iphone_status = get_icloud_location(config)
    store_location_in_nextcloud(config, iphone_location, iphone_status)
