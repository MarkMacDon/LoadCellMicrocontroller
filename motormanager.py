# motormanager.py
#
# Vibration Motor Manager for Power and Pulse Patterns

import board
import time
import pwmio


class MotorManager:

    def __init__(self):

        # Set up motor control
        self.motor = pwmio.PWMOut(board.D13, frequency=5000, duty_cycle=0)

        # Timers
        self.onTime = 0.0
        self.offTime = 0.0

        self.onInterval = 0.0
        self.offInterval = 0.0

        self.POWER_CUTOFF = 0.2    # Threshold at which to turn motor off to avoid low loads that won't spin it anyhow

        self.updateTimeRef = time.monotonic()

        # Power intensity
        self.powerLevel = 1.0


    def update(self):
        if (self.onInterval != 0.0):
            if (time.monotonic() < self.onTime):
                # To avoid loading the motor at low values, trim duty cycles below threshld
                if (self.powerLevel > self.POWER_CUTOFF):
                    self.motor.duty_cycle = int(self.powerLevel*65535.0)
                else:
                    self.motor.duty_cycle = 0

            elif (time.monotonic() < self.offTime):
                self.motor.duty_cycle = 0
            else:
                self.onTime = time.monotonic()+self.onInterval
                self.offTime = self.onTime+self.offInterval

        pass

    def setPower(self,power):
        power = min(power,1.0)
        power = max(power,0.0)
        self.powerLevel = power

    def motorOn(self):
        self.setPulse(1.0,0.0)  # Always on

    def motorOff(self):
        self.motor.duty_cycle = 0   # Stop motor right away
        self.setPulse(0.0,1.0) # Always off

    def setPulse(self,onTime,offTime):
        self.onInterval = onTime
        self.offInterval = offTime
        self.onTime = time.monotonic()+self.onInterval
        self.offTime = self.onTime+self.offInterval

    def updatePulse(self,onTime,offTime):
        self.onInterval = onTime
        self.offInterval = offTime
