import os
import sys
import telebot
from dotenv import load_dotenv
from pathlib import Path
from telebot import types
from SettingsData import SETTINGS_DATA
from TelegramBotFuncs.KeyboardHandling import start_menu_keyboard,location_keyboard, option_keyboard, \
    get_option_number, filtering_keyboard, debug_keyboard
from TelegramBotFuncs.NameGetting import get_user_name
from TransportAPI.APIHandler import TransportAPIHandler
from TransportAPI.BusStopInfo import request_bus_stop_code_from_name, get_nearby_bus_stops, \
    return_bus_stop_name_json
from UtilLib.JSONHandler import JSONHandler
from UtilLib.Logging import LoggerClass

# ======================================================================================================================
# Logger
logger = LoggerClass("Main Module", "TwelfthDoctor1")

ENV_PATH = os.path.join(Path(__file__).resolve().parent, "RefKey.env")

# Load ENV
load_dotenv(dotenv_path=ENV_PATH)

# Get Values from ENV
API_KEY_TG = os.getenv("BOT_KEY")
API_KEY_LTA = os.getenv("API_KEY_LTA")
ENV_LIST = [API_KEY_LTA]

# API Handling & Data Caching
api_handler = TransportAPIHandler(API_KEY_LTA)


# Timed Caching Function
def cache_bus_stop_svc_data():
    """
    Function to run daily to cache data of bus services and stops.

    This ensures that data is always up-to-date.
    :return:
    """
    # Cache data
    api_handler.store_json_data()

    logger.info("Updated data for Bus stop and Services data.")


# Run Init Caching
cache_bus_stop_svc_data()

# Bot Class Var
bot = telebot.TeleBot(API_KEY_TG)

# TestValues
svc_filter_ran_once = False

# ======================================================================================================================
# JSON Memory Handling
json_mem = JSONHandler("MemoryData")
gen_state = json_mem.generate_json(dict())
json_mem.formulate_json()

# ======================================================================================================================
# Base Functions

def init_user_mem_data(username: str):
    if json_mem.json_data.get(f"{username}") is None:
        json_mem.add_json_entry(
            f"{username}",
            {
                "bus_mem": "",
                "favourites": [],
                "svc_mem": []
            }
        )
        json_mem.update_json_file()

def check_user_mem_data_exists(username: str):
    if json_mem.json_data.get(f"{username}") is None:
        init_user_mem_data(username)


# ======================================================================================================================
# Commands
@bot.message_handler(commands=["start"])
def bot_svc_start(message: types.Message):
    """
    Start command. Use to reset bot if stuck.
    :param message:
    :return:
    """

    init_user_mem_data(get_user_name(message))

    msg = "Welcome to the Bus Timings Telegram Bot.\n" \
          "To start, please type /query_timing or /search.\n\n" \
          "Program created by TwelfthDoctor1."
    bot.send_message(message.chat.id, msg, reply_markup=start_menu_keyboard(message))


@bot.message_handler(commands=["query_timing"])
def query_timing(message: types.Message):
    """
    Command to query timing of bus stop.

    This section requests for the bus stop.
    :param message:
    :return:
    """
    check_user_mem_data_exists(get_user_name(message))
    sent_msg = bot.send_message(
        message.chat.id,
        "Enter either the following to query bus timings:"
        "\n- 5-digit Bus Stop Code"
        "\n- Bus Stop Name and/or Road Name (i.e. Aft Blk 87 @ Zion Road OR Aft Blk 87)"
        "\n\nOr Send Location for nearby bus stops.",
        reply_markup=location_keyboard()
    )
    bot.register_next_step_handler(sent_msg, search_query_proc)


@bot.message_handler(commands=["filter"])
def filter_preface(message: types.Message):
    """
    Filter command to filter for buses.

    This section handles the filter command init.
    :param message:
    :return:
    """
    mem_dict = json_mem.return_specific_json(f"{get_user_name(message)}")

    # Check if there is no queried bus stop to disallow filtering
    if mem_dict["bus_mem"] == "":
        bot.send_message(
            message.chat.id,
            "You cannot filter for explicit buses if you have not queried for a bus timing. Please use /query_timing "
            "or /search instead.",
            reply_markup=start_menu_keyboard(message)
        )
        return None

    return bus_stop_selection(message, mem_dict["bus_mem"])


def bus_stop_selection(message: types.Message, bus_stop_code: str | list = ""):
    """
    Function to filter a bus stop from a list. (If any) Else, it will be passed through to filtering.
    :param message:
    :param bus_stop_code:
    :return:
    """
    msg = f"Bus Stops matching {bus_stop_code}\n"
    msg_data = []

    # User cancel
    if message.text == "/cancel" or message.text == "Cancel":
        bot.send_message(message.chat.id, "Action cancelled.", reply_markup=start_menu_keyboard(message))
        return

    # Assume bus stop code as message text if empty
    # Applicable to Query Timing function command
    if bus_stop_code == "":
        bus_stop_code = message.text

    # If bus stop is not an integer and not a list instance (list of bus stops)
    if not bus_stop_code.isdigit() and not isinstance(bus_stop_code, list):
        # Split from Name @ Road -> [Name, Road]
        bus_stop_info_data = bus_stop_code.split("@")

        # Trim Spacing (if any)
        for i in range(len(bus_stop_info_data)):
            bus_stop_info_data[i] = bus_stop_info_data[i].strip()

        # Get Bus Stop Code or list of codes from Name and/or Road
        if len(bus_stop_info_data) == 1:
            # If Name is given only, to get bus stop code or list of codes (if more than 1)
            bus_stop_code = request_bus_stop_code_from_name(bus_stop_info_data[0])
        else:
            # If Name and Road is given, to get bus stop code or list of codes (If more than 1, but unlikely)
            bus_stop_code = request_bus_stop_code_from_name(bus_stop_info_data[0], bus_stop_info_data[1])

    # Proceed to Filtering if Var is a string (no list)
    if isinstance(bus_stop_code, str):
        svc_filtering(message, bus_stop_code)

    # If Var is a list - Options
    elif isinstance(bus_stop_code, list):
        # Generate list of options for buttons
        for i in range(len(bus_stop_code)):
            msg += f"\n{i + 1}. {bus_stop_code[i][1]} @ {bus_stop_code[i][2]} [{bus_stop_code[i][0]}]"
            msg_data.append(f"{bus_stop_code[i][1]} @ {bus_stop_code[i][2]} [{bus_stop_code[i][0]}]")

        msg += "\n\nEnter the list number to view the bus timings for that bus stop or /cancel to stop filter: "

        # Send message of options
        sent_msg = bot.send_message(
            message.chat.id,
            msg,
            reply_markup=option_keyboard(msg_data, 1)
        )
        bot.register_next_step_handler(sent_msg, pre_filter_get_bus_stop, bus_stop_code, msg_data)


def pre_filter_get_bus_stop(message: types.Message, bus_stop_code, msg_data):
    """
    Function to get bus stop from selection and send it to filtering.
    :param message:
    :param bus_stop_code:
    :param msg_data:
    :return:
    """
    # User Cancel
    if message.text == "/cancel" or message.text == "Cancel":
        bot.send_message(message.chat.id, "Action cancelled.", reply_markup=start_menu_keyboard(message))
        return None

    # Option - Button
    elif message.text.startswith("["):
        opt_num = get_option_number(message.text, msg_data)
        return svc_filtering(message, bus_stop_code[int(opt_num) - 1][0])

    # Not an Integer
    elif not message.text.isdigit():
        bot.send_message(message.chat.id, "Unknown option. Please try again.")
        return bus_stop_selection(message, bus_stop_code)

    # Option out of range
    elif int(message.text) <= 0 or int(message.text) > len(bus_stop_code):
        bot.send_message(message.chat.id, "Option out of range. Please try again.")
        return bus_stop_selection(message, bus_stop_code)

    # Option - Raw Integer
    return svc_filtering(message, bus_stop_code[int(message.text) - 1][0])


def svc_filtering(message: types.Message, bus_stop_code: str = "", svc_filter: list | None = None):
    """
    Function to filter for an explicit group of services from the full list of services in a bus stop.
    :param message:
    :param bus_stop_code:
    :param svc_filter:
    :return:
    """
    # Request Service List
    svc_list = api_handler.request_bus_stop_svc_list(bus_stop_code)
    check_user_mem_data_exists(get_user_name(message))

    print(f"{svc_list} | {svc_filter}")

    if svc_filter is None:
        svc_filter = []

    # Show message of available services to be filtered
    bot.send_message(
        message.chat.id,
        "Enter the explicit bus services to see only. Otherwise leave 0 to see all services. (i.e.: 5, 12e, 46)",
        reply_markup=filtering_keyboard(svc_list, svc_filter)
    )

    sent_msg = bot.send_message(message.chat.id, f"Services:\n{svc_list}\n\nFilter: {','.join(svc_filter)}")
    bot.register_next_step_handler(sent_msg, post_svc_filtering, bus_stop_code, svc_filter)


def post_svc_filtering(message: types.Message, bus_stop_code, svc_filter: list | None = None):
    if message.text == "/cancel" or message.text == "Cancel":
        bot.send_message(message.chat.id, "Action cancelled.", reply_markup=start_menu_keyboard(message))
        # svc_filter = []
        return None

    # No Filter
    elif message.text == "No Filtering":
        return parse_data(message, bus_stop_code)

    elif message.text == "Done":
        svc_str = ", ".join(svc_filter)
        return parse_data(message, bus_stop_code, svc_str)

    svc_sel = message.text.split(",")
    mem_dict = json_mem.return_specific_json(f"{get_user_name(message)}")
    global svc_filter_ran_once
    if bus_stop_code != mem_dict["bus_mem"] and svc_filter_ran_once is False:
        svc_filter = []
        svc_filter_ran_once = True

    for svc in svc_sel:
        if svc.find("✅") != -1:
            svc = svc[0:svc.index("✅") - 1]
            svc_filter.remove(svc)
            continue

        if svc not in svc_filter:
            svc_filter.append(svc)
            svc_filter.sort()
        else:
            svc_filter.remove(svc)

    # Option - Raw Integer
    return svc_filtering(message, bus_stop_code, svc_filter)


def parse_data(message: types.Message, bus_stop_info: str, bus_svc_list_str: str = ""):
    """
    Function to parst bus stop and filter to return bus stop timing.
    :param message:
    :param bus_stop_info:
    :param bus_svc_list_str:
    :return:
    """
    # Get data of user based of name/username
    mem_dict = json_mem.return_specific_json(f"{get_user_name(message)}")

    # Init check settings data
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

    hide_cmd_list = mem_dict["settings"]["hide_cmd_list"]["data"]

    # User Cancel
    if message.text == "/cancel" or message.text == "Cancel":
        bot.send_message(message.chat.id, "Action cancelled.", reply_markup=start_menu_keyboard(message))
        return

    # If Var is an integer -> Bus Stop Code
    if bus_stop_info.isdigit():
        bus_stop_code = bus_stop_info

    # Else Var is string (fallback code)
    else:
        # Split from Name @ Road -> [Name, Road]
        bus_stop_info_data = bus_stop_info.split("@")

        # Trim Spacing (if any)
        for i in range(len(bus_stop_info_data)):
            bus_stop_info_data[i] = bus_stop_info_data[i].strip()

        # Get Bus Stop Code or list of codes from Name and/or Road
        # If Name is given only, to get bus stop code or list of codes (if more than 1)
        # If Name and Road is given, to get bus stop code or list of codes (If more than 1, but unlikely)
        bus_stop_code = request_bus_stop_code_from_name(
            bus_stop_info_data[0],
            "" if len(bus_stop_info_data) == 1 else bus_stop_info_data[1]
        )

    # Get Filter
    if bus_svc_list_str == "":
        bus_svc_list_str = message.text

    # No Filter - 0
    if bus_svc_list_str == "0" or bus_svc_list_str == "No Filtering":
        bus_svc_list = []
        mem_dict["svc_mem"] = []

    # If Var is a list
    elif isinstance(bus_svc_list_str, list):
        bus_svc_list = bus_svc_list_str
        mem_dict["svc_mem"] = bus_svc_list

    # Transform string to list
    else:
        bus_svc_list = bus_svc_list_str.split(",")

        for i in range(len(bus_svc_list)):
            bus_svc_list[i] = bus_svc_list[i].strip()

        mem_dict["svc_mem"] = bus_svc_list

    # Get Arrival Time
    mem_dict["bus_mem"] = bus_stop_code
    returner = api_handler.request_arrival_time(bus_stop_code, bus_svc_list, f"{get_user_name(message)}")

    # if len(returner) == 1:
    #     bot.send_message(message.chat.id, returner[0])
    #     return

    # Message Header
    bot.send_message(message.chat.id, returner[0], reply_markup=start_menu_keyboard(message))

    # Check condition if return only has 1 item (at least 2)
    if len(returner) == 1:
        return

    # Print Services by message
    for i in range(1, len(returner)):
        # No Services Available
        if isinstance(returner[i], str) and i == 1:
            bot.send_message(message.chat.id, returner[i])
            break

        # Send Service
        bot.send_message(
            message.chat.id,
            f"{returner[i][0]}\n{returner[i][1]}\n\n{returner[i][2]}\n{returner[i][3]}\n{returner[i][4]}\n"
            f"\n{returner[i][5]}"
        )

    # Send Message on Time Estimation & Bus Gaps
    bot.send_message(
        message.chat.id,
        "[EST] - Timing based on Schedule Timings, Bus not yet deployed or providing geolocation\n\n"
        "Noticed a big gap between different bus timings? It might be due to a bus that may not be tracked by the system or it could be a traffic related issue.\n"
        "If it is not a traffic related issue, consider using previously known duration times to plan your journey."
    )

    if hide_cmd_list is False:
        bot.send_message(
            message.chat.id,
            "List of Commands\n\nTo refresh: /refresh\nTo query: /query_timing\nTo search: /search\nTo filter: /filter"
            "\nTo clear: /clear"
        )

    # Save data to JSON Mem
    json_mem.update_specific_json(f"{get_user_name(message)}", mem_dict)
    json_mem.update_json_file()

    global svc_filter_ran_once
    svc_filter_ran_once = False


@bot.message_handler(commands=["refresh"])
def refresh_timings(message: types.Message):
    """
    Command function to refresh timings.
    :param message:
    :return:
    """
    # Get data from name/username
    mem_dict = json_mem.return_specific_json(f"{get_user_name(message)}")

    # Disallow if query memory is empty
    if mem_dict["bus_mem"] == "":
        bot.send_message(
            message.chat.id, "You have not queried for a bus timing. Please use /query_timing or /search instead.",
            reply_markup=start_menu_keyboard(message)
        )
        return

    # Request Timing
    parse_data(message, mem_dict["bus_mem"], mem_dict["svc_mem"])


@bot.message_handler(commands=["clear"])
def clear_mem(message: types.Message):
    """
    Command function to clear bus and service memory.
    :param message:
    :return:
    """
    # Get data from name/username
    mem_dict = json_mem.return_specific_json(f"{get_user_name(message)}")

    # Clear values
    mem_dict["bus_mem"] = ""
    mem_dict["svc_mem"] = []

    # Update config
    json_mem.update_specific_json(f"{get_user_name(message)}", mem_dict)
    json_mem.update_json_file()

    bot.send_message(
        message.chat.id,
        "Memory cleared. Please use /query_timing or /search to start again.",
        reply_markup=start_menu_keyboard(message)
    )


@bot.message_handler(commands=["search"])
def search_query(message: types.Message):
    """
    Command function to search for bus stop based on location.
    :param message:
    :return:
    """
    # Message with Send Location
    sent_msg = bot.send_message(
        message.chat.id, "Select the \"Send Location\" button to send your location, or use the \"Attachment\" button "
                         "to send a location. To exit, press \"Cancel\".",
        reply_markup=location_keyboard()
    )
    bot.register_next_step_handler(sent_msg, search_query_proc)


def search_query_proc(message: types.Message):
    """
    Function to process location coordinates to list nearby bus stops up to 500 metres in range
    :param message:
    :return:
    """
    msg_data = []
    # User cancel
    if message.text == "/cancel" or message.text == "Cancel":
        bot.send_message(message.chat.id, "Action cancelled.", reply_markup=start_menu_keyboard(message))
        return None

    if message.location is None:
        return bus_stop_selection(message, message.text)

    # Get location from message data
    lon = message.location.longitude
    lat = message.location.latitude

    # Get list of nearby stops from coordinates
    nearby_stops = get_nearby_bus_stops(lon, lat)

    msg = "Nearby Bus Stops\n"

    # No Nearby Stops
    if len(nearby_stops) == 0:
        msg += f"\nNo nearby Bus Stops."

    # >=1 Stops Nearby
    else:
        for i in range(len(nearby_stops)):
            msg += f"\n{i + 1}. {nearby_stops[i][2]} @ {nearby_stops[i][1]} [{nearby_stops[i][0]}] " \
                   f"({nearby_stops[i][3]} m)"
            msg_data.append(
                f"{nearby_stops[i][2]} @ {nearby_stops[i][1]} [{nearby_stops[i][0]}] ({nearby_stops[i][3]} m)"
            )

        msg += "\n\nEnter the list number to view the bus timings for that bus stop or /cancel to stop: "

    sent_msg = bot.send_message(message.chat.id, msg, reply_markup=option_keyboard(msg_data, 1))

    return bot.register_next_step_handler(sent_msg, post_search_query, nearby_stops, msg_data)


def post_search_query(message: types.Message, nearby_stops: list, msg_data):
    """
    Function to handle search query option
    :param message:
    :param nearby_stops:
    :param msg_data:
    :return:
    """
    # User Cancel
    if message.text == "/cancel" or message.text == "Cancel":
        bot.send_message(message.chat.id, "Action cancelled.", reply_markup=start_menu_keyboard(message))
        return None

    # Option - Button
    elif message.text.startswith("["):
        opt_num = get_option_number(message.text, msg_data)
        return bus_stop_selection(message, nearby_stops[int(opt_num) - 1][0])

    # Not an Integer
    elif not message.text.isdigit():
        bot.send_message(message.chat.id, "Unknown option. Please try again.")
        return search_query(message)

    # Option out of range
    elif int(message.text) <= 0 or int(message.text) > len(nearby_stops):
        bot.send_message(message.chat.id, "Option out of range. Please try again.")
        return search_query(message)

    # Option - Raw Integer
    return bus_stop_selection(message, nearby_stops[int(message.text) - 1][0])


@bot.message_handler(commands=["add_to_favourites"])
def add_to_favourites(message: types.Message):
    """
    Command Option to add current query into list of favourites
    :param message:
    :return:
    """
    # Get data from name/username
    mem_dict = json_mem.return_specific_json(f"{get_user_name(message)}")

    # Disallow if no queries in memory
    if mem_dict["bus_mem"] == "":
        bot.send_message(
            message.chat.id, "You have not queried for a bus timing. Please use /query_timing or /search instead.",
            reply_markup=start_menu_keyboard(message)
        )
        return

    # Save to Favourites
    if mem_dict.get("favourites") is not None:
        mem_dict["favourites"].append([mem_dict["bus_mem"], mem_dict["svc_mem"]])

    # Create KV and Save to Favourites
    else:
        mem_dict["favourites"] = [[mem_dict["bus_mem"], mem_dict["svc_mem"]]]

    # Update config
    json_mem.update_specific_json(f"{get_user_name(message)}", mem_dict)
    json_mem.update_json_file()

    bot.send_message(
        message.chat.id,
        "The current bus timing query has been added to favourites.",
        reply_markup=start_menu_keyboard(message)
    )


@bot.message_handler(commands=["favourites"])
def list_favourites(message: types.Message):
    """
    Command option to query timing from a favourite query
    :param message:
    :return:
    """
    msg_data = []
    mem_dict = json_mem.return_specific_json(f"{get_user_name(message)}")

    # Disallow empty/non existent favourites list
    if mem_dict.get("favourites") is None or mem_dict.get("favourites") == []:
        bot.send_message(
            message.chat.id, "No favourite bus timing queries.",
            reply_markup=start_menu_keyboard(message)
        )
        return

    msg = "Bus Timing Favourites\n"

    # Generate options
    for i in range(len(mem_dict["favourites"])):
        msg += f"\n{i + 1}. {return_bus_stop_name_json(mem_dict['favourites'][i][0])[0]} | " \
               f"{str(', ').join(mem_dict['favourites'][i][1])}"
        msg_data.append(
            f"{return_bus_stop_name_json(mem_dict['favourites'][i][0])[0]} | "
            f"{str(', ').join(mem_dict['favourites'][i][1])}"
        )

    msg += f"\n\nEnter the list number to view the bus timings for that bus stop or /cancel to stop: "

    sent_msg = bot.send_message(
        message.chat.id,
        msg,
        reply_markup=option_keyboard(msg_data, 1)
    )

    bot.register_next_step_handler(sent_msg, fav_post_proc, mem_dict["favourites"], msg_data)


def fav_post_proc(message: types.Message, fav_list, msg_data):
    """
    Function to handle Favourites Option
    :param message:
    :param fav_list:
    :param msg_data:
    :return:
    """
    # User Cancel
    if message.text == "/cancel" or message.text == "Cancel":
        bot.send_message(message.chat.id, "Action cancelled.", reply_markup=start_menu_keyboard(message))
        return None

    # Option - Button
    elif message.text.startswith("["):
        opt_num = get_option_number(message.text, msg_data)
        return parse_data(message, fav_list[int(opt_num) - 1][0], fav_list[int(opt_num) - 1][1])

    # Not an Integer
    elif not message.text.isdigit():
        bot.send_message(message.chat.id, "Unknown option. Please try again.")
        return list_favourites(message)

    # Option out of range
    elif int(message.text) <= 0 or int(message.text) > len(fav_list):
        bot.send_message(message.chat.id, "Option out of range. Please try again.")
        return list_favourites(message)

    # Option - Raw Integer
    return parse_data(message, fav_list[int(message.text) - 1][0], fav_list[int(message.text) - 1][1])


@bot.message_handler(commands=["delete_from_favourites"])
def delete_favourites_list(message: types.Message):
    """
    Command Function to delete selected favourite query
    :param message:
    :return:
    """
    msg_data = []
    mem_dict = json_mem.return_specific_json(f"{get_user_name(message)}")

    # Disallow empty/non existent favourites list
    if mem_dict.get("favourites") is None or len(mem_dict["favourites"]) == 0:
        bot.send_message(
            message.chat.id, "No favourite bus timing queries.", start_menu_keyboard(message)
        )
        return

    msg = "Bus Timing Favourites\n"

    # Generate option list
    for i in range(len(mem_dict["favourites"])):
        msg += f"\n{i + 1}. {return_bus_stop_name_json(mem_dict['favourites'][i][0])[0]} | " \
               f"{str(', ').join(mem_dict['favourites'][i][1])}"
        msg_data.append(
            f"{return_bus_stop_name_json(mem_dict['favourites'][i][0])[0]} | "
            f"{str(', ').join(mem_dict['favourites'][i][1])}"
        )

    msg += f"\n\nEnter the list number to delete that bus timing for that bus stop or /cancel to stop: "

    sent_msg = bot.send_message(message.chat.id, msg, reply_markup=option_keyboard(msg_data, 1))

    bot.register_next_step_handler(sent_msg, del_fav_proc, mem_dict["favourites"], msg_data)


def del_fav_proc(message: types.Message, fav_list, msg_data):
    """
    Function to handle option and deletion of favourite
    :param message:
    :param fav_list:
    :param msg_data:
    :return:
    """
    pos = -1
    # User Cancel
    if message.text == "/cancel" or message.text == "Cancel":
        bot.send_message(message.chat.id, "Action cancelled.", reply_markup=start_menu_keyboard(message))
        return None

    # Option - Button
    elif message.text.startswith("["):
        opt_num = get_option_number(message.text, msg_data)
        pos = int(opt_num) - 1

    # Not an integer
    elif not message.text.isdigit():
        bot.send_message(message.chat.id, "Unknown option. Please try again.")
        return delete_favourites_list(message)

    # Option out of range
    elif int(message.text) <= 0 or int(message.text) > len(fav_list):
        bot.send_message(message.chat.id, "Option out of range. Please try again.")
        return delete_favourites_list(message)

    # Option - Raw Integer
    if pos <= -1:
        pos = int(message.text) - 1

    # Get data from name/username
    mem_dict = json_mem.return_specific_json(f"{get_user_name(message)}")

    # Remove specified favourite from position
    mem_dict["favourites"].pop(pos)

    # Update config
    json_mem.update_specific_json(f"{get_user_name(message)}", mem_dict)
    json_mem.update_json_file()

    return bot.send_message(
        message.chat.id,
        "The selected bus timing has been deleted from favourites.",
        reply_markup=start_menu_keyboard(message)
    )


@bot.message_handler(commands=["refresh_cache"])
def refresh_cache(message: types.Message):
    """
    Command Function to refresh cache
    :param message:
    :return:
    """
    if get_user_name(message) != "TwelfthDoctor1":
        bot.send_message(message.chat.id, "Ineligible perms.")
        return

    cache_bus_stop_svc_data()

    bot.send_message(message.chat.id, "Updated Bus Stop and Service data.")


@bot.message_handler(commands=["settings"])
def settings_init(message: types.Message):
    msg_data = []
    # Get data from name/username
    mem_dict = json_mem.return_specific_json(f"{get_user_name(message)}")

    # Init Settings Data
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

    # Update config
    json_mem.update_specific_json(f"{get_user_name(message)}", mem_dict)
    json_mem.update_json_file()

    msg = "Settings List\n"

    # Generate options
    for k, v in mem_dict["settings"].items():
        msg += f"\n{v['name']} -> {v['data']}"

        msg_data.append(v['name'])

    msg += f"\n\nEnter the setting name to change the value of that setting: "

    sent_msg = bot.send_message(
        message.chat.id,
        msg,
        reply_markup=option_keyboard(msg_data, 1)
    )

    bot.register_next_step_handler(sent_msg, proc_handle_setting, msg_data)


def proc_handle_setting(message: types.Message, msg_data):
    key = ""
    # User Cancel
    if message.text == "/cancel" or message.text == "Cancel":
        bot.send_message(message.chat.id, "Action cancelled.", reply_markup=start_menu_keyboard(message))
        return None

    # Option - Button
    elif message.text.startswith("["):
        opt_num = get_option_number(message.text, msg_data)
        key_text = msg_data[int(opt_num) - 1]

    # Not string
    elif not isinstance(message.text, str):
        bot.send_message(message.chat.id, "Unknown option. Please try again.")
        return delete_favourites_list(message)

    # Option - Raw Text
    else:
        key_text = message.text

    # Get data from name/username
    mem_dict = json_mem.return_specific_json(f"{get_user_name(message)}")

    # Get Key Name
    for k, v in mem_dict["settings"].items():
        if v["name"] == key_text:
            key = k
            break

    if key == "":
        bot.send_message(
            message.chat.id,
            "Unknown key, please enter a correct key.",
            reply_markup=start_menu_keyboard(message)
        )

    # Update Setting Value
    mem_dict["settings"][key]["data"] = not mem_dict["settings"][key]["data"]

    # Update config
    json_mem.update_specific_json(f"{get_user_name(message)}", mem_dict)
    json_mem.update_json_file()

    return bot.send_message(
        message.chat.id,
        f"The setting [{mem_dict['settings'][key]['name']}] has been changed.",
        reply_markup=start_menu_keyboard(message)
    )


@bot.message_handler(commands=["debug"])
def debug_mode_main(message: types.Message):
    if get_user_name(message) != "TwelfthDoctor1":
        return

    msg = "Debug Mode\n"

    # msg_data = []

    msg += f"\n\nSelect debug action: "

    sent_msg = bot.send_message(
        message.chat.id,
        msg,
        reply_markup=debug_keyboard()
    )

    bot.register_next_step_handler(sent_msg, debug_mode_proc)


def debug_mode_proc(message: types.Message):
    # User Cancel
    if message.text == "/cancel" or message.text == "Cancel":
        bot.send_message(message.chat.id, "Action cancelled.", reply_markup=start_menu_keyboard(message))
        return

    elif message.text == "Formulate JSON":
        json_mem.formulate_json()
        bot.send_message(message.chat.id, "Formulated JSON.", reply_markup=start_menu_keyboard(message))
        return

    elif message.text == "Refresh Cache":
        refresh_cache(message)
        bot.send_message(message.chat.id, "Refreshed Transport Data Caches.", reply_markup=start_menu_keyboard(message))
        return

    elif message.text == "Shutdown":
        bot.send_message(message.chat.id, "Shutting down...", reply_markup=start_menu_keyboard(message))
        sys.exit("SHUTDOWN - INITIATED BY COMMAND")

    # elif message.text == "Restart":
    #     bot.send_message(message.chat.id, "Restarting...", reply_markup=start_menu_keyboard(message))
    #     subprocess.call([sys.executable, os.path.realpath(__file__)] + sys.argv[1:])


@bot.message_handler(func=lambda message: True)
def kb_text_redirect(message: types.Message):
    """
    Detection Function to handle Option texts and redirect them to various command functions
    :param message:
    :return:
    """
    if message.text == "Query Timing":
        return query_timing(message)
    elif message.text == "Search":
        return search_query(message)
    elif message.text == "Refresh":
        return refresh_timings(message)
    elif message.text == "Filter":
        return filter_preface(message)
    elif message.text == "Clear":
        return clear_mem(message)
    elif message.text == "Add to Favourites":
        return add_to_favourites(message)
    elif message.text == "Favourites":
        return list_favourites(message)
    elif message.text == "Delete from Favourites":
        return delete_favourites_list(message)
    elif message.text == "Settings":
        return settings_init(message)
    elif message.text == "Debug Mode":
        return debug_mode_main(message)
    else:
        return None


# ======================================================================================================================
# Start Bot and detect commands
bot.infinity_polling()
