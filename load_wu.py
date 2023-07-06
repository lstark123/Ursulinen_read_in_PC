
from PyQt5.QtWidgets import QApplication,  QLineEdit, QHBoxLayout, QLabel ,QWidget, QMainWindow, QPushButton,QFileDialog, QVBoxLayout, QInputDialog,QComboBox
import matplotlib
import matplotlib.pyplot
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt5 import QtCore
from PyQt5.QtCore import *
from PyQt5.QtGui import QIntValidator,QDoubleValidator
import sys
import os
import serial
import datetime
import numpy as np
from bs4 import BeautifulSoup as BS
from selenium import webdriver
import time
import sounddevice as sd
import traceback
import random
import xarray as xr
import pandas as pd
from pyflightdata import FlightData


class Measurement:
    def __init__(self):
        self.initial_time = datetime.datetime.now()
        self.time = np.array(self.initial_time)
        self.save_newfile_ndatapoints = 60*60
        print(f"Saving every second in {self.save_newfile_ndatapoints} seconds files")
        self.total_n_updates = 0

class Weatherdata(Measurement):
    def __init__(self):
        # now with default values
        super().__init__()
        # Set the absolute path to chromedriver


        self.chromedrive_path = r"C:\Users\peaq\AppData\Local\Google\Chrome\chromedriver.exe"
        self.data = self.get_data()

    def render_page(self, url):
        driver = webdriver.Chrome(self.chromedrive_path)
        driver.get(url)
        time.sleep(3)  # Could potentially decrease the sleep time
        r = driver.page_source
        driver.quit()

        return r

    def get_data(self):
        station = "IINNSB41"
        date = datetime.date.today().strftime("%Y-%m-%d")
        # Render the url and open the page source as BS object
        url = 'https://www.wunderground.com/dashboard/pws/%s/table/%s/%s/daily' % (station,
                                                                                   date, date)
        print("I open the webpage")
        r = self.render_page(url)
        soup = BS(r, "html.parser", )

        container = soup.find('lib-history-table')

        # Check that lib-history-table is found
        if container is None:
            raise ValueError("could not find lib-history-table in html source for %s" % url)

        # Get the timestamps and data from two separate 'tbody' tags
        all_checks = container.find_all(
            'tbody')  # get the data in the tablebody (there are two tables, one with time, one with data)
        time_check = all_checks[0]
        data_check = all_checks[1]

        # Iterate through 'tr' tags and get the timestamps
        hours = []
        for i in time_check.find_all('tr'):
            trial = i.get_text()
            hours.append(trial)

        # For data, locate both value and no-value ("--") classes
        classes = ['wu-value wu-value-to', 'wu-unit-no-value ng-star-inserted']

        # Iterate through span tags and get data
        data1 = []

        for i in data_check.find_all('span', class_=classes):
            trial = i.get_text()
            data1.append(trial)

        columns1 = ['Temperature', 'Dew Point', 'Humidity', 'Wind Speed',
                    'Wind Gust', 'Pressure', 'Precip. Rate', 'Precip. Accum.']

        # Convert NaN values (stings of '--') to np.nan
        data1_nan = [np.nan if x == '--' else x for x in data1]

        # Convert list of data to an array
        data1_array = np.array(data1_nan, dtype=float)
        data1_array = data1_array.reshape(-1, len(columns1))

        data2 = data_check.find_all("strong")
        data2 = [i.get_text() for i in data2]
        data2 = [np.nan if x == '--' else x for x in data2]

        columns2 = ["Time", "Wind Dir", "UV", "Solar radiation"]

        data2_array = np.array(data2)
        data2_array = data2_array.reshape(-1, len(columns2))
        data2_array = data2_array[:, 1:]  # erase the time column
        columns2 = columns2[1:]

        # Prepend date to HH:MM strings
        timestamps = ['%s %s' % (date, t) for t in hours]

        data_array = np.concatenate((data1_array, data2_array), axis=1)  # concat data 1 and 2

        # Convert to dataframe
        df = pd.DataFrame(index=timestamps, data=data_array, columns=columns1 + columns2)
        df.index = pd.to_datetime(df.index)

        return df