import board
import digitalio
import time

from adafruit_ble import BLERadio
from adafruit_ble.advertising.standard import ProvideServicesAdvertisement
from adafruit_ble.services.nordic import UARTService

from adafruit_bluefruit_connect.packet import Packet

from hx711 import HX711
from pixelflasher import PixelFlasher
from datastreammanager import DataStreamManager
from settings import Settings
from motormanager import MotorManager


ble = BLERadio()
uart = UARTService()
advertisement = ProvideServicesAdvertisement(uart)
settings = Settings()

class MotorState():
    ACTIVE_PERFECT = 'perfect'
    ACTIVE_UPPER = 'active_upper'
    ACTIVE_LOWER = 'active_lower'
    RESTING = 'resting'
    STARTING = 'starting'
    FAILED = 'failed'
    UNKNOWN = 'unknown'

# Default Connection Interval
DEFAULT_CI = 28             # 28ms - Actually rounds up to 30 when set, but setting 30 results in 45, which is weird
MESSAGE_WEIGHT_TH = 0.0     # Weights below this amount not reported via BLE

# Turn on power to HX711 board (connected to a GPIO pin)
power = digitalio.DigitalInOut(board.D5)
power.switch_to_output()
power.value = True

hx = HX711(digitalio.DigitalInOut(board.D9), digitalio.DigitalInOut(board.D10))

# Subsystems
flasher = PixelFlasher()
motor = MotorManager()

# Motor Pulse feedback states
motorRangeEnabled = False
motorPulseEnabled = False

motorRange = 0.0

# Motor varibales. Can probably be moved to MotorManager
motorCustomEnabled = False
motorRepStarted = False
motorRepStartIndicationFinished = False

motorStartTime = 0.0

motorBoundLower = 0.0
motorBoundGoalUpper = 0.0
motorBoundGoalLower = 0.0
motorBoundUpper = 0.0
motorGoal = 0.0

MRP_PULSE = 0.5     # On time for pulses in pulse feedback modes
MRP_BREAK = 1.0     # Off time for pulses in pulse feedback modes (modulated by load cell pressure)

def clearMotorModes():
    global motorRangeEnabled
    global motorPulseEnabled

    motorRangeEnabled = False
    motorPulseEnabled = False

    global motorCustomEnabled
    global motorFastPulse

    motorCustomEnabled = False
    motorFastPulse = False

    motor.motorOff()


# Sample function for data manager
def getHX711Sample():
    return hx.get_value(1)

dsm = DataStreamManager(getHX711Sample,1)

# Command processor - This is pretty basic/brute force, but there are only a handful of commands
def process_device_command(command):

    global motorRange
    global motorRangeEnabled
    global motorPulseEnabled
    global MRP_PULSE
    global MRP_BREAK
    global MESSAGE_WEIGHT_TH

    # --- NEW ---
    global motorCustomEnabled
    global motorRepStarted
    global motorBoundLower
    global motorBoundGoalUpper
    global motorBoundGoalLower
    global motorBoundUpper
    global motorGoal

    # Clean and standardize command
    clean = command.strip().upper().decode("utf-8")
    print(f'CLEAN: {clean}')

    # --- TARE COMMAND ---
    if (clean == 'TARE'):
        dsm.tare()

    # --- CALIBRATION COMMAND ----
    elif (clean.startswith('CAL')):
        try:
            cal = float(clean[3:])
            dsm.calibrate(cal)
        except ValueError:
            print("Invalid calibration request")

    # --- GET CONNECTION INTERVAL COMMAND ---
    elif (clean == 'CI'):
        connection = ble.connections[0]
        uart.write(f'CI:{connection.connection_interval}\n')

    # --- SET CONNECTION INTERVAL COMMAND ---
    elif (clean.startswith('SETCI')):
        try:
            ci = int(clean[5:])
            if (ci > 10) and (ci < 255):   # Sanity check value

                # Request Change to CI
                settings.set_connectionInterval(ci)
                print("Requesting CI:",ci)
                connection = ble.connections[0]
                connection.connection_interval = settings.get_connectionInterval()

                # Echo new CI back to controller
                print("Actual CI:",connection.connection_interval)
                uart.write(f'CI:{connection.connection_interval}\n')

        except ValueError:
            print("Invalid CI request")
    
    # --- MOTOR POWER COMMAND ---
    elif (clean.startswith('MPOW')):
        try:
            pow = float(clean[4:])
            motor.setPower(pow)
        except ValueError:
            print("Invalid Motor Power Request")
    # --- MOTOR ON COMMAND ---
    elif (clean == "MON"):
        clearMotorModes()
        motor.motorOn()
        print('Motor turned on')

    # --- MOTOR OFF COMMAND ---
    elif (clean == "MOFF"):
        clearMotorModes()
        motor.motorOff()

    # --- MOTOR PULSE COMMAND ---
    elif (clean.startswith('MP')):
        clearMotorModes()
        try:
            splitme = clean[2:]
            split = splitme.split(":")
            if (len(split) == 2):
                on = float(split[0])
                off = float(split[1])
                motor.setPulse(on,off)
            else:
                print('Invalid Motor Pulse Request')
        except ValueError:
            print("Invalid Motor Pulse Request")

    # --- MOTOR RANGE PULSE COMMAND ---
    elif (clean.startswith('MRP')):
        clearMotorModes()
        try:
            motorRange = float(clean[3:])
            motorPulseEnabled = True
            motor.setPower(1.0)
            motor.setPulse(MRP_PULSE,MRP_BREAK)
        except ValueError:
            print('Invalid Motor Range Pulse Request')

    # --- MOTOR RANGE COMMAND ---
    elif (clean.startswith('MR')):
        clearMotorModes()
        try:
            motorRange = float(clean[2:])
            motorRangeEnabled = True
            motor.motorOn()
        except ValueError:
            print('Invalid Motor Range Request')

    # --- WEIGHT THRESHOLD ---
    elif (clean.startswith('TH')):
        try:
            MESSAGE_WEIGHT_TH = float(clean[2:])
        except ValueError:
            print('Bad weight threshold')

    # --- NEW MOTOR CUSTOM COMMAND --- Format MC##.##.##.##.## (MC<lower>.<goalLower>.<goalUpper>.<upper>.<goal>)
    elif (clean.startswith('C')):
        clearMotorModes()
        print(clean)
        try:
            motorBoundLower = float(clean[1:4])
            motorBoundGoalLower = float(clean[4:7])
            motorBoundGoalUpper= float(clean[7:10])
            motorBoundUpper= float(clean[10:13])
            motorGoal = float(clean[13:])
            print(f'{motorBoundLower},{motorBoundGoalLower},{motorBoundGoalUpper},{motorBoundUpper},{motorGoal}')
            motorCustomEnabled = True
            motor.motorOn()
        except ValueError:
            print('Invalid custom motor upper values')

    # --- NEW MOTOR DUAL CUSTOM COMMAND --- Format Z1########## (each number = 5 characters including decimal)
    elif (clean.startswith('Z1')):
        clearMotorModes()
        print(clean)
        try:
            motorBoundLower = float(clean[2:7])
            motorBoundGoalLower = float(clean[7:])
            motorCustomEnabled = True
        except ValueError:
            print('Invalid custom motor lower values')
            
    # --- Format ############### (each number = 5 characters including decimal)
    elif (clean[0].isdigit()):
        print(clean)
        try:
            motorBoundGoalUpper = float(clean[:5])
            motorBoundUpper = float(clean[5:10])
            motorGoal= float(clean[10:15])
            motorCustomEnabled = True
            motor.motorOn()
        except ValueError:
            print('Invalid custom motor upper values')

    elif (clean.startswith('R')):
        motorCustomEnabled = True

def get_motor_state(val):
    if val < motorBoundLower or (val < motorGoal and not motorRepStarted):
        return MotorState.RESTING
    elif motorRepStarted and not motorRepStartIndicationFinished:
        return MotorState.STARTING
    elif val < motorBoundGoalLower and motorRepStartIndicationFinished:
        return MotorState.ACTIVE_LOWER
    elif val < motorBoundGoalUpper and motorRepStartIndicationFinished:
        return MotorState.ACTIVE_PERFECT
    elif motorRepStartIndicationFinished:
        return MotorState.ACTIVE_UPPER
    else:
        return MotorState.UNKNOWN

def get_motor_bools(val):
    global motorRepStarted
    global motorStartTime
    global motorRepStartIndicationFinished

    if val > motorGoal and not motorRepStarted:
        motorRepStarted = True
        print('REP STARTED')
        motorStartTime = time.monotonic()

    elif motorRepStarted and val > motorBoundLower and motorStartTime + .6 <= time.monotonic() and not motorRepStartIndicationFinished:
        motorRepStartIndicationFinished = True
        print(f'INDICATION FINISHED {motorStartTime - time.monotonic()}')

    elif val < 5:
        motorRepStartIndicationFinished = False
        motorRepStarted = False

# Main loop
while True:

    # Start advertising BLE packets
    print('HERE')
    ble.start_advertising(advertisement)

    # Disconnected State
    print('AWAITING CONNECTION')
    print(advertisement)
    flasher.setDisconnectedState()

    # Keep Subsystems Updated
    while not ble.connected:
        flasher.update()
        motor.update()

    # Transition to Connected State
    if ble.connected:
        print('CONNECTED')

        # Status update
        flasher.setNegotiatingState()
        flasher.update()

        # Set up connection interval
        connection = ble.connections[0]

        # Check for uninitialized default value in settings
        if (settings.get_connectionInterval() == 0xff):
            print('Setting default connection interval to 30ms')
            settings.set_connectionInterval(DEFAULT_CI)

        # Read actual connection interval
        connection.connection_interval = settings.get_connectionInterval()
        print('Stored CI:',settings.get_connectionInterval())
        print('Actual CI:',connection.connection_interval,' ms')

        # Update flash pattern
        flasher.setConnectedState()

    # Connected State
    while ble.connected:

        # Process Commands
        if (uart.in_waiting > 0):
            # Send to command interpreter
            print(f' IN WAITING {uart.in_waiting}')
            process_device_command(uart.read(16))
            uart.write(f'D:{6969}\n')

        # Update Subsystems
        flasher.update()
        motor.update()

        # Process Samples
        if (hx.is_ready()):
            dsm.sample()

            # Send latest sample to device
            val = dsm.get_filtered_value()
            if (abs(val) > MESSAGE_WEIGHT_TH):
                uart.write(f'D:{val}\n')

            # Check special motor feedback modes to see if they need updates
            if motorRangeEnabled:
                motor.setPower(val/motorRange)

            if motorCustomEnabled:
                get_motor_bools(val)
                motorState = get_motor_state(val)
                print(f'MOTOR STATE: {motorState}, STARTING: {motorRepStarted}, STARTED: {motorRepStartIndicationFinished}, GOAL: {motorGoal}')
                if motorState == 'resting':
                    motor.motorOn()
                    if val < 4:
                        motor.setPower(0)
                    else:
                        motor.setPower(val/motorGoal)
                # TODO Determine relevant motor/pull states for Loadcell
                # ? Resting, Started, FAILED,
                if motorState == 'starting':
                    motor.motorOff()
                    # ensures setPulse is only called once
                    # if motor.onInterval != 0.2:
                    #     motor.setPulse(0.2, 0.1)
                    #     motor.setPower(1)
                elif motorState =='active_lower':
                    motor.motorOn()
                    motor.setPower(1)
                elif motorState == 'perfect':
                    motor.setPower(0)
                    motor.setPulse(0.05, 0.05)
                elif motorState == 'active_upper':
                    motor.setPower(1)
                elif motorState == 'failed':
                    motor.setPower(1)
                    motor.setPulse(0.1, 0.05)
                elif motorState == 'unknown':
                    motor.setPower(0)
