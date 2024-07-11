import pyvisa as visa
from . import VISAInstrumentDriver
from lightlab.equipment.abstract_drivers import Configurable
from lightlab.laboratory.instruments import VectorGenerator

import numpy as np


class JKEM_201_TempController(VISAInstrumentDriver):
    ''' JKEM 201 Temperature Controller
    '''

    def __init__(self, name=None, address=None, **kwargs):
        name = name or 'JKEM201'

        kwargs.extend(dict(
            baud=9600,
            write_termination = '\r',
            read_termination = '\r',
            data_bits = 8,
            stop_bits = visa.constants.StopBits.one,
            parity = visa.constants.Parity.none,
            timeout = 1000,
        ))

        VISAInstrumentDriver.__init__(self, name=name, address=address, **kwargs)
    
    def set_setpoint(self, temperature):
        cmd = f"S(1,{round(temperature, 1)})"
        return float(self.query(cmd)) # returns the set temperature after setting it

    def read_setpoint(self):
        cmd = 'P(1)'
        return float(self.query(cmd)) # returns the set temperature
    
    def read_temperature(self):
        cmd = 'T(1)'
        return float(self.query(cmd)) # returns the current temperature from the sensor
    