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

#fragen:
# wieso sind die Messpunkte nicht immer zur gleichen Zeit?
# since I implemented the flight arrivals after every 5th timestamp big gap -> takes too long to plot?



class Measurement:
    def __init__(self):
        self.initial_time = datetime.datetime.now()
        self.time = np.array(self.initial_time)
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
        self.n_values = 3
        self.data = xr.DataArray(
            np.full([self.save_newfile_ndatapoints, self.n_values],np.nan),
            coords = {"time": np.full(self.save_newfile_ndatapoints,datetime.datetime(2000,1,1)), #placeholder for time
                      "measured_variable": ["LDSA", "diameter", "number_conc"]},
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
                return np.array(newline[13:16])
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
    def __init__(self):
        self.data = self.get_flightdata()

    def extract_relevant_data(self, flightdata_array, arrival_or_departure):
        flight_movement_info = {"time": np.array([]),
                                "status" : np.array([]),
                                "origin": np.array([]),
                                "destination": np.array([]),
                                "aircraftmodel": np.array([]),
                                "callsign": np.array([])}
        for flight in flightdata_array:
            try:
                date = flight["flight"]["time"]["estimated"][arrival_or_departure + "_date"]
                time = flight["flight"]["time"]["estimated"][arrival_or_departure + "_time"]
                flight_movement_time = pd.to_datetime(date + time, format='%Y%m%d%H%M')
                flight_movement_info["time"] = np.append(flight_movement_info["time"], flight_movement_time)
            except:
                try:
                    date = flight["flight"]["time"]["real"][arrival_or_departure + "_date"]
                    time = flight["flight"]["time"]["real"][arrival_or_departure + "_time"]
                    flight_movement_time = pd.to_datetime(date + time, format='%Y%m%d%H%M')
                    flight_movement_info["time"] = np.append(flight_movement_info["time"], flight_movement_time)
                except:
                    date = flight["flight"]["time"]["scheduled"][arrival_or_departure + "_date"]
                    time = flight["flight"]["time"]["scheduled"][arrival_or_departure + "_time"]
                    flight_movement_time = pd.to_datetime(date + time, format='%Y%m%d%H%M')
                    flight_movement_info["time"] = np.append(flight_movement_info["time"], flight_movement_time)
            for z in ["origin", "destination"]:
                try:
                    flight_place = flight["flight"]["airport"][z]["code"]["iata"]
                    flight_movement_info[z] = np.append(flight_movement_info[z], flight_place)
                except:
                    flight_movement_info[z] = np.append(flight_movement_info[z], "")
            try:
                flight_movement_info["aircraftmodel"] = np.append(flight_movement_info["aircraftmodel"],
                                                                  flight["flight"]["aircraft"]["model"]["text"])
                flight_movement_info["callsign"] = np.append(flight_movement_info["callsign"],
                                                             flight["flight"]["identification"]["callsign"])
                flight_movement_info["status"] = np.append(flight_movement_info["status"],
                                                             flight["flight"]["status"]["text"])

            except:
                flight_movement_info["aircraftmodel"] = np.append(flight_movement_info["aircraftmodel"], "")
                flight_movement_info["callsign"] = np.append(flight_movement_info["callsign"], "")

        flight_movement_info = pd.DataFrame(flight_movement_info)

        flight_movement_info = xr.DataArray(
            flight_movement_info.loc[:,["origin","destination","aircraftmodel","callsign","status"]].values,
            coords={"time": flight_movement_info.time,
                    "flightdata": flight_movement_info.loc[:,["origin","destination","aircraftmodel","callsign","status"]].columns.values},
            dims=["time", "flightdata"])

        print("Extracted relevant information out of flight data response")

        return flight_movement_info
    def get_flightdata(self):
        f = FlightData()
        arrivals_alldata = f.get_airport_arrivals('INN',earlier_data = True)
        departures_alldata = f.get_airport_departures('INN',earlier_data = True)

        arrivals = self.extract_relevant_data(arrivals_alldata, "arrival")
        departures = self.extract_relevant_data(departures_alldata, "departure")
        arrivals = arrivals.sortby(arrivals.time)
        departures = departures.sortby(departures.time)

        flightdata = {"arrivals" : arrivals, "departures": departures}
        return flightdata



class Weatherdata(Measurement):
    def __init__(self):
        # now with default values
        super().__init__()
        # Set the absolute path to chromedriver
        self.service = Service(r"C:\Users\peaq\AppData\Local\Google\Chrome\chromedriver14_win32\chromedriver.exe")
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
        columns = columns1 + columns2
        #to xarray
        weatherdata = xr.DataArray(
            data_array,
            coords={"time": timestamps,
                    "weatherdata": columns},
            dims=["time", "weatherdata"])

        return weatherdata


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
        self.save_location = str(QFileDialog.getExistingDirectory(self, "Wo speicher ich die Daten hin?"))
        # self.save_location = r"C:/Users/ag_hansel/Documents/Ursulinen_data"
        self.date_save_location = os.path.join(self.save_location, datetime.date.today().strftime("%Y_%m_%d"))
        if not(os.path.exists(self.date_save_location)):
            os.mkdir(self.date_save_location)
        print(f"Saving data at {self.save_location}")

        self.comportpartector = self.dialogue_select_comport()
        self.part = Partector(self.comportpartector)
        self.mic = Microphone()
        self.flight = Flightdata()
        self.weather = Weatherdata()

        #get cutout seconds which are plotted back
        self.secondsback = 60
        self.amp_threshold = 80
        self.plottiming = {"begin":0,"end":0}

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
        self.timer_onesec .setInterval(self.time_onesec)
        self.timer_onesec .timeout.connect(self.timer_onesec_funct_to_worker)
        print("starting timer")
        self.timer_onesec .start()

        self.time_fivesec = 5000
        self.timer_fivesec = QtCore.QTimer()
        self.timer_fivesec.setInterval(self.time_fivesec)
        self.timer_fivesec.timeout.connect(self.timer_fivesec_funct_to_worker )
        self.timer_fivesec.start()


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
        print(f"thread {self.threadpool.activeThreadCount()} -> download line {self.part.number_downloads_onefile} for " + measurement.data.attrs["Measurement"])
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
        if self.part.number_downloads_onefile % self.save_file_update_ndatapoints == 0:
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

        # this happens at the end of the file
        if self.part.number_downloads_onefile % self.part.save_newfile_ndatapoints == 0:
            #update flight data and save it
            self.flight.data = self.flight.get_flightdata()
            self.weather.data = self.weather.get_data()

            time.sleep(10)
            self.flight.data["arrivals"].to_netcdf(self.save_file_current_path, group="Flight_arrivals", engine="netcdf4", mode="a")
            self.flight.data["departures"].to_netcdf(self.save_file_current_path, group="Flight_departures", engine="netcdf4",mode="a")
            print("..saved flight data")

            self.weather.data.to_netcdf(self.save_file_current_path, group="Weather", engine="netcdf4", mode="a")


            #make a new file
            self.save_file_current_inital_time = datetime.datetime.now()
            self.save_file_current_path = os.path.join(self.date_save_location,
                                                       self.save_file_current_inital_time.strftime("%Y_%m_%d_%Hh%Mm%Ss") + ".nc")
            print(f"open new file at {self.save_file_current_path}")
            self.part.number_downloads_onefile = 0
            self.mic.number_downloads_onefile = 0




    def update_plot(self,axis,measurement,datatoplot, color):
        try:
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
            for arrdep in ["arrivals","departures"]:
               times = self.flight.data[arrdep].time.sel(time = selectedtime).values

               if arrdep == "arrivals":
                   strings = ["Flug " + self.flight.data[arrdep].sel(flightdata = "callsign").sel(time = selectedtime).values[i] +" von "+
                              self.flight.data[arrdep].sel(flightdata = "origin").sel(time = selectedtime).values[i]
                                for i in range(0,self.flight.data[arrdep].sel(time = selectedtime).shape[0])]
               if arrdep == "departures":
                   strings = ["Flug"+ self.flight.data[arrdep].sel(flightdata = "callsign").sel(time = selectedtime).values[i] +" nach "+
                              self.flight.data[arrdep].sel(flightdata = "destination").sel(time = selectedtime).values[i]
                                     for i in range(0,self.flight.data[arrdep].sel(time = selectedtime).shape[0])]
               for time, string in zip(times, strings):
                    axis.axvline(x = time, color='r')
                    if datatoplot == "diameter":
                        axis.text(time, 1, string, rotation=90)
               print("Plot ", arrdep, "timestamps at", times)

            axis.legend([datatoplot])
            if datatoplot == "number_conc":
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
        except:
            print("...Could no plot ", datatoplot, " data")

    def timer_onesec_funct_to_worker(self):
        def dowloads_saves():
            self.part.number_downloads_onefile += 1
            self.mic.number_downloads_onefile += 1

            self.download_data(self.part, np.full(3, self.part.number_downloads_onefile)) #****
            # self.download_data(self.part, self.part.get_data(self.part.ser))
            self.download_data(self.mic, np.random.rand(1))  # *****
            # self.download_data(self.mic, self.mic.get_onesec_meanamplitude())
            self.save_datarow()

        worker = Worker(dowloads_saves)
        self.threadpool.start(worker)

    def timer_fivesec_funct_to_worker(self):


        def update_plot_all():
            self.plottiming["begin"] = datetime.datetime.now() - datetime.timedelta(seconds=self.secondsback)
            self.plottiming["end"] = datetime.datetime.now() + datetime.timedelta(seconds=self.secondsback/6)
            self.update_plot(self.canvas.ax3, self.part, "diameter", color='C0')
            self.update_plot(self.canvas.ax2, self.part, "number_conc", color='C1')
            self.update_plot(self.canvas.ax1,self.mic,"Amplitude",color='C3')

        worker = Worker(update_plot_all)
        self.threadpool.start(worker)
        print(f"thread {self.threadpool.activeThreadCount()} -> update plot")



def main():
    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()
    app.exec()


if __name__ == '__main__':
    main()
