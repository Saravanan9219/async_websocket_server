#! /bin/python3


class DataFrame(object):

    def __init__(self, data=None, payload=None, close=False):
        if data:
            self.raw_data = data
            self.fin = self.__get_fin()
            self.opcode = self.__get_opcode() 
            content_type_map = {
                0x1: 'text',
                0x2: 'binary',
                0x8: 'close'
            }
            self.__mask_starts = 2
            self.content_type = content_type_map.get(self.opcode)
            self.payload_length = self.__get_payload_length()
            self.masked = self.__is_masked()
            self.close = bool(self.content_type == 'close')
            if self.masked:
                self.mask_key = self.__get_mask_key()
            self.payload = self.__get_payload()

        elif payload:
            self.raw_data = b''
            self.close = close
            self.content_type = None
            self.opcode = None 
            self.payload_length = 0
            self.payload = b''
            self.fin = 0x1
            self.__set_payload(payload)
            self.raw_data = self.__generate_raw_data()
        else:
            raise Exception("No Raw data or payload")

    def __get_fin(self):
        frame_part = self.raw_data[0]
        fin = frame_part & 0x80
        if fin == 0x80:
            return True
        else:
            return False

    def __get_opcode(self):
        frame_part = self.raw_data[0]
        return frame_part & 0xf 
    
    def __get_payload_length(self):
        frame_part = self.raw_data[1]
        length = frame_part & 0x7f

        if length == 126:
            frame_part = bytes(self.raw_data[2:4])
            length = int.from_bytes(frame_part, 'big')
            self.__mask_starts = 4
        elif length == 127:
            frame_part = bytes(self.raw_data[2:10])
            length = int.from_bytes(frame_part, 'big')
            self.__mask_starts = 10

        return length

    def __is_masked(self):
        frame_part = self.raw_data[1]
        masked = frame_part & 0x80
        if masked == 0x80:
            return True
        else:
            return False

    def __get_mask_key(self):
        return self.raw_data[self.__mask_starts: self.__mask_starts + 4]

    def __get_payload(self):
        # revisit for faster implementation
        masked_payload = self.raw_data[-self.payload_length:]
        data = []
        for index, value in enumerate(masked_payload):
            if self.masked:
                mask_byte = self.mask_key[index % 4]
                unmasked_byte = value ^ mask_byte
            else:
                unmasked_byte = value
            data.append(unmasked_byte)
        data = bytes(data)
        if self.content_type == 'text':
            data = data.decode("utf-8")
        return data

    def __set_content_type(self, content_type):
        content_type_map = {
            'text': 0x1,
            'binary': 0x2,
            'close': 0x8
        }
        self.content_type = 'close' if self.close else content_type
        self.opcode = content_type_map.get(self.content_type)

    def __set_payload(self, payload, content_type='text'):
        payload_in_bytes = bytes(payload, 'utf-8')
        self.payload_length = len(payload_in_bytes)
        self.payload = payload_in_bytes
        self.__set_content_type(content_type)

    def __convert_to_bytes(self, int_value, nbytes=2):
        bin_value = bin(int_value)[2:].zfill(nbytes * 8)
        bytes_ = [
            int(bin_value[i:i+8], 2)
            for i in range(0, len(bin_value), 8)
        ]
        return bytes_

    def __generate_raw_data(self):
        self.masked = False
        self.mask_key = None
        self.bytes = []

        # process fin and opcode
        fin = self.fin << 7
        opcode = self.opcode 
        self.bytes.append(fin | opcode)

        # process masked and payload length
        masked = 0x1 << 7 if self.masked else 0x0 << 7

        if self.payload_length < 126:
            payload_length = self.payload_length
            extended_payload_length = bytes([])

        elif 65535 >= self.payload_length >= 126:
            payload_length = 126
            extended_payload_length = self.__convert_to_bytes(self.payload_length, nbytes=2)

        else: 
            payload_length = 127
            extended_payload_length = self.__convert_to_bytes(self.payload_length, nbytes=8)

        self.bytes.append(masked | payload_length)

        if extended_payload_length:
            self.bytes.extend(extended_payload_length)

        # mask key
        # self.bytes = self.bytes + [0, 0, 0, 0]

        self.header_bytes = bytes(self.bytes)
        self.raw_bytes = self.header_bytes + self.payload
        return self.raw_bytes


    def __repr__(self):
        try:
            return self.payload
        except AttributeError:
            return super(DataFrame, self).__repr__()

