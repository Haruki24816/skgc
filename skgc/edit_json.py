import aiofiles
import json


async def load_json(path):
    try:
        async with aiofiles.open(path) as file:
            json_text = await file.read()
            return json.loads(json_text)
    except FileNotFoundError:
        return {}


async def save_json(path, data):
    async with aiofiles.open(path, "w") as file:
        json_text = json.dumps(data)
        await file.write(json_text)
