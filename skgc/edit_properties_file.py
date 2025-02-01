import aiofiles


async def load_properties_file(path):
    async with aiofiles.open(path) as file:
        lines = await file.readlines()

    data = {}

    for line in lines:
        line_without_comment = line.split("#")[0]
        if len(line_without_comment.split()) == 0:
            continue
        items = line_without_comment.strip().split("=")
        key = items[0]
        value = items[1]
        data[key] = value
    
    return data


async def save_properties_file(path, data):
    text_data = ""

    for key, value in data.items():
        text_data += f"{key}={value}\n"

    async with aiofiles.open(path, "w") as file:
        await file.write(text_data)
