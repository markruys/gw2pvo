
import logging
import argparse
import locale
import datetime
from astral import Astral
from gw2pvo import gw_api
from gw2pvo import gw_csv
from gw2pvo import pvo_api
from gw2pvo import __version__

def run():

    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Upload GoodWe power inverter data to PVOutput.org")
    parser.add_argument("--gw-station-id", help="GoodWe station ID", metavar='ID', required=True)
    parser.add_argument("--pvo-system-id", help="PVOutput system ID", metavar='ID', required=True)
    parser.add_argument("--pvo-api-key", help="PVOutput API key", metavar='KEY', required=True)
    parser.add_argument("--log", help="Set log level (default info)", choices=['debug', 'info', 'warning', 'critical'], default="info")
    parser.add_argument("--skip-offline", help="Skip uploads when inverter is offline", action='store_true')
    parser.add_argument("--city", help="Skip uploads from dusk till dawn")
    parser.add_argument('--csv', help="Add readings to a Excel compatible CSV file, DATE in the name will be replaced by the current date")
    parser.add_argument('--version', action='version', version='%(prog)s ' + __version__)
    args = parser.parse_args()

    # Configure the logging
    numeric_level = getattr(logging, args.log.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError('Invalid log level: %s' % loglevel)
    logging.basicConfig(format='%(levelname)-8s %(message)s', level=numeric_level)

    # Check if we only want ti run during daylight
    if args.city:
        a = Astral()
        sun = a[args.city].sun(local=True)
        now = datetime.datetime.time(datetime.datetime.now())
        if sun['dawn'].time() < now or sun['dusk'].time() > now:
            logging.debug("Skipped upload as it's night")
            return

    # Fetch the last reading from GoodWe
    gw = gw_api.GoodWeApi(args.gw_station_id)
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

    # Submit reading to PVOutput
    pvo = pvo_api.PVOutputApi(args.pvo_system_id, args.pvo_api_key)
    pvo.add_status(data)

if __name__ == "__main__":
    run()
