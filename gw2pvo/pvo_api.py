import logging
import time
import requests

__author__ = "Mark Ruys"
__copyright__ = "Copyright 2017, Mark Ruys"
__license__ = "MIT"
__email__ = "mark@paracas.nl"

class PVOutputApi:

    def __init__(self, system_id, api_key):
        self.m_system_id = system_id
        self.m_api_key = api_key


    def add_status(self, pgrid_w, eday_kwh):
        t = time.localtime()
        payload = {
            'd' : "{:04}{:02}{:02}".format(t.tm_year, t.tm_mon, t.tm_mday),
            't' : "{:02}:{:02}".format(t.tm_hour, t.tm_min),
            'v1' : round(eday_kwh * 1000),
            'v2' : round(pgrid_w)
        }

        self.call("https://pvoutput.org/service/r2/addstatus.jsp", payload)

    def add_day(self, data):
        # Send day data in batches of 30.

        for chunk in [ data[i:i + 30] for i in range(0, len(data), 30) ]:

            readings = []
            for reading in chunk:
                dt = reading['dt']
                fields = [
                    dt.strftime('%Y%m%d'),
                    dt.strftime('%H:%M'),
                    str(round(reading['eday_kwh'] * 1000)),
                    str(reading['pgrid_w'])
                ]
                readings.append(",".join(fields))

            payload = {
                'data' : ";".join(readings)
            }

            self.call("https://pvoutput.org/service/r2/addbatchstatus.jsp", payload)

    def call(self, url, payload):
        logging.debug(payload)

        headers = {
            'X-Pvoutput-Apikey' : self.m_api_key,
            'X-Pvoutput-SystemId' : self.m_system_id,
            'X-Rate-Limit': '1'
        }

        for i in range(3):
            try:
                r = requests.post(url, headers=headers, data=payload, timeout=10)
                reset = round(float(r.headers['X-Rate-Limit-Reset']) - time.time())
                if int(r.headers['X-Rate-Limit-Remaining']) < 10:
                    logging.warning("Only {} requests left, reset after {} seconds".format(
                        r.headers['X-Rate-Limit-Remaining'],
                        reset))
                if r.status_code == 403:
                    logging.warning("Forbidden: " + r.reason)
                    time.sleep(reset + 1)
                else:
                    r.raise_for_status()
                    break
            except requests.exceptions.RequestException as arg:
                logging.warning(arg)
            time.sleep(3)
        else:
            logging.error("Failed to call PVOutput API")

