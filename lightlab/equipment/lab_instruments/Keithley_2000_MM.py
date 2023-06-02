from . import VISAInstrumentDriver
from lightlab.equipment.abstract_drivers import Configurable
from lightlab.laboratory.instruments import Keithley

import numpy as np
import time
from lightlab import logger


class Keithley_2000_MM(VISAInstrumentDriver, Configurable):
    ''' A Keithley 2000 driver.

        `Manual: <http://research.physics.illinois.edu/bezryadin/labprotocol/Keithley2400Manual.pdf>`__

        Usage: :any:`/ipynbs/Hardware/Keithley.ipynb`

        Capable of sourcing current and measuring voltage, such as a Keithley

        Also provides interface methods for measuring resistance and measuring power
    '''
    # instrument_category = Keithley
    mode = 'DC'


    def __init__(self, name=None, address=None, **kwargs):
        '''
            Args:
                currStep (float): amount to step if ramping in current mode. Default (None) is no ramp
                voltStep (float): amount to step if ramping in voltage mode. Default (None) is no ramp
                rampStepTime (float): time to wait on each ramp step point
        '''
        VISAInstrumentDriver.__init__(self, name=name, address=address, **kwargs)
        Configurable.__init__(self, headerIsOptional=False, verboseIsOptional=False)

    def startup(self):
        self.write('*RST')

    def set_voltage_mode(self, mode='DC'):
        if mode == 'DC' or mode == 'AC':
            self.mode = mode
            self.write(':CONFigure:VOLTage:'+mode)
        else:
            print('Please select one of two voltage sensing modes: DC, or AC')
            
    def set_current_mode(self, mode='DC'):
        if mode == 'DC' or mode == 'AC':
            self.mode = mode
            self.write(':CONFigure:CURRent:'+mode)
        else:
            print('Please select one of two current sensing modes: DC, or AC')
            
    def meas_voltage(self, mode='DC'):
        return float(self.query(':MEASure:VOLTage:'+mode+'?'))
        
    def meas_current(self, mode='DC'):
        return float(self.query(':MEASure:CURRent:'+mode+'?'))
        
    def get_config(self):
        return self.query(':CONFigure?')
        