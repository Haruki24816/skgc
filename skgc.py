import fire
import os
from pathlib import Path
import json
import psutil
import subprocess
import threading
import time


DEFAULT_START_COMMAND_JAVA = "java -jar minecraft_server.jar --nogui"
DEFAULT_START_COMMAND_BEDROCK = "LD_LIBRARY_PATH=. ./bedrock_server"


class Server:

    def __init__(self, path):
        self.path = Path(path)

        self.edition = ""
        self.start_command = ""
        self.server_data = {}

        self.pid = None

        try:
            self.reload_data()
        except Exception:
            pass

    def init(self, edition):
        skgc_path = self.path / Path("skgc/")
        os.makedirs(skgc_path, exist_ok=False)

        if edition == "bedrock":
            self.edition = "bedrock"
            self.start_command = DEFAULT_START_COMMAND_BEDROCK
            self.server_data = {}
            self.pid = None
        else:
            self.edition = "java"
            self.start_command = DEFAULT_START_COMMAND_JAVA
            self.server_data = {}
            self.pid = None

        self.update_data()

    def start(self):
        self.reload_data()

        if self.pid is not None:
            raise Exception("起動済みです")

        process = subprocess.Popen(
            self.start_command,
            shell=True,
            cwd=self.path,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            encoding="utf-8",
        )

        self.pid = process.pid
        self.update_data()

        def stdout_loop():
            stdout_path = self.path / Path("skgc/stdout")
            stdout_path.touch()
            with open(stdout_path, mode="w", encoding="utf-8") as file:
                file.write("")
            while True:
                line = process.stdout.readline()
                if line:
                    with open(stdout_path, mode="a", encoding="utf-8") as file:
                        file.write("\n" + line.rstrip())
                if not line and process.poll() is not None:
                    break

        def stdin_loop():
            stdin_path = self.path / Path("skgc/stdin")
            stdin_path.touch()
            while True:
                time.sleep(1)
                if process.poll() is not None:
                    break
                with open(stdin_path, encoding="utf-8") as file:
                    lines = file.readlines()
                if len(lines) < 1:
                    continue
                process.stdin.write(lines[0])
                process.stdin.flush()
                with open(stdin_path, mode="w", encoding="utf-8") as file:
                    file.write("")

        stdout_loop_thread = threading.Thread(target=stdout_loop)
        stdout_loop_thread.start()

        stdin_loop_thread = threading.Thread(target=stdin_loop)
        stdin_loop_thread.start()

    def input_command(self, command):
        self.reload_data()

        if self.pid is None:
            raise Exception("起動していません")

        stdin_path = self.path / Path("skgc/stdin")

        with open(stdin_path, mode="a", encoding="utf-8") as file:
            file.write(command + "\n")

    def read_log(self):
        self.reload_data()

        if self.pid is None:
            raise Exception("起動していません")

        count = 0
        stdout_path = self.path / Path("skgc/stdout")

        while True:
            time.sleep(1)
            with open(stdout_path, encoding="utf-8") as file:
                lines = file.readlines()
            while len(lines) > count:
                yield lines[count]
                count += 1
            if self.pid is not None and not psutil.pid_exists(self.pid):
                break

    def reload_data(self):
        skgc_path = self.path / Path("skgc/")

        if not skgc_path.is_dir():
            raise Exception("初期化されていません")

        config_path = self.path / Path("skgc/config.json")
        config_data = open_json(config_path)

        self.edition = config_data["edition"]
        self.start_command = config_data["start_command"]
        self.server_data = config_data["server_data"]

        status_path = self.path / Path("skgc/status.json")
        status_data = open_json(status_path)

        self.pid = status_data["pid"]

        if self.pid is not None and not psutil.pid_exists(self.pid):
            self.pid = None

        self.update_data()

    def update_data(self):
        config_path = self.path / Path("skgc/config.json")

        save_json(
            config_path,
            {
                "edition": self.edition,
                "start_command": self.start_command,
                "server_data": self.server_data,
            },
        )

        status_path = self.path / Path("skgc/status.json")

        save_json(
            status_path,
            {
                "pid": self.pid,
            },
        )


def open_json(path):
    if path.is_file():
        with open(path, "r") as file:
            return json.load(file)
    else:
        return {}


def save_json(path, data):
    with open(path, "w") as file:
        json.dump(data, file)


def init_server(path, edition):
    server = Server(path)
    server.init(edition)
    print("サーバーを初期化しました")


def start_server(path):
    server = Server(path)
    server.start()

    def console_stdout():
        for text in server.read_log():
            print(text)

    console_stdout_thread = threading.Thread(target=console_stdout)
    console_stdout_thread.start()

    while True:
        try:
            server.input_command(input())
        except Exception:
            break


def console(path):
    server = Server(path)

    def console_stdout():
        for text in server.read_log():
            print(text)

    console_stdout_thread = threading.Thread(target=console_stdout)
    console_stdout_thread.start()

    while True:
        try:
            server.input_command(input())
        except Exception:
            break


if __name__ == "__main__":
    fire.Fire(
        {
            "init": init_server,
            "start": start_server,
            "console": console,
        }
    )
