# settings.py
#
#   Non-Volatile Memory / Settings Manager


import sys
from microcontroller import nvm
import struct


class Settings:

    OFFSET_CI = 0       # Connection Interval Byte Offset (1 bytes)
    OFFSET_ZERO = 1     # Zero Point Calibration (4 bytes)
    OFFSET_SCALE = 5    # Unit Scale Factor Calibration (8 bytes)

    OFFSET_END = 9

    def get_connectionInterval(self):
        return int.from_bytes(nvm[self.OFFSET_CI:self.OFFSET_ZERO],sys.byteorder)

    def set_connectionInterval(self,interval):
        if (interval <= 255):
            nvm[self.OFFSET_CI:self.OFFSET_ZERO] = interval.to_bytes(1,sys.byteorder)

    def get_tare(self):
        [x] = struct.unpack("f",nvm[self.OFFSET_ZERO:self.OFFSET_SCALE])
        return x

    def set_tare(self,offset):
        nvm[self.OFFSET_ZERO:self.OFFSET_SCALE] = struct.pack("f",offset)

    def get_calibration(self):
        [x] = struct.unpack("f",nvm[self.OFFSET_SCALE:self.OFFSET_END])
        return x

    def set_calibration(self,offset):
        nvm[self.OFFSET_SCALE:self.OFFSET_END] = struct.pack("f",offset)


