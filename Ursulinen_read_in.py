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
from selenium.webdriver.common.by import By
# importing the module
import logging


#fragen:
# wieso sind die Messpunkte nicht immer zur gleichen Zeit?
# since I implemented the flight arrivals after every 5th timestamp big gap -> takes too long to plot?



class Measurement:
    def __init__(self):
        self.initial_time = datetime.datetime.now()
        self.time = np.array(self.initial_time)
        # self.save_newfile_ndatapoints = 60*60
        self.save_newfile_ndatapoints = 30
        print(f"Saving every second in {self.save_newfile_ndatapoints} seconds files")
        self.total_n_updates = 0


class Partector(Measurement):
    def __init__(self,comport):
        # now with default values
        super().__init__()

        self.data_names = np.array(["Time since instrument start [s]",
                           "Charger diffusion current [nA]",
                           "Charger high voltage [V]",
                           "Electrometer 1 reading [mV]",
                           "Electrometer 2 reading [mV]",
                           "Electrometer 1 amplitude [mV]",
                           "Electrometer 2 amplitude [mV]",
                           "Temperature [°C]",
                           "Relative Humidity [%]",
                           "Status [see documentation]",
                           "Precipitator voltage [V]",
                           "Battery voltage [V]",
                           "Phase angle (disregard)",
                           "LDSA value [mum2/cm3]",
                           "Diameter [nm]",
                           "Number [1/cm3]",
                           "????",
                           "Differential Pressure [Pa/240]",
                           "Lag (disregard)"])
        self.n_values = self.data_names.size
        self.data = xr.DataArray(
            np.full([self.save_newfile_ndatapoints, self.n_values],np.nan),
            coords = {"time": np.full(self.save_newfile_ndatapoints,datetime.datetime(2000,1,1)), #placeholder for time
                      "measured_variable": self.data_names},
            dims = ["time","measured_variable"]

        )

        self.datasecondsback = xr.DataArray(
            np.full([self.save_newfile_ndatapoints, 1],np.nan),
            coords = {"time": np.full(self.save_newfile_ndatapoints,datetime.datetime(2000,1,1)), #placeholder for time
                      "measured_variable": ["Amplitude"]},
            dims = ["time","measured_variable"]
        )
        self.data.attrs["Measurement"] = "Partector"
        self.number_downloads_onefile = 0
        self.comport = comport
        self.ser = self.serial_connection(self.comport)


    def serial_connection(self ,COM):
        global ser
        COMPORT = f"COM{COM}"
        for x in range(0,10):
            try:
                ser = serial.Serial(COMPORT,
                                    115200,
                                    parity = serial.PARITY_NONE,
                                    stopbits = serial.STOPBITS_ONE,
                                    bytesize = serial.EIGHTBITS,
                                    rtscts=True
                )
                print(f"I opened COM port {COM}")
                return ser
                break
            except:
                print(f"I tried opening COM port {COMPORT}")

            x +=1
        print(f"error with connecting partector COM")
        ser = False
        return ser
        # check to see if port is open or closed
    def serial_connetction_one_time(self, ser):
        try:
            ser = serial.Serial(self.comport,
                                     115200,
                                     parity=serial.PARITY_NONE,
                                     stopbits=serial.STOPBITS_ONE,
                                     bytesize=serial.EIGHTBITS,
                                     rtscts=True
                                     )
            print(f"I made new COM port {self.comport} connection")
        except:
            try:
                ser.open()
                print(f"I opened COM port {self.comport}")

            except:
                pass

    def get_data(self,ser):
        if ser == False:
            self.serial_connetction_one_time(self.ser)
            print(f"COM port {self.comport} is not opened")
        if (ser.isOpen() == False):
            self.serial_connetction_one_time(self.ser)
            print(f"COM port {self.comport} is not opened")

        else:
            try:
                ser.write(bytearray('D?', 'ascii'))
                newline = ser.readline()
                newline = str(newline, 'utf-8').split('\t')
                newline = [float(x) for x in newline]
                return np.array(newline)
            except:
                print(f"Something went wrong with querying data form Partector")
                ser.close()
                return np.full(3,np.nan)






    def check_listening(self):
        pass

class Microphone(Measurement):
    def __init__(self):
        # now with default values
        super().__init__()
        try:
            self.stream = sd.InputStream(
                samplerate=44100,
                channels=2,
                blocksize=44100)
        except:
            self.stream = sd.InputStream(
                samplerate=44100,
                channels=1,
                blocksize=44100)

        self.data = xr.DataArray(
            np.full([self.save_newfile_ndatapoints, 1],np.nan),
            coords = {"time": np.full(self.save_newfile_ndatapoints,datetime.datetime(2000,1,1)), #placeholder for time
                      "measured_variable": ["Amplitude"]},
            dims = ["time","measured_variable"]
        )
        self.data.attrs["Measurement"] = "Microphone"

        self.datasecondsback = xr.DataArray(
            np.full([self.save_newfile_ndatapoints, 1],np.nan),
            coords = {"time": np.full(self.save_newfile_ndatapoints,datetime.datetime(2000,1,1)), #placeholder for time
                      "measured_variable": ["Amplitude"]},
            dims = ["time","measured_variable"]
        )
        self.time_abovethreshold = np.empty(1,dtype=bool)
        self.data_names = "Audiodaten vom Dach"
        self.stream.start()
        self.number_downloads_onefile = 0
        print("I opened Microphone")

    def get_onesec_meanamplitude(self):
        if sd.query_devices(sd.default.device[0])["name"] == "Mikrofon (BY-LM40)":
            try:
                recording,status = self.stream.read(44100)
                recording = np.nansum(recording, axis = 1)
                calibfactor = 1 / 45000
                recording = recording/calibfactor

                def rms_flat(data):
                    return np.sqrt(np.mean(np.absolute(data) ** 2))

                dBdata = 20 * np.log10(rms_flat(recording))
                return(dBdata)
            except:
                print("Something went wrong in gathering Microphone Amplitude")
                return np.nan
        else:
            print("default device is not external microphone")
# download flight data by:
# flight = Flightdata()
# flight.data = flight.get_flightdata()
#get flight data acces xarray by: flight.data["arrivals"] or flight.data["departures"]
# select data by: flight.data["departures"].sel(flightdata = x)
# with x as 'scheduled', 'estimated', 'origin', 'destination', 'aircraftmodel', 'callsign'
class Flightdata():
    """
    The data is stored in self.data as an xarray with coordinates time, flightdata
    The time dimesion is scheduled time
    Flightdata is all *str: [time_estimated_UNIX, time_real_UNIX", "time_scheduled_UNIX", "status", "origin", "destination", "aircraftmodel",
                            "aircraftmodel_code", "callsign", "airline", "arrival_departure"]
    And is "" if no data is given
    """
    def __init__(self):
        self.data = self.get_flightdata()

    def extract_relevant_data(self, flightdata_array, arrival_or_departure):
        nrflights = len(flightdata_array)
        time_coordinates = np.empty(nrflights, dtype="datetime64[s]")
        flight_movement_info = {"default_identification": [""] * nrflights,
                                "time_scheduled_UNIX_departure": [""]*nrflights,
                                "time_scheduled_UNIX_arrival": [""] * nrflights,
                                "time_estimated_UNIX": [""]*nrflights,
                                "time_real_UNIX": [""]*nrflights,
                                "time_best_UNIX": [""]*nrflights,
                                "status" : [""]*nrflights,
                                "origin": [""]*nrflights,
                                "destination": [""]*nrflights,
                                "aircraftmodel": [""]*nrflights,
                                "aircraftmodel_code": [""]*nrflights,
                                "callsign": [""]*nrflights,
                                "airline": [""]*nrflights,
                                "arrival_departure": [""]*nrflights,
                                "fillout_direction_of_flight_to_from_innsbruck": [""]*nrflights
                                }
        for index, flight in enumerate(flightdata_array):
            flight_movement_info["arrival_departure"][index] = arrival_or_departure

            date = flight["flight"]["time"]["scheduled"][arrival_or_departure + "_date"]
            time = flight["flight"]["time"]["scheduled"][arrival_or_departure + "_time"]
            flight_movement_time = pd.to_datetime(date + time, format='%Y%m%d%H%M')
            time_coordinates[index] = flight_movement_time
            flight_movement_info["time_scheduled_UNIX_"+ arrival_or_departure][index] = str(round(flight_movement_time.timestamp()))
            flight_movement_info["time_best_UNIX"][index] = str(round(flight_movement_time.timestamp()))
            if arrival_or_departure == "departure":
                time_millis = flight["flight"]["time"]["scheduled"]["arrival_millis"]
                flight_movement_time = datetime.datetime.fromtimestamp(time_millis / 1000)
                flight_movement_info["time_scheduled_UNIX_arrival"][index] = str(round(flight_movement_time.timestamp()))
            else:
                time_millis = flight["flight"]["time"]["scheduled"]["departure_millis"]
                flight_movement_time = datetime.datetime.fromtimestamp(time_millis / 1000)
                flight_movement_info["time_scheduled_UNIX_departure"][index] = str(
                    round(flight_movement_time.timestamp()))

            try:
                date = flight["flight"]["time"]["estimated"][arrival_or_departure + "_date"]
                time = flight["flight"]["time"]["estimated"][arrival_or_departure + "_time"]
                flight_movement_time = pd.to_datetime(date + time, format='%Y%m%d%H%M')
                flight_movement_info["time_estimated_UNIX"][index] = str(round(flight_movement_time.timestamp()))
                flight_movement_info["time_best_UNIX"][index] = str(round(flight_movement_time.timestamp()))
            except:
                flight_movement_info["time_estimated_UNIX"][index] = ""
            try:
                date = flight["flight"]["time"]["real"][arrival_or_departure + "_date"]
                time = flight["flight"]["time"]["real"][arrival_or_departure + "_time"]
                flight_movement_time = pd.to_datetime(date + time, format='%Y%m%d%H%M')
                flight_movement_info["time_real_UNIX"][index] = str(round(flight_movement_time.timestamp()))
                flight_movement_info["time_best_UNIX"][index] = str(round(flight_movement_time.timestamp()))
            except:
                flight_movement_info["time_real_UNIX"][index] = ""

            for z in ["origin", "destination"]:
                try:
                    flight_place = flight["flight"]["airport"][z]["code"]["iata"]
                    flight_movement_info[z][index] = flight_place
                except:
                    flight_movement_info[z][index] = ""
            try:
                flight_movement_info["aircraftmodel"][index]= flight["flight"]["aircraft"]["model"]["text"]
                flight_movement_info["aircraftmodel_code"][index] = flight["flight"]["aircraft"]["model"]["code"]
                flight_movement_info["callsign"][index] = flight["flight"]["identification"]["callsign"]
                flight_movement_info["status"][index] = flight["flight"]["status"]["text"]

            except:
                flight_movement_info["aircraftmodel"][index] = ""
                flight_movement_info["callsign"][index] = ""
                flight_movement_info["aircraftmodel_code"][index] = ""
                flight_movement_info["status"][index] = ""

            try:
                flight_movement_info["airline"][index] = flight["flight"]["airline"]["name"]
            except:
                flight_movement_info["airline"][index] = ""
            try:
                flight_movement_info["default_identification"][index] = flight["flight"]["identification"]["number"]["default"]
            except:
                flight_movement_info["default_identification"][index] = ""

        flight_movement_info = pd.DataFrame(flight_movement_info)
        flight_movement_info.index = time_coordinates
        print("Extracted relevant information out of flight data response")

        return flight_movement_info
    def get_flightdata(self):
        print("Try to get Flight data")
        f = FlightData()
        arrivals_alldata = f.get_airport_arrivals('INN',earlier_data = True)
        departures_alldata = f.get_airport_departures('INN',earlier_data = True)

        arrivals = self.extract_relevant_data(arrivals_alldata, "arrival")
        departures = self.extract_relevant_data(departures_alldata, "departure")
        flight_movements = pd.concat([arrivals,departures])

        flight_movements_info = xr.DataArray(
            flight_movements,
            coords={"time": flight_movements.index,
                    "flightdata": flight_movements.columns.values},
            dims=["time", "flightdata"])

        flight_movements_info = flight_movements_info.sortby(flight_movements_info.time)

        return flight_movements_info

    def make_screenshot_of_flight_path(self,callsign, time_flight, savelocation_screenshot):
        """
        :param callsign: `str` - callsign of the vehicle.
        :param time_flight: "str" - scheduled time of flight movement (arrival/depature) at Innsbruck Airport in Unix time
        :return:
        """
        service = Service(r"C:\Users\peaq\Uniarbeit\Python\chromedriver\chromedriver-win64\chromedriver.exe")
        options = webdriver.ChromeOptions()
        options.add_argument("--start-maximized")
        driver = webdriver.Chrome(service=service, options=options)
        time_flightmovement = str(time_flight)  # scheduled time in UNIX
        print("Try getting path of flight callsign ", callsign, " with time ",
              datetime.datetime.fromtimestamp(1695812100))
        # try:
        webadress = "https://www.flightradar24.com/data/flights/" + callsign
        print("access website")
        # driver.get('https://www.flightradar24.com/data/airports/inn/arrivals')
        driver.get(webadress)
        print("wait 1s")
        time.sleep(1)

        btn_accept = driver.find_element(By.XPATH, "//button[@id='onetrust-accept-btn-handler']").click()
        print("accept cookies")
        print("wait 1s")
        time.sleep(1)

        # try:
        btn_selectplay = driver.find_element(By.XPATH,
                                             "//a[@data-timestamp='{}' and @class='btn btn-sm btn-playback btn-table-action text-white bkg-blue fs-10 ']".format(
                                                 time_flightmovement)).click()
        print("select flight to display")
        # loadmoreflights_btn = driver.find_element(By.XPATH,"//button[@class='btn btn-table-action btn-flights-load']").click()
        print("wait 6s")
        time.sleep(6)
        # print(datetime.datetime.fromtimestamp(int(time_flight)).strftime("%Y-%m-%d_%H_%M"))
        # print(callsign)
        driver.get_screenshot_as_file(savelocation_screenshot)
        driver.quit()
        print("saved the screenshot to ", savelocation_screenshot)
        print("end...")


class Weatherdata(Measurement):
    def __init__(self):
        # now with default values
        super().__init__()
        # Set the absolute path to chromedriver
        # self.service = Service(r"C:\Users\c7441354\PycharmProjects\Ursulinen_read_in_PC\chromedriver_win32\chromedriver17.exe")
        self.service = Service(r"C:\Users\peaq\Uniarbeit\Python\chromedriver\chromedriver-win64\chromedriver.exe")

        self.options = webdriver.ChromeOptions()
        # driver = webdriver.Chrome(service=service, options=options)
        # self.chromedrive_path = r"C:\Users\peaq\AppData\Local\Google\Chrome\chromedriver.exe"
        self.data = self.get_data()

    def render_page(self, url):
        driver = webdriver.Chrome(service=self.service, options=self.options)
        driver.get(url)
        time.sleep(3)  # Could potentially decrease the sleep time
        r = driver.page_source
        driver.quit()

        return r

    def get_data(self):
        station = "IINNSB41"
        date = datetime.date.today().strftime("%Y-%m-%d")
        print("Trying to get data from the wunderground page")
        # Render the url and open the page source as BS object
        url = 'https://www.wunderground.com/dashboard/pws/%s/table/%s/%s/daily' % (station,
                                                                                   date, date)
        print("I open the wunderground webpage")
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

            data_array = np.concatenate((data1_array, data2_array), axis=1)  # concat data 1 and 2
            columns = columns1 + columns2
            #to xarray
            weatherdata = xr.DataArray(
                data_array,
                coords={"time": timestamps,
                        "weatherdata": columns},
                dims=["time", "weatherdata"])

            return weatherdata
        else:
            print("No weatherdata for this time")
            return  0

#Workers for multithreading
class WorkerSignals(QObject):
    '''
    Defines the signals available from a running worker thread.

    Supported signals are:

    finished
        No data

    error
        tuple (exctype, value, traceback.format_exc() )

    result
        object data returned from processing, anything

    progress
        int indicating % progress

    '''
    finished = pyqtSignal()
    error = pyqtSignal(tuple)
    result = pyqtSignal(object)

class Worker(QRunnable):
    '''
    Worker thread

    Inherits from QRunnable to handler worker thread setup, signals and wrap-up.

    :param callback: The function callback to run on this worker thread. Supplied args and
                     kwargs will be passed through to the runner.
    :type callback: function
    :param args: Arguments to pass to the callback function
    :param kwargs: Keywords to pass to the callback function

    '''

    def __init__(self, fn, *args, **kwargs):
        super(Worker, self).__init__()

        # Store constructor arguments (re-used for processing)
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()


    @pyqtSlot()
    def run(self):
        '''
        Initialise the runner function with passed args, kwargs.
        '''

        # Retrieve args/kwargs here; and fire processing using them
        try:
            result = self.fn(*self.args, **self.kwargs)
        except:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc()))
        else:
            self.signals.result.emit(result)  # Return the result of the processing
        finally:
            self.signals.finished.emit()  # Done

# so the worker can then be initialised by worker = Worker(function, arguments)
# the output of the function can be shown by worker.signals.result.connect(print_ouput function)
# the worker can say when it is finished by: worker.signals.finished.connect(print_completefunciton)

#canvas for matplotlib
class MplCanvas(FigureCanvas):

    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        gs = self.fig.add_gridspec(3, 1)
        self.ax1 = self.fig.add_subplot(gs[0,0])
        self.ax2 = self.fig.add_subplot(gs[1, 0])
        self.ax3 = self.fig.add_subplot(gs[2, 0])
        self.ax1.tick_params('x', labelbottom=False)
        self.ax2.tick_params('x', labelbottom=False)


        super(MplCanvas, self).__init__(self.fig)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        #self.save_location = str(QFileDialog.getExistingDirectory(self, "Wo speicher ich die Daten hin?"))
        self.save_location = r"C:\Users\c7441354\Documents\Ursulinen\roof_data"
        #self.save_location = "F:\\Uniarbeit\\data\\test"
        self.date_save_location = os.path.join(self.save_location, datetime.date.today().strftime("%Y_%m_%d"))
        if not(os.path.exists(self.date_save_location)):
            os.mkdir(self.date_save_location)
        print(f"Saving data at {self.save_location}")
        self.loggingfile_location = os.path.join(self.date_save_location,"logging"+datetime.datetime.now().strftime("%Y_%m_%d-%H-%M") + ".txt")

        self.comportpartector = 4# self.dialogue_select_comport()
        self.part = Partector(self.comportpartector)
        self.mic = Microphone()
        self.flight = Flightdata()

        loadweatherdata = False
        if loadweatherdata:
            self.weather = Weatherdata()

        #get cutout seconds which are plotted back
        self.secondsback = 60
        self.amp_threshold = 80
        self.plottiming = {"begin":0,"end":0}
        self.timer_counting = True

        # update save file every n datapoints
        self.save_file_update_ndatapoints = 15

        # path of current file to save to first is a little to early here, but no problem
        self.save_file_current_inital_time = datetime.datetime.now()
        self.save_file_current_path = os.path.join(self.date_save_location,
                                                   self.save_file_current_inital_time.strftime("%Y_%m_%d_%Hh%Mm%Ss") + ".nc")
        # initiate ui
        self.init_ui()
        #multithreading
        self.threadpool = QThreadPool()


        #update data every second
        self.time_onesec = 1000
        self.timer_onesec = QtCore.QTimer()
        self.timer_onesec.setInterval(self.time_onesec)
        self.timer_onesec.timeout.connect(self.timer_onesec_funct_to_worker)
        print("starting timer")
        self.timer_onesec.start()


    def init_ui(self):
        print("Initializing Window")
        self.setGeometry(0,0,1000,1000)
        mainlayout = QVBoxLayout()
        self.canvas = MplCanvas(self, width=5, height=4, dpi=100)
        mainlayout.addWidget(self.canvas)


        self.timewindow_combobox = QComboBox()
        self.timewindow_combobox.addItems(["1 min", "5 min","30min", "1 h"])
        mainlayout.addWidget(self.timewindow_combobox)
        self.timewindow_combobox.currentIndexChanged.connect(self.timewindow_combobox_changed)

        #
        threshold_selctor = QLineEdit()
        threshold_selctor.setValidator(QDoubleValidator(0.99, 99.99, 4))
        threshold_selctor.textChanged.connect(self.threshold_changed)

        self.horizontalLayout = QHBoxLayout()
        self.label = QLabel("select threshold")
        self.horizontalLayout.addWidget(self.label)
        self.horizontalLayout.addWidget(threshold_selctor)
        mainlayout.addLayout(self.horizontalLayout)

        self.exitbutton = QPushButton("Exit")
        mainlayout.addWidget(self.exitbutton)
        self.exitbutton.clicked.connect(self.the_button_was_clicked)

        widget = QWidget()
        widget.setLayout(mainlayout)
        self.setCentralWidget(widget)

    def timer_onesec_funct_to_worker(self):
        if self.timer_counting == True:
            def timer_one_sec():
                try:
                    self.part.number_downloads_onefile += 1
                    print(self.part.number_downloads_onefile,"download dataline")
                    self.download_data(self.part, np.full(19, self.part.number_downloads_onefile))  # ****
                    # self.download_data(self.part, self.part.get_data(self.part.ser))
                    self.download_data(self.mic, np.random.rand(1))  # *****
                    # self.download_data(self.mic, self.mic.get_onesec_meanamplitude())


                    if self.part.number_downloads_onefile % 20 == 0:  # every update datapoints save (it is normally 60*60 downloads)
                        print(self.part.number_downloads_onefile, "Save file")
                        print("Stopping Timer")
                        self.timer_counting = False
                        self.save_file()
                        self.timer_counting = True
                        print("Restarting Timer")
                        f = open(self.loggingfile_location, "a")
                        f.write("\n" + datetime.datetime.now().strftime("%H-%M-%S") + "New file")

                    if self.part.number_downloads_onefile % 15 == 0:  # every update datapoints save (it is normally 15)
                        print(self.part.number_downloads_onefile, "Save the datarows")
                        self.save_datarow()
                        f = open(self.loggingfile_location, "a")
                        f.write("\n" + datetime.datetime.now().strftime("%H-%M-%S") + "Save datarow")


                    if self.part.number_downloads_onefile % 5 == 0:  # update plots every 5 downloads
                        print(self.part.number_downloads_onefile, "Update Plot")
                        self.plottiming["begin"] = datetime.datetime.now() - datetime.timedelta(seconds=self.secondsback)
                        self.plottiming["end"] = datetime.datetime.now() + datetime.timedelta(seconds=self.secondsback / 6)
                        self.update_plot(self.canvas.ax3, self.part, "Diameter [nm]", color='C0')
                        self.update_plot(self.canvas.ax2, self.part, "Number [1/cm3]", color='C1')
                        self.update_plot(self.canvas.ax1,self.mic,"Amplitude",color='C3')
                except Exception as error:
                    f = open(self.loggingfile_location, "a")
                    f.write("\n" + datetime.datetime.now().strftime("%H-%M-%S") + str(error))


            worker = Worker(timer_one_sec)
            self.threadpool.start(worker)

    def the_button_was_clicked(self):
        self.part.ser.close()
        sys.exit(0)

    def dialogue_select_comport(self):
        comport, ok = QInputDialog.getInt(self, 'input dialog', 'Auf welchen Comport ist der Partector')
        if ok:
            print("Search for Partector on COM port ", comport)
            return comport

    def threshold_changed(self,text):
        def to_worker():
            self.amp_threshold = float(text.replace(",","."))
            print(f"New Amplitude threshold: {self.amp_threshold}")

        worker = Worker(to_worker)
        self.threadpool.start(worker)

    def timewindow_combobox_changed(self, index):
        self.index = index
        if self.index == 0:
            self.secondsback = 60
        elif self.index == 1:
            self.secondsback = 5*60
        elif self.index == 2:
            self.secondsback = 60*30
        elif self.index == 3:
            self.secondsback = 60*60
        print(f"plotte jetzt {self.secondsback}s zurück")



    def download_data(self,measurement,newline):
        #first download new line

        newline = newline
        newtime = datetime.datetime.now()
        # print(f"thread {self.threadpool.activeThreadCount()} at computertime {datetime.datetime.now()} -> downloaded complete line {self.part.number_downloads_onefile} with time {newtime} for " + measurement.data.attrs["Measurement"])


        #now append it to the cached data (shift up)
        if measurement.data.where(measurement.data['time.year'] == 2000, drop=True).size > 0:  # if we have placeholdetime
            index_newrow = np.argwhere((measurement.data['time.year'] == 2000).values)[
                0]  # here we convolutedly get the first row where we have a placeholder
            measurement.data[index_newrow, :] = newline
            newtimes = measurement.data.time.values
            newtimes[index_newrow] = newtime
            measurement.data = measurement.data.assign_coords({'time': ('time', newtimes)})

        else:  # shift the values up (newest are down, oldest are up)
            measurement.data = measurement.data.shift(time=-1)
            measurement.data[dict(time=measurement.save_newfile_ndatapoints - 1)] = newline
            newtimes = (measurement.data.time.shift(time=-1, fill_value=newtime)).values
            measurement.data = measurement.data.assign_coords({'time': ('time', newtimes)})


    def save_datarow(self):
        #save the new data every save_file_update_ndatapoints seconds
            #if we have a new day make new directory
            if os.path.basename(self.date_save_location) != datetime.date.today().strftime("%Y_%m_%d"):
                self.date_save_location = os.path.join(self.save_location, datetime.date.today().strftime("%Y_%m_%d"))
                if not (os.path.exists(self.date_save_location)):
                    os.mkdir(self.date_save_location)
                #we have to update the save_file_current_path since the directory changed
                self.save_file_current_path = os.path.join(self.date_save_location,
                                                           self.save_file_current_inital_time.strftime(
                                                               "%Y_%m_%d_%Hh%Mm%Ss") + ".nc")

            print(f"thread {self.threadpool.activeThreadCount()} -> save line {self.part.number_downloads_onefile - self.save_file_update_ndatapoints} to {self.part.number_downloads_onefile} at {self.save_file_current_path} ...")

            self.part.data.to_netcdf(self.save_file_current_path, group=self.part.data.attrs["Measurement"],engine="netcdf4", mode = "w")
            print("...saved Partector")

            self.mic.data.to_netcdf(self.save_file_current_path, group=self.mic.data.attrs["Measurement"], engine="netcdf4", mode="a")
            print("...save Microphone")

    def save_file(self):
        print(
            f"thread {self.threadpool.activeThreadCount()} -> save whole file at {self.save_file_current_path} ...")

        # this happens at the end of the file
        #update flight data and save it
        try:
            self.flight.data = self.flight.get_flightdata()


            time.sleep(10)
            self.flight.data.to_netcdf(self.save_file_current_path, group="Flights", engine="netcdf4", mode="a")
            print("..saved flight data")
            selectedtime = slice(datetime.datetime.now() - datetime.timedelta(hours=1), datetime.datetime.now())
            for flight_time_best,identification, fligth_time_departure in zip(self.flight.data.sel(time = selectedtime).sel(flightdata = "time_best_UNIX").values,
                                                     self.flight.data.sel(time = selectedtime).sel(flightdata = "default_identification").values,
                                                     self.flight.data.sel(time = selectedtime).sel(flightdata = "time_scheduled_UNIX_departure").values):
                if identification != "None":
                    try:
                        flight_str = datetime.datetime.fromtimestamp(int(flight_time_best)).strftime( "%Y-%m-%d_%H_%M")+ "_" +"flight" + "_"+ identification + ".png"
                        screenshot_sp = os.path.join(self.date_save_location, flight_str)
                        #problem: button is labled on starting time of flight!!! on arrivals that is a prblem
                        self.flight.make_screenshot_of_flight_path(identification,fligth_time_departure, screenshot_sp)
                    except Exception as error:
                        print("Didnot find any path for the flight ", identification, " at ", flight_time_best, "Error: ", error)
                else:
                    print("No identification number on this flight", identification, " at ", flight_time_best)
        except Exception as error:
            print("Could not save flight data ", error)

        try:
            self.weather.data = self.weather.get_data()
            self.weather.data.to_netcdf(self.save_file_current_path, group="Weather", engine="netcdf4", mode="a")
            print("..saved weather data")
        except Exception as error:
            print("Could not save weather data.", error)

        #make a new file
        self.save_file_current_inital_time = datetime.datetime.now()
        self.save_file_current_path = os.path.join(self.date_save_location,
                                                   self.save_file_current_inital_time.strftime("%Y_%m_%d_%Hh%Mm%Ss") + ".nc")
        print(f"open new file at {self.save_file_current_path}")
        self.part.number_downloads_onefile = 0





    def update_plot(self,axis,measurement,datatoplot, color):
        #try:
        #initialize change with new boundaries
        axis.cla()
        axis.set_xlim(self.plottiming["begin"], self.plottiming["end"])
        exclude_default_data = measurement.data.where(measurement.data['time.year'] > 2000, drop=True)
        axis.set_ylim([0, max(exclude_default_data.sel(measured_variable=datatoplot).values)*1.1])
        axis.grid()
        axis.set_xlabel("local time")

        # short time plotting
        if self.secondsback <= 5 * 60:
            axis.plot(exclude_default_data.time, exclude_default_data.sel(measured_variable=datatoplot), color=color)


        #plotting with averages for longer time periods
        elif self.secondsback > 5 * 60:
            #manipulate data, so that we dont show default data (time = year 2000) and are strictly monotonic
            exclude_default_data = measurement.data.where(measurement.data['time.year'] > 2000, drop=True)
            avgs = exclude_default_data.sortby(exclude_default_data.time).resample(time='15s').mean()
            axis.plot(avgs.time, avgs.sel(measured_variable=datatoplot), color=color)

        if measurement.data.attrs["Measurement"] == "Microphone":
            # # #making background color
            # timetrue = measurement.data.where(measurement.data.time > np.datetime64(self.plottiming["begin"]),
            #                                   drop=True) < self.amp_threshold
            # timetrue = np.array([1 if i else 0 for i in timetrue])
            # firsttime = pd.to_datetime(measurement.data.time[0].values)
            # norm = matplotlib.pyplot.Normalize(0, 1)
            # if firsttime > self.plottiming["begin"]:
            #
            #     x_axislimit1, x_axislimit2 = axis.get_xlim()
            #     seconds_to_firstpoint = datetime.datetime.now() - firsttime
            #     x_axislimit1 = x_axislimit2 - (x_axislimit2 - x_axislimit1) * (
            #         seconds_to_firstpoint.total_seconds()) / self.secondsback
            #     axis.pcolorfast((x_axislimit1, x_axislimit2), axis.get_ylim(), timetrue[np.newaxis], cmap='RdYlGn',
            #                     norm=norm, alpha=0.3)
            # else:
            #     axis.pcolorfast(axis.get_xlim(), axis.get_ylim(), timetrue[np.newaxis], cmap='RdYlGn', norm=norm,
            #                     alpha=0.3)
            axis.axhline(y=self.amp_threshold)
            axis.legend(["Amplitude Mikrophon"])
            axis.set_ylabel(r"[$dB$]")

        # make the flight time y axis
        selectedtime = slice(datetime.datetime.now()-datetime.timedelta(hours =1),datetime.datetime.now())
        for arrdep in ["arrival","departure"]:
            arrdep_data = self.flight.data.where(self.flight.data.loc[:,'arrival_departure'] == arrdep).dropna(dim="time", how="any").sel(time = selectedtime)
            times = [datetime.datetime.fromtimestamp(float(x)-2*60*60) for x in arrdep_data.sel(flightdata = "time_best_UNIX").sel(time = selectedtime)]
            if arrdep == "arrival":
                strings = ["Flug " + str(arrdep_data.sel(flightdata = "default_identification").sel(time = selectedtime).values[i]) +" von "+
                              str(arrdep_data.sel(flightdata = "origin").sel(time = selectedtime).values[i])
                            for i in range(0,arrdep_data.sel(time = selectedtime).shape[0])]
                for time, string in zip(times, strings):
                    axis.axvline(x = time, color='tab:red')
                    if datatoplot == "diameter":
                        axis.text(time, 1, string, rotation=90)
            if arrdep == "departure":
                strings = ["Flug "+ str(arrdep_data.sel(flightdata = "default_identification").sel(time = selectedtime).values[i]) +" nach "+
                          str(arrdep_data.sel(flightdata = "destination").sel(time = selectedtime).values[i])
                                 for i in range(0,arrdep_data.sel(time = selectedtime).shape[0])]
            for time, string in zip(times, strings):
                axis.axvline(x = time, color='tab:purple')
                if datatoplot == "Diameter [nm]":
                    axis.text(time, 1, string, rotation=90)
                    print("Plot ", arrdep, "timestamp at", time, "with", string)

        axis.legend([datatoplot])
        if datatoplot == "Number [1/cm3]":
            axis.set_ylabel(r"[$ Teilchen/cm^3$]")
            axis.legend(["Anzahldichte Aerosolpartikel"])

        elif datatoplot == "Amplitude":
            axis.set_ylabel(r"[$dB$]")
            axis.legend(["Lautstärke vom Dach"])
        else:

            axis.set_ylabel(r"[$nm$]")
            axis.legend(["Durchmesser Aerosolpartikel"])
            axis.set_xlabel("local time")

        self.canvas.draw()
        #except:
        #    print("...Could no plot ", datatoplot, " data")


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    app.exec()
    # Flightdata()


if __name__ == '__main__':
    main()
