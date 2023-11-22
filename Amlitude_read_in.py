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
    def __init__(self, Filepath):
        self.filepath = Filepath

    def save_logging(self, text):
        time =datetime.datetime.now().strftime("%Y-%M-%D_%H:%M:%S")
        with open(self.filepath, "a") as f:
            f.write("\n" + time + text)

class Error(Logging):
    def __init__(self, Filepath):
        self.filepath = Filepath
        super().__init__(self.filepath)

    def give_error(self, text):
        self.save_logging(f"Error -------------------------\n {text}")
        self.nr_sms += 1
        
class Measurement:
    def __init__(self):
        self.initial_time = datetime.datetime.now()
        self.time = np.array(self.initial_time)
        self.save_newfile_ndatapoints = 60*60
        print(f"Saving every second in {self.save_newfile_ndatapoints} seconds files")
        self.total_n_updates = 0
        
class Microphone(Measurement):
    def __init__(self, Parent):
        # now with default values
        super().__init__()
        self.parent = Parent
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
            self.parent.errors.give_error(" Error streaming mic " + str(error))


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
            except Exception as error:
                print("Something went wrong in gathering Microphone Amplitude")
                self.parent.errors.give_error(" Error gathering Microphone Amplitude " + str(error))
                return np.nan
        else:
            print("default device is not external microphone")

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
        self.save_location = r"C:\Users\c7441354\Documents\Ursulinen\roof_data"
        #self.save_location = "F:\\Uniarbeit\\data\\test"
        self.date_save_location = os.path.join(self.save_location, datetime.date.today().strftime("%Y_%m_%d"))
        if not(os.path.exists(self.date_save_location)):
            os.mkdir(self.date_save_location)
        print(f"Saving data at {self.save_location}")
        loggingfile_location = os.path.join(self.date_save_location,"logging"+datetime.datetime.now().strftime("%Y_%m_%d-%H-%M") + ".txt")
        self.logging = Logging(loggingfile_location)
        self.errors = Error(loggingfile_location)
        

        self.mic = Microphone(self)

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
                                                   self.save_file_current_inital_time.strftime("%Y_%m_%d_%Hh%Mm%Ss_mic") + ".nc")
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
        # #
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

    def timer_onesec_funct_to_worker(self):
        if self.timer_counting == True:
            def timer_one_sec():
                try:
                    self.mic.number_downloads_onefile += 1
                    print(self.mic.number_downloads_onefile,"download dataline")
                    #self.download_data(self.part, np.full(19, self.mic.number_downloads_onefile))  # ****
                    # self.download_data(self.part, self.part.get_data(self.part.ser))
                    #self.download_data(self.mic, np.random.rand(1))  # *****
                    self.download_data(self.mic, self.mic.get_onesec_meanamplitude())


                    #if self.mic.number_downloads_onefile % (60) == 0:  # every update datapoints save (it is normally 60*60 downloads)
                    if self.mic.number_downloads_onefile % self.mic.save_newfile_ndatapoints == 0:
                        print(self.mic.number_downloads_onefile, "Save file")
                        print("Stopping Timer")
                        self.timer_counting = False
                        self.save_file()
                        self.timer_counting = True
                        print("Restarting Timer")
                        self.logging.save_logging(" New file")

                    if self.mic.number_downloads_onefile % 15 == 0:  # every update datapoints save (it is normally 15)
                        print(self.mic.number_downloads_onefile, "Save the datarows")
                        self.save_datarow()
                        #self.logging.save_logging(" Save datarow")

                    if self.mic.number_downloads_onefile % 5 == 0:  # update plots every 5 downloads
                        print(self.mic.number_downloads_onefile, "Update Plot")
                        self.plottiming["begin"] = datetime.datetime.now() - datetime.timedelta(seconds=self.secondsback)
                        self.plottiming["end"] = datetime.datetime.now() + datetime.timedelta(seconds=self.secondsback / 6)
                    #     self.update_plot(self.canvas.ax3, self.part, "Diameter [nm]", color='C0')
                    #     self.update_plot(self.canvas.ax2, self.part, "Number [1/cm3]", color='C1')
                        self.update_plot(self.canvas.ax1,self.mic,"Amplitude",color='C3')
                except Exception as error:
                    print(error)
                    self.errors.give_error(" Error undefined in timer function "+ str(error))

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



    def download_data(self,measurement,newline):
        #first download new line

        newline = newline
        newtime = datetime.datetime.now()
        # print(f"thread {self.threadpool.activeThreadCount()} at computertime {datetime.datetime.now()} -> downloaded complete line {self.mic.number_downloads_onefile} with time {newtime} for " + measurement.data.attrs["Measurement"])

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
        print(self.mic.data.where(self.mic.data['time.year'] > 2000, drop=True))
        #save the new data every save_file_update_ndatapoints seconds
        print(f"thread {self.threadpool.activeThreadCount()} -> save line {self.mic.number_downloads_onefile - self.save_file_update_ndatapoints} to {self.mic.number_downloads_onefile} at {self.save_file_current_path} ...")

        self.mic.data.where(self.mic.data['time.year'] > 2000, drop=True).to_netcdf(self.save_file_current_path, group=self.mic.data.attrs["Measurement"], engine="netcdf4", mode="w")
        print("...save Microphone")




    def save_file(self):
        self.mic.data.where(self.mic.data['time.year'] > 2000, drop=True).to_netcdf(self.save_file_current_path, group=self.mic.data.attrs["Measurement"], engine="netcdf4", mode="w")
        print("...save Microphone")

        if os.path.basename(self.date_save_location) != datetime.date.today().strftime("%Y_%m_%d"):
            # if we have a new day make a new file
            self.date_save_location = os.path.join(self.save_location, datetime.date.today().strftime("%Y_%m_%d"))
            if not (os.path.exists(self.date_save_location)):
                os.mkdir(self.date_save_location)
            # we have to update the save_file_current_path since the directory changed
            self.save_file_current_path = os.path.join(self.date_save_location,
                                                       self.save_file_current_inital_time.strftime(
                                                           "%Y_%m_%d_%Hh%Mm%Ss") + ".nc")
            self.logging.filepath =  os.path.join(self.date_save_location, "_logging"+datetime.datetime.now().strftime("%Y_%m_%d-%H-%M") + ".txt")
            self.errors.filepath = os.path.join(self.date_save_location, "_logging"+datetime.datetime.now().strftime("%Y_%m_%d-%H-%M") + ".txt")

        #make a new file
        self.save_file_current_inital_time = datetime.datetime.now()
        self.save_file_current_path = os.path.join(self.date_save_location,
                                                   self.save_file_current_inital_time.strftime("%Y_%m_%d_%Hh%Mm%Ss") + ".nc")
        print(f"open new file at {self.save_file_current_path}")
        self.mic.number_downloads_onefile = 0




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
        axis.plot(exclude_default_data.time, exclude_default_data.sel(measured_variable=datatoplot), color=color)
        #
        #
        # #plotting with averages for longer time periods
        # elif self.secondsback > 5 * 60:
        #     #manipulate data, so that we dont show default data (time = year 2000) and are strictly monotonic
        #     exclude_default_data = measurement.data.where(measurement.data['time.year'] > 2000, drop=True)
        #     avgs = exclude_default_data.sortby(exclude_default_data.time).resample(time='15s').mean()
        #     axis.plot(avgs.time, avgs.sel(measured_variable=datatoplot), color=color)

        # make the flight time y axis
        # selectedtime = slice(datetime.datetime.now()-datetime.timedelta(hours =1),datetime.datetime.now())
        # for arrdep in ["arrival","departure"]:
        #     arrdep_data = self.flight.data.where(self.flight.data.loc[:,'arrival_departure'] == arrdep).dropna(dim="time", how="any").sel(time = selectedtime)
        #     times = [datetime.datetime.fromtimestamp(float(x)-2*60*60) for x in arrdep_data.sel(flightdata = "time_best_UNIX").sel(time = selectedtime)]
        #     if arrdep == "arrival":
        #         strings = ["Flug " + str(arrdep_data.sel(flightdata = "default_identification").sel(time = selectedtime).values[i]) +" von "+
        #                       str(arrdep_data.sel(flightdata = "origin").sel(time = selectedtime).values[i])
        #                     for i in range(0,arrdep_data.sel(time = selectedtime).shape[0])]
        #         for time, string in zip(times, strings):
        #             axis.axvline(x = time, color='tab:red')
        #             if datatoplot == "diameter":
        #                 axis.text(time, 1, string, rotation=90)
        #     if arrdep == "departure":
        #         strings = ["Flug "+ str(arrdep_data.sel(flightdata = "default_identification").sel(time = selectedtime).values[i]) +" nach "+
        #                   str(arrdep_data.sel(flightdata = "destination").sel(time = selectedtime).values[i])
        #                          for i in range(0,arrdep_data.sel(time = selectedtime).shape[0])]
        #     for time, string in zip(times, strings):
        #         axis.axvline(x = time, color='tab:purple')
        #         if datatoplot == "Diameter [nm]":
        #             axis.text(time, 1, string, rotation=90)
        #             print("Plot ", arrdep, "timestamp at", time, "with", string)

        if datatoplot == "Number [1/cm3]":
            axis.set_ylabel(r"[$ Teilchen/cm^3$]")
            axis.legend(["Anzahldichte Aerosolpartikel"])

        elif datatoplot == "Amplitude":
            axis.set_ylabel(r"[$dB$]")
            axis.axhline(y=self.amp_threshold)
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


if __name__ == '__main__':
    main()
