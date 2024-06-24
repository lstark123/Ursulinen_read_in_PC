import sys
import os
import datetime as dt
import numpy as np
import time
import sounddevice as sd
import traceback
import pandas as pd
from pyflightdata import FlightData
import pytz
import traceback
import logging

fp_logging = r"C:\Users\c7441354\Documents\Ursulinen\Data_airport\logging"
time_now = dt.datetime.now()
filename = f"logging_microphone_{time_now.strftime('%Y-%m-%d_%H_%M_%S')}.log"
loggingfp = os.path.join(fp_logging,filename)
logging.basicConfig(
    filename=loggingfp,
    encoding='utf-8',
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
print(f"Logging in {loggingfp}")


class Microphone():
    def __init__(self, File_ndatatpoints,Save_directory):
        # now with default values
        self.file_ndatapoints = File_ndatatpoints

        # self.file_ndatapoints = 5
        self.save_directory = Save_directory
        self.thisfile_initialtime = dt.datetime.now()
        self.thisfile_location = os.path.join(self.save_directory, self.thisfile_initialtime.strftime("%Y_%m_%d_%Hh%Mm%Ss") + ".csv")
        logger.info(f"Saving every second in {self.file_ndatapoints} seconds files at {self.thisfile_location}")


        try:
            self.stream = sd.InputStream(
                samplerate=44100,
                channels=2,
                blocksize=44100)
            logger.info("Try opening stream")
        except Exception as error:
            self.stream = sd.InputStream(
                samplerate=44100,
                channels=1,
                blocksize=44100)
            logger.error(f"An error occurred: {str(e)}")
            logger.error(traceback.format_exc())
            # self.parent.logging.give_error(" Error streaming mic " + str(error))
        self.column_names = ['Time_UNIX', 'Amplitude']
        self.data = pd.DataFrame(columns=self.column_names)
        self.stream.start()

        logger.info("I opened Microphone")
    def restart_stream(self):
        logger.info("Restart Stream Microphone")
        self.stream.stop()
        self.stream = sd.InputStream(
            samplerate=44100,
            channels=2,
            blocksize=44100)
        self.stream.start()

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
                try:
                    logger.error("Error with getting one sec amplitude, try to reopen stream")
                    logger.error(traceback.format_exc())
                    self.restart_stream()
                except:
                    logger.error("Error with getting one sec amplitude, try to reopen stream")
                    logger.error(traceback.format_exc())


        else:
            logger.error("default device is not external microphone")
            logger.error(traceback.format_exc())

    def download_data(self):
        # first download new line
        new_mean_ampl= self.get_onesec_meanamplitude()
        newtime = dt.datetime.now()
        newtime_UNIX = newtime.timestamp()

        new_df = pd.DataFrame([[newtime_UNIX,new_mean_ampl]],columns=self.column_names)
        self.data = pd.concat([self.data, new_df], ignore_index=True)

        if len(self.data) > self.file_ndatapoints:
            self.data = self.data.tail(self.file_ndatapoints)

    def save_new_datarows(self):
        #save the new data every save_file_update_ndatapoints seconds
        self.data[self.data.Time_UNIX > self.thisfile_initialtime.timestamp()].to_csv(self.thisfile_location, index=True)
        logger.info(f"Saved new datarows to {self.thisfile_location}")


    def save_file(self):
        self.data[self.data.Time_UNIX > self.thisfile_initialtime.timestamp()].to_csv(self.thisfile_location, index=True)
        #make a new file
        self.thisfile_initialtime = dt.datetime.now()
        self.thisfile_location = os.path.join(self.save_directory,
                                                   self.thisfile_initialtime.strftime("%Y_%m_%d_%Hh%Mm%Ss") + ".csv")
        logger.info(f"open new file at {self.thisfile_location}")

        # problem with double saving!!!

def main():
    save_location = "C:\\Users\\c7441354\\Documents\\Ursulinen\\Data_airport\\microphone"
    logger.info(f"Saving data at {save_location}")

    timer_interval_s = 1
    number_downloads_current_file = 0
    file_ndatapoints = 60*60
    save_file_update_ndatapoints = 15
    mic = Microphone(file_ndatapoints, save_location)
    logger.info("Initiate Microphone")

    timer_counting = True
    while True:
        number_downloads_current_file += 1
        try:
            if timer_counting == True:

                # download a new dataline every cycle
                try:
                    print(number_downloads_current_file, "download dataline")
                    mic.download_data()

                except Exception as error:
                    print(error)
                    logger.error(" Error in downloading data " + str(error))
                    logger.error(traceback.format_exc())

                # save the new datalines every save_file_update_ndatapoints cycle
                if number_downloads_current_file % save_file_update_ndatapoints == 0:
                    try:
                        timer_counting = False
                        print("Stopping Timer")
                        print(f"save all new lines at {mic.thisfile_location} ...")
                        mic.save_new_datarows()
                        print("Restart Timer")
                        timer_counting = True
                    except Exception as error:
                        print(error)
                        logger.error(" Error saving 15s datarows " + str(error))
                        logger.error(traceback.format_exc())

                # save to a new file every file_ndatapoints cycle restart stream and make number_dowmloads_current_file to 0
                if number_downloads_current_file % file_ndatapoints == 0:
                    try:
                        print(number_downloads_current_file, "Save file")
                        print("Stopping Timer")
                        timer_counting = False
                        mic.save_file()
                        mic.restart_stream()
                        number_downloads_current_file = 0
                        timer_counting = True
                        print(f"Make a new file at {mic.thisfile_location}")
                        print("Restarting Timer")
                        logger.info(f"New file at {mic.thisfile_location}")
                    except Exception as error:
                        print(error)
                        logger.error("Error saving file " + str(error))
                        logger.error(traceback.format_exc())
                time.sleep(timer_interval_s)


        except Exception as e:
            logging.error(f"An error occurred during the timer: {str(e)}")
            logging.error(traceback.format_exc())
            continue


if __name__ == '__main__':
    main()

