import json
import logging
import time
from datetime import datetime, timedelta
import requests

__author__ = "Mark Ruys"
__copyright__ = "Copyright 2017, Mark Ruys"
__license__ = "MIT"
__email__ = "mark@paracas.nl"

class GoodWeApi:

    def __init__(self, system_id, account, password):
        self.system_id = system_id
        self.account = account
        self.password = password
        self.token = '{"version":"v3.1","client":"ios","language":"en"}'
        self.global_url = 'https://semsportal.com/api/'
        self.base_url = self.global_url
        self.status = { -1 : 'Offline', 0 : 'Waiting', 1 : 'Normal' }

    def getCurrentReadings(self):
        ''' Download the most recent readings from the GoodWe API. '''

        payload = {
            'powerStationId' : self.system_id
        }

        # goodwe_server
        data = self.call("v2/PowerStation/GetMonitorDetailByPowerstationId", payload)

        inverterData = data['inverter'][0]

        result = {
            'status' : self.status[inverterData['status']],
            'pgrid_w' : inverterData['out_pac'],
            'eday_kwh' : inverterData['eday'],
            'etotal_kwh' : inverterData['etotal'],
            'grid_voltage' : self.parseValue(inverterData['output_voltage'], 'V'),
            'pv_voltage' : inverterData['d']['vpv1'],
            'latitude' : data['info'].get('latitude'),
            'longitude' : data['info'].get('longitude')
        }

        message = "{status}, {pgrid_w} W now, {eday_kwh} kWh today".format(**result)
        if result['status'] == 'Normal' or result['status'] == 'Offline':
            logging.info(message)
        else:
            logging.warning(message)

        return result

    def getActualKwh(self, date):
        payload = {
            'powerstation_id' : self.system_id,
            'count' : 1,
            'date' : date.strftime('%Y-%m-%d')
        }
        data = self.call("v2/PowerStationMonitor/GetPowerStationPowerAndIncomeByDay", payload)
        if not data:
            logging.warning("GetPowerStationPowerAndIncomeByDay missing data")
            return 0

        eday_kwh = 0
        for day in data:
            if day['d'] == date.strftime('%m/%d/%Y'):
                eday_kwh = day['p']

        return eday_kwh

    def getLocation(self):
        payload = {
            'powerStationId' : self.system_id
        }
        data = self.call("v2/PowerStation/GetMonitorDetailByPowerstationId", payload)
        if 'info' not in data:
            logging.warning("GetMonitorDetailByPowerstationId returned bad data: " + str(data))
            return {}

        return {
            'latitude' : data['info'].get('latitude'),
            'longitude' : data['info'].get('longitude'),
        }

    def getDayPac(self, date):
        payload = {
            'id' : self.system_id,
            'date' : date.strftime('%Y-%m-%d')
        }
        data = self.call("v2/PowerStationMonitor/GetPowerStationPacByDayForApp", payload)
        if 'pacs' not in data:
            logging.warning("GetPowerStationPacByDayForApp returned bad data: " + str(data))
            return []

        return data['pacs']

    def getDayReadings(self, date):
        result = self.getLocation()
        pacs = self.getDayPac(date)

        hours = 0
        kwh = 0
        result['entries'] = []
        for sample in pacs:
            parsed_date = datetime.strptime(sample['date'], "%m/%d/%Y %H:%M:%S")
            next_hours = parsed_date.hour + parsed_date.minute / 60
            pgrid_w = sample['pac']
            if pgrid_w > 0:
                kwh += pgrid_w / 1000 * (next_hours - hours)
                result['entries'].append({
                    'dt' : parsed_date,
                    'pgrid_w': pgrid_w,
                    'eday_kwh': round(kwh, 3)
                })
            hours = next_hours

        eday_kwh = self.getActualKwh(date)
        if eday_kwh > 0:
            correction = eday_kwh / kwh
            for sample in result['entries']:
                sample['eday_kwh'] *= correction

        return result

    def call(self, url, payload):
        for i in range(1, 4):
            try:
                headers = {
                    'User-Agent': 'SEMS Portal/3.1 (iPhone; iOS 13.5.1; Scale/2.00)',
                    'Token': self.token,
                }

                r = requests.post(self.base_url + url, headers=headers, data=payload, timeout=10)
                r.raise_for_status()
                data = r.json()
                logging.debug(data)

                try:
                    code = int(data['code'])
                except ValueError:
                    raise Exception("Failed to call GoodWe API (no code)")

                if code == 0 and data['data'] is not None:
                    return data['data']
                elif code == 100001:
                    loginPayload = {
                        'account': self.account,
                        'pwd': self.password,
                    }
                    r = requests.post(self.global_url + 'v2/Common/CrossLogin', headers=headers, data=loginPayload, timeout=10)
                    r.raise_for_status()
                    data = r.json()
                    if 'api' not in data:
                        raise Exception(data['msg'])
                    self.base_url = data['api']
                    self.token = json.dumps(data['data'])
                else:
                    raise Exception("Failed to call GoodWe API (code {})".format(code))
            except requests.exceptions.RequestException as exp:
                logging.warning(exp)
            time.sleep(i ** 3)
        else:
            raise Exception("Failed to call GoodWe API (too many retries)")

        return {}

    def parseValue(self, value, unit):
        try:
            return float(value.rstrip(unit))
        except ValueError as exp:
            logging.warning(exp)
            return 0
