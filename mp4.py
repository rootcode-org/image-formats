# Copyright is waived. No warranty is provided. Unrestricted use and modification is permitted.

# ISO/IEC Base Media file format is described here;
#   https://mpeg.chiariglione.org/standards/mpeg-4/iso-base-media-file-format/text-isoiec-14496-12-5th-edition
#
# Atom types and specification owner are listed at http://mp4ra.org/#/atoms
#
# HEIF file format is described here;
#   https://mpeg.chiariglione.org/standards/mpeg-h/image-file-format/text-isoiec-cd-23008-12-image-file-format

import io
import sys
import datetime
from streams import FileStream
from tiff import TIFF


class MP4:
    def __init__(self):
        self.url = None
        self.stream = None
        self.image_time = None
        self.exif_id = None

    def load(self, url):
        self.url = url
        self.stream = FileStream(url, 'rb', FileStream.BIG_ENDIAN)
        self.parse(self.stream.get_length())

    # Parse one or more sequential atoms and try to locate image creation time
    def parse(self, end_position):
        while self.stream.get_position() < end_position:
            # Parse the atom header
            atom_size = self.stream.read_u32()
            if atom_size == 0:                      # Size of 0 means 'parse to end of file'
                continue                            # We can ignore because we parse to the end of the atom list anyway
            atom_type = self.stream.read_string(4)
            atom_size = self.stream.read_u64() if atom_size == 1 else atom_size
            atom_type = self.stream.read_u8_array(8) if atom_type == 0x75756964 else atom_type
            atom_version = 0
            atom_flags = 0

            # These atoms are containers for other atoms
            if atom_type in ['moov', 'udta', 'meta']:
                self.parse(self.stream.get_position() + atom_size - 8)

            # Parse Movie Header atom
            elif atom_type == 'mvhd':
                self.version = self.stream.read_u8()
                self.flags = self.stream.read_u8_array(3)
                self.creation_time = self.stream.read_u32()         # this is what we're looking for
                self.modification_time = self.stream.read_u32()
                self.time_scale = self.stream.read_u32()
                self.duration = self.stream.read_u32()
                self.preferred_rate = self.stream.read_u32()
                self.preferred_volume = self.stream.read_u16()
                self.stream.set_position(10, io.SEEK_CUR)        # skip reserved bytes
                self.matrix = self.stream.read_u8_array(36)
                self.preview_time = self.stream.read_u32()
                self.preview_duration = self.stream.read_u32()
                self.poster_time = self.stream.read_u32()
                self.selection_time = self.stream.read_u32()
                self.selection_duration = self.stream.read_u32()
                self.current_time = self.stream.read_u32()
                self.next_track_id = self.stream.read_u32()

                # Convert the creation time to a datetime object
                if self.creation_time != 0:
                    mac_unix_epoch_diff = 2082844800        # Difference in seconds between mac and unix epoch times
                    timestamp = self.creation_time - mac_unix_epoch_diff
                    self.image_time = datetime.datetime.utcfromtimestamp(timestamp)

            # Parse iTunes metadata
            elif atom_type == '\xa9day':
                data_size = self.stream.read_u16()
                data_language = self.stream.read_u16()
                time_string = self.stream.read_string(data_size)[0:19]
                try:
                    self.image_time = datetime.datetime.strptime(time_string, '%Y-%m-%dT%H:%M:%S')
                except ValueError:
                    pass

            # Parse Item Information Box (found in Apple HEIC files)
            elif atom_type == 'iinf':
                atom_version = self.stream.read_u8()
                atom_flags = self.stream.read_u24()
                if atom_version == 0:
                    item_count = self.stream.read_u16()
                    self.parse(self.stream.get_position() + atom_size - 14)
                else:
                    item_count = self.stream.read_u32()
                    self.parse(self.stream.get_position() + atom_size - 16)

            # Parse Item Information Entry (found in Apple HEIC files)
            # Here we're looking for the index to the Exif data, which we will then look up in the 'iloc' atom
            elif atom_type == 'infe':
                atom_version = self.stream.read_u8()
                atom_flags = self.stream.read_u24()
                if atom_version == 2:
                    item_id = self.stream.read_u16()
                    item_index = self.stream.read_u16()
                    item_type = self.stream.read_string(4)
                    item_name = self.stream.read_nt_string()
                    if item_type == 'Exif':
                        self.exif_id = item_id
                    else:
                        self.stream.set_position(atom_size - 21, whence=io.SEEK_CUR)
                else:
                    sys.exit('Unsupported INFE atom version')

            # Parse Item Location Box (found in Apple HEIC files)
            elif atom_type == 'iloc':
                atom_version = self.stream.read_u8()
                atom_flags = self.stream.read_u24()
                offset_size = self.stream.read_u8()
                length_size = offset_size & 0x0f
                offset_size >>= 4
                base_offset_size = self.stream.read_u8()
                index_size = base_offset_size & 0x0f
                base_offset_size >>= 4
                item_count = self.stream.read_u16() if atom_version < 2 else self.stream.read_u32()
                extent_offset = extent_length = 0
                for i in range(item_count):
                    item_id = self.stream.read_u16() if atom_version < 2 else self.stream.read_u32()
                    if atom_version == 1 or atom_version == 2:
                        construction_method = self.stream.read_u16() & 0x000f
                    else:
                        construction_method = 0
                    data_reference_index = self.stream.read_u16()
                    if base_offset_size > 0:
                        base_offset = self.stream.read_u32() if base_offset_size == 4 else self.stream.read_u64()
                    else:
                        base_offset = 0
                    extent_count = self.stream.read_u16()
                    for j in range(extent_count):
                        if (atom_version == 1 or atom_version == 2) and index_size > 0:
                            extent_index = self.stream.read_u32() if index_size == 4 else self.stream.read_u64()
                        else:
                            extent_index = 0
                        extent_offset = self.stream.read_u32() if offset_size == 4 else self.stream.read_u64()
                        extent_length = self.stream.read_u32() if length_size == 4 else self.stream.read_u64()

                    # If this is the Exif item then decode it
                    if item_id == self.exif_id:
                        self.stream.push_position(extent_offset)
                        # Read Exif marker
                        marker_length = self.stream.read_u32()
                        marker = self.stream.read_string(4)
                        if marker != 'Exif':
                            sys.exit('Invalid exif marker')
                        self.stream.set_position(marker_length-4, io.SEEK_CUR)
                        # Parse Exif to extract creation date
                        t = TIFF()
                        t.init(self.stream)
                        t.parse()
                        self.image_time = t.get_image_time()
                        self.stream.pop_position()

            # All other types are skipped
            else:
                self.stream.set_position(atom_size - 8, io.SEEK_CUR)

    def get_image_time(self):
        return self.image_time
