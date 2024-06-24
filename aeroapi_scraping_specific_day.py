import os.path
import schedule
import time
from aeroapi_python import AeroAPI
from aeroapi_python.Flights import Flights
from aeroapi_python.Airports import Airports
import datetime
import pandas as pd
import traceback
import aeroapi_base as ab
import datetime

def main():
    ab.logging.save_logging(f"Start loading in flights of the day at {datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')}")
    start_date = datetime.date(2024,5,4)
    end_date = datetime.date(2024,5,12)
    if end_date:
        ddays = (end_date-start_date).days
    else:
        ddays = 5
    # Create a list of datetime.date objects for the last week
    dates_to_load = [start_date + datetime.timedelta(days=x) for x in range(ddays)]
    # dates_to_load = [datetime.date(2024,5,10)]
    print(f"Scraping flights for days {dates_to_load}")
    data_for_all_dates = {}
    for date in dates_to_load:
        all_data_this_date = {}
        all_data_this_date["aeroapi"] = ab.get_flightdata_aeroapi_and_save(date)
        # all_data_this_date["flightradar"] = ab.get_flightdata_flightradar24_and_save(date)
        all_data_this_date["tracks"] = ab.get_tracks_of_flights_and_save(all_data_this_date["aeroapi"])
        data_for_all_dates[date] = all_data_this_date
        if len(dates_to_load) > 1:
            time.sleep(100)

if __name__ == "__main__":
    main()