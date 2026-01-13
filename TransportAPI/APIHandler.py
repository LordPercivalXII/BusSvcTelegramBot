from SettingsData import SETTINGS_DATA
from TransportAPI.BusStopInfo import request_bus_stop_name_lta, return_bus_stop_name_json, store_bus_stop_data
from TransportAPI.BusArrival import request_bus_stop_timing
from TransportAPI.BusService import return_bus_svc_json, store_bus_svc_data
from TransportAPI.BusRoute import store_bus_route_data, get_bus_svc_from_bus_stop_code
from UtilLib.JSONHandler import JSONHandler


class TransportAPIHandler:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.json_mem = JSONHandler("MemoryData")

    def store_json_data(self):
        store_bus_stop_data(self.api_key)
        store_bus_svc_data(self.api_key)
        store_bus_route_data(self.api_key)

    def request_arrival_time(self, bus_stop_code: str, explicit_buses: list, name: str):
        # JSON Settings Values Formulation
        self.json_mem.formulate_json()
        mem_dict = self.json_mem.return_specific_json(name)

        # If Settings Data does not exist
        if mem_dict.get("settings") is None:
            mem_dict["settings"] = SETTINGS_DATA

        # Add new KVs
        else:
            for key_verify, value_verify in SETTINGS_DATA.items():
                verify_check = False
                for k, v in mem_dict["settings"].items():
                    # If KV exists
                    if k == key_verify:
                        verify_check = True
                        continue

                # Insert new KV if non existent
                if not verify_check:
                    mem_dict["settings"][key_verify] = value_verify

        # Get Required KVs
        consolidated_timing = mem_dict["settings"]["timing_consolidated"]["data"]
        use_emojis = mem_dict["settings"]["use_emojis"]["data"]

        # Get Bus Stop Data
        curr_stop_returner = request_bus_stop_name_lta(bus_stop_code, self.api_key)
        arrival_returner = request_bus_stop_timing(bus_stop_code, self.api_key, explicit_buses,
                                                   no_exact_time=consolidated_timing, short_forms=consolidated_timing,
                                                   use_emojis=use_emojis)
        main_returner = []


        if curr_stop_returner[2] is True:
            print(
                f"=======================================================================================\n"
                f"{curr_stop_returner[0]} @ {curr_stop_returner[1]} [{bus_stop_code}]\n"
                f"======================================================================================="
            )
            main_returner.append(f"{curr_stop_returner[0]} @ {curr_stop_returner[1]} [{bus_stop_code}]")
        else:
            print(
                f"=======================================================================================\n"
                f"Bus Stop No: {bus_stop_code} Services\n"
                f"======================================================================================="
            )
            main_returner.append(f"Bus Stop No: {bus_stop_code} Services")

        # No Bus Svc Formulation
        if len(arrival_returner) == 0:
            print(
                f"There is no bus services available.\n"
                f"======================================================================================="
            )
            main_returner.append(f"There is no bus services available.")
            return main_returner

        # Bus Svc Formulation
        for arrival_data in arrival_returner:
            svc_info_returner = return_bus_svc_json(arrival_data[0], 1)

            if svc_info_returner[4] != arrival_data[18] and svc_info_returner[5] != arrival_data[19]:
                svc_info_returner = return_bus_svc_json(arrival_data[0], 2)

            if svc_info_returner[7] is False:
                svc_info = f"{return_bus_stop_name_json(svc_info_returner[4])[0]} >>> " \
                           f"{return_bus_stop_name_json(svc_info_returner[5])[0]} " \
                           f"[{svc_info_returner[3]}]"

            elif svc_info_returner[7] is True:
                svc_info = f"Loop @ {svc_info_returner[6]} to " \
                           f"{return_bus_stop_name_json(svc_info_returner[5])[0]} " \
                           f"[{svc_info_returner[3]}]"

            else:
                svc_info = f"This service does not exist."

            print(
                f"Service [{arrival_data[0]}] | {arrival_data[1]}\n"
                f"{svc_info}\n"
                f"=======================================================================================\n"
                f"{f'{arrival_data[2]} | {arrival_data[5]} | {arrival_data[8]} | Visit: {arrival_data[11]} | Accurate: {arrival_data[20]}' if arrival_data[2] != "Not in Service" else arrival_data[2]}\n"
                f"{f'{arrival_data[3]} | {arrival_data[6]} | {arrival_data[9]} | Visit: {arrival_data[12]} | Accurate: {arrival_data[21]}' if arrival_data[3] != "Not in Service" else arrival_data[3]}\n"
                f"{f'{arrival_data[4]} | {arrival_data[7]} | {arrival_data[10]} | Visit: {arrival_data[13]} | Accurate: {arrival_data[22]}' if arrival_data[4] != "Not in Service" else arrival_data[4]}\n"
            )

            print(
                f"Estimated Duration: {arrival_data[14]} min" if arrival_data[17] is True else
                f"Estimated Duration (Visit 1): {arrival_data[15]} min\n"
                f"Estimated Duration (Visit 2): {arrival_data[16]} min"
            )

            print(
                f"======================================================================================="
            )

            main_returner.append(
                [
                    f"Service [{arrival_data[0]}] | {arrival_data[1]}",
                    f"{svc_info}",
                    f"{arrival_data[2]} | {arrival_data[5]} | {arrival_data[8]} | Visit: {arrival_data[11]}" + (f" [EST]" if not arrival_data[20] else ""),
                    f"{arrival_data[3]} | {arrival_data[6]} | {arrival_data[9]} | Visit: {arrival_data[12]}" + (f" [EST]" if not arrival_data[21] else ""),
                    f"{arrival_data[4]} | {arrival_data[7]} | {arrival_data[10]} | Visit: {arrival_data[13]}" + (f" [EST]" if not arrival_data[22] else ""),
                    f"Estimated Duration: {arrival_data[14]} min" if arrival_data[17] is True else
                    f"Estimated Duration (Visit 1): {arrival_data[15]} min\n"
                    f"Estimated Duration (Visit 2): {arrival_data[16]} min"
                ]
            )

        return main_returner

    @staticmethod
    def request_bus_stop_svc_list(bus_stop_code: str):
        returner = ""

        # Noted that no bus services will list on end of service - Write new method and deprecate old method
        # svc_returner = request_bus_stop_timing(bus_stop_code=bus_stop_code, api_key=self.api_key, svc_num=[],
        #                                        return_svc_list=True)

        svc_returner = get_bus_svc_from_bus_stop_code(bus_stop_code)

        for i in range(len(svc_returner)):
            if i == 0:
                returner = str(svc_returner[i])
            else:
                returner += f", {svc_returner[i]}"

        return returner
