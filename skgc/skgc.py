import fire
import aiofiles
import asyncio
from .server import Server
from . import server_exceptions


def main():
    fire.Fire(
        {
            "init": init_server,
            "start": start_server,
            "console": server_console,
            "stop": stop_server,
            "coordinate": get_player_coordinate,
            "status": get_server_status,
            "port": set_server_port,
            "alias": set_server_alias,
            "edition": set_server_edition,
            "start_command": set_server_start_command,
            "stop_command": set_server_stop_command,
        }
    )


async def init_server(path, edition):
    server = Server(path)
    await server.init(edition)
    print("サーバーを初期化しました")


async def start_server(path):
    server = Server(path)

    async def read_stdout():
        await asyncio.sleep(1)
        async for line in server.read_log():
            print(line)

    async def write_stdin():
        await asyncio.sleep(1)
        while True:
            line = await aiofiles.stdin.readline()
            line = line
            try:
                await server.input_command(line)
            except server_exceptions.ServerInputException:
                break

    await asyncio.gather(server.start(), read_stdout(), write_stdin())


async def server_console(path):
    server = Server(path)

    async def read_stdout():
        await asyncio.sleep(1)
        async for line in server.read_log():
            print(line)

    async def write_stdin():
        await asyncio.sleep(1)
        while True:
            line = await aiofiles.stdin.readline()
            line = line
            try:
                await server.input_command(line)
            except server_exceptions.ServerInputException:
                break

    await asyncio.gather(read_stdout(), write_stdin())


async def stop_server(path):
    server = Server(path)
    await server.stop()
    print("サーバーを停止します")


async def get_player_coordinate(path, player_name):
    server = Server(path)
    print(await server.get_coordinate(player_name))


async def get_server_status(path):
    server = Server(path)
    print("状態: " + str(await server.get_status()))
    print("初期化ID: " + str(await server.get_init_id()))
    print("エイリアス: " + await server.get_alias())
    print("エディション: " + await server.get_edition())
    print("起動コマンド: " + await server.get_start_command())
    print("停止コマンド: " + await server.get_stop_command())
    print("ポート情報: " + str(await server.get_port()))


async def set_server_port(path, port):
    server = Server(path)
    await server.set_port(port)
    print("設定しました")


async def set_server_alias(path, alias):
    server = Server(path)
    await server.set_alias(alias)
    print("設定しました")


async def set_server_edition(path, edition):
    server = Server(path)
    await server.set_edition(edition)
    print("設定しました")


async def set_server_start_command(path, command):
    server = Server(path)
    await server.set_start_command(command)
    print("設定しました")


async def set_server_stop_command(path, command):
    server = Server(path)
    await server.set_stop_command(command)
    print("設定しました")


if __name__ == "__main__":
    main()
