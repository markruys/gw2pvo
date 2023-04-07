#!/usr/bin/env python3

import sys, os
if sys.version_info < (3,6):
    sys.exit('Sorry, you need at least Python 3.6 for Astral 2')

import logging
import argparse
import locale
import time
from datetime import datetime
from configparser import ConfigParser

from astral import LocationInfo
from astral.geocoder import lookup, database
from astral.location import Location

from gw2pvo import ds_api
from gw2pvo import ow_api
from gw2pvo import gw_api
from gw2pvo import netatmo_api
from gw2pvo import gw_csv
from gw2pvo import pvo_api
from gw2pvo import __version__

__author__ = "Mark Ruys"
__copyright__ = "Copyright 2017-2020, Mark Ruys"
__license__ = "MIT"
__email__ = "mark@paracas.nl"
__doc__ = "Upload GoodWe power inverter data to PVOutput.org"

last_eday_kwh = 0

def get_temperature(settings, latitude, longitude):
    if settings.netatmo_username and settings.netatmo_password and settings.netatmo_client_id and settings.netatmo_client_secret:
        netatmo = netatmo_api.NetatmoApi(
            settings.netatmo_username,
            settings.netatmo_password,
            settings.netatmo_client_id,
            settings.netatmo_client_secret,
        )
        netatmo.authorize()
        if settings.netatmo_device_id:
            return netatmo.get_device_temperature(settings.netatmo_device_id)
        else:
            return netatmo.get_location_temperature(latitude, longitude)
    elif settings.darksky_api_key:
        ds = ds_api.DarkSkyApi(settings.darksky_api_key)
        return ds.get_temperature(latitude, longitude)
    elif settings.openweather_api_key:
        ow = ow_api.OpenWeatherApi(settings.openweather_api_key)
        return ow.get_temperature(latitude, longitude)
    return None

def run_once(settings, city):
    global last_eday_kwh

    # Check if we only want to run during daylight
    if city:
        now = datetime.time(datetime.now())
        if now < city.dawn().time() or now > city.dusk().time():
            logging.debug("Skipped upload as it's night")
            return

    # Fetch the last reading from GoodWe
    gw = gw_api.GoodWeApi(settings.gw_station_id, settings.gw_account, settings.gw_password)
    data = gw.getCurrentReadings()

    # Check if we want to abort when offline
    if settings.skip_offline:
        if data['status'] == 'Offline':
            logging.debug("Skipped upload as the inverter is offline")
            return

    # Append reading to CSV file
    if settings.csv:
        if data['status'] == 'Offline':
            logging.debug("Don't append offline data to CSV file")
        else:
            locale.setlocale(locale.LC_ALL, locale.getlocale())
            csv = gw_csv.GoodWeCSV(settings.csv)
            csv.append(data)

    # Submit reading to PVOutput, if they differ from the previous set
    eday_kwh = data['eday_kwh']
    if data['pgrid_w'] == 0 and abs(eday_kwh - last_eday_kwh) < 0.001:
        logging.debug("Ignore unchanged reading")
    else:
        last_eday_kwh = eday_kwh

    temperature = get_temperature(settings, data['latitude'], data['longitude'])
    if temperature:
        logging.info("Current local temperature is {:.1f} °C".format(temperature))
        data['temperature'] = temperature

    voltage = data['grid_voltage']
    if settings.pv_voltage:
        voltage=data['pv_voltage']

    if settings.pvo_system_id and settings.pvo_api_key:
        pvo = pvo_api.PVOutputApi(settings.pvo_system_id, settings.pvo_api_key)
        pvo.add_status(data['pgrid_w'], last_eday_kwh, data.get('temperature'), voltage)
    else:
        logging.debug(str(data))
        logging.warning("Missing PVO id and/or key")

def copy(settings):
    # Fetch readings from GoodWe
    date = datetime.strptime(settings.date, "%Y-%m-%d")
    gw = gw_api.GoodWeApi(settings.gw_station_id, settings.gw_account, settings.gw_password)
    data = gw.getDayReadings(date)

    if settings.pvo_system_id and settings.pvo_api_key:
        if settings.darksky_api_key:
            ds = ds_api.DarkSkyApi(settings.darksky_api_key)
            temperatures = ds.get_temperature_for_day(data['latitude'], data['longitude'], date)
        elif settings.openweather_api_key:
            ow = ow_api.OpenWeatherApi(settings.openweather_api_key)
            temperatures = ow.get_temperature_for_day(data['latitude'], data['longitude'], date)
        else:
            temperatures = None

        # Submit readings to PVOutput
        pvo = pvo_api.PVOutputApi(settings.pvo_system_id, settings.pvo_api_key)
        pvo.add_day(data['entries'], temperatures)
    else:
        for entry in data['entries']:
            logging.info("{}: {:6.0f} W {:6.2f} kWh".format(
                entry['dt'],
                entry['pgrid_w'],
                entry['eday_kwh'],
            ))
        logging.warning("Missing PVO id and/or key")

def run():
    defaults = {
        'log': "info"
    }

    # Parse any config file specification. We make this parser with add_help=False so
    # that it doesn't parse -h and print help.
    conf_parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        add_help=False
    )
    conf_parser.add_argument("--config", help="Specify config file", metavar='FILE')
    args, remaining_argv = conf_parser.parse_known_args()

    # Read configuration file and add it to the defaults hash.
    if args.config:
        config = ConfigParser()
        config.read(args.config)
        if "Defaults" in config:
            defaults.update(dict(config.items("Defaults")))
        else:
            sys.exit("Bad config file, missing Defaults section")

    # Parse rest of arguments
    parser = argparse.ArgumentParser(
        description=__doc__,
        parents=[conf_parser],
    )
    parser.set_defaults(**defaults)
    parser.add_argument("--gw-station-id", help="GoodWe station ID", metavar='ID')
    parser.add_argument("--gw-account", help="GoodWe account", metavar='ACCOUNT')
    parser.add_argument("--gw-password", help="GoodWe password", metavar='PASSWORD')
    parser.add_argument("--pvo-system-id", help="PVOutput system ID", metavar='ID')
    parser.add_argument("--pvo-api-key", help="PVOutput API key", metavar='KEY')
    parser.add_argument("--pvo-interval", help="PVOutput interval in minutes", type=int, choices=[5, 10, 15])
    parser.add_argument("--darksky-api-key", help="Dark Sky Weather API key")
    parser.add_argument("--openweather-api-key", help="Open Weather API key")
    parser.add_argument("--netatmo-username", help="Netatmo username")
    parser.add_argument("--netatmo-password", help="Netatmo password")
    parser.add_argument("--netatmo-client-id", help="Netatmo OAuth client id")
    parser.add_argument("--netatmo-client-secret", help="Netatmo OAuth client secret")
    parser.add_argument("--netatmo-device-id", help="Netatmo device id")
    parser.add_argument("--log", help="Set log level (default info)", choices=['debug', 'info', 'warning', 'critical'])
    parser.add_argument("--date", help="Copy all readings (max 14/90 days ago)", metavar='YYYY-MM-DD')
    parser.add_argument("--pv-voltage", help="Send pv voltage instead of grid voltage", action='store_true')
    parser.add_argument("--skip-offline", help="Skip uploads when inverter is offline", action='store_true')
    parser.add_argument("--city", help="Sets timezone and skip uploads from dusk till dawn")
    parser.add_argument('--csv', help="Append readings to a Excel compatible CSV file, DATE in the name will be replaced by the current date")
    parser.add_argument('--version', action='version', version='%(prog)s ' + __version__)
    args = parser.parse_args()

    # Configure the logging
    numeric_level = getattr(logging, args.log.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError('Invalid log level: %s' % loglevel)
    logging.basicConfig(format='%(levelname)-8s %(message)s', level=numeric_level)

    logging.debug("gw2pvo version " + __version__)

    if isinstance(args.skip_offline, str):
        args.skip_offline = args.skip_offline.lower() in ['true', 'yes', 'on', '1']

    if args.gw_station_id is None or args.gw_account is None or args.gw_password is None:
        sys.exit("Missing --gw-station-id, --gw-account and/or --gw-password")

    if args.city:
        city = Location(lookup(args.city, database()))
        os.environ['TZ'] = city.timezone
        time.tzset()
    else:
        city = None
    logging.debug("Timezone {}".format(datetime.now().astimezone().tzinfo))

    # Check if we want to copy old data
    if args.date:
        try:
            copy(args)
        except KeyboardInterrupt:
            sys.exit(1)
        except Exception as exp:
            logging.error(exp)
        sys.exit()

    startTime = datetime.now()

    while True:
        try:
            run_once(args, city)
        except KeyboardInterrupt:
            sys.exit(1)
        except Exception as exp:
            logging.error(exp)

        if args.pvo_interval is None:
            break

        interval = args.pvo_interval * 60
        time.sleep(interval - (datetime.now() - startTime).seconds % interval)

if __name__ == "__main__":
    run()
