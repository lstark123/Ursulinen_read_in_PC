from PyQt5.QtWidgets import QApplication,  QLineEdit, QCheckBox, QHBoxLayout, QLabel ,QWidget, QMainWindow, QPushButton,QFileDialog, QVBoxLayout, QInputDialog,QComboBox
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
# import serial
import datetime
import numpy as np
from bs4 import BeautifulSoup as BS
# from selenium import webdriver
# from selenium.webdriver.chrome.service import Service
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
import traceback
class Logging:
    def __init__(self):
        self.filepath = os.path.join("C:\\Users\\c7441354\\Documents\\Ursulinen\\Data_airport\\logging", "logging_microphone_"+datetime.datetime.now().strftime("%Y_%m_%d-%H-%M") + ".txt")
        print("Logging to ", self.filepath)
        with open(self.filepath, "a") as f:
            f.write(f"-----Logging----- starting from: {datetime.datetime.now()}" )
    def save_logging(self, text):
        print(text)
        time =datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
        with open(self.filepath, "a") as f:
            f.write("\n" + time + text)
    def give_error(self, text):
        print(f"Error: {text}")
        time =datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
        stack_trace = traceback.format_exc()
        with open(self.filepath, "a") as f:
            f.write("\n" + time + "Error -------------------------\n"+ text + "\n")
            f.write(stack_trace)



class Microphone():
    def __init__(self, File_ndatatpoints,Save_location):
        # now with default values
        self.file_ndatapoints = File_ndatatpoints

        # self.file_ndatapoints = 5
        self.save_location = Save_location
        self.thisfile_initialtime = datetime.datetime.now()
        self.thisfile_location = os.path.join(self.save_location, self.thisfile_initialtime.strftime("%Y_%m_%d_%Hh%Mm%Ss") + ".csv")
        print(f"Saving every second in {self.file_ndatapoints} seconds files at {self.thisfile_location}")


        try:
            self.stream = sd.InputStream(
                samplerate=44100,
                channels=2,
                blocksize=44100)
        except Exception as error:
            self.stream = sd.InputStream(
                samplerate=44100,
                channels=1,
                blocksize=44100)
            # self.parent.logging.give_error(" Error streaming mic " + str(error))
        self.column_names = ['Time_UNIX', 'Amplitude']
        self.data = pd.DataFrame(columns=self.column_names)
        self.stream.start()
        self.nr_downloads = 0

        print("I opened Microphone")
    def restart_stream(self,logging):
        logging.save_logging("Restart Stream Microphone")
        self.stream.stop()
        self.stream = sd.InputStream(
            samplerate=44100,
            channels=2,
            blocksize=44100)
        self.stream.start()

    def get_onesec_meanamplitude(self, logging):
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
                try:
                    logging.give_error("Error with getting one sec amplitude, try to reopen stream")
                    self.restart_stream(logging)
                except:
                    logging.give_error("Error with getting one sec amplitude, try to reopen stream")


        else:
            print("default device is not external microphone")

    def download_data(self,logging):
        # first download new line
        new_mean_ampl= self.get_onesec_meanamplitude(logging)
        newtime = datetime.datetime.now()
        newtime_UNIX = newtime.timestamp()

        new_df = pd.DataFrame([[newtime_UNIX,new_mean_ampl]],columns=self.column_names)
        self.data = pd.concat([self.data, new_df], ignore_index=True)

        if len(self.data) > self.file_ndatapoints:
            self.data = self.data.tail(self.file_ndatapoints)
        self.nr_downloads += 1



    def save_datarow(self):
        #save the new data every save_file_update_ndatapoints seconds
        self.data[self.data.Time_UNIX > self.thisfile_initialtime.timestamp()].to_csv(self.thisfile_location, index=True)


    def save_file(self):
        self.data[self.data.Time_UNIX > self.thisfile_initialtime.timestamp()].to_csv(self.thisfile_location, index=True)
        #make a new file
        self.thisfile_initialtime = datetime.datetime.now()
        self.thisfile_location = os.path.join(self.save_location,
                                                   self.thisfile_initialtime.strftime("%Y_%m_%d_%Hh%Mm%Ss") + ".csv")
        print(f"open new file at {self.thisfile_location}")

        # problem with double saving!!!

class Flightdata():
    """
    The data is stored in self.data as an xarray with coordinates time, flightdata
    The time dimesion is scheduled time
    Flightdata is all *str: [time_estimated_UNIX, time_real_UNIX", "time_scheduled_UNIX", "status", "origin", "destination", "aircraftmodel",
                            "aircraftmodel_code", "callsign", "airline", "arrival_departure"]
    And is "" if no data is given
    """
    def __init__(self):
        self.data = []
        self.get_flightdata()

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

        return flight_movement_info
    def get_flightdata(self):
        print("Try to get Flight data")
        f = FlightData()
        arrivals_alldata = f.get_airport_arrivals('INN',earlier_data = True)
        departures_alldata = f.get_airport_departures('INN',earlier_data = True)

        arrivals = self.extract_relevant_data(arrivals_alldata, "arrival")
        departures = self.extract_relevant_data(departures_alldata, "departure")
        flight_movements = pd.concat([arrivals,departures])
        flight_movements = flight_movements.sort_index()
        self.data = flight_movements
        return flight_movements

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

    def __init__(self, fn, *args, parent = 0):
        super(Worker, self).__init__()

        # Store constructor arguments (re-used for processing)
        self.parent = parent
        self.fn = fn
        self.args = args
        #self.kwargs = kwargs
        self.signals = WorkerSignals()


    @pyqtSlot()
    def run(self):
        '''
        Initialise the runner function with passed args, kwargs.
        '''

        # Retrieve args/kwargs here; and fire processing using them
        try:
            result = self.fn(*self.args)#, **self.kwargs)
        except Exception as error:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc()))
            with open(self.parent.loggingfile_location, "a") as f:
                f.write("\n" + datetime.datetime.now().strftime("%H:%M:%S") + " Error " + str(error))
        else:
            self.signals.result.emit(result)  # Return the result of the processing
        finally:
            self.signals.finished.emit()  # Done
            
            

class MplCanvas(FigureCanvas):

    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        gs = self.fig.add_gridspec(1, 1)
        self.ax1 = self.fig.add_subplot(gs[0,0])
        super(MplCanvas, self).__init__(self.fig)

class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Amplitude read in")
        #self.save_location = str(QFileDialog.getExistingDirectory(self, "Wo speicher ich die Daten hin?"))
        self.save_location = "C:\\Users\\c7441354\\Documents\\Ursulinen\\Data_airport\\microphone"
        #self.save_location = "F:\\Uniarbeit\\data\\test"
        print(f"Saving data at {self.save_location}")
        self.logging = Logging()

        self.number_downloads_current_file = 0
        self.file_ndatapoints = 60*60
        self.mic = Microphone(self.file_ndatapoints,self.save_location)
        self.flight = Flightdata()

        #get cutout seconds which are plotted back
        self.secondsback = 60
        self.amp_threshold = 80
        self.plottiming = {"begin":0,"end":0}
        self.timer_counting = True
        self.plotflights = True

        # update save file every n datapoints
        self.save_file_update_ndatapoints = 15

        # path of current file to save to first is a little to early here, but no problem
        self.save_file_current_inital_time = datetime.datetime.now()
        self.save_file_current_path = os.path.join(self.save_location,
                                                   self.save_file_current_inital_time.strftime("%Y_%m_%d_%Hh%Mm%Ss_mic") + ".csv")
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
        # 
        # 
        self.timewindow_combobox = QComboBox()
        self.timewindow_combobox.addItems(["1 min", "5 min","30min", "1 h"])
        mainlayout.addWidget(self.timewindow_combobox)
        self.timewindow_combobox.currentIndexChanged.connect(self.timewindow_combobox_changed)
        # 
        self.checkbox = QCheckBox('Show flights')
        self.checkbox.setChecked(True)
        mainlayout.addWidget(self.checkbox)
        self.checkbox.stateChanged.connect(self.checkbox_state_changed)
        # threshold_selctor = QLineEdit()
        # threshold_selctor.setValidator(QDoubleValidator(0.99, 99.99, 4))
        # threshold_selctor.textChanged.connect(self.threshold_changed)
        # 
        # self.horizontalLayout = QHBoxLayout()
        # self.label = QLabel("select threshold")
        # self.horizontalLayout.addWidget(self.label)
        # self.horizontalLayout.addWidget(threshold_selctor)
        # mainlayout.addLayout(self.horizontalLayout)
        # 
        # self.exitbutton = QPushButton("Exit")
        # mainlayout.addWidget(self.exitbutton)
        # self.exitbutton.clicked.connect(self.the_button_was_clicked)

        widget = QWidget()
        widget.setLayout(mainlayout)
        self.setCentralWidget(widget)

    def checkbox_state_changed(self, state):
        # state == 2 when checked, state == 0 when unchecked
        if state == 2:
            print('Checkbox checked')
            self.plotflights = True
        elif state == 0:
            print('Checkbox unchecked')
            self.plotflights = False

    def timer_onesec_funct_to_worker(self):
        if self.timer_counting == True:
            def timer_one_sec():
                try:
                    self.number_downloads_current_file += 1
                    print(self.number_downloads_current_file,"download dataline")
                    self.mic.download_data(self.logging)
                except Exception as error:
                    print(error)
                    self.logging.give_error(" Error in downloading data " + str(error))


                if self.number_downloads_current_file % self.file_ndatapoints == 0:
                    try:
                        print(self.number_downloads_current_file, "Save file")
                        print("Stopping Timer")
                        self.timer_counting = False
                        self.mic.save_file()
                        self.flight.get_flightdata()
                        self.number_downloads_current_file = 0
                        self.mic.restart_stream()
                        self.timer_counting = True
                        print("Restarting Timer")
                        self.logging.save_logging(" New file")
                    except Exception as error:
                        print(error)
                        self.logging.give_error("Error saving file "  + str(error))

                if self.number_downloads_current_file % 60*10 == 0:
                    try:
                        print(f"Get new flight data")
                        self.flight.get_flightdata()
                    except Exception as error:
                        print(error)
                        self.logging.give_error("Error getting new flight data" + str(error))

                if self.number_downloads_current_file % 15 == 0:
                    try:
                        print(
                            f"thread {self.threadpool.activeThreadCount()} -> save line {self.number_downloads_current_file - self.save_file_update_ndatapoints} to {self.number_downloads_current_file} at {self.save_file_current_path} ...")
                        self.mic.save_datarow()
                    except Exception as error:
                        print(error)
                        self.logging.give_error("Error saving 15 datarows " + str(error))

                if self.number_downloads_current_file % 5 == 0:  # update plots every 5 downloads
                    try:
                        print(self.number_downloads_current_file, "Update Plot")
                        self.plottiming["begin"] = datetime.datetime.now() - datetime.timedelta(seconds=self.secondsback)
                        self.plottiming["end"] = datetime.datetime.now() + datetime.timedelta(seconds=self.secondsback / 6)
                        self.update_plot(self.canvas.ax1,self.mic,"Amplitude",color='C3')
                    except Exception as error:
                        self.logging.give_error("Error updating plot " + str(error))


            worker = Worker(timer_one_sec, parent=self)
            self.threadpool.start(worker)


    def dialogue_select_comport(self):
        comport, ok = QInputDialog.getInt(self, 'input dialog', 'Auf welchen Comport ist der Partector')
        if ok:
            print("Search for Partector on COM port ", comport)
            return comport

    def threshold_changed(self,text):
        def to_worker():
            self.amp_threshold = float(text.replace(",","."))
            print(f"New Amplitude threshold: {self.amp_threshold}")

        worker = Worker(to_worker, parent= self)
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





    def update_plot(self,axis,measurement,datatoplot, color):
        #try:
        #initialize change with new boundaries
        axis.cla()
        axis.set_xlim(self.plottiming["begin"], self.plottiming["end"])
        axis.set_ylim([0, max(measurement.data.Amplitude) * 1.1])
        axis.grid()
        axis.set_xlabel("local time")
        # short time plotting
        # print( pd.to_datetime(measurement.data.Time_UNIX), measurement.data.Amplitude)
        axis.plot(pd.to_datetime(measurement.data.Time_UNIX + 60*60, unit = "s"), measurement.data.Amplitude, color="C1")
        if self.plotflights:
            start_datetime = pd.Timestamp(self.plottiming["begin"])
            end_datetime = pd.Timestamp(self.plottiming["end"])
            selected_flight_data = self.flight.data[start_datetime:end_datetime]
            for arrdep in ["arrival","departure"]:
                arrdep_data = selected_flight_data[selected_flight_data.arrival_departure == arrdep]
                for time_index, row in arrdep_data.iterrows():
                    best_time = pd.to_datetime(row.time_best_UNIX, unit='s', utc=True)
                    if arrdep == "arrival":
                        string = f"{best_time.strftime('%H:%M')} Flug {row.default_identification} von {row.origin}, Status: {row.status}"
                        axis.axvline(x=best_time, color='tab:green')
                    if arrdep == "departure":
                        string = f"{best_time.strftime('%H:%M')} Flug {row.default_identification} nach {row.destination}, Status: {row.status}"
                        axis.axvline(x=best_time, color='tab:pink')
                    axis.text(best_time, 1, string, rotation=90)


        axis.set_ylabel(r"[$dB$]")
        axis.axhline(y=self.amp_threshold)
        axis.legend(["Lautstärke vom Dach"])

        self.canvas.draw()

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    app.exec()


if __name__ == '__main__':
    main()
