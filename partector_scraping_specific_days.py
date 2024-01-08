import datetime
import pytz
import matplotlib.pyplot as plt
import pandas as pd
from naneos.iotweb import download_from_iotweb
import os
import traceback

class Logging:
    def __init__(self):
        self.filepath = os.path.join("C:\\Users\\c7441354\\Documents\\Ursulinen\\Data_airport\\logging", "logging_partector" + datetime.datetime.now().strftime("%Y_%m_%d-%H-%M_%S") + ".txt")

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
            f.write("\n" + time + "Error -------------------------\n"+ text + "\n")
            f.write(stack_trace)



def download_day(date) -> pd.DataFrame:
    TOKEN = "sC3nkb7BZGQVwPLMSXZouqswMoajcvF1ppYEJXRR8E6NOEXWZunfdIV1x0MILK19bQKpKXZJ3rXyrnkIrvKDaw=="

    timezone = datetime.timezone(datetime.timedelta(hours=1))
    first_hour_today = datetime.datetime.combine(date, datetime.datetime.min.time(), timezone)
    last_hour_today = datetime.datetime.combine(date, datetime.datetime.max.time(), timezone)
    serial_number = "8278"
    name = "leanderstark"

    df = download_from_iotweb(name, serial_number, first_hour_today, last_hour_today, TOKEN)
    return df


def main():
    logging = Logging()
    partector_savepath = "C:\\Users\\c7441354\\Documents\\Ursulinen\\Data_airport\\partector"
    # start_date = datetime.date(2023,11,20)
    # end_date = datetime.date(2023,11,30)
    # if end_date:
    #     ddays = (end_date-start_date).days
    # else:
    #     ddays = 5
    # # Create a list of datetime.date objects for the last week
    # dates_to_load = [start_date + datetime.timedelta(days=x) for x in range(ddays)]
    dates_to_load = [datetime.date(2023,12,12)]
    for date_to_load in dates_to_load:
        try:
            logging.save_logging(f"Load data of day: {date_to_load}")
            df = download_day(date_to_load)
            df.index = df.index.tz_convert('Europe/Paris')

            thisfile_savepath = os.path.join(partector_savepath,
                                            date_to_load.strftime("%Y_%m_%d")+ "_partector.csv")
            logging.save_logging(f"Save data of day {date_to_load} to {thisfile_savepath}")
            df.to_csv(thisfile_savepath)
        except:
            logging.give_error("")

if __name__ == "__main__":
    main()