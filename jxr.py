# Copyright is waived. No warranty is provided. Unrestricted use and modification is permitted.

# For JXR format see https://www.itu.int/rec/T-REC-T.832-201906-I/en

import io
from streams import ByteStream, FileStream

pixel_formats = {
    0x05: 'BlackWhite',
    0x08: '8bppGray',
    0x09: '16bppBGR555',
    0x0a: '16bppBGR565',
    0x0b: '16bppGray',
    0x0c: '24bppBGR',
    0x0d: '24bppRGB',
    0x0e: '32bppBGR',
    0x0f: '32bppBGRA',
    0x10: '32bppPBGRA',
    0x11: '32bppGrayFloat',
    0x12: '48bppRGBFixedPoint',
    0x13: '16bppGrayFixedPoint',
    0x14: '32bppBGR101010',
    0x15: '48bppRGB',
    0x16: '64bppRGBA',
    0x17: '64bppPRGBA',
    0x18: '96bppRGBFixedPoint',
    0x19: '128bppRGBAFloat',
    0x1a: '128bppPRGBAFloat',
    0x1b: '128bppRGBFloat',
    0x1c: '32bppCMYK',
    0x1d: '64bppRGBAFixedPoint',
    0x1e: '128bppRGBAFixedPoint',
    0x1f: '64bppCMYK',
    0x20: '24bpp3Channels',
    0x21: '32bpp4Channels',
    0x22: '40bpp5Channels',
    0x23: '48bpp6Channels',
    0x24: '56bpp7Channels',
    0x25: '64bpp8Channels',
    0x26: '48bpp3Channels',
    0x27: '64bpp4Channels',
    0x28: '80bpp5Channels',
    0x29: '96bpp6Channels',
    0x2a: '112bpp7Channels',
    0x2b: '128bpp8Channels',
    0x2c: '40bppCMYKAlpha',
    0x2d: '80bppCMYKAlpha',
    0x2e: '32bpp3ChannelsAlpha',
    0x2f: '40bpp4ChannelsAlpha',
    0x30: '48bpp5ChannelsAlpha',
    0x31: '56bpp6ChannelsAlpha',
    0x32: '64bpp7ChannelsAlpha',
    0x33: '72bpp8ChannelsAlpha',
    0x34: '64bpp3ChannelsAlpha',
    0x35: '80bpp4ChannelsAlpha',
    0x36: '96bpp5ChannelsAlpha',
    0x37: '112bpp6ChannelsAlpha',
    0x38: '128bpp7ChannelsAlpha',
    0x39: '144bpp8ChannelsAlpha',
    0x3a: '64bppRGBAHalf',
    0x3b: '48bppRGBHalf',
    0x3d: '32bppRGBE',
    0x3e: '16bppGrayHalf',
    0x3f: '32bppGrayFixedPoint',
    0x40: '64bppRGBFixedPoint',
    0x41: '128bppRGBFixedPoint',
    0x42: '64bppRGBHalf',
    0x43: '80bppCMYKDIRECTAlpha',
    0x44: '12bppYCC420',
    0x45: '16bppYCC422',
    0x46: '20bppYCC422',
    0x47: '32bppYCC422',
    0x48: '24bppYCC444',
    0x49: '30bppYCC444',
    0x4a: '48bppYCC444',
    0x4b: '48bppYCC444FixedPoint',
    0x4c: '20bppYCC420Alpha',
    0x4d: '24bppYCC422Alpha',
    0x4e: '30bppYCC422Alpha',
    0x4f: '48bppYCC422Alpha',
    0x50: '32bppYCC444Alpha',
    0x51: '40bppYCC444Alpha',
    0x52: '64bppYCC444Alpha',
    0x53: '64bppYCC444AlphaFixedPoint',
    0x54: '32bppCMYKDIRECT',
    0x55: '64bppCMYKDIRECT',
    0x56: '40bppCMYKDIRECTAlpha',
}


class JXR:
    def __init__(self):
        self.file_path = None
        self.pixel_format = 0
        self.image_width = 0
        self.image_height = 0
        self.image_offset = 0
        self.image_byte_count = 0
        self.image_data = None
        self.source_checksum = 0

    def load(self, file_path):
        self.file_path = file_path
        stream = FileStream(self.file_path, 'rb')
        identifier = stream.read_u32()
        if identifier != 0x01bc4949:
            raise ValueError

        next_ifd_offset = stream.read_u32()
        while next_ifd_offset != 0:
            stream.set_position(next_ifd_offset)
            num_entries = stream.read_u16()
            for i in range(num_entries):
                field_tag = stream.read_u16()
                element_type = stream.read_u16()
                num_elements = stream.read_u32()
                element_type_size = [0, 1, 1, 2, 4, 8, 1, 1, 2, 4, 8, 4, 8][element_type]
                element_size = element_type_size * num_elements

                if field_tag == 0xbc01:
                    # pixel format
                    offset = stream.read_u32()
                    stream.push_position(offset + 15)       # first 15 bytes of the pixel format are irrelevant
                    self.pixel_format = stream.read_u8()  # last byte is the only significant byte
                    stream.pop_position()
                elif field_tag == 0xbc80:
                    self.image_width = self.__read_element(stream, element_size)
                elif field_tag == 0xbc81:
                    self.image_height = self.__read_element(stream, element_size)
                elif field_tag == 0xbcc0:
                    self.image_offset = self.__read_element(stream, element_size)
                elif field_tag == 0xbcc1:
                    self.image_byte_count = self.__read_element(stream, element_size)
                elif field_tag == 0xcfc5:                   # Custom tag for source image checksum
                    self.source_checksum = stream.read_u32()
                else:
                    stream.set_position(element_size, io.SEEK_CUR)
            next_ifd_offset = stream.read_u32()

        stream.set_position(self.image_offset)
        self.image_data = stream.read_u8_array(self.image_byte_count)

    @staticmethod
    def __read_element(stream, element_size):
        if element_size == 1:
            return stream.read_u8()
        elif element_size == 2:
            return stream.read_u16()
        else:
            return stream.read_u32()

    def get_width(self):
        return self.image_width

    def get_height(self):
        return self.image_height

    def get_pixel_format(self):
        return self.pixel_format

    def get_pixel_format_name(self):
        return pixel_formats[self.pixel_format]

    def get_source_checksum(self):
        return self.source_checksum

    def set_source_checksum(self, checksum):
        self.source_checksum = checksum

    def save(self):
        stream = ByteStream()

        # Write header
        stream.write_u32(0x01bc4949)            # file identifier
        stream.write_u32(0x00000008)            # offset to IFD table

        # Write IFD table
        ifd_length = 2 + (12 * 6) + 4

        stream.write_u16(6)                   # IFD table contains 6 entries

        stream.write_u16(0xbc01)              # pixel format
        stream.write_u16(0x01)                # BYTE type
        stream.write_u32(0x10)                  # pixel format consists of 16 bytes
        stream.write_u32(8 + ifd_length)        # pixel format bytes follow header and ifd table

        stream.write_u16(0xbc80)              # image width
        stream.write_u16(0x04)                # ULONG type
        stream.write_u32(0x01)                  # one element
        stream.write_u32(self.image_width)

        stream.write_u16(0xbc81)              # image height
        stream.write_u16(0x04)                # ULONG type
        stream.write_u32(0x01)                  # one element
        stream.write_u32(self.image_height)

        stream.write_u16(0xbcc0)              # image offset
        stream.write_u16(0x04)                # ULONG type
        stream.write_u32(0x01)                  # one element
        stream.write_u32(8 + ifd_length + 16)   # image data follows header, ifd table, and pixel format

        stream.write_u16(0xbcc1)              # image byte count
        stream.write_u16(0x04)                # ULONG type
        stream.write_u32(0x01)                  # one element
        stream.write_u32(self.image_byte_count)

        # custom tag holding source image checksum
        stream.write_u16(0xcfc5)              # custom tag for source image checksum
        stream.write_u16(0x01)                # BYTE type
        stream.write_u32(0x04)                  # contains 4 bytes
        stream.write_u32(self.source_checksum)

        stream.write_u32(0)                     # IFD terminator

        # write pixel format bytes
        stream.write_u8_array(bytearray([0x24, 0xC3, 0xDD, 0x6F, 0x03, 0x4E, 0xFE, 0x4B, 0xB1, 0x85, 0x3D, 0x77, 0x76, 0x8D, 0xC9]))
        stream.write_u8(self.pixel_format)

        # write image data
        stream.write_u8_array(self.image_data)

        with open(self.file_path, 'wb') as f:
            f.write(stream.get_data())
