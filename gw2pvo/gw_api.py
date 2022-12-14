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
        self.token = '{"version":"v3.3.4","client":"ios","language":"en"}'
        self.global_url = 'https://semsportal.com/api/'
        self.base_url = self.global_url

    def statusText(self, status):
        labels = { -1 : 'Offline', 0 : 'Waiting', 1 : 'Normal', 2: 'Fault' }
        return labels[status] if status in labels else 'Unknown'

    def calcPvVoltage(self, data):
        pv_voltages = [
            data['vpv' + str(i)]
            for i in range(1, 5)
            if 'vpv' + str(i) in data
            if data['vpv' + str(i)]
            if data['vpv' + str(i)] < 6553
        ]
        return round(sum(pv_voltages), 1)

    def getCurrentReadings(self):
        ''' Download the most recent readings from the GoodWe API. '''

        payload = {
            'powerStationId' : self.system_id
        }
        data = self.call("v2/PowerStation/GetMonitorDetailByPowerstationId", payload)

        result = {
            'status' : 'Unknown',
            'pgrid_w' : 0,
            'eday_kwh' : 0,
            'etotal_kwh' : 0,
            'grid_voltage' : 0,
            'pv_voltage' : 0,
            'latitude' : data['info'].get('latitude'),
            'longitude' : data['info'].get('longitude'),
            'pload_w' : 0,
            'load_total_kwh': 0, 
        }

        count = 0
        for inverterData in data['inverter']:
            status = self.statusText(inverterData['status'])
            if status == 'Normal':
                result['status'] = status
                result['pgrid_w'] += inverterData['out_pac']
                result['grid_voltage'] += self.parseValue(inverterData['output_voltage'], 'V')
                result['pv_voltage'] += self.calcPvVoltage(inverterData['d'])
                count += 1
            result['eday_kwh'] += inverterData['eday']
            result['etotal_kwh'] += inverterData['etotal']
            if inverterData['invert_full']['hasmeter']:
                result['pload_w'] += round(result['pgrid_w'] - inverterData['invert_full']['pmeter'])

        if inverterData['invert_full']['hasmeter']:    
            result['load_total_kwh'] = data["energeStatisticsCharts"]['consumptionOfLoad']
  
        if count > 0:
            # These values should not be the sum, but the average
            result['grid_voltage'] /= count
            result['pv_voltage'] /= count
        elif len(data['inverter']) > 0:
            # We have no online inverters, then just pick the first
            inverterData = data['inverter'][0]
            result['status'] = self.statusText(inverterData['status'])
            result['pgrid_w'] = inverterData['out_pac']
            result['grid_voltage'] = self.parseValue(inverterData['output_voltage'], 'V')
            result['pv_voltage'] = self.calcPvVoltage(inverterData['d'])
            result['pload_w'] = result['pgrid_w'] - inverterData['invert_full']['pmeter']
            result['load_total_kwh'] = inverterData["energeStatisticsCharts"]['consumptionOfLoad']
        message = "{status}, {pgrid_w} W now, {eday_kwh} kWh today, {etotal_kwh} kWh all time, {grid_voltage} V grid, {pv_voltage} V PV".format(**result)
        if inverterData['invert_full']['hasmeter']:
            message += ", {pload_w} W Load, {load_total_kwh} kWh Load today".format(**result)
        if result['status'] == 'Normal' or result['status'] == 'Offline':
            logging.info(message)
        else:
            logging.warning(message)

        return result

    def getLoadKwh(self, date):
        payload = {
            'id' : self.system_id,
            'range' : '2',
            'chartIndexId': '8',
            'date' : date.strftime('%Y-%m-%d')
        }
        data = self.call("v2/Charts/GetChartByPlant", payload)
        if not data:
            logging.warning("GetChartByPlant missing data")
            return 0

        elday_kwh = 0
        for line in data["lines"]:
            if line['label'] == "Consumption (kWh)":
                for xy in line["xy"]:
                    if xy["x"] == date.strftime('%Y-%m-%d'):
                        logging.debug(f"Found load consumption {xy['y']}")
                        elday_kwh = xy['y']

        return elday_kwh

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
        #print(data)
        if 'pacs' not in data:
            logging.warning("GetPowerStationPacByDayForApp returned bad data: " + str(data))
            return []

        return data['pacs']

    def getDayPload(self, date):
        payload = {
            'id' : self.system_id,
            'date' : date.strftime('%Y-%m-%d'),
            'range':"2",
            'chartIndexId':"1"
        }
        data = self.call("v2/Charts/GetChartByPlant", payload)
        #print(data)
        if 'lines' not in data:
            logging.warning("GetChartByPlant returned bad data: " + str(data))
            return []

        return data['lines']


    def getDayReadings(self, date):
        result = self.getLocation()
        pacs = self.getDayPac(date)
        ploads = self.getDayPload(date)
        for val in ploads: 
            if  val["label"] == "Load (W)":
                ploads_d = val["xy"]
        #print(ploads_d)    
        hours = 0
        kwh = 0
        kwh_l = 0
        result['entries'] = []
        for samplepac, samplepload in zip(pacs, ploads_d):
            parsed_date = datetime.strptime(samplepac['date'], "%m/%d/%Y %H:%M:%S")
            next_hours = parsed_date.hour + parsed_date.minute / 60
            pgrid_w = samplepac['pac']
            pload_w = samplepload['y']
            kwh_l += pload_w / 1000 * (next_hours - hours)
            kwh += pgrid_w / 1000 * (next_hours - hours)
            result['entries'].append({
                'dt' : parsed_date,
                'pgrid_w': pgrid_w,
                'eday_kwh': round(kwh, 3),
                'pload_w': pload_w,
                'ploadday_kwh': round(kwh_l,3)
                })
            hours = next_hours

        eday_kwh = self.getActualKwh(date)
        elday_kwh = self.getLoadKwh(date)
        if eday_kwh > 0:
            correction = eday_kwh / kwh
            for sample in result['entries']:
                sample['eday_kwh'] *= correction
        if elday_kwh > 0:
            correction = elday_kwh / kwh_l
            for sample in result['entries']:
                sample['ploadday_kwh'] *= correction

        return result

    def call(self, url, payload):
        for i in range(1, 4):
            try:
                headers = {
                    'User-Agent': 'SEMS Portal/3.3.4 (iPhone; iOS 15.3.1; Scale/2.00)',
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
                    r = requests.post(self.global_url + 'v2/Common/CrossLogin', headers=headers, data=loginPayload, timeout=20)
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
