import json
import os
import urllib.request
from dotenv import load_dotenv
from pathlib import Path
from TransportAPI.BusService import sort_bus_svc_list
from UtilLib.JSONHandler import JSONHandler

bus_route_data: JSONHandler


def request_bus_route_info(api_key: str):
    """
    Gets and returns information of the bus service. Does not cover bus route.

    :param api_key: The LTA API Key
    :return: Tuple containing:
             [0] -> Service Number,
             [1] -> Service Operator,
             [2] -> Direction,
             [3] -> Service Category,
             [4] -> Origin of Travel (in code),
             [5] -> Destination (in code),
             [6] -> Loop Description,
             [7] -> boolean stating whether this service is a loop
    """
    skip_val = 0
    while True:
        url = f"https://datamall2.mytransport.sg/ltaodataservice/BusRoutes?$skip={skip_val}"

        headers = {
            "AccountKey": api_key,
            "accept": "application/json"
        }

        request = urllib.request.Request(url=url, headers=headers, method="GET")

        with urllib.request.urlopen(request) as response:
            json_dict = response.read().decode("utf-8")
            dict_data = json.loads(json_dict)
            route_dict = dict()
            # temp_route_dict = dict()

            for data in dict_data["value"]:
                # print(f"PROC: {data['ServiceNo']}")
                if data["ServiceNo"] not in route_dict:
                    route_dict[data["ServiceNo"]] = {
                        data["Direction"]: {
                            data["StopSequence"]: (data["BusStopCode"], data["Distance"]),
                        }
                    }
                    # print(f"PROC: DIRECTION: {data['Direction']} | STOP: {data['StopSequence']} | BUS: {data['BusStopCode']} | DISTANCE: {data['Distance']}")
                else:
                    temp_route_dict = route_dict[data["ServiceNo"]]

                    if data["Direction"] in route_dict[data["ServiceNo"]]:
                        temp_route_dict[data["Direction"]][data["StopSequence"]] = (data["BusStopCode"], data["Distance"])

                    else:
                        temp_route_dict[data["Direction"]] = {data["StopSequence"]: (data["BusStopCode"], data["Distance"])}

                    route_dict[data["ServiceNo"]] = temp_route_dict

                    # print(f"PROC: DIRECTION: {data['Direction']} | STOP: {data['StopSequence']} | BUS: {data['BusStopCode']} | DISTANCE: {data['Distance']}")

            if len(dict_data["value"]) < 500:
                break
            else:
                skip_val += 500

            # print(f"PROC: SKIP: {skip_val}")

    # print(route_dict)

    return route_dict


def store_bus_route_data(api_key: str):
    global bus_route_data
    bus_route_data = JSONHandler("BusRouteData")

    curr_data = {"value": []}
    skip_val = 0
    while True:
        url = f"https://datamall2.mytransport.sg/ltaodataservice/BusRoutes?$skip={skip_val}"

        headers = {
            "AccountKey": api_key,
            "accept": "application/json"
        }

        request = urllib.request.Request(url=url, method="GET", headers=headers)

        with urllib.request.urlopen(request) as response:
            json_dict = response.read().decode("utf-8")
            dict_data = json.loads(json_dict)

            curr_data["value"].extend(dict_data["value"])

            if len(dict_data["value"]) < 500:
                break

            else:
                skip_val += 500

        for data in dict_data["value"]:
            route_dict = dict()
            # print(f"PROC: {data['ServiceNo']} | {data['Direction']} | {data['StopSequence']} | {data['BusStopCode']}")
            if data["ServiceNo"] not in bus_route_data.json_data:
                # print(f"PROC: CREATE FOR {data['ServiceNo']}")
                bus_route_data.update_specific_json(
                    data["ServiceNo"],
                    {
                        data["Direction"]: {
                            data["StopSequence"] : (data["BusStopCode"], data["Distance"])
                        }
                    }
                )
                # print(f"PROC: DIRECTION: {data['Direction']} | STOP: {data['StopSequence']} | BUS: {data['BusStopCode']} | DISTANCE: {data['Distance']}")
            else:
                route_dict = bus_route_data.return_specific_json(data["ServiceNo"])
                # print(f"PROC: {data['ServiceNo']} | {data['Direction']}")
                # print(f"{route_dict}")

                if data["Direction"] in route_dict:
                    route_dict[data["Direction"]][data["StopSequence"]] = (data["BusStopCode"], data["Distance"])

                else:
                    route_dict[data["Direction"]] = {data["StopSequence"] : (data["BusStopCode"], data["Distance"])}

                bus_route_data.update_specific_json(data["ServiceNo"], route_dict)

                # print(f"PROC: DIRECTION: {data['Direction']} | STOP: {data['StopSequence']} | BUS: {data['BusStopCode']} | DISTANCE: {data['Distance']}")

    # bus_route_data.update_json(curr_data)
    bus_route_data.update_json_file()
    bus_route_data.formulate_json()


def get_bus_svc_route(svc: str, direction: str):
    return bus_route_data.return_specific_json(svc)[direction]


def get_bus_svc_from_bus_stop_code(bus_stop_code: str):
    svc_list = []
    for svc, data in bus_route_data.return_json().items():
        for direction, dir_data in data.items():
            for stop, stop_data in dir_data.items():
                if bus_stop_code in stop_data and svc not in svc_list:
                    svc_list.append(svc)
                    break

    return sort_bus_svc_list(svc_list)

if __name__ == "__main__":
    ENV_PATH = os.path.join(Path(__file__).resolve().parent.parent, "RefKey.env")

    # Load ENV
    load_dotenv(dotenv_path=ENV_PATH)

    # Get Values from ENV
    API_KEY_LTA = os.getenv("API_KEY_LTA")
    store_bus_route_data(API_KEY_LTA)

    returner = request_bus_route_info(API_KEY_LTA)

    print(returner)

    print(get_bus_svc_from_bus_stop_code("77009"))
    # if returner[7] is False:
    #     print(
    #         f"=======================================================================================\n"
    #         f"[{returner[0]}] | {returner[1]}\n"
    #         f"{returner[3]} Service\n"
    #         f"{returner[4]} >>> {returner[5]} [Direction: {returner[2]}]\n"
    #         f"======================================================================================="
    #     )
    # elif returner[7] is True:
    #     print(
    #         f"=======================================================================================\n"
    #         f"[{returner[0]}] | {returner[1]}\n"
    #         f"{returner[3]} Service\n"
    #         f"Loop @ {returner[6]} to {returner[5]}\n"
    #         f"======================================================================================="
    #     )
    # else:
    #     print(
    #         f"=======================================================================================\n"
    #         f"This service does not exist.\n"
    #         f"======================================================================================="
    #     )
