import time

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QApplication, QWidget, QMainWindow,QLabel, QLineEdit, QGridLayout, QPushButton, QVBoxLayout, QCheckBox,QComboBox
import matplotlib
matplotlib.use('Qt5Agg')
from PyQt5.QtCore import *
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import xarray as xr
import glob
import datetime
import numpy as np
import sys
from pathlib import Path
import os
import pandas as pd
from pyqt_checkbox_list_widget.checkBoxListWidget import CheckBoxListWidget
from cycler import cycler

#Workers for multithreading

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

    @pyqtSlot()
    def run(self):
        '''
        Initialise the runner function with passed args, kwargs.
        '''
        self.fn(*self.args, **self.kwargs)



class MplCanvas(FigureCanvas):

    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        gs = self.fig.add_gridspec(3, 1)
        self.ax1 = self.fig.add_subplot(gs[0,0])
        self.ax2 = self.fig.add_subplot(gs[1, 0])
        self.ax3 = self.fig.add_subplot(gs[2, 0])
        # self.ax1.tick_params('x', labelbottom=False)
        # self.ax2.tick_params('x', labelbottom=False)
        self.fig.subplots_adjust(bottom=0.05, right=0.95, top=0.95,wspace= 0.1, hspace= 0.1)
        super(MplCanvas, self).__init__(self.fig)


class Ui_MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        print("Initializing Window")
        self.threadpool = QThreadPool()
        self.threadpool.setMaxThreadCount(1)
        self.setGeometry(0, 0, 1000, 1000)
        #multithreading
        self.save_newfile_ndatapoints = 60*60 # 1 h files
        self.parentdir = r"E:\Uniarbeit\data_dach"
        self.filenames_old_loaded = np.array([False])
        self.filenames_new_loaded = np.array([False])
        self.averaging = 1
        self.plotinfo = {'plot1':{'selected_line': ["microphone"], "logy": False,"axis": 1},
                         'plot2': {'selected_line': [], "logy": False,"axis": 2},
                         'plot3': {'selected_line': [], "logy": False, "axis": 3}
                         }

        self.measured_variables = np.array(["LDSA","diameter","number_conc"])



        starttime = datetime.datetime.now() - datetime.timedelta(seconds=60 * 60 * 5)
        endtime = datetime.datetime.now() - datetime.timedelta(seconds=60 * 60 * 1)
        self.startend = {'starttime': starttime, 'endtime': endtime}
        self.data = self.load()
        self.setupUi()
        # self.replot()

    def logy_checkbox(self,whichplot):
        print("Logy of ", whichplot)
        self.plotinfo[whichplot]["logy"] = self.logy_selections[whichplot].isChecked()
        self.update_plot(whichplot)

    def change_time(self, time_selected, time_to_change):
        def to_worker():
            self.startend[time_to_change] = time_selected.dateTime().toPyDateTime()
            print(f"changed {time_to_change} to {self.startend[time_to_change]}")
            print()

        worker = Worker(to_worker)
        self.threadpool.start(worker)

    def load(self):
        def to_worker():
            print(f"thread {self.threadpool.activeThreadCount()} -> load data")
            self.data =self.load_data()
            print(f"thread {self.threadpool.activeThreadCount()} -> load data finished")
        worker = Worker(to_worker)
        self.threadpool.start(worker)

    def replot(self):
        def to_worker():
            print(f"thread {self.threadpool.activeThreadCount()} -> update plot")
            self.update_plot("plot1")
            print(f"thread {self.threadpool.activeThreadCount()} -> update plot finished")
        worker = Worker(to_worker)
        self.threadpool.start(worker)

    def load_replot(self):
        def to_worker():
            print(f"thread {self.threadpool.activeThreadCount()} -> load data and update plot")
            self.data = []
            self.data =self.load_data()
            self.update_plot("plot1")
            # time.sleep(0.5)
            self.update_plot("plot2")
            # time.sleep(0.5)
            self.update_plot("plot3")
            print(f"thread {self.threadpool.activeThreadCount()} -> load data and update plot finished")
        worker = Worker(to_worker)
        self.threadpool.start(worker)

    def selectmeasurement(self,whichplot):
        def to_worker():
            print(f"thread {self.threadpool.activeThreadCount()} -> select other line" )
            self.plotinfo[whichplot]["selected_line"] = self.measured_variables[self.selections[whichplot].getCheckedRows()]
            print("new selected measurments =", self.plotinfo[whichplot]["selected_line"])
            self.update_plot(whichplot)
            print(f"thread {self.threadpool.activeThreadCount()} -> select other line finished")
        worker = Worker(to_worker)
        self.threadpool.start(worker)


    def load_data(self):
        self.filenames_old_loaded = self.filenames_new_loaded
        file_length = datetime.timedelta(seconds=self.save_newfile_ndatapoints)
        filenames = np.array(glob.glob(self.parentdir + "\**\*.nc", recursive=True))
        files_datetimes = [Path(path).stem for path in filenames]
        files_datetimes = pd.to_datetime(files_datetimes, errors='coerce', format="%Y_%m_%d_%Hh%Mm%Ss")
        # preselect a range (afterwards more narrow selection)
        self.filenames_new_loaded = filenames[np.where(
            (self.startend["starttime"] < files_datetimes - file_length) & (files_datetimes < (self.startend["endtime"] + file_length)))]
        print("filenames old ", self.filenames_old_loaded)
        print("filenames new: ", self.filenames_new_loaded)
        functionreturn = {"microphone":[],
                          "partector" : []}
        print("funct load_data : Load files with filepaths", self.filenames_new_loaded)

        if self.filenames_new_loaded.size > 1:
            if not np.array_equal(self.filenames_old_loaded, self.filenames_new_loaded):
                if len(self.filenames_new_loaded) > 10:
                    print("Time range too big,only loading first 10 files")
                    self.filenames_new_loaded = self.filenames_new_loaded[0:10]

                with xr.open_mfdataset(self.filenames_new_loaded, group="Partector",
                                       combine="nested",
                                       preprocess=lambda ds: ds.isel(time=ds['time.year'] > 2000)) as ds:
                    functionreturn["partector"] = ds
                    print("Downloaded Partector data", ds)

                with xr.open_mfdataset(self.filenames_new_loaded, group="Microphone",
                                       combine="nested",
                                       preprocess=lambda ds: ds.isel(time=ds['time.year'] > 2000)) as ds:
                    functionreturn["microphone"] = ds
                    print("Downloaded Microphone data", ds)
                    return functionreturn
                #bei gewissen sachen laden: Process finished with exit code -1073740791 (0xC0000409)
                #    raise ValueError(ValueError: cannot reindex or align along dimension 'time' because the (pandas) index has duplicate values

            else:
                print("funct load_data: Data already loaded -> no new download")
        else:
            print("funct load_data: No data at this time")
            return -1

    def update_plot(self,whichplot):
        # initialize change with new boundaries
        print("update plot from " + self.startend["starttime"].strftime("%Y.%m.%d %H-%M-%S") + " to " +
              self.startend[
                  "endtime"].strftime("%Y.%m.%d %H-%M-%S"))
        axis = self.plotinfo[whichplot]["axis"]
        logyplot = self.plotinfo[whichplot]["logy"]
        # if np.array_equal(self.filenames_old_loaded, self.filenames_new_loaded):
        #     axis.set_xlim(self.startend["starttime"], self.startend["endtime"])
        # else:
        axis.cla()
        axis.set_xlim(self.startend["starttime"], self.startend["endtime"])
        axis.grid()
        axis.set_xlabel("local time")

        if whichplot == "plot1":
            measurement = "microphone"
            datatoplot = ["Amplitude"]
            custom_cycler = (cycler(color=['tab:blue']))
            axis.axhline(y=80,color = 'tab:red')
        else:
            measurement = "partector"
            datatoplot = self.plotinfo[whichplot]["selected_line"]
            color = [color for (i,color) in enumerate(['tab:orange', 'tab:green', 'tab:red']) if self.measured_variables[i] in datatoplot]
            print(color)
            custom_cycler = (cycler(color=color))

        axis.set_prop_cycle(custom_cycler)
        # short time plotting#
        if self.data != -1:
            print(f"Plotting with {self.averaging}s averaging")
            print("with data:", measurement, datatoplot)
            #problem wahrscheinlich wenn das xarray in anderem thread ist -> hab mich auf einen thread reduziert
            for line in datatoplot:
                print("plotted " + line)
                print("plotting values", self.data[measurement]["__xarray_dataarray_variable__"].time.values,
                      self.data[measurement]["__xarray_dataarray_variable__"].sel(measured_variable=line).values)

                if logyplot:
                    #change cyclecolor dependent of plot
                    axis.semilogy(self.data[measurement]["__xarray_dataarray_variable__"].time.values,
                                  self.data[measurement]["__xarray_dataarray_variable__"].sel(measured_variable=line).values)
                else:
                    axis.plot(self.data[measurement]["__xarray_dataarray_variable__"].time.values,
                              self.data[measurement]["__xarray_dataarray_variable__"].sel(measured_variable=line).values)
            axis.legend(datatoplot)
        else:
            print("Did not download data yet")
            # axis.legend([datatoplot])

        self.plots_widget.draw()


    ''' here we setup the window with:
        self.start/endtime_select = selection widget
        self.plots_widget = Widget with Plots inside
        self.selection_plot_1/2/3 = Selection widget 1-3
    '''



    def setupUi(self):
        self.setObjectName("MainWindow")
        self.centralwidget = QtWidgets.QWidget(self)
        self.centralwidget.setObjectName("centralwidget")
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(self.centralwidget)
        self.verticalLayout_2.setObjectName("verticalLayout_2")

        self.gridLayout = QtWidgets.QGridLayout()
        self.gridLayout.setObjectName("gridLayout")

        self.starttime_label = QtWidgets.QLabel(self.centralwidget)
        self.starttime_label.setObjectName("starttimestarttime")
        self.gridLayout.addWidget(self.starttime_label, 0, 0, 1, 1)
        self.endtime_label = QtWidgets.QLabel(self.centralwidget)
        self.endtime_label.setObjectName("endtime")
        self.gridLayout.addWidget(self.endtime_label, 0, 1, 1, 1)

        self.starttime_select = QtWidgets.QDateTimeEdit(self.centralwidget)
        self.starttime_select.setObjectName("starttime_select")
        self.starttime_select.setDateTime(QDateTime.currentDateTime().addSecs(-60*60))
        self.gridLayout.addWidget(self.starttime_select, 1, 0, 1, 1)
        self.starttime_select.dateTimeChanged.connect(lambda: self.change_time(self.starttime_select,"starttime"))
        self.endtime_select = QtWidgets.QDateTimeEdit(self.centralwidget)
        self.endtime_select.setDateTime(QDateTime.currentDateTime())
        self.endtime_select.setObjectName("endtime_select")
        self.gridLayout.addWidget(self.endtime_select, 1, 1, 1, 1)
        self.endtime_select.dateTimeChanged.connect(lambda: self.change_time(self.endtime_select,"endtime"))

        self.button_confirm_datetime_selection = QtWidgets.QPushButton("Plots updaten")
        self.button_confirm_datetime_selection.setObjectName("Plots updaten")
        self.gridLayout.addWidget(self.button_confirm_datetime_selection, 1, 2, 1, 1)
        self.button_confirm_datetime_selection.clicked.connect(self.load_replot)

        self.verticalLayout_2.addLayout(self.gridLayout)


        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")

        #here come the plots
        self.plots_widget = MplCanvas(self)
        self.plotinfo["plot1"]["axis"] = self.plots_widget.ax1
        self.plotinfo["plot2"]["axis"] = self.plots_widget.ax2
        self.plotinfo["plot3"]["axis"] = self.plots_widget.ax3
        self.plots_widget.setObjectName("plots_widget")
        self.horizontalLayout.addWidget(self.plots_widget)

        #here come the selction
        # self.datatoplot_checkBoxes = CheckBoxListWidget()
        # self.datatoplot_checkBoxes.addItems(self.part.datatoplot_checkboxnames)


        self.verticalLayout = QtWidgets.QVBoxLayout()
        self.verticalLayout.setObjectName("verticalLayout")

        self.logy_plot1 = QCheckBox("Plot logarithmisch")
        self.verticalLayout.addWidget(self.logy_plot1)
        self.logy_plot1.stateChanged.connect(lambda: self.logy_checkbox("plot1"))

        self.selection_plot_1 = CheckBoxListWidget()
        self.verticalLayout.addWidget(self.selection_plot_1)

        self.logy_plot2 = QCheckBox("Plot logarithmisch")
        self.verticalLayout.addWidget(self.logy_plot2)
        self.logy_plot2.stateChanged.connect(lambda: self.logy_checkbox("plot2"))

        self.selection_plot_2 = CheckBoxListWidget()
        self.selection_plot_2.setObjectName("selection_plot_2")
        self.selection_plot_2.addItems(self.measured_variables)
        self.selection_plot_2.checkedSignal.connect(lambda: self.selectmeasurement("plot2"))
        self.verticalLayout.addWidget(self.selection_plot_2)

        self.logy_plot3 = QCheckBox("Plot logarithmisch")
        self.verticalLayout.addWidget(self.logy_plot3)
        self.logy_plot3.stateChanged.connect(lambda: self.logy_checkbox("plot3"))

        self.selection_plot_3 = CheckBoxListWidget()
        self.selection_plot_3.addItems(self.measured_variables)
        self.selection_plot_3.checkedSignal.connect(lambda: self.selectmeasurement("plot3"))
        self.selection_plot_3.setObjectName("selection_plot_3")
        self.verticalLayout.addWidget(self.selection_plot_3)

        self.selections = {"plot1": self.selection_plot_1, "plot2":self.selection_plot_2, "plot3": self.selection_plot_3}
        self.logy_selections = {"plot1": self.logy_plot1, "plot2":self.logy_plot2, "plot3": self.logy_plot3}

        # adjustment of layout
        self.horizontalLayout.addLayout(self.verticalLayout)
        self.horizontalLayout.setStretch(0, 3)
        self.horizontalLayout.setStretch(1, 1)
        self.verticalLayout_2.addLayout(self.horizontalLayout)
        self.setCentralWidget(self.centralwidget)

        self.menubar = QtWidgets.QMenuBar(self)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 717, 18))
        self.menubar.setObjectName("menubar")
        self.menuLoad_Files = QtWidgets.QMenu(self.menubar)
        self.menuLoad_Files.setObjectName("menuLoad_Files")
        self.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(self)
        self.statusbar.setObjectName("statusbar")
        self.setStatusBar(self.statusbar)
        self.actionSelect_File = QtWidgets.QAction(self)
        self.actionSelect_File.setObjectName("actionSelect_File")
        self.menuLoad_Files.addAction(self.actionSelect_File)
        self.menubar.addAction(self.menuLoad_Files.menuAction())

        self.retranslateUi()
        QtCore.QMetaObject.connectSlotsByName(self)

    def retranslateUi(self):
        _translate = QtCore.QCoreApplication.translate
        self.setWindowTitle(_translate("MainWindow", "MainWindow"))
        self.starttime_label.setText(_translate("MainWindow", "Starttime"))
        self.endtime_label.setText(_translate("MainWindow", "Endtime"))
        # self.selection_plot_1.setText(_translate("MainWindow", "PushButton"))
        # self.selection_plot_2.setText(_translate("MainWindow", "PushButton"))
        # self.selection_plot_3.setText(_translate("MainWindow", "PushButton"))
        self.menuLoad_Files.setTitle(_translate("MainWindow", "Load Files"))
        self.actionSelect_File.setText(_translate("MainWindow", "Select File"))



if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    ui = Ui_MainWindow()
    ui.show()
    sys.exit(app.exec_())
