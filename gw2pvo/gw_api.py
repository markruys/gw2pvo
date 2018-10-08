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
        self.token = '{"version":"v2.0.4","client":"ios","language":"en"}'
        self.global_url = 'https://globalapi.sems.com.cn/api/'
        self.base_url = self.global_url
        self.status = { -1 : 'Offline', 1 : 'Normal' }

    def getCurrentReadings(self):
        ''' Download the most recent readings from the GoodWe API. '''

        payload = {
            'powerStationId' : self.system_id
        }

        # goodwe_server
        data = self.call("v1/PowerStation/GetMonitorDetailByPowerstationId", payload)
        
        inverterData = data['inverter'][0]
        
        result = {
            'status' : self.status[inverterData['status']],
            'pgrid_w' : inverterData['out_pac'],
            'eday_kwh' : inverterData['eday'],
            'etotal_kwh' : inverterData['etotal'],
            'grid_voltage' : self.parseValue(inverterData['output_voltage'], 'V'),
            'latitude' : data['info'].get('latitude'),
            'longitude' : data['info'].get('longitude')
        }

        message = "{status}, {pgrid_w} W now, {eday_kwh} kWh today".format(**result)
        if result['status'] == 'Normal' or result['status'] == 'Offline':
            logging.info(message)
        else:
            logging.warning(message)

        return result


    def getDayReadings(self, date):
        entries = []

        payload = {
            'powerStationId' : self.system_id
        }

        data = self.call("v1/PowerStation/GetMonitorDetailByPowerstationId", payload)

        payload = {
            'powerstation_id' : self.system_id,
            'count' : 1,
            'date' : date.strftime('%Y-%m-%d')
        }
        
        result = {
            'latitude' : data['info'].get('latitude'),
            'longitude' : data['info'].get('longitude')
        }

        data = self.call("PowerStationMonitor/GetPowerStationPowerAndIncomeByDay", payload)
        eday_kwh = data[0]['p']

        payload = {
            'id' : self.system_id,
            'date' : date.strftime('%Y-%m-%d')
        }

        data = self.call("PowerStationMonitor/GetPowerStationPacByDayForApp", payload)
        if len(data) < 2:
            logging.warning(payload['date'] + " - Received bad data " + str(data))
        else:
            minutes = 0
            eday_from_power = 0
            for sample in data['pacs']:
                parsed_date = datetime.strptime(sample['date'], "%m/%d/%Y %H:%M:%S")
                next_minutes = parsed_date.hour * 60 + parsed_date.minute
                sample['minutes'] = next_minutes - minutes
                minutes = next_minutes
                eday_from_power += sample['pac'] * sample['minutes']
            factor = eday_kwh / eday_from_power

            if len(data['pacs']) == 145:
                data.pop()

            eday_kwh = 0
            for sample in data['pacs']:
                date += timedelta(minutes=sample['minutes'])
                pgrid_w = sample['pac']
                increase = pgrid_w * sample['minutes'] * factor
                if increase > 0:
                    eday_kwh += increase
                    entries.append({
                        'dt' : date,
                        'pgrid_w': pgrid_w,
                        'eday_kwh': round(eday_kwh, 3)
                    })

        result['entries'] = entries

        return result


    def call(self, url, payload):
        for i in range(1, 4):
            try:
                headers = { 'User-Agent': 'PVMaster/2.0.4 (iPhone; iOS 11.4.1; Scale/2.00)', 'Token': self.token }

                r = requests.post(self.base_url + url, headers=headers, data=payload, timeout=10)
                r.raise_for_status()
                data = r.json()
                logging.debug(data)

                if data['msg'] == 'success' and data['data'] is not None:
                    return data['data']
                else:
                    loginPayload = { 'account': self.account, 'pwd': self.password }
                    r = requests.post(self.global_url + 'v1/Common/CrossLogin', headers=headers, data=loginPayload, timeout=10)
                    r.raise_for_status()
                    data = r.json()
                    self.base_url = data['api']
                    self.token = json.dumps(data['data'])
            except requests.exceptions.RequestException as exp:
                logging.warning(exp)
            time.sleep(i ** 3)
        else:
            logging.error("Failed to call GoodWe API")

        return {}

    def parseValue(self, value, unit):
        try:
            return float(value.rstrip(unit))
        except ValueError as exp:
            logging.warning(exp)
            return 0
