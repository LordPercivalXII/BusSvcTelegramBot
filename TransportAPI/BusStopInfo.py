import json
import os
import ssl
import urllib.request
from urllib.error import URLError
from dotenv import load_dotenv
from math import sqrt
from pathlib import Path
from UtilLib.JSONHandler import JSONHandler

bus_stop_data: JSONHandler
LON_LAT_CONV = 111139


def request_bus_stop_name_lta(bus_stop_code: int | str, api_key: str, debug: bool = False):
    """
    Gets and returns the Bus Stop Information of the Bus Stop.

    This method makes use of the data limit to cycle and check through if the codes matches.
    :param bus_stop_code: 5-digit Bus Stop Code
    :param api_key: LTA API Key
    :param debug: A boolean state to show debug text
    :return: Tuple containing:
             [0] -> Description,
             [1] -> Road Name,
             [2] -> Acquisition Success (for use in fallback)
    """
    skip_val = 0
    while True:
        url = f"https://datamall2.mytransport.sg/ltaodataservice/BusStops?$skip={skip_val}"

        headers = {
            "AccountKey": api_key,
            "accept": "application/json"
        }

        request = urllib.request.Request(url=url, method="GET", headers=headers)

        try:
            with urllib.request.urlopen(request) as response:
                json_dict = response.read().decode("utf-8")
                dict_data = json.loads(json_dict)

                for data in dict_data["value"]:
                    if data["BusStopCode"] == str(bus_stop_code):
                        if debug:
                            print(
                                f"=======================================================================================\n"
                                f"{data['Description']} @ {data['RoadName']} [{bus_stop_code}]\n"
                                f"======================================================================================="
                            )

                        return (
                            data["Description"],
                            data["RoadName"],
                            True
                        )

                if len(dict_data["value"]) < 500:
                    return (
                        None,
                        None,
                        False
                    )

                else:
                    skip_val += 500
            return None
        except URLError as e:
            if hasattr(e, "code") and hasattr(e, "reason"):
                # HTTP Error Code + Reason
                print(f"[{e.code} | {e.reason}] Error connecting to LTA DataMall API Service")

            elif hasattr(e, "reason"):
                # HTTP Error Reason
                print(f"[{e.reason}] Error connecting to LTA DataMall API Service")

            else:
                # Exception Error Dump
                print(f"[{e}] Error connecting to LTA DataMall API Service")

            return None


def request_bus_stop_name_tih(bus_stop_code: int | str, api_key: str):
    """
    RECOMMENDED NOT FOR USE FOR SECURITY REASONS.

    This API on TIH gets the data of the Bus Stop Information by referencing with a bus stop code.
    However, due to certification issues (which is bypassed), it is therefore not recommended to use it.
    :param bus_stop_code: The 5-digit Bus Stop Code
    :param api_key: TIH API Key
    :return: Tuple containing:
             [0] -> Description,
             [1] -> Road Name
    """
    url = f"https://api.stb.gov.sg/services/transport/v2/bus-stops/{bus_stop_code}"

    headers = {
        "X-API-Key": api_key,
        "accept": "application/json"
    }

    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE

    request = urllib.request.Request(url=url, headers=headers, method="GET")

    with urllib.request.urlopen(request, context=ssl_ctx) as response:
        json_dict = response.read().decode("utf-8")
        dict_data = json.loads(json_dict)
        return (
            dict_data["data"][0]["description"],
            dict_data["data"][0]["roadName"]
        )


def store_bus_stop_data(api_key: str):
    global bus_stop_data
    bus_stop_data = JSONHandler("BusStopData")

    curr_data = {"value": []}
    skip_val = 0
    while True:
        url = f"https://datamall2.mytransport.sg/ltaodataservice/BusStops?$skip={skip_val}"

        headers = {
            "AccountKey": api_key,
            "accept": "application/json"
        }

        request = urllib.request.Request(url=url, method="GET", headers=headers)

        try:
            with urllib.request.urlopen(request) as response:
                json_dict = response.read().decode("utf-8")
                dict_data = json.loads(json_dict)

                curr_data["value"].extend(dict_data["value"])

                if len(dict_data["value"]) < 500:
                    break

                else:
                    skip_val += 500
        except URLError as e:
            if hasattr(e, "code") and hasattr(e, "reason"):
                # HTTP Error Code + Reason
                print(f"[{e.code} | {e.reason}] Error connecting to LTA DataMall API Service")

            elif hasattr(e, "reason"):
                # HTTP Error Reason
                print(f"[{e.reason}] Error connecting to LTA DataMall API Service")

            else:
                # Exception Error Dump
                print(f"[{e}] Error connecting to LTA DataMall API Service")

            return

    bus_stop_data.update_json(curr_data)
    bus_stop_data.update_json_file()
    bus_stop_data.formulate_json()
    return


def return_bus_stop_name_json(bus_stop_code: str):
    for data in bus_stop_data.return_specific_json("value"):
        if data["BusStopCode"] == bus_stop_code:
            return (
                data["Description"],
                data["RoadName"]
                )

    return None


def request_bus_stop_code_from_name(stop_name: str, road_name: str = "", return_first_val: bool = False):
    matched_values = []

    for data in bus_stop_data.return_specific_json("value"):
        # print(f"{data["Description"].lower()} | {stop_name.lower()} ||| {data["RoadName"].lower()} | {road_name}")
        if data["Description"].lower() == stop_name.lower() and road_name == "":
            if return_first_val:
                return data["BusStopCode"]
            else:
                matched_values.append([data["BusStopCode"], data["Description"], data["RoadName"]])

        if data["Description"].lower() == stop_name.lower() and data["RoadName"].lower() == road_name.lower():
            if return_first_val:
                return data["BusStopCode"]
            else:
                matched_values.append([data["BusStopCode"], data["Description"], data["RoadName"]])

    if len(matched_values) > 0:
        return matched_values

    return "00000"


def get_nearby_bus_stops(lon: float, lat: float):
    nearby_stops = []
    sorted_nearby_stops = []
    disp_sorter = []

    lon_m = lon * LON_LAT_CONV
    lat_m = lat * LON_LAT_CONV

    for data in bus_stop_data.return_specific_json("value"):
        bus_lon_m = data["Longitude"] * LON_LAT_CONV
        bus_lat_m = data["Latitude"] * LON_LAT_CONV

        diff_lon = max(lon_m, bus_lon_m) - min(lon_m, bus_lon_m)
        diff_lat = max(lat_m, bus_lat_m) - min(lat_m, bus_lat_m)

        disp = sqrt(diff_lon * diff_lon + diff_lat * diff_lat)

        if disp <= 500:
            nearby_stops.append(
                (
                    data["BusStopCode"],
                    data["RoadName"],
                    data["Description"],
                    round(disp)
                )
            )
            disp_sorter.append(
                (
                    disp,
                    len(nearby_stops) - 1
                )
            )

    disp_sorter = sorted(disp_sorter)

    for (disp, i) in disp_sorter:
        sorted_nearby_stops.append(nearby_stops[i])

        if len(sorted_nearby_stops) == 15:
            break

    return sorted_nearby_stops


if __name__ == "__main__":
    ENV_PATH = os.path.join(Path(__file__).resolve().parent.parent, "RefKey.env")

    # Load ENV
    load_dotenv(dotenv_path=ENV_PATH)

    # Get Values from ENV
    API_KEY_LTA = os.getenv("API_KEY_LTA")
    # API_KEY_TIH = os.getenv("API_KEY_TIH")
    store_bus_stop_data(API_KEY_LTA)

    returner = request_bus_stop_name_lta(77009, API_KEY_LTA)

    print(f"{returner[0]} | {returner[1]}")
    print(f"{request_bus_stop_code_from_name('Blk 502', 'Pasir Ris St 52')}")
