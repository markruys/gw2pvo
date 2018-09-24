
# gw2pvo

gw2pvo is a command line tool to upload solar data from a GoodWe power inverter to the PVOutput.org website.

## Installation

You need to have Python 3 and pip installed. Then:

    pip install https://github.com/markruys/gw2pvo/releases/download/v1.1.0/gw2pvo-1.1.0.tar.gz

Next determine the Station ID from the GoodWe site as follows. Open

    https://www.goodwe-power.com/Mobile/GetMyPowerStationByUser?userName=USERNAME
    https://au.goodwe-power.com/Mobile/GetMyPowerStationByUser?userName=USERNAME
    https://eu.goodwe-power.com/Mobile/GetMyPowerStationByUser?userName=USERNAME

where you substitute your username for USERNAME. As reponse you'll get a JSON string like:

    [{
       "stationId" : "bf9a6415-cdcc-af48-b393-442fa89a2b7f",
       ...
       "currentPower" : "0.700kW",
       "value_eDayTotal" : "1.5kWh"
    }]

Indeed, no password needed, so far for security. Take note of the string within the double quotes after stationId.

Furthermore, you need a (free) [PVOutput](PVOutput.org) account. Register a device and enable the API. From PVOutput you need:

  1. The API Key
  2. The System Id of your device

Optionally, for actual weather information you can get a (free) [Dark Sky API](https://darksky.net/dev) account. Register and get 1,000 free calls per day. From DarkSky you need:
  
  1. Secret API Key

## Usage

```
usage: gw2pvo [-h] --gw-station-id ID --gw-account ACCOUNT --gw-password 
              PASSWORD --pvo-system-id ID --pvo-api-key KEY 
              [--pvo-interval {5,10,15}]
              [--darksky-api-key KEY]
              [--log {debug,info,warning,critical}] [--date YYYY-MM-DD]
              [--skip-offline] [--city CITY] [--csv CSV] [--version]

Upload GoodWe power inverter data to PVOutput.org

optional arguments:
  -h, --help                show this help message and exit
  --gw-station-id ID        GoodWe station ID
  --gw-account ACCOUNT      GoodWe account (e-mail address)
  --gw-password PASSWORD    GoodWe account password
  --pvo-system-id ID        PVOutput system ID
  --pvo-api-key KEY         PVOutput API key
  --pvo-interval {5,10,15}  PVOutput interval in minutes
  --darksky-api-key KEY     DarkSky API key
  --log {debug,info,warning,critical}
                            Set log level (default info)
  --date YYYY-MM-DD         Copy all readings (max 14/90 days ago)
  --skip-offline            Skip uploads when inverter is offline
  --city CITY               Skip uploads from dusk till dawn
  --csv CSV                 Append readings to a Excel compatible CSV file, DATE
                            in the name will be replaced by the current date
  --version                 show program's version number and exit
```

Possible regions are EU, AU, or global.

### Examples

```
gw2pvo --gw-station-id GWID --gw-region global --pvo-system-id PVOID --pvo-api-key KEY --log debug
```

If you want to save readings in a daily CSV file:

```
gw2pvo --gw-station-id GWID --gw-region global --pvo-system-id PVOID --pvo-api-key KEY --csv "Solar DATE.csv"
```

Off course replace GWID, PVOID, and KEY for the proper values. DATE will be automatically substitured by the current date.

## Automatic uploads

The power graph on PVOutput is not based on the power reading from GoodWe, but on the amount of energy produced this day. This has the advantage that it does not matter if you skip one or more readings.

PVOutput gives you the option to choose to upload each 5, 10, or 15 minutes. Make sure you upload at the same rate as configured at PVOutput.

The inverter updates goodwe-power.com each 8 minutes. The API gives resolution for produced energy of only 0.1 kWh. So for a 5 minute interval we get a resolution of 1200 watt, which is pretty big. To get smooth PVOutput graphs, we apply a running average which depends on the configured PVOutput upload interval time.

### Systemd service

If you run gw2pvo on a Systemd based Linux, you could install the script as a service, like:

```
[Unit]
Description=Read GoodWe inverter and upload data to PVOutput.org

[Service]
WorkingDirectory=/home/gw2pvo
ExecStart=/usr/local/bin/gw2pvo --gw-station-id GWID --gw-region global --pvo-system-id PVOID --pvo-api-key KEY --pvo-interval 5
Restart=always
RestartSec=300
User=gw2pvo

[Install]
WantedBy=multi-user.target
```

Store the file as ``/etc/systemd/system/gw2pvo.service`` and run:

    sudo useradd -m gw2pvo
    sudo systemctl enable gw2pvo
    sudo systemctl start gw2pvo
    sudo systemctl status gw2pvo
    sudo journalctl -u gw2pvo -f

## Recover missed data

You can copy a day of readings from GoodWe to PVOutput. Interval will be 10 minutes as this is what the API provides. Syntax:

```
gw2pvo --gw-station-id GWID --gw-region global --pvo-system-id PVOID --pvo-api-key KEY --data YYYY-MM-DD
```

Beware that the date parameter must be not be older than 14 days from the current date. In donation mode, not more than 90 days.

## Docker

Michaël Hompus created a [Docker container](https://hub.docker.com/r/energy164/gw2pvo/) ([Github](https://github.com/eNeRGy164/gw2pvo-docker)) to run gw2pvo.

## Warning

GoodWe access is based on the undocumented API used by mobile apps. It could be very well that at a certain point GoodWe decides to alter or disable the API.
