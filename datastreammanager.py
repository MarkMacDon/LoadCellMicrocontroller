# datastreammanager.py
#
# Manager for HX711 data stream

from settings import Settings
import math

settings = Settings()

class DataStreamManager:

    def __init__(self, sample_function, filter_ratio = 0.10):
        self.filter_ratio = filter_ratio
        self.sample_function = sample_function
        self.filtered_value = sample_function()

        if math.isnan(settings.get_tare()):
            # Tare is uninitialized - set default of 0
            print('Tare uninitialized. Setting to 0')
            settings.set_tare(0.0)

        self.tare_val = settings.get_tare()
        print('Tare loaded:',self.tare_val)

        if math.isnan(settings.get_calibration()):
            # Calibration is uninitialized, set default of 1.0
            print('Calibration uninitialized. Setting to 1')
            settings.set_calibration(1.0)

        self.calibration_scale = settings.get_calibration()     # Unit scale for calibration point
        print('Calibration loaded:',self.calibration_scale)

        self.REJECT_RATIO = 100.0        # Back to back samples that are off by this ratio are rejected

    def sample(self):
        val = self.sample_function();

        # Is this a reasonable value?

        # Ignore -1 values
        if (val == -1):
            print("Rejected outlier:",val)
            return

        self.filtered_value = (1.0-self.filter_ratio)*self.filtered_value + self.filter_ratio*val


    def get_filtered_value(self):
        return (self.filtered_value - self.tare_val)*self.calibration_scale

    # Reset tare value to current load
    def tare(self):
        self.tare_val = self.filtered_value
        settings.set_tare(self.tare_val)
        print("Tared to:",self.tare_val)

    # Set calibration for current load value
    def calibrate(self, current_load):
        # Assuming tare = 0, we can create a unit scale factor based on this sample point
        self.calibration_scale = current_load/(self.filtered_value-self.tare_val)
        settings.set_calibration(self.calibration_scale)
