import math
import logging
import time
from oauthlib.oauth2 import LegacyApplicationClient
from requests_oauthlib import OAuth2Session

__author__ = "Mark Ruys"
__copyright__ = "Copyright 2020, Mark Ruys"
__license__ = "MIT"
__email__ = "mark@paracas.nl"

# https://dev.netatmo.com/apidocumentation/weather

class NetatmoApi:
    _BASE_URL = "https://api.netatmo.com/"

    def __init__(self, username, password, client_id, client_secret):
        self.username = username
        self.password = password
        self.client_id = client_id
        self.client_secret = client_secret

    def authorize(self):
        token_url = self._BASE_URL + "oauth2/token"
        client = LegacyApplicationClient(client_id=self.client_id)
        self.oauth = OAuth2Session(client=client, scope=['read_station'])
        self.oauth.fetch_token(token_url=token_url,
            username=self.username, password=self.password,
            client_id=self.client_id, client_secret=self.client_secret)

    def get_temperature(self, measures):
        for sensor in measures:
            for i, type in enumerate(measures[sensor]['type']):
                if type == 'temperature':
                    for res in measures[sensor]['res']:
                        return measures[sensor]['res'][res][i]
        return None

    def haversine_distance(self, lat1, lon1, lat2, lon2):
        R = 6371.0088
        lat1 = math.radians(lat1)
        lon1 = math.radians(lon1)
        lat2 = math.radians(lat2)
        lon2 = math.radians(lon2)
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        distance = R * c
        return distance * 1000

    def get_location_temperature(self, latitude, longitude):
        delta = 0.002
        for i in range(10):
            data = {
                "lat_ne" : latitude + delta,
                "lat_sw" : latitude - delta,
                "lon_ne" : longitude + delta,
                "lon_sw" : longitude - delta,
                "required_data": "temperature",
                "filter": True,
            }
            result = self.call('api/getpublicdata', data)

            if not (result and result['status'] == 'ok'):
                return None
            if len(result['body']) == 0:
                delta *= 2
                logging.debug("Retry with delta {}".format(delta))
            else:
                best_distance = 999999
                for i, station in enumerate(result['body']):
                    location = station['place']['location']
                    distance = self.haversine_distance(latitude, longitude, location[1], location[0])
                    if distance < best_distance:
                        best_distance = distance
                        best_station = station
                logging.info("Found device {} ({}, {}) at a distance of {:.0f} meters".format(
                    best_station['_id'],
                    best_station['place']['street'],
                    best_station['place']['city'],
                    best_distance,
                ))
                return self.get_temperature(best_station['measures'])

        return None

    def get_device_temperature(self, device_id):
        data = { "device_id" : device_id }
        result = self.call('api/getpublicmeasure', data)

        if result and result['status'] == 'ok':
            for station in result['body']:
                temperature = self.get_temperature(station['measures'])
                if temperature is not None:
                    return temperature
        return None

    def call(self, command, payload):
        for i in range(1, 4):
            response = self.oauth.get(self._BASE_URL + command, data=payload)
            logging.debug(response.json())
            if response.status_code == 200:
                return response.json()
            time.sleep(i ** 3)
        return None
