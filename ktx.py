# Copyright is waived. No warranty is provided. Unrestricted use and modification is permitted.

# KTX file format: https://github.khronos.org/KTX-Specification/

import io
import struct
from streams import ByteStream, FileStream

pixel_format_names = {
    0x8C92: 'ATC_RGB',
    0x8C93: 'ATC_RGBA',         # ATC Explicit Alpha
    0x87EE: 'ATC_RGBA_IA',      # ATC Interpolated Alpha
    0x83F0: 'RGB_DXT1',
    0x83F1: 'RGBA_DXT1',
    0x83F2: 'RGBA_DXT3',
    0x83f3: 'RGBA_DXT5'
}


class KTX:
    def __init__(self):
        self.file_path = None
        self.identifier1 = 0
        self.identifier2 = 0
        self.identifier3 = 0
        self.endianness = 0
        self.gl_type = 0
        self.gl_type_size = 0
        self.gl_format = 0
        self.gl_internal_format = 0
        self.gl_base_internal_format = 0
        self.pixel_width = 0
        self.pixel_height = 0
        self.pixel_depth = 0
        self.num_array_elements = 0
        self.num_faces = 0
        self.num_mipmaps = 0
        self.metadata_size = 0
        self.metadata = {}
        self.source_checksum = 0
        self.mip_images = []

    def load(self, file_path):
        self.file_path = file_path
        stream = FileStream(self.file_path, "rb")

        # parse header
        self.identifier1 = stream.read_u32()
        self.identifier2 = stream.read_u32()
        self.identifier3 = stream.read_u32()
        self.endianness = stream.read_u32()
        if self.endianness == 0x01020304:
            stream.set_endian(FileStream.BIG_ENDIAN)
        self.gl_type = stream.read_u32()
        self.gl_type_size = stream.read_u32()
        self.gl_format = stream.read_u32()
        self.gl_internal_format = stream.read_u32()
        self.gl_base_internal_format = stream.read_u32()
        self.pixel_width = stream.read_u32()
        self.pixel_height = stream.read_u32()
        self.pixel_depth = stream.read_u32()
        self.num_array_elements = stream.read_u32()
        self.num_faces = stream.read_u32()
        self.num_mipmaps = stream.read_u32()
        self.metadata_size = stream.read_u32()

        # parse metadata
        metadata_end = stream.get_position() + self.metadata_size
        while stream.get_position() < metadata_end:

            kv_pair_size = stream.read_u32()
            kv_pair_end = stream.get_position() + kv_pair_size

            # read key name
            key = ''
            char = stream.read_u8()
            while char != 0:
                key += chr(char)
                char = stream.read_u8()

            # read value
            value = bytearray()
            while stream.get_position() < kv_pair_end:
                byte = stream.read_u8()
                value.append(byte)

            padding_length = 3 - ((kv_pair_size + 3) % 4)
            stream.set_position(padding_length, io.SEEK_CUR)
            self.metadata[key] = value

        # parse image data
        for mip_level in range(self.num_mipmaps):
            mip_size = stream.read_u32()
            mip_size = (mip_size + 3) & -4
            self.mip_images.append(stream.read_u8_array(mip_size))

    def get_width(self):
        return self.pixel_width

    def get_height(self):
        return self.pixel_height

    def get_pixel_format_code(self):
        return self.gl_internal_format

    def get_pixel_format_name(self):
        return pixel_format_names[self.gl_internal_format]

    def get_source_checksum(self):
        if "SCRC" in self.metadata:
            return struct.unpack("<I", self.metadata['SCRC'])[0]
        else:
            return None

    def set_source_checksum(self, checksum):
        if not "SCRC" in self.metadata:
            self.metadata_size += 16            # rounded up 4 (size) + 5 (key) + 4 (data)
        self.metadata['SCRC'] = bytearray(struct.pack("<I", checksum))

    def save(self):
        stream = ByteStream(ByteStream.LITTLE_ENDIAN)

        # write header
        stream.write_u32(self.identifier1)
        stream.write_u32(self.identifier2)
        stream.write_u32(self.identifier3)
        stream.write_u32(self.endianness)
        stream.write_u32(self.gl_type)
        stream.write_u32(self.gl_type_size)
        stream.write_u32(self.gl_format)
        stream.write_u32(self.gl_internal_format)
        stream.write_u32(self.gl_base_internal_format)
        stream.write_u32(self.pixel_width)
        stream.write_u32(self.pixel_height)
        stream.write_u32(self.pixel_depth)
        stream.write_u32(self.num_array_elements)
        stream.write_u32(self.num_faces)
        stream.write_u32(self.num_mipmaps)
        stream.write_u32(self.metadata_size)

        # write metadata
        for key in self.metadata:
            value = self.metadata[key]
            length = len(key) + 1 + len(value)
            stream.write_u32(length)
            stream.write_string(key)
            stream.write_u8(0)
            stream.write_u8_array(value)
            padding = 3 - ((length + 3) % 4)
            for i in range(padding):
                stream.write_u8(0)

        # write mip images
        for mip_image in self.mip_images:
            stream.write_u32(len(mip_image))
            stream.write_u8_array(mip_image)

        with open(self.file_path, "wb") as f:
            f.write(stream.get_data())
