import logging
import time
import datetime
import requests

__author__ = "Mark Ruys"
__copyright__ = "Copyright 2017, Mark Ruys"
__license__ = "MIT"
__email__ = "mark@paracas.nl"

class GoodWeApi:

    def __init__(self, system_id, region):
        self.system_id = system_id
        if region == 'EU':
            self.base_url = 'https://eu.goodwe-power.com'
        elif region == 'AU':
            self.base_url = 'https://au.goodwe-power.com'
        else:
            self.base_url = 'https://www.goodwe-power.com'

    def getCurrentReadings(self):
        ''' Download the most recent readings from the GoodWe API. '''

        payload = {
            'stationId' : self.system_id
        }

        # goodwe_server: # eu, au or www
        data = self.call("/Mobile/GetMyPowerStationById", payload)

        result = {
            'status' : data["status"],
            'pgrid_w' : self.parseValue(data["curpower"], 'kW') * 1000,
            'eday_kwh' : self.parseValue(data["eday"], 'kWh'),
            'etotal_kwh' : self.parseValue(data["etotal"], 'kWh'),
        }

        message = "{status}, {pgrid_w} W now, {eday_kwh} kWh today".format(**result)
        if data['status'] == 'Normal' or data['status'] == 'Offline':
            logging.info(message)
        else:
            logging.warning(message)

        return result


    def getDayReadings(self, date):
        result = []

        payload = {
            'stationId' : self.system_id,
            'date' : date.strftime('%Y-%m-%d')
        }
        data = self.call("/Mobile/GetEDayForMobile", payload)
        eday_kwh = float(data['EDay'])

        data = self.call("/Mobile/GetPacLineChart", payload)
        if len(data) < 2:
            logging.warning(payload['date'] + " - Received bad data " + str(data))
        else:
            minutes = 0
            eday_from_power = 0
            for sample in data:
                hm = sample['HourNum'].split(":")
                next_minutes = int(hm[0]) * 60 + int(hm[1])
                sample['minutes'] = next_minutes - minutes
                minutes = next_minutes
                eday_from_power += int(sample['HourPower']) * sample['minutes']
            factor = eday_kwh / eday_from_power

            if len(data) == 145:
                data.pop()

            eday_kwh = 0
            for sample in data:
                date += datetime.timedelta(minutes=sample['minutes'])
                pgrid_w = int(sample['HourPower'])
                increase = pgrid_w * sample['minutes'] * factor
                if increase > 0:
                    eday_kwh += increase
                    result.append({
                        'dt' : date,
                        'pgrid_w': pgrid_w,
                        'eday_kwh': round(eday_kwh, 3)
                    })

        return result


    def call(self, url, payload):
        for i in range(3):
            try:
                r = requests.get(self.base_url + url, params=payload, timeout=10)
                r.raise_for_status()
                json = r.json()
                logging.debug(json)
                return json
            except requests.exceptions.RequestException as exp:
                logging.warning(exp)
            time.sleep(3)
        else:
            logging.error("Failed to call GoodWe API")

        return {}

    def parseValue(self, value, unit):
        try:
            return float(value.rstrip(unit))
        except ValueError as exp:
            logging.warning(exp)
            return 0
