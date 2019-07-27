#!/usr/bin/env python3

import sys
import logging
import argparse
import locale
import time
from datetime import datetime
from astral import Astral
from gw2pvo import ds_api
from gw2pvo import gw_api
from gw2pvo import gw_csv
from gw2pvo import pvo_api
from gw2pvo import __version__

__author__ = "Mark Ruys"
__copyright__ = "Copyright 2017-2018, Mark Ruys"
__license__ = "MIT"
__email__ = "mark@paracas.nl"

last_eday_kwh = 0

def run_once(args):
    global last_eday_kwh

    # Check if we only want to run during daylight
    if args.city:
        a = Astral()
        sun = a[args.city].sun(local=True)
        now = datetime.time(datetime.now())
        if now < sun['dawn'].time() or now > sun['dusk'].time():
            logging.debug("Skipped upload as it's night")
            return

    # Fetch the last reading from GoodWe
    gw = gw_api.GoodWeApi(args.gw_station_id, args.gw_account, args.gw_password)
    data = gw.getCurrentReadings()

    # Check if we want to abort when offline
    if args.skip_offline:
        if data['status'] == 'Offline':
            logging.debug("Skipped upload as the inverter is offline")
            return

    # Append reading to CSV file
    if args.csv:
        if data['status'] == 'Offline':
            logging.debug("Don't append offline data to CSV file")
        else:
            locale.setlocale(locale.LC_ALL, locale.getlocale())
            csv = gw_csv.GoodWeCSV(args.csv)
            csv.append(data)

    # Submit reading to PVOutput, if they differ from the previous set
    eday_kwh = data['eday_kwh']
    if data['pgrid_w'] == 0 and abs(eday_kwh - last_eday_kwh) < 0.001:
        logging.debug("Ignore unchanged reading")
    else:
        last_eday_kwh = eday_kwh

    if args.darksky_api_key:
        ds = ds_api.DarkSkyApi(args.darksky_api_key)
        data['temperature'] = ds.get_temperature(data['latitude'], data['longitude'])
        
    voltage = data['grid_voltage']
    if args.pv_voltage:
        voltage=data['pv_voltage']

    pvo = pvo_api.PVOutputApi(args.pvo_system_id, args.pvo_api_key)
    pvo.add_status(data['pgrid_w'], last_eday_kwh, data.get('temperature'), voltage)

def copy(args):
    # Fetch readings from GoodWe
    if args.date == "yesterday":
    	date = datetime.today() - timedelta(days=1)
    else:
        date = datetime.strptime(args.date, "%Y-%m-%d")

    gw = gw_api.GoodWeApi(args.gw_station_id, args.gw_account, args.gw_password)
    data = gw.getDayReadings(date)

    if args.darksky_api_key:
        ds = ds_api.DarkSkyApi(args.darksky_api_key)
        temperatures = ds.get_temperature_for_day(data['latitude'], data['longitude'], date)
    else:
        temperatures = None

    # Submit readings to PVOutput
    pvo = pvo_api.PVOutputApi(args.pvo_system_id, args.pvo_api_key)
    pvo.add_day(data['entries'], temperatures)

def run():

    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Upload GoodWe power inverter data to PVOutput.org")
    parser.add_argument("--gw-station-id", help="GoodWe station ID", metavar='ID', required=True)
    parser.add_argument("--gw-account", help="GoodWe account", metavar='ACCOUNT', required=True)
    parser.add_argument("--gw-password", help="GoodWe password", metavar='PASSWORD', required=True)
    parser.add_argument("--pvo-system-id", help="PVOutput system ID", metavar='ID', required=True)
    parser.add_argument("--pvo-api-key", help="PVOutput API key", metavar='KEY', required=True)
    parser.add_argument("--pvo-interval", help="PVOutput interval in minutes", type=int, choices=[5, 10, 15])
    parser.add_argument("--darksky-api-key", help="Dark Sky Weather API key")
    parser.add_argument("--log", help="Set log level (default info)", choices=['debug', 'info', 'warning', 'critical'], default="info")
    parser.add_argument("--date", help="Copy all readings (max 14/90 days ago)", metavar='YYYY-MM-DD')
    parser.add_argument("--pv-voltage", help="Send pv voltage instead of grid voltage", action='store_true')
    parser.add_argument("--skip-offline", help="Skip uploads when inverter is offline", action='store_true')
    parser.add_argument("--city", help="Skip uploads from dusk till dawn")
    parser.add_argument('--csv', help="Append readings to a Excel compatible CSV file, DATE in the name will be replaced by the current date")
    parser.add_argument('--version', action='version', version='%(prog)s ' + __version__)
    args = parser.parse_args()

    # Configure the logging
    numeric_level = getattr(logging, args.log.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError('Invalid log level: %s' % loglevel)
    logging.basicConfig(format='%(levelname)-8s %(message)s', level=numeric_level)

    # Check if we're running the supported Python version
    if sys.version_info[0] != 3:
        logging.error("Please use Python 3 to run this script")
        sys.exit()

    # Check if we want to copy old data
    if args.date:
        copy(args)
        sys.exit()

    startTime = datetime.now()

    while True:
        try:
            run_once(args)
        except Exception as exp:
            logging.error(exp)

        if args.pvo_interval is None:
            break

        interval = args.pvo_interval * 60
        time.sleep(interval - (datetime.now() - startTime).seconds % interval)

if __name__ == "__main__":
    run()
