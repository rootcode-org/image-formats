# Copyright is waived. No warranty is provided. Unrestricted use and modification is permitted.

# For JPEG format see https://en.wikipedia.org/wiki/JPEG
# For app segments see http://www.ozhiker.com/electronics/pjmt/jpeg_info/app_segments.html
# For EXIF format see http://www.exif.org/Exif2-2.PDF

import io
import struct
import datetime
import xml.etree.ElementTree as ET
from filestream import FileStream
from bytestream import ByteStream
from tiff import TIFF


class JPEG:
    def __init__(self):
        self.file_path = None
        self.jfif_version = 0
        self.density_units = 0
        self.x_density = 0
        self.y_density = 0
        self.x_thumbnail = 0
        self.y_thumbnail = 0
        self.thumbnail_image = None
        self.quantization_tables = []
        self.huffman_tables = []
        self.comments = []
        self.frame_start = None
        self.scan_header = None
        self.scan_data = None
        self.exif = None
        self.image_time = None

    def load(self, file_path):
        self.file_path = file_path
        stream = FileStream(file_path, 'rb', FileStream.BIG_ENDIAN)

        while not stream.is_eof():
            marker = stream.read_u16()

            # start of image marker
            if marker == 0xffd8:
                pass

            # app0 marker (jfif/jfxx)
            elif marker == 0xffe0:
                length = stream.read_u16() - 2
                identifier = stream.read_u32()
                terminator = stream.read_u8()
                if identifier == 0x4a464946:            # 'jfif'
                    self.jfif_version = stream.read_u16()
                    self.density_units = stream.read_u8()
                    self.x_density = stream.read_u16()
                    self.y_density = stream.read_u16()
                    self.x_thumbnail = stream.read_u8()
                    self.y_thumbnail = stream.read_u8()
                    self.thumbnail_image = stream.read_u8_array(self.x_thumbnail * self.y_thumbnail * 3)
                else:
                    raise ValueError

            # app1/app3 markers
            elif marker == 0xffe1 or marker == 0xffe3:
                length = stream.read_u16() - 2
                position = stream.get_position()

                signature = stream.read_string(4)
                if signature == 'Exif' or signature == 'Meta':
                    stream.set_position(2, io.SEEK_CUR)
                    stream.push_endian()
                    t = TIFF()
                    t.init(stream)
                    t.parse()
                    stream.pop_endian()
                    stream.set_position(position + length)
                    if not self.image_time:
                        self.image_time = t.get_image_time()

                # Adobe 'http' metadata or 'XMP\x00' metadata
                elif signature == 'http' or signature == 'XMP\x00':
                    url_string = stream.read_nt_string()
                    text_length = length - len(url_string) - 5
                    text = stream.read_string(text_length)
                    text = text.rstrip(' \r\n\x00')
                    xml_root = ET.fromstring(text)
                    element = xml_root.find('.//{http://www.w3.org/1999/02/22-rdf-syntax-ns#}Description[@{http://ns.adobe.com/exif/1.0/}DateTimeOriginal]')
                    if element is not None:
                        timestamp = element.attrib['{http://ns.adobe.com/exif/1.0/}DateTimeOriginal'][0:19]
                        self.image_time = datetime.datetime.strptime(timestamp, '%Y-%m-%dT%H:%M:%S')
                else:
                    raise ValueError

            # app2 marker (icc profile)
            elif marker == 0xffe2:
                length = stream.read_u16() - 2
                stream.set_position(length, io.SEEK_CUR)

            # app4 marker (scalado/FlashPix/PreviewImage)
            elif marker == 0xffe4:
                # TODO - FlashPix format can contain the image date
                # see https://www.sno.phy.queensu.ca/~phil/exiftool/TagNames/FlashPix.html
                length = stream.read_u16() - 2
                stream.set_position(length, io.SEEK_CUR)

            # app10 marker (PhoTags)
            elif marker == 0xffea:
                length = stream.read_u16() - 2
                stream.set_position(length, io.SEEK_CUR)

            # app12 marker (Picture Info/Ducky)
            elif marker == 0xffec:
                length = stream.read_u16() - 2
                stream.set_position(length, io.SEEK_CUR)

            # app13 marker (Adobe IRB)
            elif marker == 0xffed:
                length = stream.read_u16() - 2

                # Parse IRB blocks
                # See 'Image Resource Blocks' in http://www.adobe.com/devnet-apps/photoshop/fileformatashtml/
                irb_end = stream.get_position() + length
                photoshop_version = stream.read_nt_string()
                while stream.get_position() < irb_end:
                    irb_signature = stream.read_string(4)
                    if irb_signature != '8BIM':
                        raise ValueError

                    resource_type = stream.read_u16()
                    resource_name_length = stream.read_u8()
                    resource_name = stream.read_string(resource_name_length)
                    if (resource_name_length & 1) == 0:
                        stream.set_position(1, io.SEEK_CUR)
                    resource_data_length = stream.read_u32()

                    if resource_type == 0x404:
                        # IPTC-NAA Record; See https://www.iptc.org/std/IIM/4.1/specification/IIMV4.1.pdf
                        # N.B. this record can be shorter than the resource_data_length specified; it appears the
                        # resource length is padded to the next word boundary
                        iptc_end = stream.get_position() + resource_data_length
                        while stream.get_position() < iptc_end - 3:
                            tag_marker = stream.read_u8()
                            record_number = stream.read_u8()
                            data_set_number = stream.read_u8()
                            data_field_count = stream.read_u16()

                            # Any of these record types can contain a date
                            # 1:70 (Date Sent), 2:30 (Release Date), 2:55 (Date Created), 2:62 (Digital Creation Date)
                            if (record_number == 1 and data_set_number == 70)\
                            or (record_number == 2 and data_set_number == 30)\
                            or (record_number == 2 and data_set_number == 55)\
                            or (record_number == 2 and data_set_number == 62):
                                date_string = stream.read_string(data_field_count)
                                self.image_time = datetime.datetime.strptime(date_string, '%Y%m%d')
                            else:
                                stream.set_position(data_field_count, io.SEEK_CUR)

                        # Adjust the stream position since it may not be in the correct place due to the IPTC
                        # record being shorter than actually specified in the resource length
                        stream.set_position(iptc_end)
                    else:
                        stream.set_position(resource_data_length, io.SEEK_CUR)

                    # Resources are always padded to the next 16-bit boundary
                    if (resource_data_length & 1) == 1:
                        stream.set_position(1, io.SEEK_CUR)

            # app14 marker (Adobe DCT)
            elif marker == 0xffee:
                length = stream.read_u16() - 2
                stream.set_position(length, io.SEEK_CUR)

            # quantization table marker
            elif marker == 0xffdb:
                length = stream.read_u16() - 2
                self.quantization_tables.append(stream.read_u8_array(length))

            # huffman table marker
            elif marker == 0xffc4:
                length = stream.read_u16() - 2
                self.huffman_tables.append(stream.read_u8_array(length))

            # start of frame marker (Baseline DCT)
            elif marker == 0xffc0:
                length = stream.read_u16() - 2
                self.frame_start = stream.read_u8_array(length)

            # start of frame marker (Progressive DCT)
            elif marker == 0xffc2:
                length = stream.read_u16() - 2
                self.frame_start = stream.read_u8_array(length)

            # define restart interval
            elif marker == 0xffdd:
                length = stream.read_u16() - 2
                stream.set_position(length, io.SEEK_CUR)

            # text comment
            elif marker == 0xfffe:
                length = stream.read_u16() - 2
                stream.set_position(length, io.SEEK_CUR)

            # start of scan marker
            elif marker == 0xffda:
                length = stream.read_u16() - 2
                self.scan_header = stream.read_u8_array(length)
                # Assume this marker is the last marker except for the end of image marker
                length = stream.get_length() - stream.get_position() - 2
                self.scan_data = stream.read_u8_array(length)
                break

            # end of image marker
            elif marker == 0xffd9:
                break

            # any other markers are unhandled for now
            else:
                raise ValueError

    def get_image_time(self):
        return self.image_time

    def get_source_checksum(self):
        # Retrieve the source checksum from a comment marker
        source_checksum = None
        for comment in self.comments:
            if len(comment) == 8:
                comment_value = struct.unpack('>Q', str(comment))[0]
                if (comment_value >> 32) == 0x53435243:                 # 'SCRC'
                    source_checksum = comment_value & 0xffffffff
        return source_checksum

    def set_source_checksum(self, checksum):
        # Store source image checksum in a comment marker
        comment_value = (0x53435243 << 32) + checksum           # 'SCRC' identifies comment as  'Source CRC checksum'
        comment_bytes = bytearray(struct.pack('>Q', comment_value))
        self.comments = [comment_bytes]

    def save(self, file_path):
        self.file_path = file_path
        stream = ByteStream(ByteStream.BIG_ENDIAN)

        # Write start of image marker
        stream.write_u16(0xffd8)

        # Write JFIF-APP0 marker
        stream.write_u16(0xffe0)          # jfif marker
        stream.write_u16(16)              # marker length
        stream.write_u32(0x4a464946)        # jfif-app0 identifier
        stream.write_u8(0)                # identifier terminator
        stream.write_u16(self.jfif_version)
        stream.write_u8(self.density_units)
        stream.write_u16(self.x_density)
        stream.write_u16(self.y_density)
        stream.write_u8(self.x_thumbnail)
        stream.write_u8(self.y_thumbnail)
        stream.write_u8_array(self.thumbnail_image)

        # Write Exif marker
        if self.exif:
            stream.write_u16(0xffe1)
            stream.write_u16(len(self.exif) + 2)
            stream.write_u8_array(self.exif)

        # Write comments
        for comment in self.comments:
            stream.write_u16(0xffef)
            stream.write_u16(len(comment) + 2)
            stream.write_u8_array(comment)

        # Write quantization tables
        for quant_table in self.quantization_tables:
            stream.write_u16(0xffdb)
            stream.write_u16(len(quant_table) + 2)
            stream.write_u8_array(quant_table)

        # Write frame start
        stream.write_u16(0xffc0)
        stream.write_u16(len(self.frame_start) + 2)
        stream.write_u8_array(self.frame_start)

        # Write huffman tables
        for huff_table in self.huffman_tables:
            stream.write_u16(0xffc4)
            stream.write_u16(len(huff_table) + 2)
            stream.write_u8_array(huff_table)

        # Write scan data
        stream.write_u16(0xffda)
        stream.write_u16(len(self.scan_header) + 2)
        stream.write_u8_array(self.scan_header)
        stream.write_u8_array(self.scan_data)

        # Write end of image
        stream.write_u16(0xffd9)

        with open(self.file_path, 'wb') as f:
            f.write(stream.get_data())
