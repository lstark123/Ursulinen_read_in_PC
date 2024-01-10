import os.path
import schedule
import time
from aeroapi_python import AeroAPI
from aeroapi_python.Flights import Flights
from aeroapi_python.Airports import Airports
import datetime
import pandas as pd
import traceback


apiKey = "uDCw3K3dktz0XAIymLK5uqvAGJgj2PTS"
apiUrl = "https://aeroapi.flightaware.com/aeroapi/"
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

class Logging:
    def __init__(self):
        self.filepath = os.path.join("D:\\Uniarbeit 23_11_09\\data\\Data_airport\\Data_airport\\logging", "logging_flights_" + datetime.datetime.now().strftime("%Y_%m_%d-%H-%M_%S") + ".txt")

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
        path = self.api_caller._build_path(endpoint= self.endpoint, sub_path=f"{flight_id}/track")
        global paid_amount
        paid_amount += 0.012
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
        path = self.api_caller._build_path(self.endpoint, sub_path=sub_path, query=query)
        global paid_amount
        paid_amount += 0.02
        return self.api_caller.get(path)

class AeroAPI_exp(AeroAPI):
    def __init__(self, api_key):
        super().__init__(api_key)
        self.flights = Flights_exp(self.api_caller)


aeroapi_exp = AeroAPI_exp(apiKey)

def conversion_track_to_SI(track_df):
    feet_to_meter = 0.3048
    knots_to_mps = 0.514444
    track_df.altitude = track_df.altitude * feet_to_meter * 100
    track_df.groundspeed = track_df.groundspeed * knots_to_mps

def save_flightinfo_and_track_to_csv(flightinfo,track,filepath,nrflights):
    with open(filepath, 'w', encoding='utf-8') as file:
        for column in flightinfo.index:
            try:
                file.write(f'#Flight number {column} of {nrflights}: {flightinfo.loc[column]}\n')
            except Exception as Error:
                logging.give_error()
                logging.save_logging(f"Error wrinting: \n# {column}: {flightinfo.loc[column]}\n")
            try:
                track.drop(columns=['fa_flight_id']).to_csv(file, index=False, lineterminator='\n')
            except Exception as Error:
                logging.give_error()
                logging.save_logging(f"Error writing: {track}\n")


def load_flights_of_the_day(date_to_load_flights_of):
    global logging
    try:
        flights_save_path = "D:\\Uniarbeit 23_11_09\\data\\Data_airport\\Data_airport\\flights"
        if not (os.path.exists(flights_save_path)):
            os.mkdir(flights_save_path)

        timezone = datetime.timezone(datetime.timedelta(hours=2))
        first_hour_today = datetime.datetime.combine(date_to_load_flights_of,datetime.datetime.min.time(),timezone)
        last_hour_today = datetime.datetime.combine(date_to_load_flights_of,datetime.datetime.max.time(),timezone)

        datetime_format_call = "%Y-%m-%dT%H:%M:%SZ"
        def format_datetime(datetime_object):
            str = datetime_object.strftime(datetime_format_call)
            return str
        flight_movements = aeroapi_exp.airports.all_flights(airport_id=airport, start=format_datetime(first_hour_today), end=format_datetime(last_hour_today))
        logging.save_logging(f"Retrieving flights for the airport {airport} from aeroapi costs, 0.02$")
        logging.save_logging(f"Total paid:  {paid_amount}")
        arrivals = pd.DataFrame(flight_movements["arrivals"])
        departures = pd.DataFrame(flight_movements["departures"])
        scheduled_arrivals = pd.DataFrame(flight_movements["scheduled_arrivals"])
        scheduled_departures = pd.DataFrame(flight_movements["scheduled_departures"])

        # save the arrivals and departure dataframes
        # Save the DataFrame to a CSV file
        arrivals_sp = os.path.join(flights_save_path, (date_to_load_flights_of.strftime("%Y-%m-%d") + "_arrivals" + ".csv"))
        arrivals.to_csv(arrivals_sp, index=False)  # Set index=False to exclude the index column
        print(f'Arrivals saved to {arrivals_sp}')
        departures_sp = os.path.join(flights_save_path, (date_to_load_flights_of.strftime("%Y-%m-%d") +"_departures" + ".csv"))
        departures.to_csv(departures_sp, index=False)
        print(f'Departures saved to {departures_sp}')
        arrivalssched_sp = os.path.join(flights_save_path, (date_to_load_flights_of.strftime("%Y-%m-%d")+ "_arrivals_sched" +".csv"))
        scheduled_arrivals.to_csv(arrivalssched_sp, index=False)  # Set index=False to exclude the index column
        print(f'Arrivals_scheduled saved to {arrivalssched_sp}')
        departuressched_sp = os.path.join(flights_save_path, (date_to_load_flights_of.strftime("%Y-%m-%d")+ "_departures_sched" +".csv"))
        scheduled_departures.to_csv(departuressched_sp, index=False)  # Set index=False to exclude the index column
        print(f'Departures_scheduled saved to {departuressched_sp}')

        arr_deps = ["arr"]#["arr","dep"]

        for arr_dep in arr_deps:
            if arr_dep == "arr":
                df = arrivals
            if arr_dep == "dep":
                df = departures
            nrflights = df.shape[0]
            for index, flight in df.iterrows():
                logging.save_logging(f"Flight {arr_dep}, {index} of {df.shape[0]}")
                global nr_request
                if nr_request < 8:
                    try:
                        track_info = aeroapi_exp.flights.flight_track(flight.fa_flight_id)
                    except:
                        logging.give_error()
                    logging.save_logging(f"Retrieving track for the flight {flight.fa_flight_id} from aeroapi costs, 0.012$")
                    logging.save_logging(f"Total paid: {paid_amount}")
                    nr_request += 1
                    track = pd.DataFrame(track_info["positions"])
                    conversion_track_to_SI(track)
                    print("track of ", flight.fa_flight_id, " : ", track)
                    def get_fitting_flight_time(flight,arr_dep):
                        if arr_dep == "arr":
                            time_off_on_runway_ibk = flight.scheduled_on
                            if pd.isna(time_off_on_runway_ibk):
                                time_off_on_runway_ibk = flight.estimated_on
                                if pd.isna(time_off_on_runway_ibk):
                                    time_off_on_runway_ibk = flight.actual_on
                                    if pd.isna(time_off_on_runway_ibk):
                                        time_off_on_runway_ibk = date_to_load_flights_of
                                        return time_off_on_runway_ibk.strftime("%Y-%m-%d")

                        if arr_dep == "dep":
                            time_off_on_runway_ibk = flight.scheduled_off
                            if pd.isna(time_off_on_runway_ibk):
                                time_off_on_runway_ibk = flight.estimated_off
                                if pd.isna(time_off_on_runway_ibk):
                                    time_off_on_runway_ibk = flight.actual_off
                                    if pd.isna(time_off_on_runway_ibk):
                                        time_off_on_runway_ibk = date_to_load_flights_of
                                        return time_off_on_runway_ibk.strftime("%Y-%m-%d")

                        return time_off_on_runway_ibk.replace(":", "_")

                    time_off_on_runway_ibk = get_fitting_flight_time(flight,arr_dep)

                    filename = time_off_on_runway_ibk + "_" + arr_dep + "_" + flight.ident+ ".csv"
                    filepath_tracks = os.path.join(flights_save_path,"tracks")
                    filepath = os.path.join(filepath_tracks,filename)
                    save_flightinfo_and_track_to_csv(flight,track,filepath,nrflights)
                    logging.save_logging(f"Save flight to {filepath}")



                else:
                    logging.save_logging("wait for 100s ")
                    time.sleep(100)
                    nr_request = 0

        logging.save_logging("Finished loading flights \n ------------------------")
    except Exception as error:
        logging.give_error()

def main():
    global logging
    logging = Logging()
    logging.save_logging(f"Start loading in flights of the day at {datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')}")

    start_date = datetime.date(2023,12,31)
    end_date = datetime.date(2024,1,7)
    if end_date:
        ddays = (end_date-start_date).days
    else:
        ddays = 5
    # Create a list of datetime.date objects for the last week
    dates_to_load = [start_date + datetime.timedelta(days=x) for x in range(ddays)]
    dates_to_load = [datetime.date(2023,12,30)]
    for date in dates_to_load:
        load_flights_of_the_day(date)
        logging.save_logging("wait for 100s ")
        # time.sleep(100)

if __name__ == "__main__":
    main()