
# gw2pvo

**This repository is unmaintained. New maintainer(s) are welcomed.**

gw2pvo is a command line tool to upload solar data from a GoodWe power inverter to the PVOutput.org website.

## Installation

You need to have Python 3 and pip installed. Then:

```shell
sudo pip3 install --upgrade gw2pvo
```

Next determine the Station ID from the GoodWe site as follows. Open the [Sems Portal](https://www.semsportal.com). The Plant Status will reveal the Station ID in the URL. Example:

    https://www.semsportal.com/powerstation/powerstatussnmin/9a6415bf-cdcc-46af-b393-2b442fa89a7f

So the Station ID is `9a6415bf-cdcc-46af-b393-2b442fa89a7f`.

Furthermore, you need a (free) [PVOutput](PVOutput.org) account. Register a device and enable the API. From PVOutput you need:

  1. The API Key
  2. The System Id of your device

### Netatmo

In case you have some Netatmo weather station nearby, you can use it to fetch the local temperature. First you need to create an (free) account at [developers portal](https://dev.netatmo.com/). Next create an app. This gives you a username, password, client_id, and a client_secret, which you need to supply to `gw2pvo`.

You have the option to either let `gw2pvo` find the nearest public weather station, or to select one yourself.

### Dark Sky

Optionally, for actual weather information you can get a (free) [Dark Sky API](https://darksky.net/dev) account. Register and get 1,000 free calls per day. Note that Dark Sky will [shut down](https://blog.darksky.net/dark-sky-has-a-new-home/) it's API in 2021 and does not accept new signups anymore.

## Usage

```shell
usage: gw2pvo [-h] [--config FILE] [--gw-station-id ID]
                   [--gw-account ACCOUNT] [--gw-password PASSWORD]
                   [--pvo-system-id ID] [--pvo-api-key KEY]
                   [--pvo-interval {5,10,15}]
                   [--darksky-api-key DARKSKY_API_KEY]
                   [--netatmo-username NETATMO_USERNAME]
                   [--netatmo-password NETATMO_PASSWORD]
                   [--netatmo-client-id NETATMO_CLIENT_ID]
                   [--netatmo-client-secret NETATMO_CLIENT_SECRET]
                   [--netatmo-device-id NETATMO_DEVICE_ID]
                   [--log {debug,info,warning,critical}] [--date YYYY-MM-DD]
                   [--pv-voltage] [--skip-offline] [--city CITY] [--csv CSV]
                   [--version]

Upload GoodWe power inverter data to PVOutput.org

optional arguments:
  -h, --help            show this help message and exit
  --config FILE         Specify config file
  --gw-station-id ID    GoodWe station ID
  --gw-account ACCOUNT  GoodWe account
  --gw-password PASSWORD
                        GoodWe password
  --pvo-system-id ID    PVOutput system ID
  --pvo-api-key KEY     PVOutput API key
  --pvo-interval {5,10,15}
                        PVOutput interval in minutes
  --darksky-api-key DARKSKY_API_KEY
                        Dark Sky Weather API key
  --netatmo-username NETATMO_USERNAME
                        Netatmo username
  --netatmo-password NETATMO_PASSWORD
                        Netatmo password
  --netatmo-client-id NETATMO_CLIENT_ID
                        Netatmo OAuth client id
  --netatmo-client-secret NETATMO_CLIENT_SECRET
                        Netatmo OAuth client secret
  --netatmo-device-id NETATMO_DEVICE_ID
                        Netatmo device id
  --log {debug,info,warning,critical}
                        Set log level (default info)
  --date YYYY-MM-DD     Copy all readings (max 14/90 days ago)
  --pv-voltage          Send pv voltage instead of grid voltage
  --skip-offline        Skip uploads when inverter is offline
  --city CITY           Sets timezone and skip uploads from dusk till dawn
  --csv CSV             Append readings to a Excel compatible CSV file, DATE
                        in the name will be replaced by the current date
  --version             show program's version number and exit
```

The list of allowed cities can be found in the [Astral documentation](https://astral.readthedocs.io/en/stable/index.html#cities).

### Examples

```shell
gw2pvo --gw-station-id GWID --gw-account ACCOUNT --gw-password PASSWORD --pvo-system-id PVOID --pvo-api-key KEY --log debug
```

If you want to save readings in a daily CSV file:

```shell
gw2pvo --gw-station-id GWID --gw-account ACCOUNT --gw-password PASSWORD --pvo-system-id PVOID --pvo-api-key KEY --csv "Solar DATE.csv"
```

Replace GWID, ACCOUNT, PVOID, PASSWORD, and KEY by the proper values. DATE is a template and will be automatically substituted by the current date.

### Config file

It is more secure to define credentials in a config file instead of adding it to the command line. E.g. if you created `gw2pvo.cfg` as follows:

```ini
[Defaults]
gw_station_id = ...
gw_account = ...
gw_password = ...

pvo_api_key = ...
pvo_system_id = ...

darksky_api_key = ...

city = ...
```

Then this will also upload your inverter data to PVOutput:

```shell
gw2pvo --config gw2pvo.cfg --log debug
```

You can add any argument setting to the config file as you like.

## Automatic uploads

The power graph on PVOutput is not based on the power reading from GoodWe, but on the amount of energy produced this day. This has the advantage that it does not matter if you skip one or more readings.

PVOutput gives you the option to choose to upload each 5, 10, or 15 minutes. Make sure you upload at the same rate as configured at PVOutput.

The inverter updates goodwe-power.com each 8 minutes. The API gives resolution for produced energy of only 0.1 kWh. So for a 5 minute interval we get a resolution of 1200 watt, which is pretty big. To get smooth PVOutput graphs, we apply a running average which depends on the configured PVOutput upload interval time.

### Systemd service

If you run gw2pvo on a Systemd based Linux, you could install the script as a service, like:

```ini
[Unit]
Description=Read GoodWe inverter and upload data to PVOutput.org

[Service]
WorkingDirectory=/home/gw2pvo
ExecStart=/usr/local/bin/gw2pvo --config /etc/gw2pvo.cfg --pvo-interval 5 --skip-offline
Restart=always
RestartSec=300
User=gw2pvo

[Install]
WantedBy=multi-user.target
```

Store the file as ``/etc/systemd/system/gw2pvo.service`` and run:

```shell
sudo useradd -m gw2pvo
sudo systemctl enable gw2pvo
sudo systemctl start gw2pvo
sudo systemctl status gw2pvo
sudo journalctl -u gw2pvo -f
```

## Docker

You can use the [Dockerfile](https://github.com/markruys/gw2pvo/blob/master/Dockerfile) to run a Docker container as follows:

```shell
docker build --tag gw2pvo .
```

Add all settings to config file named `gw2pvo.cfg` like:

```ini
[Defaults]
gw_station_id = ...
gw_account = ...
gw_password = ...

pvo_api_key = ...
pvo_system_id = ...

city = Amsterdam
log = info
pvo_interval = 5
skip_offline = yes
```

Do set `city` to a [valid value](https://astral.readthedocs.io/en/stable/index.html#cities) otherwise the container will use the UTC timezone. Then start the container like:

```shell
docker run --rm -v $(pwd)/gw2pvo.cfg:/gw2pvo.cfg gw2pvo
```

or use docker compose:


```shell
docker compose up -d
```

## Recover missed data

You can copy a day of readings from GoodWe to PVOutput. Interval will be 10 minutes as this is what the API provides. Syntax:

```shell
gw2pvo --config gw2pvo.cfg --date YYYY-MM-DD
```

Beware that the date parameter must be not be older than 14 days from the current date. In donation mode, not more than 90 days.

## Disclaimer and warrenty

Gw2pvo is *not* an official software from GoodWe/Sems and it is not endorsed or supported by this company. Gw2pvo has been written as a personal work. Feel free to improve or adapt it to your own needs.

GoodWe API access is based on the Chinese Sems Swagger documentation: [global](http://globalapi.sems.com.cn:82/swagger/ui/index), [Europe](http://eu.semsportal.com:82/swagger/ui/index#). It could be very well that at a certain point GoodWe decides to alter or disable the API.

The software is provided "as is", without warranty of any kind, express or implied, including but not limited to the warranties of merchantability, fitness for a particular purpose and noninfringement. In no event shall the authors or copyright holders be liable for any claim, damages or other liability, whether in an action of contract, tort or otherwise, arising from, out of or in connection with the software or the use or other dealings in the software.

