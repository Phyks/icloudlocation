iCloud to Nextcloud
===================

Apple iCloud "Find My" only lets you see your latest position, but sometimes
you want to scroll back in time and find previous positions. This scripts
autoamtically scrapes your iPhone location from iCloud and stores it in
Nextcloud, so that you get access to the full history.


## Installation

First, git clone and install required dependencies:

```bash
git clone …
cd icloudlocation
python -m venv .venv
./.venv/bin/pip install -r requirements.txt
```

Then, set up the configuration:

```bash
cp config.example.ini config.ini
$EDITOR config.ini
```

Beware that your credentials will be stored in plaintext. You might want to
enable 2FA everywhere and only run it on a trusted machine/environment (disk
encryption, etc.). `cat`ing config in the following commands is here to help
you add an extra layer of security at rest (symmetric GPG, etc.) on your
config file. For the Nextcloud part, you might want to use a dedicated access
token.


Run the program a first time to ensure everything is running smooth:

```bash
cat config.ini | ./.venv/bin/python icloud_to_nextcloud.py
```

_Note:_ If you enabled 2FA on your Apple iCloud account, this first run will
be interactive and requires you explicitly trusting the session from one of
your device.


## Usage

```bash
cat config.ini | ./.venv/bin/python icloud_to_nextcloud.py
```

Use a `cron` daemon to run it periodically at the frequency of your choice.


## License

Code published under an MIT license.

```
Copyright 2024 Phyks

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
```