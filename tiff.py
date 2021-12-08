# Copyright is waived. No warranty is provided. Unrestricted use and modification is permitted.

# For TIFF format see http://www.fileformat.info/format/tiff/egff.htm
# For EXIF tags see http://www.sno.phy.queensu.ca/~phil/exiftool/TagNames/EXIF.html

import datetime
from filestream import FileStream


class TIFF:
    def __init__(self):
        self.url = None
        self.stream = None
        self.ifd_start = 0
        self.image_time = None

    def init(self, stream):
        self.stream = stream

    def open(self, url):
        self.url = url
        self.stream = FileStream(url, "rb")

    def parse(self):
        self.parse_header()
        next_ifd = self.parse_ifd()
        while next_ifd != 0:
            self.stream.set_position(self.ifd_start + next_ifd)
            next_ifd = self.parse_ifd()

    def parse_header(self):
        # All IFD offsets are relative to this position
        self.ifd_start = self.stream.get_position()

        # Determine the file byte order
        byte_order = self.stream.read_u16()
        if byte_order == 0x4949:
            self.stream.set_endian(self.stream.LITTLE_ENDIAN)
        elif byte_order == 0x4d4d:
            self.stream.set_endian(self.stream.BIG_ENDIAN)
        else:
            raise ValueError

        # Check signature value
        fortytwo = self.stream.read_u16()
        if fortytwo != 42:
            raise ValueError

        # Now we get the offset to the first IFD
        ifd_offset = self.stream.read_u32()
        self.stream.set_position(self.ifd_start + ifd_offset)

    def parse_ifd(self):
        num_entries = self.stream.read_u16()
        for i in range(num_entries):
            tag = self.stream.read_u16()
            type = self.stream.read_u16()
            count = self.stream.read_u32()
            offset = self.ifd_start + self.stream.read_u32()

            # This tag provides an offset to another IFD
            if tag == 0x8769:             # ExifOffset
                self.stream.push_position(offset)
                self.parse_ifd()
                self.stream.pop_position()

            # If tag is one of ModifyDate, DateTimeOriginal or CreateDate then attempt to extract a timestamp
            elif tag in [0x0132, 0x9003, 0x9004]:
                self.stream.push_position(offset)
                time_string = self.stream.read_string(count - 1)
                self.stream.pop_position()
                if time_string[0:4] != "0000":
                    try:
                        self.image_time = datetime.datetime.strptime(time_string, "%Y:%m:%d %H:%M:%S")
                    except ValueError:
                        # Sometimes dates can be malformed, e.g. Feb 29 in a non-leap year. Attempt to handle this.
                        try:
                            dt = datetime.datetime.strptime(time_string[0:7], "%Y:%m")
                            days = int(time_string[8:10])
                            delta = datetime.timedelta(days-1)
                            self.image_time = dt + delta
                        except ValueError:
                            pass
            else:
                pass

        next_ifd = self.stream.read_u32()
        return next_ifd

    def get_image_time(self):
        return self.image_time
