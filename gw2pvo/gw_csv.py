import logging
import datetime
import csv

class GoodWeCSV:

    def __init__(self, filename):
        self.filename = filename.replace('DATE', datetime.date.today().isoformat())

    def append(self, data):
        ''' Append a row to the CSV file. '''
        try:
            with open(self.filename, 'x', newline='') as csvfile:
                csvfile.write('\ufeff') # Add UTF-8 BOM header
                csvwriter = csv.writer(csvfile, dialect='excel', delimiter=';')
                csvwriter.writerow([self.label(field) for field in self.order()])
        except:
            pass

        with open(self.filename, 'a', newline='') as csvfile:
            csvwriter = csv.writer(csvfile, dialect='excel', delimiter=';')
            csvwriter.writerow([self.format_field(data[field]) for field in self.order()])

    def format_field(self, value):
        ''' Format values while respecting the locale, so Excel opens the CSV properly. '''
        if type(value) is float:
            return "{:n}".format(value)
        if type(value) is list:
            return "/".join([self.format_field(v) for v in value])
        return value

    def label(self, field):
        return {
            'status': 'Status',
            'pgrid_w': 'Power (W)',
            'eday_kwh': 'Energy today (kWh)',
            'etotal_kwh': 'Energy total (kWh)',
        }[field]

    def order(self):
        return [
            'status',
            'pgrid_w',
            'eday_kwh',
            'etotal_kwh',
        ]
