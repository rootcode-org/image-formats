# Copyright is waived. No warranty is provided. Unrestricted use and modification is permitted.

# RIFF format: https://web.archive.org/web/20191226055430/http://www.morgan-multimedia.com/download/odmlff2.pdf
# Chunk identifiers:  http://www.sno.phy.queensu.ca/~phil/exiftool/TagNames/RIFF.html

import io
import datetime
from streams import FileStream


class AVI:
    def __init__(self):
        self.file_path = None
        self.stream = None
        self.chunk_type_stack = []
        self.image_time = None

    def load(self, file_path):
        self.file_path = file_path
        self.stream = FileStream(file_path, 'rb')
        signature = self.stream.read_string(4)
        if signature != 'RIFF':
            raise ValueError
        file_size = self.stream.read_u32()
        file_type = self.stream.read_string(4)
        if file_type != 'AVI ':
            raise ValueError
        self.parse_chunks(file_size)

    def parse_chunks(self, end_position):
        while self.stream.get_position() < end_position:
            chunk_id = self.stream.read_string(4)
            chunk_size = self.stream.read_u32()
            if chunk_id == 'LIST':
                list_type = self.stream.read_string(4)
                self.chunk_type_stack.append(list_type)
                self.parse_chunks(self.stream.get_position() + chunk_size)
                self.chunk_type_stack.pop()
            elif chunk_id == 'ICRD':
                time_string = self.stream.read_string(chunk_size).rstrip(' \r\n\x00')
                try:
                    self.image_time = datetime.datetime.strptime(time_string, '%Y-%m-%d')
                except ValueError:
                    pass
            elif chunk_id == 'IDIT':
                time_string = self.stream.read_string(chunk_size).rstrip(' \r\n\x00')
                try:
                    self.image_time = datetime.datetime.strptime(time_string, '%a %b %d %H:%M:%S %Y')
                except ValueError:
                    pass
            else:
                self.stream.set_position(chunk_size, io.SEEK_CUR)

    def get_image_time(self):
        return self.image_time
