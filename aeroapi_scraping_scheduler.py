import os.path
import schedule
import time
from aeroapi_python import AeroAPI
from aeroapi_python.Flights import Flights
from aeroapi_python.Airports import Airports
import datetime
import pandas as pd
import traceback
from pyflightdata import FlightData
import numpy as np
import aeroapi_base as ab

def main():
    ab.logging.save_logging(f"Start loading in flights of the day at {datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')}")
    # Define the specific time (e.g., 10:30 AM)
    specific_time = "23:00"
    # load_flights_of_the_day()
    print("Start the flight scraping script")
    ab.logging.save_logging(f"Getting the flights every day at {specific_time}")
    # Schedule the task at the specific time
    schedule.every().day.at(specific_time).do(run_scheduled)

    while True:
        schedule.run_pending()
        time.sleep(30)

def run_scheduled():
    all_data_this_date = {}
    all_data_this_date["aeroapi"] = ab.get_flightdata_aeroapi_and_save(datetime.date.today())
    all_data_this_date["flightradar"] = ab.get_flightdata_flightradar24_and_save()
    all_data_this_date["tracks"] = ab.get_tracks_of_flights_and_save(all_data_this_date["aeroapi"])


if __name__ == "__main__":
    main()
