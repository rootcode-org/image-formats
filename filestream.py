# Copyright is waived. No warranty is provided. Unrestricted use and modification is permitted.

"""
Read/Write a stream of bytes from/to a file
"""

import os
import io
from stream import Stream


class FileStream(Stream):

    def __init__(self, file_name, mode, endian=None):
        Stream.__init__(self, endian)
        self.handle = io.open(file_name, mode)
        self.length = os.path.getsize(file_name)
        self.position_stack = []

    def close(self):
        self.handle.close()

    def set_position(self, position, whence=io.SEEK_SET):
        self.handle.seek(position, whence)

    def get_position(self):
        return self.handle.tell()

    def push_position(self, new_position):
        current_position = self.get_position()
        self.position_stack.append(current_position)
        self.set_position(new_position)
        return current_position

    def pop_position(self):
        self.set_position(self.position_stack.pop())

    def get_remaining(self):
        return self.length - self.handle.tell()

    def is_eof(self):
        return self.handle.tell() == self.length

    def write_u8(self, value):
        self.handle.write(bytes([value]))
        self.length += 1

    def write_u8_array(self, data):
        self.handle.write(data)
        self.length += len(data)

    def read_u8(self):
        return ord(self.handle.read(1))

    def read_u8_array(self, length):
        return bytearray(self.handle.read(length))

    def flush(self):
        self.handle.flush()
