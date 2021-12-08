# Copyright is waived. No warranty is provided. Unrestricted use and modification is permitted.

"""
Base class for ByteStream, FileStream and SocketStream
"""

import struct


class Stream:

    LITTLE_ENDIAN = 0
    BIG_ENDIAN = 1

    def __init__(self, endian=None):
        self.length = 0
        self.endian = endian if endian else self.LITTLE_ENDIAN
        self.endian_stack = []

    def get_length(self):
        return self.length

    def set_endian(self, value):
        self.endian = value

    def get_endian(self):
        return self.endian

    def push_endian(self, new_value=None):
        self.endian_stack.append(self.endian)
        if new_value is not None:
            self.endian = new_value

    def pop_endian(self):
        self.endian = self.endian_stack.pop()

    def write_u8(self, value):
        raise ("Virtual function")

    def write_u8_array(self, data):
        raise ("Virtual function")

    def write_bool(self, value):
        self.write_u8(1 if value else 0)

    def write_u16(self, value):
        if self.endian == self.LITTLE_ENDIAN:
            self.write_u8(value & 0xff)
            self.write_u8(value >> 8)
        else:
            self.write_u8(value >> 8)
            self.write_u8(value & 0xff)

    def write_u24(self, value):
        if self.endian == self.LITTLE_ENDIAN:
            self.write_u8(value & 0xff)
            self.write_u8((value >> 8) & 0xff)
            self.write_u8(value >> 16)
        else:
            self.write_u8(value >> 16)
            self.write_u8((value >> 8) & 0xff)
            self.write_u8(value & 0xff)

    def write_u32(self, value):
        if self.endian == self.LITTLE_ENDIAN:
            self.write_u16(value & 0xffff)
            self.write_u16(value >> 16)
        else:
            self.write_u16(value >> 16)
            self.write_u16(value & 0xffff)

    def write_u64(self, value):
        if self.endian == self.LITTLE_ENDIAN:
            self.write_u32(value & 0xffffffff)
            self.write_u32(value >> 32)
        else:
            self.write_u32(value >> 32)
            self.write_u32(value & 0xffffffff)

    def write_f32(self, value):
        if self.endian == self.LITTLE_ENDIAN:
            value = struct.pack('<f', value)
        else:
            value = struct.pack('>f', value)
        self.write_u8_array(value)

    def write_f64(self, value):
        if self.endian == self.LITTLE_ENDIAN:
            value = struct.pack('<d', value)
        else:
            value = struct.pack('>d', value)
        self.write_u8_array(value)

    # variable length unsigned quantity
    # value is stored 7 bits at a time in little-endian order; last value has MSB of 0
    def write_vluq(self, value):
        while value > 0x7f:
            self.write_u8((value & 0x7f) + 0x80)
            value >>= 7
        self.write_u8(value)

    # variable length signed quantity
    # same as VLUQ but the sign is stored in the low bit
    def write_vlsq(self, value):
        sign = 1 if value < 0 else 0
        value = (abs(value) << 1) + sign
        self.write_vluq(value)

    def write_string(self, string):
        string_data = string.encode("latin_1")
        self.write_u8_array(string_data)

    # null terminated string
    def write_nt_string(self, string):
        self.write_string(string)
        self.write_u8(0)

    # string preceded by length as a variable-length-unsigned-quantity
    def write_vluq_string(self, string):
        string_data = string.encode("latin_1")
        self.write_vluq(len(string_data))
        self.write_u8_array(string_data)

    def read_u8(self):
        raise ("Virtual function")

    def read_u8_array(self, length):
        raise ("Virtual function")

    def read_bool(self):
        value = self.read_u8()
        return False if value == 0 else True

    def read_u16(self):
        if self.endian == self.LITTLE_ENDIAN:
            value = self.read_u8() + (self.read_u8() << 8)
        else:
            value = (self.read_u8() << 8) + self.read_u8()
        return value

    def read_u24(self):
        if self.endian == self.LITTLE_ENDIAN:
            value = self.read_u8() + (self.read_u8() << 8) + (self.read_u8() << 16)
        else:
            value = (self.read_u8() << 16) + (self.read_u8() << 8) + self.read_u8()
        return value

    def read_u32(self):
        if self.endian == self.LITTLE_ENDIAN:
            value = self.read_u16() + (self.read_u16() << 16)
        else:
            value = (self.read_u16() << 16) + self.read_u16()
        return value

    def read_u64(self):
        if self.endian == self.LITTLE_ENDIAN:
            value = self.read_u32() + (self.read_u32() << 32)
        else:
            value = (self.read_u32() << 32) + self.read_u32()
        return value

    def read_f32(self):
        data = self.read_u8_array(4)
        if self.endian == self.LITTLE_ENDIAN:
            return struct.unpack('<f', data)[0]
        else:
            return struct.unpack('>f', data)[0]

    def read_f64(self):
        data = self.read_u8_array(8)
        if self.endian == self.LITTLE_ENDIAN:
            return struct.unpack('<d', data)[0]
        else:
            return struct.unpack('>d', data)[0]

    # variable length unsigned quantity
    # value is stored 7 bits at a time in little-endian order; last value has MSB of 0
    def read_vluq(self):
        accumulator = shift = 0
        value = self.read_u8()
        while value > 0x7f:
            accumulator += (value & 0x7f) << shift
            shift += 7
            value = self.read_u8()
        return accumulator + (value << shift)

    # variable length signed quantity
    # same as VLUQ but the sign is stored in the low bit
    def read_vlsq(self):
        value = self.read_vluq()
        sign = value & 1
        value >>= 1
        return -value if sign else value

    def read_string(self, length):
        value = self.read_u8_array(length)
        return value.decode("latin_1")

    # null terminated string; null character is not returned with string
    def read_nt_string(self):
        output = bytearray()
        value = self.read_u8()
        while value != 0:
            output.append(value)
            value = self.read_u8()
        return output.decode("latin_1")

    # CR/LF terminated string; CR/LF is returned with string
    def read_crlf_string(self):
        output = bytearray()
        value = self.read_u8()
        while value != 0x0d:
            output.append(value)
            value = self.read_u8()
        output.append(value)
        output.append(self.read_u8())      # Expected to be 0x0a (line feed)
        return output.decode("latin_1")

    # string preceded by length as a variable-length-unsigned-quantity
    def read_vluq_string(self):
        length = self.read_vluq()
        return self.read_string(length)
