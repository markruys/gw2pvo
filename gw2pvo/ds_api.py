from datetime import datetime
import logging
import time
import requests

__author__ = "Michaël Hompus"
__copyright__ = "Copyright 2018, Michaël Hompus"
__license__ = "MIT"
__email__ = "michael@hompus.nl"

class DarkSkyApi:
    def __init__(self, api_key):
        self.api_key = api_key


    def get_temperature(self, latitude, longitude):
        if latitude is None or longitude is None:
            return None

        data = {
            'apiKey' : self.api_key,
            'latitude' : latitude,
            'longitude' : longitude
        }

        url = "https://api.darksky.net/forecast/{apiKey}/{latitude},{longitude}?units=si&exclude=minutely,hourly,daily,alerts,flags".format(**data)
                
        for i in range(1, 4):
            try:
                r = requests.get(url, timeout=10)
                r.raise_for_status()
                result = r.json()

                return result['currently']['temperature']
            except requests.exceptions.RequestException as arg:
                logging.warning(arg)
            time.sleep(i ** 3)
        else:
            logging.error("Failed to call DarkSky API")

    def get_temperature_for_day(self, latitude, longitude, date):
        if latitude is None or longitude is None:
            return None

        data = {
            'apiKey' : self.api_key,
            'latitude' : latitude,
            'longitude' : longitude,
            'date' : date.astimezone(datetime.now().tzinfo).isoformat()
        }

        url = "https://api.darksky.net/forecast/{apiKey}/{latitude},{longitude},{date}?units=si&exclude=minutely,currently,daily,alerts,flags".format(**data)

        for i in range(1, 4):
            try:
                r = requests.get(url, timeout=10)
                r.raise_for_status()
                result = r.json()

                return result['hourly']['data']
            except requests.exceptions.RequestException as arg:
                logging.warning(arg)
            time.sleep(i ** 3)
        else:
            logging.error("Failed to call DarkSky API")