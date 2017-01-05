import logging
import time
import requests

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

        self.call("http://pvoutput.org/service/r2/addstatus.jsp", payload)

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
                if int(r.headers['X-Rate-Limit-Remaining']) < 20:
                    logging.warning("Only {} requests left, reset after {} seconds".format(
                        r.headers['X-Rate-Limit-Remaining'],
                        round(float(r.headers['X-Rate-Limit-Reset']) - time.time())))
                r.raise_for_status()
                break
            except requests.exceptions.RequestException as arg:
                logging.warning(arg)
            time.sleep(30)
        else:
            logging.error("Failed to call PVOutput API")

