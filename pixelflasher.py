# pixelflasher.py
#
# NeoPixel Manager for State/Blinking Patterns

import neopixel
import board
import time

class PixelFlasher:

    def __init__(self):
        self.pixel = neopixel.NeoPixel(board.NEOPIXEL, 1, brightness=0.2, auto_write=True)
        self.currentColor = (0,0,0)
        self.pixel.fill(self.currentColor)

        self.onTime = 0.0
        self.offTime = 0.0

        self.onInterval = 0.0
        self.offInterval = 0.0

        self.updateTimeRef = time.monotonic()

        pass

    def update(self):
        if (self.onInterval != 0.0):
            if (time.monotonic() < self.onTime):
                self.pixel.fill(self.currentColor)
            elif (time.monotonic() < self.offTime):
                self.pixel.fill((0,0,0))
            else:
                self.onTime = time.monotonic()+self.onInterval
                self.offTime = self.onTime+self.offInterval

        pass

    def setDisconnectedState(self):
        self.setFlash((0,0,127),0.25,0.5)

    def setNegotiatingState(self):
        self.setFlash((0,0,64),1.0,0.0)

    def setConnectedState(self):
        self.setFlash((0,64,0),1.0,0.0)

    def setFlash(self,color,onTime,offTime):
        self.currentColor = color
        self.onInterval = onTime
        self.offInterval = offTime
        self.onTime = time.monotonic()+self.onInterval
        self.offTime = self.onTime+self.offInterval