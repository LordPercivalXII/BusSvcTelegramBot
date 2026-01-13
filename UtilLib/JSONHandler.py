import os
from pathlib import Path
from UtilLib.JSONParser import json_load, json_dump
from UtilLib.Logging import LoggerClass

# Filepath to hold the JSON File
JSON_LIB = os.path.join(Path(__file__).resolve().parent.parent, "JSONLib")


class JSONHandler:
    """
    JSONHandler

    A class that is able to acquire JSON data from GitHub or from JSONLib.
    """
    def __init__(self, json_data_name: str, json_dir: Path | str = ""):
        """
        Initialise JSONHandler to acquire data.
        :param json_data_name: Name of JSON File, without .json suffix
        """
        self.logger = LoggerClass(f"JSONHandler Class @ {json_data_name}")
        self.json = json_data_name
        self.json_data: dict = dict()
        self.json_dir = json_dir
        self.json_fp = os.path.join(self.json_dir, self.json + ".json") if self.json_dir != "" \
            else os.path.join(JSON_LIB, self.json + ".json")

    def formulate_json(self):
        """
        Convert the JSON into dictionary. This function MUST RUN BEFORE returning any JSON keys.
        :return:
        """
        with open(self.json_fp, "r") as json_ref:
            self.json_data = json_load(json_ref.read())
            json_ref.close()

        self.logger.info(
            "Formulated & ascertained JSON File Data. Data can now be acquired/set with get/set functions.",
            to_console=False
        )

        return True

    def generate_json(self, data_dict: dict):
        """
        Generate the JSON File should the JSON File not exist.
        If the file exists, it will be skipped.

        :param data_dict: Data in Dictionary Form
        :return:
        """
        if not os.path.exists(self.json_fp):

            self.logger.info(f"JSON File ({self.json}) does not exist. Creating...", to_console=False)

            with open(self.json_fp, "w") as json_file:
                json_file.write(json_dump(data_dict))
                json_file.close()

            return True
        else:
            self.logger.info(f"JSON File ({self.json}) already exists. Skipping...", to_console=False)
            return False

    def update_json_file(self):
        """
        Update the JSON File to include the changed entries in self.json_data.
        :return:
        """
        with open(self.json_fp, "w") as json_file:
            # print(json_dump(self.json_data))
            json_file.write(json_dump(self.json_data))
            json_file.close()

        self.logger.info(
            "JSON File has been updated. All previous data entries have been overridden.",
            to_console=False
        )

    def return_json(self):
        """
        Return the JSON in dictionary form.
        :return:
        """
        return self.json_data

    def return_specific_json(self, key: str):
        """
        Return the specific value by referencing to a key.
        :param key: Dictionary Key
        :return:
        """
        return self.json_data[key]

    def update_json(self, data_dict: dict):
        """
        Update the entire JSON Dictionary entry.
        :param data_dict: Dictionary Data
        :return:
        """
        self.json_data = data_dict

    def update_specific_json(self, key: str, value):
        """
        Update a specific JSON Data value.
        :param key: Dictionary Key
        :param value: Dictionary Value
        :return:
        """
        self.json_data[key] = value

    def add_json_entry(self, key: str = None, value=None, dict_data: dict = None):
        """
        Add a new JSON Entry.

        Either add using Key Value or by Dictionary.
        :param key: Dictionary Key
        :param value: Dictionary Value
        :param dict_data: Dictionary Data
        :return:
        """
        if key is not None and value is not None:
            self.json_data[key] = value
        else:
            self.json_data.update(dict_data)

    def delete_json_entry(self, key: str):
        """
        Delete a JSON Entry.
        :param key: Dictionary Key
        :return:
        """
        del self.json_data[key]
