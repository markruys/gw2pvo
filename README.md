
# gw2pvo

gw2pvo is a command line tool to upload solar data from a GoodWe power inverter to the PVOutput.org website.

## Installation

You need to have Python (2.7 or 3.*) and pip installed. Then:

    pip install gw2pvo

Next determine the Station ID from the GoodWe site as follows. Open

    www.goodwe-power.com/Mobile/GetMyPowerStationByUser?userName=USERNAME

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


## Usage

```
usage: gw2pvo [-h] --gw-station-id ID --pvo-system-id ID --pvo-api-key KEY
                   [--log {debug,info,warning,critical}] [--skip-offline]
                   [--city CITY] [--csv CSV] [--version]

Upload GoodWe power inverter data to PVOutput.org

optional arguments:
  -h, --help            show this help message and exit
  --gw-station-id ID    GoodWe station ID
  --pvo-system-id ID    PVOutput system ID
  --pvo-api-key KEY     PVOutput API key
  --pvo-interval {5,10,15}
                        PVOutput interval in minutes
  --log {debug,info,warning,critical}
                        Set log level (default info)
  --skip-offline        Skip uploads when inverter is offline
  --city CITY           Skip uploads from dusk till dawn
  --csv CSV             Add readings to a Excel compatible CSV file, DATE in
                        the name will be replaced by the current date
  --version             show program's version number and exit

```

### Examples

```
gw2pvo --gw-station-id GWID --pvo-system-id PVOID --pvo-api-key KEY --log debug
```

If you want to save readings in a daily CSV file:

```
gw2pvo --gw-station-id GWID --pvo-system-id PVOID --pvo-api-key KEY --csv "Solar DATE.csv"
```

Off course replace GWID, PVOID, and KEY for the proper values. DATE will be automatically substitured by the current date.

## Automatic uploads

The power graph on PVOutput is not based on the power reading from GoodWe, but on the amount of energy produced this day. This has the advantage that it does not matter if you skip one or more readings.

The inverter updates goodwe-power.com each 8 minutes. PVOutput gives you the option to choose to upload each 5, 10, or 15 minutes. Make sure you upload at the same rate as configured at PVOutput.

### Systemd service
If you run gw2pvo on a Systemd scheduler, you could install the script as a service, like:

```
[Unit]
Description=Read GoodWe inverter and upload data to PVOutput

[Service]
WorkingDirectory=/home/gw2pvo
ExecStart=/usr/local/bin/gw2pvo --gw-station-id GWID --pvo-system-id PVOID --pvo-api-key KEY --pvo-interval INTERVAL
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

## Inspiration

  * [Capturing Solar Generation Data from the GoodWe Portal](http://persistantillusion.blogspot.nl/2015/06/capturing-solar-generation-data-from.html)
  * [The Internet-of-Things I don't really like](https://brnrd.eu/misc/2016-03-13/goodwe-logging-to-pvoutput.html)
