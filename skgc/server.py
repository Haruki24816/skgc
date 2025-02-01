import aiofiles
from aiofiles import os
import asyncio
import uuid
from pathlib import Path
from . import server_exceptions
from .edit_properties_file import load_properties_file, save_properties_file
from .edit_json import load_json, save_json


DEFAULT_START_COMMAND_JAVA = "java -jar minecraft_server.jar --nogui"
DEFAULT_STOP_COMMAND_JAVA = "stop"
DEFAULT_START_COMMAND_BEDROCK = "LD_LIBRARY_PATH=. ./bedrock_server"
DEFAULT_STOP_COMMAND_BEDROCK = "stop"


class Server(object):

    def __init__(self, path):
        self.path = Path(path)
        self.skgc_path = self.path / Path("skgc/")
        self.json_path = self.skgc_path / Path("skgc.json")
        self.stdin_path = self.skgc_path / Path("stdin")
        self.stdout_path = self.skgc_path / Path("stdout")

        if not self.path.is_dir():
            raise server_exceptions.ServerInitException("存在しないディレクトリです")

    # サーバーデータ操作関係

    async def _load_server_data(self):
        if not await os.path.isfile(self.json_path):
            raise server_exceptions.ServerDataError("初期化されていません")

        return await load_json(self.json_path)

    async def _save_server_data(self, server_data):
        await save_json(self.json_path, server_data)

    async def init(self, edition):
        await os.makedirs(self.skgc_path, exist_ok=True)

        async with aiofiles.open(self.json_path, "w") as json_file:
            await json_file.write("")

        async with aiofiles.open(self.stdin_path, "wb") as stdin_file:
            await stdin_file.write("".encode())

        async with aiofiles.open(self.stdout_path, "wb") as stdout_file:
            await stdout_file.write("".encode())

        server_data = {}
        init_id = str(uuid.uuid4())

        server_data["init_id"] = init_id
        server_data["status"] = False
        server_data["alias"] = self.path.name
        server_data["misc"] = {}

        if edition == "bedrock":
            server_data["edition"] = "bedrock"
            server_data["start_command"] = DEFAULT_START_COMMAND_BEDROCK
            server_data["stop_command"] = DEFAULT_STOP_COMMAND_BEDROCK
        else:
            server_data["edition"] = "java"
            server_data["start_command"] = DEFAULT_START_COMMAND_JAVA
            server_data["stop_command"] = DEFAULT_STOP_COMMAND_JAVA

        await self._save_server_data(server_data)

    # サーバープロセス通信関係

    async def start(self):
        server_data = await self._load_server_data()

        if server_data["status"]:
            raise server_exceptions.ServerStartingException("起動済みです")

        async with aiofiles.open(self.stdin_path, "wb") as stdin_file:
            await stdin_file.write("".encode())

        async with aiofiles.open(self.stdout_path, "wb") as stdout_file:
            await stdout_file.write("".encode())

        process = await asyncio.create_subprocess_shell(
            server_data["start_command"],
            cwd=self.path,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
        )

        server_data["status"] = True
        await self._save_server_data(server_data)

        async def loop_stdout():
            while True:
                if process.returncode is not None:
                    break
                stdout_line = await process.stdout.readline()
                async with aiofiles.open(self.stdout_path, "ab") as stdout_file:
                    await stdout_file.write(stdout_line)

        async def loop_stdin():
            async with aiofiles.open(self.stdin_path, "rb") as stdin_file:
                while True:
                    await asyncio.sleep(1)
                    if process.returncode is not None:
                        break
                    stdin_line = await stdin_file.readline()
                    if stdin_line:
                        async with aiofiles.open(self.stdout_path, "ab") as stdout_file:
                            await stdout_file.write(stdin_line)
                        process.stdin.write(stdin_line)

        await asyncio.gather(loop_stdout(), loop_stdin())

        server_data = await self._load_server_data()
        server_data["status"] = False
        await self._save_server_data(server_data)

        if process.returncode != 0:
            raise server_exceptions.ServerProcessError("子プロセスが異常終了しました")

    async def read_log(self, start_line=-100, follow=True):
        server_data = await self._load_server_data()

        if not server_data["status"]:
            raise server_exceptions.ServerOutputException("起動していません")

        async with aiofiles.open(self.stdout_path, "rb") as stdout_file:
            stdout_lines = await stdout_file.readlines()
            for stdout_line in stdout_lines[start_line:]:
                yield stdout_line.decode().rstrip()
            if not follow:
                return
            while True:
                server_data = await self._load_server_data()
                if not server_data["status"]:
                    return
                await asyncio.sleep(1)
                stdout_lines = await stdout_file.readlines()
                if len(stdout_lines) < 1:
                    continue
                for stdout_line in stdout_lines:
                    yield stdout_line.decode().rstrip()

    async def input_command(self, command):
        command = command.rstrip()
        server_data = await self._load_server_data()

        if not server_data["status"]:
            raise server_exceptions.ServerInputException("起動していません")

        async with aiofiles.open(self.stdin_path, "ab") as stdin_file:
            await stdin_file.write((command + "\n").encode())

    async def _get_command_response(self, command, verify_function):
        await self.input_command(command)
        await asyncio.sleep(2)

        lines = []
        async for line in self.read_log(follow=False):
            lines.append(line)

        split_index = 0

        for index in range(len(lines)):
            if lines[index].strip() == command:
                split_index = index

        for line in reversed(lines[split_index:]):
            if verify_function(line):
                return line

    # サーバーコマンド関係

    async def stop(self):
        server_data = await self._load_server_data()
        await self.input_command(server_data["stop_command"])

    async def get_coordinate(self, player_name):
        server_data = await self._load_server_data()

        if server_data["edition"] == "bedrock":

            def verify_function_bedrock(line):
                return f"Teleported {player_name} to" in line

            line = await self._get_command_response(
                f"execute as {player_name} at {player_name} run tp ~ ~ ~",
                verify_function_bedrock,
            )
            if line is None:
                return None
            x, y, z = line.split(f"Teleported {player_name} to")[-1].split(",")
            x, y, z = float(x), float(y), float(z)
            return x, y, z
        else:

            def verify_function_java(line):
                return f"Teleported {player_name} to" in line

            line = await self._get_command_response(
                f"execute as {player_name} at {player_name} run tp ~ ~ ~",
                verify_function_java,
            )
            if line is None:
                return None
            x, y, z = line.split(f"Teleported {player_name} to")[-1].split(",")
            x, y, z = float(x), float(y), float(z)
            return x, y, z

    # server.properties関係

    async def get_port(self):
        server_data = await self._load_server_data()
        properties_data = await load_properties_file(
            self.path / Path("server.properties")
        )

        if server_data["edition"] == "bedrock":
            return {
                "server-port": properties_data["server-port"],
                "server-portv6": properties_data["server-portv6"],
            }
        else:
            return {
                "query.port": properties_data["query.port"],
                "rcon.port": properties_data["rcon.port"],
                "server-port": properties_data["server-port"],
            }

    async def set_port(self, port):
        server_data = await self._load_server_data()
        properties_data = await load_properties_file(
            self.path / Path("server.properties")
        )

        if server_data["edition"] == "bedrock":
            properties_data["server-port"] = port  # 19132
            properties_data["server-portv6"] = port + 1  # 19133
        else:
            properties_data["query.port"] = port  # 25565
            properties_data["rcon.port"] = port + 10  # 25575
            properties_data["server-port"] = port  # 25565

        await save_properties_file(
            self.path / Path("server.properties"), properties_data
        )

    # サーバーデータ取得・設定

    async def get_status(self):
        server_data = await self._load_server_data()
        return server_data["status"]

    async def get_init_id(self):
        server_data = await self._load_server_data()
        return server_data["init_id"]

    async def get_alias(self):
        server_data = await self._load_server_data()
        return server_data["alias"]

    async def set_alias(self, alias):
        server_data = await self._load_server_data()
        server_data["alias"] = alias
        await self._save_server_data(server_data)

    async def get_edition(self):
        server_data = await self._load_server_data()
        return server_data["edition"]

    async def set_edition(self, edition):
        server_data = await self._load_server_data()
        server_data["edition"] = edition
        await self._save_server_data(server_data)

    async def get_start_command(self):
        server_data = await self._load_server_data()
        return server_data["start_command"]

    async def set_start_command(self, start_command):
        server_data = await self._load_server_data()
        server_data["start_command"] = start_command
        await self._save_server_data(server_data)

    async def get_stop_command(self):
        server_data = await self._load_server_data()
        return server_data["stop_command"]

    async def set_stop_command(self, stop_command):
        server_data = await self._load_server_data()
        server_data["stop_command"] = stop_command
        await self._save_server_data(server_data)
    
    async def get_misc_data(self):
        server_data = await self._load_server_data()
        return server_data["misc"]

    async def set_misc_data(self, data):
        server_data = await self._load_server_data()
        server_data["misc"] = data
        await self._save_server_data(server_data)
