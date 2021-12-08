# Copyright is waived. No warranty is provided. Unrestricted use and modification is permitted.

# For PSD format see https://www.adobe.com/devnet-apps/photoshop/fileformatashtml/

import io
from filestream import FileStream


class PSD:
    def __init__(self, file_path):
        self.file_path = file_path
        self.signature = 0
        self.version = 0
        self.num_channels = 0
        self.height = 0
        self.width = 0
        self.depth = 0
        self.color_mode = 0

    def load(self):
        stream = FileStream(self.file_path, "rb", FileStream.BIG_ENDIAN)
        self.signature = stream.read_u32()
        self.version = stream.read_u16()
        stream.set_position(6, io.SEEK_CUR)
        self.num_channels = stream.read_u16()
        self.height = stream.read_u32()
        self.width = stream.read_u32()
        self.depth = stream.read_u16()
        self.color_mode = stream.read_u16()

    def get_width(self):
        return self.width

    def get_height(self):
        return self.height

    def get_depth(self):
        return self.depth

    def get_color_mode(self):
        return self.color_mode

    def get_color_mode_name(self):
        return ['Bitmap', 'Grayscale', 'Indexed', 'RGB', 'CMYK', 'Multichannel', 'Duotone', 'Lab'][self.color_mode]

    def get_num_channels(self):
        return self.num_channels

    def get_source_checksum(self):
        pass

    def set_source_checksum(self, checksum):
        pass

    def save(self):
        pass
