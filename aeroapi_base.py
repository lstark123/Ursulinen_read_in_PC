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


apiKey = "uDCw3K3dktz0XAIymLK5uqvAGJgj2PTS"
apiUrl = "https://aeroapi.flightaware.com/aeroapi/"
flights_save_path = "C:\\Users\\c7441354\\Documents\\Ursulinen\\Data_airport\\flights"



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
        self.filepath = os.path.join("C:\\Users\\c7441354\\Documents\\Ursulinen\\Data_airport\\logging", "logging_flights_" + datetime.datetime.now().strftime("%Y_%m_%d-%H-%M") + ".txt")

    def save_logging(self, text):
        print(text)
        time =datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
        with open(self.filepath, "a") as f:
            f.write("\n" + time + text)
    def give_error(self, text = ""):
        time =datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
        stack_trace = traceback.format_exc()
        print(f"Error: {text}")
        print(stack_trace)
        with open(self.filepath, "a") as f:
            f.write("\n" + time + "Error -------------------------\n"+ text + "\n")
            f.write(stack_trace)



logging = Logging()



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
        self.flights = Flights_exp(self.api_caller)

    def all_flights(self, airport_id: str, airline= None, flight_type= None, start= None, end = None, max_pages: int = 1, cursor= None):
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
        self.airports = Airport_exp(self.api_caller)



aeroapi_exp = AeroAPI_exp(apiKey)



def extract_relevant_data_flightradar24(flightdata_array, arrival_or_departure):
    nrflights = len(flightdata_array)
    time_coordinates = np.empty(nrflights, dtype="datetime64[s]")
    flight_movement_info = {"default_identification": [""] * nrflights,
                            "time_scheduled_UNIX_departure": [""] * nrflights,
                            "time_scheduled_UNIX_arrival": [""] * nrflights,
                            "time_estimated_UNIX": [""] * nrflights,
                            "time_real_UNIX": [""] * nrflights,
                            "time_best_UNIX": [""] * nrflights,
                            "status": [""] * nrflights,
                            "origin": [""] * nrflights,
                            "destination": [""] * nrflights,
                            "aircraftmodel": [""] * nrflights,
                            "aircraftmodel_code": [""] * nrflights,
                            "callsign": [""] * nrflights,
                            "airline": [""] * nrflights,
                            "arrival_departure": [""] * nrflights,
                            }
    for index, flight in enumerate(flightdata_array):
        flight_movement_info["arrival_departure"][index] = arrival_or_departure

        date = flight["flight"]["time"]["scheduled"][arrival_or_departure + "_date"]
        time = flight["flight"]["time"]["scheduled"][arrival_or_departure + "_time"]
        flight_movement_time = pd.to_datetime(date + time, format='%Y%m%d%H%M')
        time_coordinates[index] = flight_movement_time
        flight_movement_info["time_scheduled_UNIX_" + arrival_or_departure][index] = str(
            round(flight_movement_time.timestamp()))
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
            flight_movement_info["aircraftmodel"][index] = flight["flight"]["aircraft"]["model"]["text"]
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
            flight_movement_info["default_identification"][index] = flight["flight"]["identification"]["number"][
                "default"]
        except:
            flight_movement_info["default_identification"][index] = ""

    flight_movement_info = pd.DataFrame(flight_movement_info)
    flight_movement_info.index = time_coordinates

    return flight_movement_info


def get_flightdata_flightradar24_and_save(date = datetime.date.today(), flights_save_path = flights_save_path):
    print("Try to get Flight data from fr24")
    f = FlightData()
    try:
        arrivals_alldata = f.get_airport_arrivals('INN', earlier_data=True)
        departures_alldata = f.get_airport_departures('INN', earlier_data=True)

        arrivals = extract_relevant_data_flightradar24(arrivals_alldata, "arrival")
        arrivals_sp = os.path.join(flights_save_path, (date.strftime("%Y-%m-%d") + "_fr24_arrivals" + ".csv"))
        arrivals.to_csv(arrivals_sp, index=False)  # Set index=False to exclude the index column
        print(f'Arrivals saved to {arrivals_sp}')

        departures = extract_relevant_data_flightradar24(departures_alldata, "departure")
        departures_sp = os.path.join(flights_save_path,
                                     (date.strftime("%Y-%m-%d") + "_fr24_departures" + ".csv"))
        departures.to_csv(departures_sp, index=False)
        print(f'Departures saved to {departures_sp}')
        logging.save_logging(f"Retrieving flights for the airport {airport} from flightradar 24")
        arrivals = arrivals.loc[arrivals.index.date == date]
        departures = departures.loc[departures.index.date == date]
        arrivals.index = arrivals.schedule_on
        fr24 =  {"arrivals":arrivals,"departures":departures}
    except:
        fr24 = 0
        logging.give_error()
    return fr24


# dont need this one
def get_flightdata_aeroapi_and_save(date = datetime.date.today(),flights_save_path = flights_save_path):
    print(f"Try to get Flight data from aeroapi for date {date}")

    datetime_format_call = "%Y-%m-%dT%H:%M:%SZ"
    timezone = datetime.timezone(datetime.timedelta(hours=2))

    def format_datetime(datetime_object):
        str = datetime_object.strftime(datetime_format_call)
        return str
    first_hour_today = datetime.datetime.combine(date,datetime.datetime.min.time(),timezone)
    last_hour_today = datetime.datetime.combine(date,datetime.datetime.max.time(),timezone)
    flight_movements = aeroapi_exp.airports.all_flights(airport_id=airport, start=format_datetime(first_hour_today),
                                                        end=format_datetime(last_hour_today),max_pages=10)
    logging.save_logging(f"Retrieving flights for the airport {airport} from aeroapi costs, 0.02$")
    logging.save_logging(f"Total paid:  {paid_amount}")
    arrivals = pd.DataFrame(flight_movements["arrivals"])
    departures = pd.DataFrame(flight_movements["departures"])
    scheduled_arrivals = pd.DataFrame(flight_movements["scheduled_arrivals"])
    scheduled_departures = pd.DataFrame(flight_movements["scheduled_departures"])

    # save the arrivals and departure dataframes
    # Save the DataFrame to a CSV file
    arrivals_sp = os.path.join(flights_save_path, (date.strftime("%Y-%m-%d") + "_aeroapi_arrivals" + ".csv"))
    arrivals.to_csv(arrivals_sp, index=False)  # Set index=False to exclude the index column
    print(f'Arrivals saved to {arrivals_sp}')
    departures_sp = os.path.join(flights_save_path,
                                 (date.strftime("%Y-%m-%d") + "_aeroapi_departures" + ".csv"))
    departures.to_csv(departures_sp, index=False)
    print(f'Departures saved to {departures_sp}')
    flights = {"arrivals":arrivals, "departures":departures}
    global nr_request
    nr_request += 1
    return  flights
    # arrivalssched_sp = os.path.join(flights_save_path, (datetime.datetime.now().strftime("%Y-%m-%d")+ "_arrivals_sched" +".csv"))
    # scheduled_arrivals.to_csv(arrivalssched_sp, index=False)  # Set index=False to exclude the index column
    # print(f'Arrivals_scheduled saved to {arrivalssched_sp}')
    # departuressched_sp = os.path.join(flights_save_path, (datetime.datetime.now().strftime("%Y-%m-%d")+ "_departures_sched" +".csv"))
    # scheduled_arrivals.to_csv(departuressched_sp, index=False)  # Set index=False to exclude the index column
    # print(f'Departures_scheduled saved to {departuressched_sp}')

def get_aeroapi_from_fa_flight_id_and_save(fa_flight_id,ident,arrdep):
    track_info = aeroapi_exp.flights.flight_track(fa_flight_id)
    print(track_info)
    track = pd.DataFrame(track_info["positions"])
    track = conversion_track_to_SI(track)
    print("track of ", fa_flight_id, " : ", track)
    time = track.timestamp[0]
    time = time.replace(":","_")
    print(time)
    filename = time + "_" + arrdep + "_" + ident + ".csv"
    filepath_tracks = os.path.join(flights_save_path, "tracks")
    filepath = os.path.join(filepath_tracks, filename)
    track = track.drop(columns=['fa_flight_id'])
    print(f"Save to {filepath}")
    track.to_csv(filepath, index=False, lineterminator='\n')


def get_fitting_flight_time(flight, arr_dep):
    # get the best estimate of the time at runway (schuduled < estimated < actual)
    if arr_dep == "arrivals":
        time_off_on_runway_ibk = flight.scheduled_on
        if pd.isna(time_off_on_runway_ibk):
            time_off_on_runway_ibk = flight.estimated_on
            if pd.isna(time_off_on_runway_ibk):
                time_off_on_runway_ibk = flight.actual_on
                if pd.isna(time_off_on_runway_ibk):
                    time_off_on_runway_ibk = datetime.datetime.now().date()
                    time_off_on_runway_ibk.strftime("%Y-%m-%d")

    if arr_dep == "departures":
        time_off_on_runway_ibk = flight.scheduled_off
        if pd.isna(time_off_on_runway_ibk):
            time_off_on_runway_ibk = flight.estimated_off
            if pd.isna(time_off_on_runway_ibk):
                time_off_on_runway_ibk = flight.actual_off
                if pd.isna(time_off_on_runway_ibk):
                    time_off_on_runway_ibk = datetime.datetime.now().date()
                    time_off_on_runway_ibk.strftime("%Y-%m-%d")

    return time_off_on_runway_ibk.replace(":", "_")

def get_tracks_of_flights_and_save(flights_aero = 0):
    if not (os.path.exists(flights_save_path)):
        os.mkdir(flights_save_path)
    tracks = {}
    running_number = 0
    global nr_request
    nr_request += 6


    # only download gps of arrivals

    for arr_dep in flights_aero:
        for index, flight in flights_aero[arr_dep].iterrows():
            #could filter for long flights with: flights_aero[arr_dep][flights_aero[arr_dep][route_distance> 200].iterrows()
            try:
                logging.save_logging(f"Flight {arr_dep}, {index} of {flights_aero[arr_dep].shape[0]}")
                if nr_request < 9:
                    track_info = aeroapi_exp.flights.flight_track(flight.fa_flight_id)
                    #all times are in UTC ISO8601
                    logging.save_logging(f"Retrieving track for the flight {flight.fa_flight_id} from aeroapi costs, 0.012$")
                    logging.save_logging(f"Total paid: {paid_amount}")
                    nr_request += 1
                    track = pd.DataFrame(track_info["positions"])
                    track = conversion_track_to_SI(track)

                    print("track of ", flight.fa_flight_id, " : ", track)


                    time_off_on_runway_ibk = get_fitting_flight_time(flight,arr_dep)

                    filename = time_off_on_runway_ibk + "_" + arr_dep + "_" + flight.ident+ ".csv"
                    filepath_tracks = os.path.join(flights_save_path,"tracks")
                    if not (os.path.exists(filepath_tracks)):
                        os.mkdir(filepath_tracks)
                    filepath = os.path.join(filepath_tracks,filename)
                    save_flightinfo_and_track_to_csv(flight,track,filepath)
                    logging.save_logging(f"Save flight to {filepath}")
                    tracks[running_number] = track
                else:
                    logging.save_logging("wait for 100s ")
                    time.sleep(100)
                    nr_request = 0
                running_number += 1

            except:
                logging.give_error()

    logging.save_logging("Finished loading flights")
    return tracks

def get_aeroapi_info_for_IATA_ident(ident_IATA, date = datetime.date.today()):
    # for which time should we filter in date? scheduled_off?
    print(f"Get aeroapi Info of {ident_IATA}")
    flights_of_ident = aeroapi_exp.flights.get_flight(ident_IATA)
    flights_of_ident = pd.DataFrame(flights_of_ident["flights"])
    print(flights_of_ident)
    flights_of_ident_at_date = flights_of_ident.loc[pd.to_datetime(flights_of_ident.scheduled_off).dt.date == date]
    return flights_of_ident_at_date
def conversion_track_to_SI(track_df):
    feet_to_meter = 0.3048
    knots_to_mps = 0.514444
    track_df.altitude = track_df.altitude * feet_to_meter * 100
    track_df.groundspeed = track_df.groundspeed * knots_to_mps
    track_df = track_df.rename(columns={'altitude': 'altitude_m','groundspeed': 'groundspeed_mps'})
    return track_df
def save_flightinfo_and_track_to_csv(flightinfo,track,filepath):
    with open(filepath, 'w', encoding='utf-8') as file:
        for column in flightinfo.index:
            try:
                file.write(f'{column}: {flightinfo.loc[column]}\n')
            except Exception as Error:
                logging.give_error()
                logging.save_logging(f"Error wrinting: \n# {column}: {flightinfo.loc[column]}\n")
        try:
            track = track.drop(columns=['fa_flight_id'])
            track.to_csv(file, index=False, lineterminator='\n')
        except Exception as Error:
            logging.give_error()
            logging.save_logging(f"Error writing: {track}\n")



def save_flightinfo_and_track_to_csv(flightinfo,track,filepath):
    with open(filepath, 'w', encoding='utf-8') as file:
        for column in flightinfo.index:
            try:
                file.write(f'{column}: {flightinfo.loc[column]}\n')
            except Exception as Error:
                logging.give_error()
                logging.save_logging(f"Error wrinting: \n# {column}: {flightinfo.loc[column]}\n")
        try:
            track = track.drop(columns=['fa_flight_id'])
            track.to_csv(file, index=False, lineterminator='\n')
        except Exception as Error:
            logging.give_error()
            logging.save_logging(f"Error writing: {track}\n")
