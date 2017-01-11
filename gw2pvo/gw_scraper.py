import logging
import requests
import time
from html.parser import HTMLParser

# Deprecated
#
# Note that this file is not used anymore as the JSON variant is more reliable.

class GwHTMLParser(HTMLParser):
    is_big_table = False
    parse_column = False
    column = []

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            attrs = dict(attrs)
            if attrs['id'] == "tab_big":
                self.is_big_table = True

        self.parse_column = self.is_big_table and tag == "td"

    def handle_data(self, data):
        if self.parse_column:
            self.column.append(data.strip())
            self.parse_column = False

    def handle_endtag(self, tag):
        if tag == "table":
            self.is_big_table = False

        if self.parse_column:
            self.column.append("")
            self.parse_column = False

    def get(self):
        return self.column

class GoodWe:
    url = "http://www.goodwe-power.com/PowerStationPlatform/PowerStationReport/InventerDetail"

    def __init__(self, system_id):
        self.system_id = system_id

    def get(self):
        ''' Scrape the most recent reading from the GoodWe site. '''
        return self.interprete(self.parseHtml(self.fetch()))

    def fetch(self):
        payload = { 'ID' : self.system_id }

        for i in range(3):
            try:
                r = requests.get(self.url, params=payload, timeout=10)
                r.raise_for_status()
                return r.text
            except requests.exceptions.RequestException as exp:
                logging.warning(exp)
            time.sleep(30)
        else:
            logging.error("Could retrieve status to GoodWe")

        return ""

    def parseHtml(self, html):
        parser = GwHTMLParser()
        parser.feed(html)
        return parser.get()

    def parseValue(self, value, unit):
        try:
            return float(value.rstrip(unit))
        except ValueError as exp:
            logging.warning(exp)
            return 0

    def parseValues(self, value, unit):
        if isinstance(unit, str):
            return [self.parseValue(v, unit) for v in value.split('/')]
        else:
            return [self.parseValue(v, unit[i]) for (i, v) in enumerate(value.split('/'))]

    def pv_voltage(self, pv_voltages):
        pv_v = [v for v in pv_voltages if v > 0]
        return sum(pv_v) / len(pv_v) if len(pv_v) > 0 else 0

    def interprete(self, data):
        result = {}
        if len(data) == 20:
            result = {
                'no': data[0],
                'status': data[1],
                'serial_number': data[2],
                'pgrid_w': self.parseValue(data[3], 'W'),
                'eday_kwh': self.parseValue(data[4], 'kWh'),
                'etotal_kwh': self.parseValue(data[5], 'kWh'),
                'htotal_h': self.parseValue(data[6], 'h'),
                'error': data[7],
                'pv_v': self.parseValues(data[8], 'V'),
                'pv_i': self.parseValues(data[9], 'A'),
                'ac_v': self.parseValues(data[10], 'V'),
                'ac_i': self.parseValues(data[11], 'A'),
                'ac_f': self.parseValues(data[12], 'Hz'),
                'temp': self.parseValue(data[13], '℃'),
                'x_v': self.parseValue(data[14], 'V'),
                'x_i': self.parseValue(data[15], 'A'),
                'soc': self.parseValues(data[16], '%'),
                'load': self.parseValues(data[17], ['V', 'A', 'KW']),
                'cday_kwh': self.parseValue(data[18], 'kWh'),
                'ctotal_kwh': self.parseValue(data[19], 'kWh')
            }
            result['pv_voltage'] = self.pv_voltage(result['pv_v'])

            logging.info("S/N: {serial_number} P:{pgrid_w} E:{eday_kwh} V:{pv_voltage} - {status}".format(**result))
        else:
            logging.warning("No solar data received from GoodWe")

        return result
