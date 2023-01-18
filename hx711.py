# hx711.py
#
#   Module for heading HX711 load cell amplifier


import time
import digitalio


class HX711:

    def __init__(self, dout, pd_sck, gain=128) -> None:
        self.pd_sck = pd_sck
        self.dout = dout

        self.pd_sck.switch_to_output()
        self.dout.switch_to_input(pull=digitalio.Pull.UP)

        if (gain == 128):
            self.GAIN = 1
        elif (gain == 64):
            self.GAIN = 3
        elif (gain == 32):
            self.GAIN = 2


        self.lastVal = 0

        time.sleep(1)


    def convertFromTwosComplement24bit(self, inputValue):
        return -(inputValue & 0x800000) + (inputValue & 0x7fffff)

    def is_ready(self):
        return self.dout.value  == 0

    def readNextBit(self):
       # Clock HX711 Digital Serial Clock (PD_SCK).  DOUT will be
       # ready 1us after PD_SCK rising edge, so we sample after
       # lowering PD_SCL, when we know DOUT will be stable.
       self.pd_sck.value = True
       self.pd_sck.value = False
       value = self.dout.value

       # Convert Boolean to int and return it.
       return int(value)

    def readNextByte(self):
        byteValue = 0

       # Read bits and build the byte from top, or bottom, depending
       # on whether we are in MSB or LSB bit mode.
        for x in range(8):
            byteValue <<= 1
            byteValue |= self.readNextBit()
        return byteValue

    # Optimized version of byte read loop
    def readNextByteFast(self):
        byteValue = 0

        sck = self.pd_sck
        dout = self.dout

        # Unroll loop
        sck.value = True
        sck.value = False
        if (dout.value):
            byteValue |= 1

        byteValue <<= 1
        sck.value = True
        sck.value = False
        if (dout.value):
            byteValue |= 1

        byteValue <<= 1
        sck.value = True
        sck.value = False
        if (dout.value):
            byteValue |= 1

        byteValue <<= 1
        sck.value = True
        sck.value = False
        if (dout.value):
            byteValue |= 1

        byteValue <<= 1
        sck.value = True
        sck.value = False
        if (dout.value):
            byteValue |= 1

        byteValue <<= 1
        sck.value = True
        sck.value = False
        if (dout.value):
            byteValue |= 1

        byteValue <<= 1
        sck.value = True
        sck.value = False
        if (dout.value):
            byteValue |= 1

        byteValue <<= 1
        sck.value = True
        sck.value = False
        if (dout.value):
            byteValue |= 1

        return byteValue

    def readRawBytes(self):
        # Wait for and get the Read Lock, incase another thread is already
        # driving the HX711 serial interface.

        # Wait until HX711 is ready for us to read a sample.
        while not self.is_ready():
            pass

        # Read three bytes of data from the HX711.
        firstByte  = self.readNextByteFast()
        secondByte = self.readNextByteFast()
        thirdByte  = self.readNextByteFast()

        # HX711 Channel and gain factor are set by number of bits read
        # after 24 data bits.
        for i in range(self.GAIN):
           # Clock a bit out of the HX711 and throw it away.
           self.pd_sck.value = True
           self.pd_sck.value = False

        # Return an orderd list of raw byte values.
        return [firstByte, secondByte, thirdByte]

    def read_long(self):
        # Get a sample from the HX711 in the form of raw bytes.
        dataBytes = self.readRawBytes()

        # Join the raw bytes into a single 24bit 2s complement value.
        twosComplementValue = ((dataBytes[0] << 16) |
                               (dataBytes[1] << 8)  |
                               dataBytes[2])

        # Convert from 24bit twos-complement to a signed value.
        signedIntValue = self.convertFromTwosComplement24bit(twosComplementValue)

        # Record the latest sample value we've read.
        self.lastVal = signedIntValue

        # Return the sample value we've read from the HX711.
        return int(signedIntValue)

    # A median-based read method, might help when getting random value spikes
    # for unknown or CPU-related reasons
    def read_median(self, times=3):
       if times <= 0:
          raise ValueError("HX711::read_median(): times must be greater than zero!")

       # If times == 1, just return a single reading.
       if times == 1:
          return self.read_long()

       valueList = []

       for x in range(times):
          valueList += [self.read_long()]

       valueList.sort()

       # If times is odd we can just take the centre value.
       if (times & 0x1) == 0x1:
          return valueList[len(valueList) // 2]
       else:
          # If times is even we have to take the arithmetic mean of
          # the two middle values.
          midpoint = len(valueList) / 2
          return sum(valueList[midpoint:midpoint+2]) / 2.0


    def get_value(self, times=3):
        return self.read_median(times)