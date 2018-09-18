import logging
import time
import datetime
import requests
import json

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

    def getCurrentReadings(self):
        ''' Download the most recent readings from the GoodWe API. '''

        payload = {
            'powerStationId' : self.system_id
        }

        # goodwe_server
        data = self.call("v1/PowerStation/GetMonitorDetailByPowerstationId", payload)
        
        inverterData = data['inverter'][0]
        
        result = {
            'status' : inverterData['warning_bms'],
            'pgrid_w' : inverterData['out_pac'],
            'eday_kwh' : inverterData['eday'],
            'etotal_kwh' : inverterData['etotal'],
            'grid_voltage' : self.parseValue(inverterData['output_voltage'], 'V'),
            'latitude' : data['info'].get('latitude'),
            'longitude' : data['info'].get('longitude')
        }
        logging.info(result)
        message = "{status}, {pgrid_w}W now, {eday_kwh}kWh today".format(**result)
        if result['status'] == 'Normal' or result['status'] == 'Offline':
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
        for i in range(4):
            try:
                headers = { 'User-Agent': 'PVMaster/2.0.4 (iPhone; iOS 11.4.1; Scale/2.00)', 'Token': self.token }

                r = requests.post(self.base_url + url, headers=headers, data=payload, timeout=10)
                r.raise_for_status()
                data = r.json()
                logging.debug(data)

                if data['msg'] == 'success' and data['data'] != None:
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
            time.sleep(i ^ 3)
        else:
            logging.error("Failed to call GoodWe API")

        return {}

    def parseValue(self, value, unit):
        try:
            return float(value.rstrip(unit))
        except ValueError as exp:
            logging.warning(exp)
            return 0
