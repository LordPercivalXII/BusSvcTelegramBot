import datetime
import urllib.request
from math import sqrt
from urllib.error import URLError
from SettingsData import SETTINGS_DATA
from UtilLib.JSONHandler import JSONHandler


class TransportAPIHandler:
    LON_LAT_CONV = 111139
    SEATING = [("SEA", "Seating Available", "🟩"), ("SDA", "Standing Available", "🟨"), ("LSD", "Limited Standing", "🟥")]
    BUS_TYPE = [("SD", "Single Deck"), ("DD", "Double Deck"), ("BD", "Bendy")]
    DBL_LOOP_DATA = {
        "42": "Lengkong Empat & Fidelio St",
        "92": "Science Pk Dr & Mount Sinai Dr",
        "291": "Tampines St 81 & Tampines St 33",
        "293": "Tampines St 71 & Tampines Ave 7",
        "307": "Choa Chu Kang St 62 & Teck Whye Lane",
        "358": "Pasir Ris Dr 10 & Pasir Ris Dr 4",
        "359": "Pasir Ris St 71 & Pasir Ris Dr 2",
        "811": "Yishun Ave 5 & Yishun Ave 1",
        "812": "Yishun Ave 4 & Yishun Ave 3",
        "911": "Woodlands Ave 2 & Woodlands Ctr Rd",
        "912": "Woodlands Ave 7 & Woodlands Ctr Rd",
        "913": "Woodlands Circle & Woodlands Ave 3"
    }

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.json_mem = JSONHandler("MemoryData")
        self.bus_stop_data = JSONHandler("BusStopData")
        self.bus_svc_data = JSONHandler("BusServiceData")
        self.bus_route_data = JSONHandler("BusRouteData")

    def store_json_data(self):
        self.store_bus_stop_data(self.api_key)
        self.store_bus_svc_data(self.api_key)
        self.store_bus_route_data(self.api_key)

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
        curr_stop_returner = self.request_bus_stop_name(bus_stop_code, self.api_key, True)
        arrival_returner = self.request_bus_stop_timing(bus_stop_code, self.api_key, explicit_buses,
                                                        no_exact_time=consolidated_timing, short_forms=consolidated_timing,
                                                        use_emojis=use_emojis)
        main_returner = []

        # if curr_stop_returner is None and arrival_returner is None:
        #     main_returner.append(f"No arrival time found for {bus_stop_code}.")
        #     return main_returner


        print(curr_stop_returner)


        if curr_stop_returner[2]:
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
            svc_info_returner = self.return_bus_svc_json(arrival_data[0], 1)

            if svc_info_returner[4] != arrival_data[18] and svc_info_returner[5] != arrival_data[19]:
                svc_info_returner = self.return_bus_svc_json(arrival_data[0], 2)

            if svc_info_returner[7] is False:
                svc_info = f"{self.return_bus_stop_name_json(svc_info_returner[4])[0]} >>> " \
                           f"{self.return_bus_stop_name_json(svc_info_returner[5])[0]} " \
                           f"[{svc_info_returner[3]}]"

            elif svc_info_returner[7] is True:
                svc_info = f"Loop @ {svc_info_returner[6]} to " \
                           f"{self.return_bus_stop_name_json(svc_info_returner[5])[0]} " \
                           f"[{svc_info_returner[3]}]"

            else:
                svc_info = f"This service does not exist."

            print(
                f"Service [{arrival_data[0]}] | {arrival_data[1]}\n"
                f"{svc_info}\n"
                f"=======================================================================================\n"
                f'{arrival_data[2]} | {arrival_data[5]} | {arrival_data[8]} | Visit: {arrival_data[11]} | Accurate: {arrival_data[20]}\n'
                f'{arrival_data[3]} | {arrival_data[6]} | {arrival_data[9]} | Visit: {arrival_data[12]} | Accurate: {arrival_data[21]}\n'
                f'{arrival_data[4]} | {arrival_data[7]} | {arrival_data[10]} | Visit: {arrival_data[13]} | Accurate: {arrival_data[22]}\n'
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

    def request_bus_stop_svc_list(self, bus_stop_code: str):
        returner = ""

        # Noted that no bus services will list on end of service - Write new method and deprecate old method
        # svc_returner = request_bus_stop_timing(bus_stop_code=bus_stop_code, api_key=self.api_key, svc_num=[],
        #                                        return_svc_list=True)

        svc_returner = self.get_bus_svc_from_bus_stop_code(bus_stop_code)

        for i in range(len(svc_returner)):
            if i == 0:
                returner = str(svc_returner[i])
            else:
                returner += f", {svc_returner[i]}"

        return returner

    # Bus Arrival Functions
    def interpret_seating(self, seating: str, use_emoji: bool = False, retain_sf: bool = False):
        for seating_data in self.SEATING:
            if seating == seating_data[0]:
                if use_emoji:
                    return seating_data[2]
                elif not retain_sf:
                    return seating_data[1]
                else:
                    return seating_data[0]
        return ""

    def interpret_type(self, bus_type: str, retain_sf: bool = False):
        for type_data in self.BUS_TYPE:
            if bus_type == type_data[0]:
                if not retain_sf:
                    return type_data[1]
                else:
                    return type_data[0]
        return ""

    @staticmethod
    def calculate_est_duration(dur_list: list):
        divisive_num = 0
        total_dur = 0

        for dur in dur_list:
            if 0 < dur < 1000:
                divisive_num += 1
                total_dur += dur

        if divisive_num == 0:
            return total_dur

        est_duration = total_dur / divisive_num

        return round(est_duration, 1)

    def request_bus_stop_timing(self, bus_stop_code: int | str, api_key: str, svc_num: list,
                                fallback_header: bool = False, debug: bool = False, return_svc_list: bool = False,
                                no_exact_time=False, short_forms=False, use_emojis=False):
        """
        Core Function to get and return the Timings of Services for a Bus Stop.
        For a specific number in Services, define the Service Number.
        :param bus_stop_code: The 5-digit Bus Stop code. Should be in string, integer not recommended for it may remove
                              leading zeros.
        :param api_key: The API Key to allow calling of API services.
        :param svc_num: A list of Bus Service Numbers to explicitly see. Optional, either string or integer is accepted in a
                        list.
        :param fallback_header: A boolean state that determines whether the fallback header should be used. (Shows the code)
        :param debug: A boolean state to show debug text
        :param return_svc_list: Returns the Bus Services for the bus stop, WILL NOT RETURN TIMING!
        :param no_exact_time: Boolean parameter to disallow the showing of exact timing for arrivals
        :param short_forms: Show short forms of certain texts
        :param use_emojis: Boolean parameter to use emoji for certain texts
        :return: A Tuple of 23 values (exc. !):
                 [0] -> Service Number,
                 [1] -> Service Operator,
                 [2] -> First Bus Timing in XX min @ XX:XX:XX,
                 [3] -> Second Bus Timing in XX min @ XX:XX:XX,
                 [4] -> Third Bus Timing in XX min @ XX:XX:XX,
                 [5] -> First Bus Seating Availability,
                 [6] -> Second Bus Seating Availability,
                 [7] -> Third Bus Seating Availability,
                 [8] -> First Bus Type,
                 [9] -> Second Bus Type,
                 [10] -> Third Bus Type,
                 [11] -> First Bus Visit Status,
                 [12] -> Second Bus Visit Status,
                 [13] -> Third Bus Visit Status,
                 [14] -> Estimated Duration for all 3 buses,
                 [15] -> Estimated Duration for 1st Visit Buses,
                 [16] -> Estimated Duration for 2nd Visit Buses,
                 [17] -> Boolean State to state whether all buses are on 1st Visit only,
                 [18] -> Origin Bus Stop,
                 [19] -> Destination Bus Stop,
                 [20] -> First Bus Timing Accuracy
                 [21] -> Second Bus Timing Accuracy
                 [22] -> Third Bus Timing Accuracy
                 [!] -> Note: For 14 to 17, bool state is to be used to determine on which type of duration(s) to be shown.
        """
        # URL Construct
        url = f"https://datamall2.mytransport.sg/ltaodataservice/v3/BusArrival?BusStopCode={bus_stop_code}"

        # Service Specific Addition - To use sep. method instead
        # if svc_num != "":
        #     URL += f"&ServiceNo={svc_num}"

        # Header Data
        headers = {
            "AccountKey": api_key,
            "accept": "application/json"
        }

        request = urllib.request.Request(url=url, method="GET", headers=headers)

        dt = datetime.datetime.now()
        bus_list = []
        bus_stop_list = []
        try:
            with urllib.request.urlopen(request) as response:
                json_data = response.read().decode("utf-8")
                dict_data = JSONHandler.json_load(json_data)

                # Sort Numbers in Ascending Order
                for bus_svc in dict_data["Services"]:
                    bus_list.append(bus_svc["ServiceNo"])

                bus_list = self.sort_bus_svc_list(bus_list)

                # print(bus_list)
                if return_svc_list:
                    print(bus_list)
                    return bus_list

                if fallback_header and debug:
                    print(
                        f"=======================================================================================\n"
                        f"Bus Stop No: {bus_stop_code} Services\n"
                        f"======================================================================================="
                    )

                # for bus_svc in dict_data["Services"]:
                for bus_ref in bus_list:
                    # Should there be an explicit to see list of bus stop numbers
                    # i.e. 3 to be seen from 3, 34, ...
                    if len(svc_num) > 0:
                        for svc_check in svc_num:
                            svc_check_test = False

                            print(f"CHECK: {svc_check} VS {bus_ref}")

                            if svc_check == str(bus_ref):
                                svc_check_test = True
                                break

                        if not svc_check_test:
                            continue

                    search_svc = False

                    for svc in dict_data["Services"]:
                        if svc["ServiceNo"] == str(bus_ref):
                            search_svc = True
                            bus_svc = svc
                            break

                    if not search_svc:
                        continue

                    # Handle 1st Bus
                    if bus_svc["NextBus"]["EstimatedArrival"] != "":
                        nb_dt = bus_svc["NextBus"]["EstimatedArrival"].split("+")[0]
                        nb_date = nb_dt.split("T")[0].split("-")
                        nb_time = nb_dt.split("T")[1].split(":")

                        dt_nb = datetime.datetime(
                            day=int(nb_date[2]),
                            month=int(nb_date[1]),
                            year=int(nb_date[0]),
                            hour=int(nb_time[0]),
                            minute=int(nb_time[1]),
                            second=int(nb_time[2])
                        )

                        duration = round((dt_nb - dt).seconds / 60)
                        if duration < 1 or duration > 1000:
                            next_bus = "Arriving"
                            duration = 0
                        else:
                            next_bus = f"{duration} min"

                    else:
                        next_bus = "Not in Service"
                        nb_time = ["X", "X", "X"]
                        duration = -1

                    # Handle 2nd Bus
                    if bus_svc["NextBus2"]["EstimatedArrival"] != "":
                        nb_dt2 = bus_svc["NextBus2"]["EstimatedArrival"].split("+")[0]
                        nb_date2 = nb_dt2.split("T")[0].split("-")
                        nb_time2 = nb_dt2.split("T")[1].split(":")

                        dt_nb2 = datetime.datetime(
                            day=int(nb_date2[2]),
                            month=int(nb_date2[1]),
                            year=int(nb_date2[0]),
                            hour=int(nb_time2[0]),
                            minute=int(nb_time2[1]),
                            second=int(nb_time2[2])
                        )

                        duration2 = round((dt_nb2 - dt).seconds / 60)
                        if duration2 < 1 or duration2 > 1000:
                            next_bus2 = "Arriving"
                            duration2 = 0
                        else:
                            next_bus2 = f"{duration2} min"

                    else:
                        next_bus2 = "Not in Service"
                        nb_time2 = ["X", "X", "X"]
                        duration2 = -1

                    # Handle 3rd Bus
                    if bus_svc["NextBus3"]["EstimatedArrival"] != "":
                        nb_dt3 = bus_svc["NextBus3"]["EstimatedArrival"].split("+")[0]
                        nb_date3 = nb_dt3.split("T")[0].split("-")
                        nb_time3 = nb_dt3.split("T")[1].split(":")

                        dt_nb3 = datetime.datetime(
                            day=int(nb_date3[2]),
                            month=int(nb_date3[1]),
                            year=int(nb_date3[0]),
                            hour=int(nb_time3[0]),
                            minute=int(nb_time3[1]),
                            second=int(nb_time3[2])
                        )

                        duration3 = round((dt_nb3 - dt).seconds / 60)
                        if duration3 < 1 or duration3 > 1000:
                            next_bus3 = "Arriving"
                            duration3 = 0
                        else:
                            next_bus3 = f"{duration3} min"

                    else:
                        next_bus3 = "Not in Service"
                        nb_time3 = ["X", "X", "X"]
                        duration3 = -1

                    # Deal with Post-Time Buses
                    if duration3 < 0 or duration3 is None:
                        # Remove 3rd bus
                        next_bus3 = "Not in Service"
                        nb_time3 = ["X", "X", "X"]
                        duration3 = 0
                        bus_svc['NextBus3']['Load'] = ""
                        bus_svc['NextBus3']['Type'] = ""
                        bus_svc['NextBus3']['VisitNumber'] = ""

                    if duration2 < 0 or duration2 is None:
                        # Move 3rd bus to 2nd
                        duration2 = duration3
                        next_bus2 = next_bus3
                        nb_time2 = nb_time3
                        bus_svc['NextBus2']['Load'] = bus_svc['NextBus3']['Load']
                        bus_svc['NextBus2']['Type'] = bus_svc['NextBus3']['Type']
                        bus_svc['NextBus2']['VisitNumber'] = bus_svc['NextBus3']['VisitNumber']

                        # Remove 3rd bus
                        next_bus3 = "Not in Service"
                        nb_time3 = ["X", "X", "X"]
                        duration3 = 0
                        bus_svc['NextBus3']['Load'] = ""
                        bus_svc['NextBus3']['Type'] = ""
                        bus_svc['NextBus3']['VisitNumber'] = ""

                    if duration < 0 or duration is None:
                        # Move 2nd bus to 1st
                        duration = duration2
                        next_bus = next_bus2
                        nb_time = nb_time2
                        bus_svc['NextBus']['Load'] = bus_svc['NextBus2']['Load']
                        bus_svc['NextBus']['Type'] = bus_svc['NextBus2']['Type']
                        bus_svc['NextBus']['VisitNumber'] = bus_svc['NextBus2']['VisitNumber']

                        # Remove 2nd bus
                        next_bus2 = "Not in Service"
                        nb_time2 = ["X", "X", "X"]
                        duration2 = 0
                        bus_svc['NextBus2']['Load'] = ""
                        bus_svc['NextBus2']['Type'] = ""
                        bus_svc['NextBus2']['VisitNumber'] = ""

                    # Estimation of Durations
                    if (bus_svc['NextBus']['VisitNumber'] == "1" or bus_svc['NextBus']['VisitNumber'] == "") and \
                            (bus_svc['NextBus2']['VisitNumber'] == "1" or bus_svc['NextBus2']['VisitNumber'] == "") and \
                            (bus_svc['NextBus3']['VisitNumber'] == "1" or bus_svc['NextBus3']['VisitNumber'] == ""):
                        one_visit = True
                        est_dur = self.calculate_est_duration([duration, duration2, duration3])
                        est_dur_1 = 0
                        est_dur_2 = 0
                    else:
                        one_visit = False
                        visit_1 = []
                        visit_2 = []

                        for i in range(1, 4):
                            if i == 1:
                                key_ref = 'NextBus'
                                dur = duration
                            else:
                                key_ref = f'NextBus{i}'

                                if i == 2:
                                    dur = duration2
                                else:
                                    dur = duration3

                            if bus_svc[key_ref]['VisitNumber'] == "1":
                                visit_1.append(dur)
                            else:
                                visit_2.append(dur)

                        if len(visit_1) < 3:
                            for i in range(3 - len(visit_1)):
                                visit_1.append(0)

                        if len(visit_2) < 3:
                            for i in range(3 - len(visit_2)):
                                visit_2.append(0)

                        est_dur = 0
                        est_dur_1 = self.calculate_est_duration([visit_1[0], visit_1[1], visit_1[2]])
                        est_dur_2 = self.calculate_est_duration([visit_2[0], visit_2[1], visit_2[2]])

                    if debug:
                        print(
                            f"Service [{bus_svc['ServiceNo']}] | {bus_svc['Operator']}\n"
                            f"=======================================================================================\n"
                            f"1. {next_bus} @ {nb_time[0]}:{nb_time[1]}:{nb_time[2]} ({bus_svc['NextBus']['EstimatedArrival']})"
                            f" | {self.interpret_seating(bus_svc['NextBus']['Load'])} | {self.interpret_type(bus_svc['NextBus']['Type'])}"
                            f" | Visit: {bus_svc['NextBus']['VisitNumber']} | Accurate: {bool(bus_svc['NextBus']['Monitored'])}\n"
                            f"2. {next_bus2} @ {nb_time2[0]}:{nb_time2[1]}:{nb_time2[2]} "
                            f"({bus_svc['NextBus2']['EstimatedArrival']}) | {self.interpret_seating(bus_svc['NextBus2']['Load'])} | "
                            f"{self.interpret_type(bus_svc['NextBus2']['Type'])}"
                            f" | Visit: {bus_svc['NextBus2']['VisitNumber']} | Accurate: {bool(bus_svc['NextBus']['Monitored'])}\n"
                            f"3. {next_bus3} @ {nb_time3[0]}:{nb_time3[1]}:{nb_time3[2]} "
                            f"({bus_svc['NextBus3']['EstimatedArrival']}) | {self.interpret_seating(bus_svc['NextBus3']['Load'])} | "
                            f"{self.interpret_type(bus_svc['NextBus3']['Type'])}"
                            f" | Visit: {bus_svc['NextBus3']['VisitNumber']} | Accurate: {bool(bus_svc['NextBus']['Monitored'])}\n"
                        )

                        print(
                            f"Estimated Duration: {est_dur} mins" if one_visit is True else
                            f"Estimated Duration (Visit 1): {est_dur_1} mins\nEstimated Duration (Visit 2): {est_dur_2} mins"
                        )

                        print(
                            f"======================================================================================="
                        )

                    # Append Compiled Data
                    bus_stop_list.append(
                        (
                            bus_svc['ServiceNo'],  # [0]
                            bus_svc['Operator'],  # [1]
                            f"{next_bus} @ {nb_time[0]}:{nb_time[1]}:{nb_time[2]}" if no_exact_time is False  # [2]
                            else f"{next_bus}",  # [2]
                            f"{next_bus2} @ {nb_time2[0]}:{nb_time2[1]}:{nb_time2[2]}" if no_exact_time is False  # [3]
                            else f"{next_bus2}",  # [3]
                            f"{next_bus3} @ {nb_time3[0]}:{nb_time3[1]}:{nb_time3[2]}" if no_exact_time is False  # [4]
                            else f"{next_bus3}",  # [4]
                            self.interpret_seating(bus_svc['NextBus']['Load'], use_emojis, short_forms),  # [5]
                            self.interpret_seating(bus_svc['NextBus2']['Load'], use_emojis, short_forms),  # [6]
                            self.interpret_seating(bus_svc['NextBus3']['Load'], use_emojis, short_forms),  # [7]
                            self.interpret_type(bus_svc['NextBus']['Type'], short_forms),  # [8]
                            self.interpret_type(bus_svc['NextBus2']['Type'], short_forms),  # [9]
                            self.interpret_type(bus_svc['NextBus3']['Type'], short_forms),  # [10]
                            bus_svc['NextBus']['VisitNumber'] if bus_svc['NextBus']['VisitNumber'] != "" else "X",  # [11]
                            bus_svc['NextBus2']['VisitNumber'] if bus_svc['NextBus2']['VisitNumber'] != "" else "X",  # [12]
                            bus_svc['NextBus3']['VisitNumber'] if bus_svc['NextBus3']['VisitNumber'] != "" else "X",  # [13]
                            est_dur,  # [14]
                            est_dur_1,  # [15]
                            est_dur_2,  # [16]
                            one_visit,  # [17]
                            bus_svc['NextBus']['OriginCode'],  # [18]
                            bus_svc['NextBus']['DestinationCode'],  # [19]
                            bool(bus_svc['NextBus']['Monitored']),  # [20]
                            bool(bus_svc['NextBus2']['Monitored']),  # [21]
                            bool(bus_svc['NextBus3']['Monitored'])  # [22]
                        )
                    )

                return bus_stop_list

        except URLError as e:
            if hasattr(e, "code") and hasattr(e, "reason"):
                # HTTP Error Code + Reason
                msg = f"[{e.code} | {e.reason}] Error connecting to LTA DataMall API Service"
                print(msg)
                return msg

            elif hasattr(e, "reason"):
                # HTTP Error Reason
                msg = f"[{e.reason}] Error connecting to LTA DataMall API Service"
                print(msg)

            else:
                # Exception Error Dump
                msg = f"[{e}] Error connecting to LTA DataMall API Service"
                print(msg)
                return msg

    # Bus Stop Info Functions
    def request_bus_stop_name(self, bus_stop_code: int | str, api_key: str, debug: bool = False):
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
                    dict_data = JSONHandler.json_load(json_dict)

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

                # Fallback
                query = list(self.return_bus_stop_name_json(bus_stop_code))

                query.append(True)

                return tuple(query)

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

                return self.return_bus_stop_name_json(bus_stop_code)

    def store_bus_stop_data(self, api_key: str):
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
                    dict_data = self.bus_stop_data.json_load(json_dict)

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

                return None

        self.bus_stop_data.update_json(curr_data)
        self.bus_stop_data.update_json_file()
        self.bus_stop_data.formulate_json()
        return None

    def return_bus_stop_name_json(self, bus_stop_code: str):
        for data in self.bus_stop_data.return_specific_json("value"):
            if data["BusStopCode"] == bus_stop_code:
                return (
                    data["Description"],
                    data["RoadName"]
                )

        return None

    def request_bus_stop_code_from_name(self, stop_name: str, road_name: str = "", return_first_val: bool = False):
        matched_values = []

        for data in self.bus_stop_data.return_specific_json("value"):
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

    def get_nearby_bus_stops(self, lon: float, lat: float):
        nearby_stops = []
        sorted_nearby_stops = []
        disp_sorter = []

        lon_m = lon * self.LON_LAT_CONV
        lat_m = lat * self.LON_LAT_CONV

        for data in self.bus_stop_data.return_specific_json("value"):
            bus_lon_m = data["Longitude"] * self.LON_LAT_CONV
            bus_lat_m = data["Latitude"] * self.LON_LAT_CONV

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

    # Bus Service Functions
    @staticmethod
    def request_bus_svc_info(svc: str, direction: int, api_key: str):
        """
        Gets and returns information of the bus service. Does not cover bus route.

        :param svc: The Service Number
        :param direction: The service direction, either 1 or 2. For loops, use 1.
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
            url = f"https://datamall2.mytransport.sg/ltaodataservice/BusServices?$skip={skip_val}"

            headers = {
                "AccountKey": api_key,
                "accept": "application/json"
            }

            request = urllib.request.Request(url=url, headers=headers, method="GET")

            try:
                with urllib.request.urlopen(request) as response:
                    json_dict = response.read().decode("utf-8")
                    dict_data = JSONHandler.json_load(json_dict)

                    for data in dict_data["value"]:
                        is_loop = False
                        if data["ServiceNo"] == svc and data["Direction"] == direction:

                            if data["Direction"] == 1 and data["LoopDesc"] != "":
                                is_loop = True

                            return (
                                data["ServiceNo"],
                                data["Operator"],
                                data["Direction"],
                                data["Category"],
                                data["OriginCode"],
                                data["DestinationCode"],
                                data["LoopDesc"],
                                is_loop
                            )

                    if len(dict_data["value"]) < 500:
                        return (
                            None,
                            None,
                            None,
                            None,
                            None,
                            None,
                            None,
                            None
                        )
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

                return None

    def store_bus_svc_data(self, api_key: str):
        curr_data = {"value": []}
        skip_val = 0
        while True:
            url = f"https://datamall2.mytransport.sg/ltaodataservice/BusServices?$skip={skip_val}"

            headers = {
                "AccountKey": api_key,
                "accept": "application/json"
            }

            request = urllib.request.Request(url=url, method="GET", headers=headers)
            try:
                with urllib.request.urlopen(request) as response:
                    json_dict = response.read().decode("utf-8")
                    dict_data = self.bus_svc_data.json_load(json_dict)

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

                return None

        self.bus_svc_data.update_json(curr_data)
        self.bus_svc_data.update_json_file()
        self.bus_svc_data.formulate_json()
        return None

    def return_bus_svc_json(self, svc: str, direction: int):
        for data in self.bus_svc_data.return_specific_json("value"):
            is_loop = False
            if data["ServiceNo"] == svc and data["Direction"] == direction:

                if data["Direction"] == 1 and data["LoopDesc"] != "":
                    is_loop = True

                for (k, v) in self.DBL_LOOP_DATA.items():
                    if k == data["ServiceNo"]:
                        data["LoopDesc"] = v

                return (
                    data["ServiceNo"],
                    data["Operator"],
                    data["Direction"],
                    data["Category"],
                    data["OriginCode"],
                    data["DestinationCode"],
                    data["LoopDesc"],
                    is_loop
                )

        return None

    def get_bus_svc_list(self):
        bus_svc_list = []
        for data in self.bus_svc_data.return_specific_json("value"):
            if data["ServiceNo"] not in bus_svc_list:
                bus_svc_list.append(data["ServiceNo"])

        return self.sort_bus_svc_list(bus_svc_list)

    @staticmethod
    def sort_bus_svc_list(svc_list: list):
        reg_num_svc = []
        sp_svc_list = []
        sep_sp_svc_list = {}
        final_svc_list = []

        for svc in svc_list:
            if svc.isdigit():
                reg_num_svc.append(int(svc))
                # print(f"APPEND {svc} to REG LIST")
            else:
                sp_svc_list.append(svc)
                # print(f"APPEND {svc} to SP LIST")

        reg_num_svc = sorted(reg_num_svc)

        for sp_svc in sp_svc_list:
            num = ""
            svc_uid = ""
            for i in sp_svc:
                if i.isdigit():
                    num += i
                else:
                    svc_uid += i

            sep_sp_svc_list[int(num)] = svc_uid

            # print(f"K: {num} V: {svc_uid}")

        for svc in reg_num_svc:
            if svc not in sep_sp_svc_list:
                final_svc_list.append(str(svc))
                # print(f"APPEND {svc} to LIST")
            else:
                final_svc_list.append(str(svc))
                # print(f"APPEND {svc} to LIST")

                final_svc_list.append(str(svc) + str(sep_sp_svc_list[svc]))
                # print(f"APPEND {str(svc) + str(sep_sp_svc_list[svc])} to LIST")

        return final_svc_list

    def get_bus_svc_directions(self, svc: str):
        bus_svc_list = []
        for data in self.bus_svc_data.return_specific_json("value"):
            # print(f"{data["ServiceNo"]} || {svc}")
            is_loop = False
            if data["ServiceNo"] == svc:

                if data["Direction"] == 1 and data["LoopDesc"] != "":
                    is_loop = True

                for (k, v) in self.DBL_LOOP_DATA.items():
                    if k == data["ServiceNo"]:
                        data["LoopDesc"] = v

                bus_svc_list.append((
                    data["ServiceNo"],
                    data["Direction"],
                    data["Category"],
                    data["OriginCode"],
                    data["DestinationCode"],
                    data["LoopDesc"],
                    is_loop
                ))

                # print(f"LEN: {len(bus_svc_list)}")

                if is_loop or len(bus_svc_list) == 2:
                    # print(F"EXIT FUNC: \n {bus_svc_list}")
                    return bus_svc_list

        return bus_svc_list

    # Bus Route Functions
    @staticmethod
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

            try:
                with urllib.request.urlopen(request) as response:
                    json_dict = response.read().decode("utf-8")
                    dict_data = JSONHandler.json_load(json_dict)
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
                                temp_route_dict[data["Direction"]][data["StopSequence"]] = (data["BusStopCode"],
                                                                                            data["Distance"])

                            else:
                                temp_route_dict[data["Direction"]] = {
                                    data["StopSequence"]: (data["BusStopCode"], data["Distance"])}

                            route_dict[data["ServiceNo"]] = temp_route_dict

                            # print(f"PROC: DIRECTION: {data['Direction']} | STOP: {data['StopSequence']} | BUS: {data['BusStopCode']} | DISTANCE: {data['Distance']}")

                    if len(dict_data["value"]) < 500:
                        break
                    else:
                        skip_val += 500

                    # print(f"PROC: SKIP: {skip_val}")

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

        # print(route_dict)

        return route_dict

    def store_bus_route_data(self, api_key: str):
        curr_data = {"value": []}
        skip_val = 0
        while True:
            url = f"https://datamall2.mytransport.sg/ltaodataservice/BusRoutes?$skip={skip_val}"

            headers = {
                "AccountKey": api_key,
                "accept": "application/json"
            }

            request = urllib.request.Request(url=url, method="GET", headers=headers)

            try:
                with urllib.request.urlopen(request) as response:
                    json_dict = response.read().decode("utf-8")
                    dict_data = self.bus_stop_data.json_load(json_dict)

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

                return None

            for data in dict_data["value"]:
                print(f"PROC: {data['ServiceNo']} | {data['Direction']} | {data['StopSequence']} | {data['BusStopCode']}")
                print(f"PROC: {type(data['ServiceNo'])} | {type(data['Direction'])} | {type(data['StopSequence'])} | {type(data['BusStopCode'])}")
                print(f"PROC: {data['ServiceNo']} not in bus_route_data.json_data: {data["ServiceNo"] not in self.bus_route_data.json_data}")

                # Create Entry if not Exist
                if data["ServiceNo"] not in self.bus_route_data.json_data:
                    print(f"PROC: CREATE FOR {data['ServiceNo']}")
                    self.bus_route_data.update_specific_json(
                        data["ServiceNo"],
                        {
                            str(data["Direction"]): {
                                str(data["StopSequence"]): (data["BusStopCode"], data["Distance"])
                            }
                        }
                    )
                    # print(f"PROC: DIRECTION: {data['Direction']} | STOP: {data['StopSequence']} | BUS: {data['BusStopCode']} | DISTANCE: {data['Distance']}")
                # Amend existing values
                else:
                    route_dict = self.bus_route_data.return_specific_json(data["ServiceNo"])
                    print(f"PROC: {data['ServiceNo']} | {data['Direction']}")
                    # print(f"{route_dict}")

                    print(f"PROC: {data['Direction']} in route_dict: {data["Direction"] in route_dict}")

                    if data["Direction"] in route_dict:
                        route_dict[str(data["Direction"])][str(data["StopSequence"])] = (data["BusStopCode"], data["Distance"])

                    else:
                        route_dict[str(data["Direction"])] = {str(data["StopSequence"]): (data["BusStopCode"], data["Distance"])}

                    self.bus_route_data.update_specific_json(data["ServiceNo"], route_dict)

                    # print(f"PROC: DIRECTION: {data['Direction']} | STOP: {data['StopSequence']} | BUS: {data['BusStopCode']} | DISTANCE: {data['Distance']}")

        # bus_route_data.update_json(curr_data)
        self.bus_route_data.update_json_file()
        self.bus_route_data.formulate_json()
        return None

    def get_bus_svc_route(self, svc: str, direction: str):
        return self.bus_route_data.return_specific_json(svc)[direction]

    def get_bus_svc_from_bus_stop_code(self, bus_stop_code: str):
        svc_list = []
        for svc, data in self.bus_route_data.return_json().items():
            for direction, dir_data in data.items():
                for stop, stop_data in dir_data.items():
                    if bus_stop_code in stop_data and svc not in svc_list:
                        svc_list.append(svc)
                        break

        return self.sort_bus_svc_list(svc_list)
