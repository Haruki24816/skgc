from pathlib import Path
import json


def open_json(path):
    path = Path(path)

    if path.is_file():
        with open(path, "r") as file:
            return json.load(file)
    else:
        return {}


def save_json(path, data):
    path = Path(path)

    with open(path, "w") as file:
        json.dump(data, file)
