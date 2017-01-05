import logging
import time
import requests

class GoodWeApi:

    def __init__(self, system_id):
        self.system_id = system_id

    def getCurrentReadings(self):
        ''' Download the most recent readings from the GoodWe API. '''

        data = self.call(
            "http://www.goodwe-power.com/Mobile/GetMyPowerStationById",
            { 'stationId' : self.system_id }
        )

        result = {
            'status': data["status"],
            'pgrid_w': self.parseValue(data["curpower"], 'kW') * 1000,
            'eday_kwh': self.parseValue(data["eday"], 'kWh'),
            'etotal_kwh': self.parseValue(data["etotal"], 'kWh'),
        }

        message = "{status}, {pgrid_w} W now, {eday_kwh} kWh today".format(**result)
        if data['status'] == 'Normal' or data['status'] == 'Offline':
            logging.info(message)
        else:
            logging.warning(message)

        return result

    def call(self, url, payload):
        for i in range(3):
            try:
                r = requests.get(url, params=payload, timeout=10)
                r.raise_for_status()
                json = r.json()
                logging.debug(json)
                return json
            except requests.exceptions.RequestException as exp:
                logging.warning(exp)
            time.sleep(30)
        else:
            logging.error("Failed to call GoodWe API")

        return {}

    def parseValue(self, value, unit):
        try:
            return float(value.rstrip(unit))
        except ValueError as exp:
            logging.warning(exp)
            return 0
