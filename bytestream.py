# Copyright is waived. No warranty is provided. Unrestricted use and modification is permitted.

"""
Read/Write a stream of bytes from/to a bytearray
"""

from stream import Stream


class ByteStream(Stream):

    SEEK_SET = 0
    SEEK_CUR = 1
    SEEK_END = 2

    def __init__(self, endian=None):
        Stream.__init__(self, endian)
        self.data = bytearray()
        self.read_position = 0        # position is used for read operations only
        self.read_position_stack = []

    def reset(self):
        self.data = bytearray()
        self.length = 0
        self.read_position = 0
        self.read_position_stack = []

    def set_data(self, data, length=None):
        self.data = bytearray(data)
        if length:
            self.length = length
        else:
            self.length = len(self.data)
        self.read_position = 0

    def get_data(self):
        return self.data

    # position is for read operations only; write operations append to the bytearray
    def set_read_position(self, offset, whence=SEEK_SET):
        if whence == ByteStream.SEEK_SET:
            self.read_position = offset                 # offset must be zero or positive
        elif whence == ByteStream.SEEK_CUR:
            self.read_position += offset                # offset can be positive or negative
        else:
            self.read_position = self.length + offset   # offset must be negative

    def get_read_position(self):
        return self.read_position

    def push_read_position(self, new_position):
        current_position = self.get_read_position()
        self.read_position_stack.append(current_position)
        self.set_read_position(new_position)
        return current_position

    def pop_read_position(self):
        self.set_read_position(self.read_position_stack.pop())

    def is_eof(self):
        return self.read_position == self.length

    def write_u8(self, value):
        self.data.append(value)
        self.length += 1

    def write_u8_array(self, data):
        self.data += data
        self.length += len(data)

    def read_u8(self):
        value = self.data[self.read_position]
        self.read_position += 1
        return value

    def read_u8_array(self, length):
        value = self.data[self.read_position:self.read_position + length]
        self.read_position += length
        return value
