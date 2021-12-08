# Copyright is waived. No warranty is provided. Unrestricted use and modification is permitted.

# For PNG format see https://www.w3.org/TR/PNG/

import io
import datetime
import xml.etree.ElementTree as ET
from filestream import FileStream


class PNG:
    def __init__(self):
        self.file_path = None
        self.image_time = None

    def load(self, file_path):
        self.file_path = file_path
        stream = FileStream(file_path, "rb", FileStream.BIG_ENDIAN)
        id1 = stream.read_u32()
        id2 = stream.read_u32()
        if id1 == 0x89504e47 and id2 == 0x0d0a1a0a:
            while not stream.is_eof():
                length = stream.read_u32()
                type = stream.read_string(4)
                if type == "tIME":
                    year = stream.read_u16()
                    month = stream.read_u8()
                    day = stream.read_u8()
                    hour = stream.read_u8()
                    minute = stream.read_u8()
                    second = stream.read_u8()
                    self.image_time = datetime.datetime(year, month, day, hour, minute, second)
                    crc = stream.read_u32()
                elif type == "tEXt":                # text
                    stream.set_position(length, io.SEEK_CUR)
                    crc = stream.read_u32()
                elif type == "zTXt":                # deflated text
                    stream.set_position(length, io.SEEK_CUR)
                    crc = stream.read_u32()
                elif type == "iTXt":                # international text
                    index = stream.get_position()
                    keyword = stream.read_nt_string()
                    compression_flag = stream.read_u8()
                    compression_method = stream.read_u8()
                    language_tag = stream.read_nt_string()
                    translated_keyword = stream.read_nt_string()
                    text_length = length - (stream.get_position() - index)
                    text = stream.read_string(text_length)
                    if keyword == "XML:com.adobe.xmp":
                        xml_root = ET.fromstring(text)
                        date_element = xml_root.find(".//{http://ns.adobe.com/photoshop/1.0/}DateCreated")
                        if date_element is not None:
                            try:
                                self.image_time = datetime.datetime.strptime(date_element.text, "%Y-%m-%dT%H:%M:%S")
                            except ValueError:
                                pass
                    crc = stream.read_u32()
                elif type == "IEND":
                    break
                else:
                    stream.set_position(length, io.SEEK_CUR)
                    crc = stream.read_u32()

    def get_image_time(self):
        return self.image_time
