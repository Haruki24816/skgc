from pathlib import Path


class PropertiesFile(dict):

    def __init__(self, path):
        self.properties_file_path = Path(path)

        with open(path) as file:
            lines = file.readlines()
        
        data = {}
        
        for line in lines:
            line_without_comment = line.split("#")[0]
            if len(line_without_comment.split()) == 0:
                continue
            items = line_without_comment.strip().split("=")
            key = items[0]
            value = items[1]
            data[key] = value

        super().__init__(data)
    
    def save(self):
        text_data = ""

        for key in self:
            value = self[key]
            text_data += f"{key}={value}\n"
        
        with open(self.properties_file_path, mode="w") as file:
            file.write(text_data)
