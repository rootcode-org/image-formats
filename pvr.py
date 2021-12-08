# Copyright is waived. No warranty is provided. Unrestricted use and modification is permitted.

# PVR file format: http://cdn.imgtec.com/sdk-documentation/PVR+File+Format.Specification.pdf

import io
from filestream import FileStream
from bytestream import ByteStream

pixel_formats = {
    # Name, Bits per pixel, Min width, Min height
    # If bits per pixel is 0 then the format has not yet been researched and specified correctly
    0: ["PVRTC1_2_RGB", 2, 16, 8],
    1: ["PVRTC1_2", 2, 16, 8],
    2: ["PVRTC1_4_RGB", 4, 8, 8],
    3: ["PVRTC1_4", 4, 8, 8],
    4: ["PVRTC2_2", 2, 8, 4],
    5: ["PVRTC2_4", 4, 4, 4],
    6: ["ETC1", 4, 4, 4],
    7: ["DXT1", 4, 4, 4],
    8: ["DXT2", 4, 4, 4],
    9: ["DXT3", 4, 4, 4],
    10: ["DXT4", 4, 4, 4],
    11: ["DXT5", 8, 4, 4],
    12: ["BC4", 8, 4, 4],
    13: ["BC5", 0, 4, 4],
    14: ["BC6", 0, 1, 1],
    15: ["BC7", 0, 1, 1],
    16: ["UYVY", 8, 2, 1],
    17: ["YUY2", 8, 2, 1],
    18: ["1BPP", 1, 8, 1],
    19: ["RGBE9995", 32, 1, 1],
    20: ["RGBG8888", 32, 2, 1],
    21: ["GRGB8888", 32, 2, 1],
    22: ["ETC2_RGB", 4, 1, 1],
    23: ["ETC2_RGBA", 4, 1, 1],
    24: ["ETC2_RGB A1", 4, 1, 1],
    25: ["EAC_R11", 0, 1, 1],
    26: ["EAC_RG11", 0, 1, 1],
    27: ["ASTC_4x4", 0, 1, 1],
    28: ["ASTC_5x4", 0, 1, 1],
    29: ["ASTC_5x5", 0, 1, 1],
    30: ["ASTC_6x5", 0, 1, 1],
    31: ["ASTC_6x6", 0, 1, 1],
    32: ["ASTC_8x5", 0, 1, 1],
    33: ["ASTC_8x6", 0, 1, 1],
    34: ["ASTC_8x8", 0, 1, 1],
    35: ["ASTC_10x5", 0, 1, 1],
    36: ["ASTC_10x6", 0, 1, 1],
    37: ["ASTC_10x8", 0, 1, 1],
    38: ["ASTC_10x10", 0, 1, 1],
    39: ["ASTC_12x10", 0, 1, 1],
    40: ["ASTC_12x12", 0, 1, 1],
    41: ["ASTC_3x3x3", 0, 1, 1],
    42: ["ASTC_4x3x3", 0, 1, 1],
    43: ["ASTC_4x4x3", 0, 1, 1],
    44: ["ASTC_4x4x4", 0, 1, 1],
    45: ["ASTC_5x4x4", 0, 1, 1],
    46: ["ASTC_5x5x4", 0, 1, 1],
    47: ["ASTC_5x5x5", 0, 1, 1],
    48: ["ASTC_6x5x5", 0, 1, 1],
    49: ["ASTC_6x6x5", 0, 1, 1],
    50: ["ASTC_6x6x6", 0, 1, 1]
}


def get_pixel_format_code(pixel_format_name):
    for pixel_format_code in pixel_formats:
        pixel_format = pixel_formats[pixel_format_code]
        if pixel_format[0] == pixel_format_name:
            return pixel_format_code
    return None


class PVR:
    def __init__(self, file_path):
        self.file_path = file_path
        self.version = 0
        self.flags = 0
        self.pixel_format = 0
        self.color_space = 0
        self.channel_type = 0
        self.height = 0
        self.width = 0
        self.depth = 0
        self.num_surfaces = 0
        self.num_faces = 0
        self.num_mipmaps = 0
        self.metadata_size = 0
        self.image_data_size = 0
        self.image_data = 0
        self.source_checksum = None
        self.meta_texture_atlas = None
        self.meta_normal_map = None
        self.meta_cube_map_order = None
        self.meta_texture_orientation = None
        self.meta_texture_border = None
        self.meta_padding = None

    def load(self):
        stream = FileStream(self.file_path, "rb")

        # parse header
        self.version = stream.read_u32()
        if self.version == 0x50565203:
            stream.set_endian(FileStream.BIG_ENDIAN)
        self.flags = stream.read_u32()
        self.pixel_format = stream.read_u64()
        self.color_space = stream.read_u32()
        self.channel_type = stream.read_u32()
        self.height = stream.read_u32()
        self.width = stream.read_u32()
        self.depth = stream.read_u32()
        self.num_surfaces = stream.read_u32()
        self.num_faces = stream.read_u32()
        self.num_mipmaps = stream.read_u32()
        self.metadata_size = stream.read_u32()

        # parse metadata
        metadata_end = stream.get_position() + self.metadata_size
        while stream.get_position() < metadata_end:
            fourcc = stream.read_u32()
            key = stream.read_u32()
            size = stream.read_u32()
            if fourcc == 0x03525650:    # 'PVR\03'
                if key == 0:            # texture atlas information
                    self.meta_texture_atlas = stream.read_u8_array(size)
                elif key == 1:          # normal map information
                    self.meta_normal_map = stream.read_u8_array(size)
                elif key == 2:          # cube map face order
                    self.meta_cube_map_order = stream.read_u8_array(size)
                elif key == 3:          # texture orientation
                    self.meta_texture_orientation = stream.read_u8_array(size)
                elif key == 4:          # texture border
                    self.meta_texture_border = stream.read_u8_array(size)
                elif key == 5:          # padding
                    self.meta_padding = stream.read_u8_array(size)
                else:
                    stream.set_position(size, io.SEEK_CUR)
            elif fourcc == 0x43524353:  # 'SCRC'
                # Custom metadata to hold source image checksum
                self.source_checksum = stream.read_u32()
            else:
                stream.set_position(size, io.SEEK_CUR)

        # parse image data
        self.image_data_size = 0
        for mip_level in range(self.num_mipmaps):
            self.image_data_size += self.get_mipmap_size(mip_level)
        self.image_data = stream.read_u8_array(self.image_data_size)

    def get_width(self):
        return self.width

    def get_height(self):
        return self.height

    def get_pixel_format_code(self):
        return self.pixel_format

    def get_pixel_format_name(self):
        if (self.pixel_format >> 32) == 0:
            return pixel_formats[self.pixel_format][0]
        else:
            format_string = ''
            channel_names = self.pixel_format >> 32
            channel_bits = self.pixel_format & 0xffffffff
            shift = 24
            while shift >= 0:
                channel_name = (channel_names >> shift) & 0xff
                channel_bit_count = (channel_bits >> shift) & 0xff
                if channel_name != 0 and channel_bits != 0:
                    format_string += chr(channel_name) + str(channel_bit_count)
                shift -= 8
            return format_string

    def get_bits_per_pixel(self):
        if (self.pixel_format >> 32) == 0:
            return pixel_formats[self.pixel_format][1]
        else:
            channel_bits = self.pixel_format & 0xffffffff
            bits_per_pixel = channel_bits >> 24
            bits_per_pixel += (channel_bits >> 16) & 0xff
            bits_per_pixel += (channel_bits >> 8) & 0xff
            bits_per_pixel += channel_bits & 0xff
            return bits_per_pixel

    def get_mipmap_size(self, mip_level):
        bits_per_pixel = self.get_bits_per_pixel()
        min_width = pixel_formats[self.pixel_format][2]
        min_height = pixel_formats[self.pixel_format][3]

        mip_width = self.width >> mip_level
        if mip_width < min_width:
            mip_width = min_width

        mip_height = self.height >> mip_level
        if mip_height < min_height:
            mip_height = min_height

        region_size = (mip_width * mip_height * bits_per_pixel) / 8
        face_size = region_size * self.depth
        surface_size = face_size * self.num_faces
        mip_size = surface_size * self.num_surfaces
        return mip_size

    def get_source_checksum(self):
        return self.source_checksum

    def set_source_checksum(self, checksum):
        if self.source_checksum is None:
            self.metadata_size += 16
        self.source_checksum = checksum

    def save(self):
        stream = ByteStream(ByteStream.LITTLE_ENDIAN)

        # Write header
        stream.write_u32(self.version)
        stream.write_u32(self.flags)
        stream.write_u64(self.pixel_format)
        stream.write_u32(self.color_space)
        stream.write_u32(self.channel_type)
        stream.write_u32(self.height)
        stream.write_u32(self.width)
        stream.write_u32(self.depth)
        stream.write_u32(self.num_surfaces)
        stream.write_u32(self.num_faces)
        stream.write_u32(self.num_mipmaps)
        stream.write_u32(self.metadata_size)

        # Write metadata
        if self.meta_texture_atlas is not None:
            stream.write_u32(0x03525650)
            stream.write_u32(0)
            stream.write_u32(len(self.meta_texture_atlas))
            stream.write_u8_array(self.meta_texture_atlas)

        if self.meta_normal_map is not None:
            stream.write_u32(0x03525650)
            stream.write_u32(1)
            stream.write_u32(len(self.meta_normal_map))
            stream.write_u8_array(self.meta_normal_map)

        if self.meta_cube_map_order is not None:
            stream.write_u32(0x03525650)
            stream.write_u32(2)
            stream.write_u32(len(self.meta_cube_map_order))
            stream.write_u8_array(self.meta_cube_map_order)

        if self.meta_texture_orientation is not None:
            stream.write_u32(0x03525650)
            stream.write_u32(3)
            stream.write_u32(len(self.meta_texture_orientation))
            stream.write_u8_array(self.meta_texture_orientation)

        if self.meta_texture_border is not None:
            stream.write_u32(0x03525650)
            stream.write_u32(4)
            stream.write_u32(len(self.meta_texture_border))
            stream.write_u8_array(self.meta_texture_border)

        if self.meta_padding is not None:
            stream.write_u32(0x03525650)
            stream.write_u32(5)
            stream.write_u32(len(self.meta_padding))
            stream.write_u8_array(self.meta_padding)

        if self.source_checksum is not None:
            # Custom metadata to hold source image checksum
            stream.write_u32(0x43524353)               # 'SCRC'
            stream.write_u32(0)
            stream.write_u32(4)
            stream.write_u32(self.source_checksum)

        # Write image data
        stream.write_u8_array(self.image_data)

        with open(self.file_path, "wb") as f:
            f.write(stream.get_data())
