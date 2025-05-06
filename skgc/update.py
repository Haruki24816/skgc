import os
import shutil
import urllib.request
from pathlib import Path


USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"


def update_java_server(path, url):
    path = Path(path)
    skgc_path = path / "skgc"
    download_path = skgc_path / "download"
    new_jar_path = download_path / "server.jar"
    backup_path = skgc_path / "backup"
    old_jar_path = path / "server.jar"

    make_empty_directory(download_path)
    download(url, new_jar_path, USER_AGENT)
    make_empty_directory(backup_path)
    shutil.move(old_jar_path, backup_path)
    shutil.move(new_jar_path, path)


def update_bedrock_server(path, url):
    path = Path(path)
    skgc_path = path / "skgc"

    # 旧データをバックアップフォルダに移動

    backup_path = skgc_path / "backup"
    make_empty_directory(backup_path)
    backup_items = os.listdir(path)
    for item in backup_items:
        if item == "skgc":
            continue
        item_path = path / item
        shutil.move(item_path, backup_path)

    # 更新データをダウンロード、展開

    download_path = skgc_path / "download"
    make_empty_directory(download_path)
    zip_path = download_path / "server.zip"
    download(url, zip_path, USER_AGENT)
    shutil.unpack_archive(zip_path, path)

    # バックアップフォルダから、ワールドデータ等をコピー

    copy_items = ("worlds", "server.properties", "permissions.json", "allowlist.json")
    for item in copy_items:
        item_path = path / item
        delete_item(item_path)
    for item in copy_items:
        item_path = backup_path / item
        copy_item(item_path, path)


def make_empty_directory(path):
    os.makedirs(path, exist_ok=True)
    shutil.rmtree(path)
    os.makedirs(path)


def download(url, path, user_agent):
    request = urllib.request.Request(
        url, headers={"User-Agent": user_agent}, method="GET"
    )

    with urllib.request.urlopen(request) as web_file:
        with open(path, "wb") as local_file:
            local_file.write(web_file.read())


def delete_item(path):
    path = Path(path)

    try:
        if path.is_file():
            os.remove(path)
        else:
            shutil.rmtree(path)
    except FileNotFoundError:
        pass


def copy_item(path, destination_path):
    path = Path(path)
    destination_path = Path(destination_path)

    if path.is_file():
        shutil.copy(path, destination_path)
    else:
        destination_path = destination_path / path.name
        shutil.copytree(path, destination_path)
