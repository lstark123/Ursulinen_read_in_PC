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
from selenium.webdriver.chrome.service import Service
import time
import sounddevice as sd
import traceback
import random
import xarray as xr
import pandas as pd
from pyflightdata import FlightData
import vonage
from selenium.webdriver.common.by import By
import vonage

class Logging:
    def __init__(self):
        self.filepath = os.path.join("C:\\Users\\c7441354\\Documents\\Ursulinen\\Data_airport\\logging", "logging_weather_"+datetime.datetime.now().strftime("%Y_%m_%d-%H-%M") + ".txt")
        print("Logging to ", self.filepath)
        with open(self.filepath, "a") as f:
            f.write(f"-----Logging----- starting from: {datetime.datetime.now()}" )
    def save_logging(self, text):
        print(text)
        time =datetime.datetime.now().strftime("%Y-%M-%D_%H:%M:%S")
        with open(self.filepath, "a") as f:
            f.write("\n" + time +" "+ text)
    def give_error(self, text):
        print(f"Error: {text}")
        time =datetime.datetime.now().strftime("%Y-%M-%D_%H:%M:%S")
        stack_trace = traceback.format_exc()
        with open(self.filepath, "a") as f:
            f.write("\n" + time + "Error -------------------------\n"+ str(text) + "\n")
            f.write(stack_trace)


logging = Logging()

class Weatherdata():
    def __init__(self):
        # Set the absolute path to chromedriver
        self.service = Service(r"C:\Users\c7441354\PycharmProjects\Ursulinen_read_in_PC\chromedriver_win32\chromedriver19.exe")
        self.options = webdriver.ChromeOptions()
        # driver = webdriver.Chrome(service=service, options=options)
        # self.chromedrive_path = r"C:\Users\peaq\AppData\Local\Google\Chrome\chromedriver.exe"

    def render_page(self, url):
        driver = webdriver.Chrome(service=self.service, options=self.options)
        driver.get(url)
        time.sleep(3)  # Could potentially decrease the sleep time
        r = driver.page_source
        driver.quit()

        return r

    def get_data(self,date_to_load_weatherdata_from):
        global logging
        logging.save_logging(f"Start scraping data for day {date_to_load_weatherdata_from}")
        station = "IINNSB49"
        date = date_to_load_weatherdata_from.strftime("%Y-%m-%d")
        # Render the url and open the page source as BS object
        url = 'https://www.wunderground.com/dashboard/pws/%s/table/%s/%s/daily' % (station,
                                                                                   date, date)
        logging.save_logging("I open the webpage")
        r = self.render_page(url)
        soup = BS(r, "html.parser", )

        container = soup.find('lib-history-table')

        # Check that lib-history-table is found
        if container is None:
            raise ValueError("could not find lib-history-table in html source for %s" % url)

        # Get the timestamps and data from two separate 'tbody' tags
        all_checks = container.find_all(
            'tbody')  # get the data in the tablebody (there are two tables, one with time, one with data)
        if all_checks:
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
            time_datetime = pd.to_datetime(timestamps, format='%Y-%m-%d %I:%M %p')
            time_UNIX = np.array(time_datetime.astype(np.int64) // 10**9)[:, np.newaxis]
            data_array = np.concatenate((time_UNIX, data1_array, data2_array), axis=1)  # concat data 1 and 2
            columns = ["Time_UNIX"] + columns1 + columns2

            df = pd.DataFrame(data_array,columns = columns)

            return df
        else:
            logging.save_logging("No weatherdata for this time")
            return []

try:
    weather = Weatherdata()
    start_date = datetime.date(2023,11,1)
    end_date = datetime.date(2023,11,22)
    if end_date:
        ddays = (end_date-start_date).days
    else:
        ddays = 5
    # Create a list of datetime.date objects for the last week
    dates_to_load = [start_date + datetime.timedelta(days=x) for x in range(ddays)]
    for date in dates_to_load:
        data = weather.get_data(date)
        path_dir = "C:\\Users\\c7441354\\Documents\\Ursulinen\\Data_airport\\weather"
        path_date = os.path.join(path_dir,date.strftime("%Y-%m-%d")+"_weather_data.csv")
        data.to_csv(path_date)
        logging.save_logging(f"Saved the loaded data to {path_date}")
except Exception as error:
    logging.give_error(error)