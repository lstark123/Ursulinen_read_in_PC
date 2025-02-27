import datetime
import pytz
import matplotlib.pyplot as plt
import pandas as pd
from naneos.iotweb import download_from_iotweb
import os
import traceback
import schedule
import time

class Logging:
    def __init__(self):
        self.filepath = os.path.join("C:\\Users\\c7441354\\Documents\\Ursulinen\\Data_airport\\logging", "logging_partector" + datetime.datetime.now().strftime("%Y_%m_%d-%H-%M_%S") + ".txt")

    def save_logging(self, text):
        print(text)
        time =datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
        with open(self.filepath, "a") as f:
            f.write("\n" + time +" "+ text)
    def give_error(self, text = ""):
        time =datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
        stack_trace = traceback.format_exc()
        print(f"Error: {text}")
        print(stack_trace)
        with open(self.filepath, "a") as f:
            f.write("\n" + time + "Error -------------------------\n"+ text + "\n")
            f.write(stack_trace)



def download_day(date,serial_number) -> pd.DataFrame:
    TOKEN = "sC3nkb7BZGQVwPLMSXZouqswMoajcvF1ppYEJXRR8E6NOEXWZunfdIV1x0MILK19bQKpKXZJ3rXyrnkIrvKDaw=="

    timezone = datetime.timezone(datetime.timedelta(hours=1))
    first_hour_today = datetime.datetime.combine(date, datetime.datetime.min.time(), timezone)
    last_hour_today = datetime.datetime.combine(date, datetime.datetime.max.time(), timezone)

    name = "leanderstark"

    df = download_from_iotweb(name, serial_number, first_hour_today, last_hour_today, TOKEN)
    return df



def main():
    serial_number = "8300"
    logging = Logging()
    partector_savepath = "C:\\Users\\c7441354\\Documents\\Ursulinen\\Data_airport\\partector"
    logging.save_logging(f"Start loading in partector data of the day at {datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')}")

    def load_part_data_of_day():
        dateyesterday = datetime.date.today() - datetime.timedelta(days=1)
        try:
            logging.save_logging(f"Load data of day: {dateyesterday}")
            df = download_day(dateyesterday,serial_number=serial_number)
            df.index = df.index.tz_convert('Europe/Paris')

            thisfile_savepath = os.path.join(partector_savepath,
                                            dateyesterday.strftime("%Y_%m_%d")+ "_partector_"+ serial_number+ ".csv")
            logging.save_logging(f"Save data of day {dateyesterday} to {thisfile_savepath}")
            df.to_csv(thisfile_savepath)
        except:
            logging.give_error("")
        # try:
        #     logging.save_logging(f"Load data of day: {dateyesterday}")
        #     df = download_day(dateyesterday,serial_number)
        #     df.index = df.index.tz_convert('Europe/Paris')
        #
        #     thisfile_savepath = os.path.join(partector_savepath,
        #                                      dateyesterday.strftime("%Y_%m_%d") + "_partector.csv")
        #     logging.save_logging(f"Save data of day {dateyesterday} to {thisfile_savepath}")
        #     df.to_csv(thisfile_savepath)
        # except:
        #     logging.give_error("")

    # Define the specific time (e.g., 10:30 AM)
    specific_time = "01:00"
    # specific_time = "14:07"
    print("Start the partector scraping script")
    logging.save_logging(f"Getting the partector data every day at {specific_time}")
    # Schedule the task at the specific time
    schedule.every().day.at(specific_time).do(load_part_data_of_day)

    while True:
        schedule.run_pending()
        time.sleep(30)




if __name__ == "__main__":
    main()