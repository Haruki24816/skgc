import fire
import os
from pathlib import Path
import psutil
import subprocess
import threading
import time
from .edit_properties_file import PropertiesFile
from .edit_json import open_json, save_json
import uuid


DEFAULT_START_COMMAND_JAVA = "java -jar minecraft_server.jar --nogui"
DEFAULT_START_COMMAND_BEDROCK = "LD_LIBRARY_PATH=. ./bedrock_server"


def main():
    fire.Fire(
        {
            "init": init_server,
            "start": start_server,
            "console": console,
            "stop": stop_server,
            "status": server_status,
            "coordinate": get_player_coordinate,
            "port": set_server_port,
            "edition": set_edition,
            "start_command": set_start_command,
            "stop_command": set_stop_command,
            "alias": set_alias,
        }
    )


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


def stop_server(path):
    server = Server(path)
    server.stop()
    print("サーバーを停止します")


def server_status(path):
    server = Server(path)
    print("起動: " + str(server.get_status()))
    print("PID: " + str(server.get_pid()))
    print("エディション: " + server.get_edition())
    print("起動コマンド: " + server.get_start_command())
    print("停止コマンド: " + server.get_stop_command())
    print("エイリアス: " + str(server.get_alias()))
    print("ポート: " + str(server.get_port()))


def get_player_coordinate(path, player_name):
    server = Server(path)
    print(server.get_coordinate(player_name))


def set_server_port(path, port):
    server = Server(path)
    server.set_port(port)
    print("設定しました")


def set_edition(path, edition):
    server = Server(path)
    server.set_edition(edition)
    print("設定しました")


def set_start_command(path, command):
    server = Server(path)
    server.set_start_command(command)
    print("設定しました")


def set_stop_command(path, command):
    server = Server(path)
    server.set_stop_command(command)
    print("設定しました")


def set_alias(path, alias):
    server = Server(path)
    server.set_alias(alias)
    print("設定しました")


class Server:

    def __init__(self, path):
        self.path = Path(path)

        if not self.path.is_dir():
            raise ServerException("存在しないディレクトリです")

    # サーバー操作

    def start(self):
        server_data = self._get_server_data()

        if server_data["pid"] is not None:
            raise ServerException("起動済みです")

        process = subprocess.Popen(
            server_data["start_command"],
            shell=True,
            cwd=self.path,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            encoding="utf-8",
        )

        server_data["pid"] = process.pid
        self._update_server_data(server_data)

        def stdout_loop():
            stdout_path = self.path / Path("skgc/stdout")
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
            stdout_path = self.path / Path("skgc/stdout")
            stdin_path = self.path / Path("skgc/stdin")
            while True:
                time.sleep(1)
                if process.poll() is not None:
                    break
                with open(stdin_path, encoding="utf-8") as file:
                    lines = file.readlines()
                if len(lines) < 1:
                    continue
                line = lines[0]
                with open(stdout_path, mode="a", encoding="utf-8") as file:
                    file.write("\n" + line.rstrip())
                process.stdin.write(line)
                process.stdin.flush()
                with open(stdin_path, mode="w", encoding="utf-8") as file:
                    file.write("")

        stdout_loop_thread = threading.Thread(target=stdout_loop)
        stdout_loop_thread.start()

        stdin_loop_thread = threading.Thread(target=stdin_loop)
        stdin_loop_thread.start()

    def input_command(self, command):
        server_data = self._get_server_data()

        if server_data["pid"] is None:
            raise ServerException("起動していません")

        stdin_path = self.path / Path("skgc/stdin")

        with open(stdin_path, mode="w", encoding="utf-8") as file:
            file.write(command + "\n")

    def stop(self):
        server_data = self._get_server_data()
        self.input_command(server_data["stop_command"])

    # サーバーデータ取得

    def read_log(self, loop=True):
        server_data = self._get_server_data()

        if server_data["pid"] is None:
            raise ServerException("起動していません")

        count = 0
        stdout_path = self.path / Path("skgc/stdout")

        while True:
            time.sleep(1)
            with open(stdout_path, encoding="utf-8") as file:
                lines = file.readlines()
            while len(lines) > count:
                yield lines[count]
                count += 1
            if not loop:
                break
            if server_data["pid"] is not None and not psutil.pid_exists(
                server_data["pid"]
            ):
                break

    def get_coordinate(self, player_name):
        server_data = self._get_server_data()

        if server_data["edition"] == "bedrock":
            lines = self._get_command_response(
                f"execute as {player_name} at {player_name} run tp ~ ~ ~"
            )
            for line in lines:
                if f"Teleported {player_name} to" in line:
                    x, y, z = line.split(f"Teleported {player_name} to")[-1].split(",")
                    x, y, z = float(x), float(y), float(z)
                    return x, y, z
        else:
            lines = self._get_command_response(
                f"execute as {player_name} at {player_name} run tp ~ ~ ~"
            )
            for line in lines:
                if f"Teleported {player_name} to" in line:
                    x, y, z = line.split(f"Teleported {player_name} to")[-1].split(",")
                    x, y, z = float(x), float(y), float(z)
                    return x, y, z

        raise ServerException("座標を取得できませんでした")

    def get_status(self):
        server_data = self._get_server_data()
        return server_data["pid"] is not None

    def get_pid(self):
        server_data = self._get_server_data()
        return server_data["pid"]

    def get_port(self):
        server_data = self._get_server_data()
        properties = PropertiesFile(self.path / Path("server.properties"))

        if server_data["edition"] == "bedrock":
            return {
                "server-port": properties["server-port"],
                "server-portv6": properties["server-portv6"],
            }
        else:
            return {
                "query.port": properties["query.port"],
                "rcon.port": properties["rcon.port"],
                "server-port": properties["server-port"],
            }

    # サーバーデータ編集

    def set_port(self, port):
        server_data = self._get_server_data()
        properties = PropertiesFile(self.path / Path("server.properties"))

        if server_data["edition"] == "bedrock":
            properties["server-port"] = port  # 19132
            properties["server-portv6"] = port + 1  # 19133
        else:
            properties["query.port"] = port  # 25565
            properties["rcon.port"] = port + 10  # 25575
            properties["server-port"] = port  # 25565

        properties.save()

    # サーバー管理データ取得

    def get_edition(self):
        server_data = self._get_server_data()
        return server_data["edition"]

    def get_start_command(self):
        server_data = self._get_server_data()
        return server_data["start_command"]

    def get_stop_command(self):
        server_data = self._get_server_data()
        return server_data["stop_command"]

    def get_alias(self):
        server_data = self._get_server_data()
        return server_data["alias"]

    # サーバー管理データ編集

    def init(self, edition):
        skgc_path = self.path / Path("skgc/")
        os.makedirs(skgc_path, exist_ok=True)

        json_path = skgc_path / Path("skgc.json")
        json_path.touch()

        stdin_path = skgc_path / Path("stdin")
        stdin_path.touch()

        stdout_path = skgc_path / Path("stdout")
        stdout_path.touch()

        server_data = {}
        init_id = str(uuid.uuid4())

        if edition == "bedrock":
            server_data["edition"] = "bedrock"
            server_data["start_command"] = DEFAULT_START_COMMAND_BEDROCK
            server_data["stop_command"] = "stop"
            server_data["alias"] = ""
            server_data["pid"] = None
            server_data["init_id"] = init_id
        else:
            server_data["edition"] = "java"
            server_data["start_command"] = DEFAULT_START_COMMAND_JAVA
            server_data["stop_command"] = "stop"
            server_data["alias"] = ""
            server_data["pid"] = None
            server_data["init_id"] = init_id

        self._update_server_data(server_data)

    def set_edition(self, edition):
        server_data = self._get_server_data()
        server_data["edition"] = edition
        self._update_server_data(server_data)

    def set_start_command(self, command):
        server_data = self._get_server_data()
        server_data["start_command"] = command
        self._update_server_data(server_data)

    def set_stop_command(self, command):
        server_data = self._get_server_data()
        server_data["stop_command"] = command
        self._update_server_data(server_data)

    def set_alias(self, alias):
        server_data = self._get_server_data()
        server_data["alias"] = alias
        self._update_server_data(server_data)

    # 内部用メソッド

    def _get_command_response(self, command):
        self.input_command(command)
        time.sleep(1)

        lines = list(self.read_log(loop=False))
        split_index = 0

        for num in range(len(lines)):
            if lines[num].strip() == command:
                split_index = num

        return list(reversed(lines[split_index:]))

    def _get_server_data(self):
        json_path = self.path / Path("skgc/skgc.json")

        if not json_path.is_file():
            raise ServerException("初期化されていません")

        server_data = open_json(json_path)

        if server_data["pid"] is not None and not psutil.pid_exists(server_data["pid"]):
            server_data["pid"] = None

        return server_data

    def _update_server_data(self, server_data):
        json_path = self.path / Path("skgc/skgc.json")
        save_json(json_path, server_data)


class ServerException(Exception):
    pass


if __name__ == "__main__":
    main()
