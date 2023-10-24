import os.path
import schedule
import time
from aeroapi_python import AeroAPI
from aeroapi_python.Flights import Flights
from aeroapi_python.Airports import Airports
import datetime
import pandas as pd


apiKey = "uDCw3K3dktz0XAIymLK5uqvAGJgj2PTS"
apiUrl = "https://aeroapi.flightaware.com/aeroapi/"
flights_save_path = "F:\\Uniarbeit\\flight_aware\\data"
# -> make a subdirectory where you store all the flight data
airport = 'LOWI'
# fa_flight_id = "AUA905-1697538514-schedule-1261p"
# payload = {'max_pages': 2}
auth_header = {'x-apikey':apiKey}
paid_amount = 0
nr_request = 0

"""
You can try calling a specific url by:
aeroapi.api_caller.get(url)

you get all flights of an airport by:
aeroapi_exp.airports.all_flights()
start and end time are gven in ISO8601 Format
"""

class Flights_exp(Flights):
    def __init__(self, api_caller):
        super().__init__(api_caller)
    def flight_track(self, flight_id: str):
        """
        Retrieves the track of a specific flight.

        Args:
            flight_id (str): The unique identifier of the flight.

        Returns:
            dict: The parsed JSON response, or None if the request failed.
        """

        print("Retrieving track for the flight ", flight_id, " from aeroapi costs, 0.012$")
        path = self.api_caller._build_path(endpoint= self.endpoint, sub_path=f"{flight_id}/track")
        global paid_amount
        paid_amount += 0.012
        print("Total paid: ", paid_amount)
        return self.api_caller.get(path)


class Airport_exp(Airports):
    def __init__(self, api_caller):
        super().__init__(api_caller)

    def all_flights(self, airport_id: str, airline: None, flight_type:  None, start:  None, end:None, cursor: None, max_pages: int = 1):
        """
        Retrieves information about all flights for a specific airport.

        Args:
            airport_id (str): The airport identifier (ICAO code).
            airline (str): Optional, the airline to filter by.
            flight_type (str): Optional, the type of flight to filter by.
            start (int): Optional, the start timestamp for the flight data (in Unix time).
            end (int): Optional, the end timestamp for the flight data (in Unix time).
            max_pages (int): Optional, the maximum number of pages to retrieve.
            cursor (str): Optional, a cursor for paginating through the results.

        Returns:
            dict: The parsed JSON response, or None if the request failed.
        """
        sub_path = f"{airport_id}/flights"
        query = {
            "airline": airline,
            "type": flight_type,
            "start": start,
            "end": end,
            "max_pages": max_pages,
            "cursor": cursor,
        }
        print("Retrieving all flights from airport ", airport_id, " from aeroapi costs, 0.02$")
        path = self.api_caller._build_path(self.endpoint, sub_path=sub_path, query=query)
        global paid_amount
        paid_amount += 0.02
        print("Total paid: ", paid_amount)
        return self.api_caller.get(path)

class AeroAPI_exp(AeroAPI):
    def __init__(self, api_key):
        super().__init__(api_key)
        self.flights = Flights_exp(self.api_caller)


def conversion_track_to_SI(track_df):
    feet_to_meter = 0.3048
    knots_to_mps = 0.514444
    track_df.altitude = track_df.altitude * feet_to_meter * 1000
    track_df.groundspeed = track_df.groundspeed * knots_to_mps

def save_flightinfo_and_track_to_csv(flightinfo,track,filepath):
    with open(filepath, 'w') as file:
        for column in flightinfo.index:
            file.write(f'# {column}: {flightinfo.loc[column]}\n')
        track.fa_flight_id = flightinfo.fa_flight_id
        track.to_csv(file, index=False, lineterminator='\n')

aeroapi_exp = AeroAPI_exp(apiKey)

def load_flights_of_the_day():
    print("Start loading in flights od the day at ", datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"))
    timezone = datetime.timezone(datetime.timedelta(hours=2))
    first_hour_today = datetime.datetime.combine(datetime.datetime.now().date(),datetime.datetime.min.time(),timezone)
    last_hour_today = datetime.datetime.combine(datetime.datetime.now().date(),datetime.datetime.max.time(),timezone)

    datetime_format_call = "%Y-%m-%dT%H:%M:%SZ"
    def format_datetime(datetime_object):
        str = datetime_object.strftime(datetime_format_call)
        return str
    flight_movements = aeroapi_exp.airports.all_flights(airport_id=airport, start=format_datetime(first_hour_today), end=format_datetime(last_hour_today))
    arrivals = pd.DataFrame(flight_movements["arrivals"])
    departures = pd.DataFrame(flight_movements["departures"])
    scheduled_arrivals = pd.DataFrame(flight_movements["scheduled_arrivals"])
    scheduled_departures = pd.DataFrame(flight_movements["scheduled_departures"])

    # save the arrivals and departure dataframes
    arr_deps = ["arr","dep"]

    for arr_dep in arr_deps:
        if arr_dep == "arr":
            df = arrivals
        if arr_dep == "dep":
            df = departures
        for index, flight in df.iterrows():
            print("Flight ", index , " of ", df.shape[0])
            global nr_request
            if nr_request < 9:
                track_info = aeroapi_exp.flights.flight_track(flight.fa_flight_id)
                nr_request += 1
                track = pd.DataFrame(track_info["positions"])
                print("track of ", flight.fa_flight_id, " : ", track)
                if arr_dep == "arr":
                    time_off_on_runway_ibk = flight.scheduled_on
                    if time_off_on_runway_ibk == None:
                        time_off_on_runway_ibk = ""
                    else:
                        time_off_on_runway_ibk = time_off_on_runway_ibk.replace(":", "_")
                if arr_dep == "dep":
                    time_off_on_runway_ibk = flight.scheduled_off
                    if time_off_on_runway_ibk == None:
                        time_off_on_runway_ibk = ""
                    else:
                        time_off_on_runway_ibk = time_off_on_runway_ibk.replace(":", "_")

                filename =  "flight" + "_" + time_off_on_runway_ibk + "_" + arr_dep + "_" + flight.ident+ ".csv"
                filepath = os.path.join(flights_save_path,filename)
                save_flightinfo_and_track_to_csv(flight,track,filepath)

            else:
                print("wait for 100s ")
                time.sleep(100)
                nr_request = 0

    print("Finished loading flights, see you tomorrow")

def main():
    def my_task():
        print("Task executed at the specific time")

    # Define the specific time (e.g., 10:30 AM)
    specific_time = "18:30"
    # load_flights_of_the_day()
    print("Start the flight scraping script")
    # Schedule the task at the specific time
    schedule.every().day.at(specific_time).do(load_flights_of_the_day)

    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    main()