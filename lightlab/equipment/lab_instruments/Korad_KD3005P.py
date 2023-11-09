from . import VISAInstrumentDriver
from lightlab.equipment.abstract_drivers import Configurable
from lightlab.laboratory.instruments import VectorGenerator

import numpy as np



class Korad_KD3005P(VISAInstrumentDriver):
    ''' Korad KD3005P Single-Channel Power Supply
    '''

    def __init__(self, name=None, address=None, **kwargs):
        name = name or 'Korad KD3005P'
        VISAInstrumentDriver.__init__(self, name=name, address=address, **kwargs)
    
    def get_idn(self):
        return self.query("*IDN?")
    
    def get_status(self):
        # from programming guide: status is 8 bits
        # bit 0:        CH1 0=CC mode, 1=CV mode
        # bit 1:        CH2 0=CC mode, 1=CV mode
        # ^ this is confusing because these are single channel power supplies ^
        # bits 2,3:     00=Independent tracking, 01: Tracking series, 11: Tracking parallel
        # ^ i don't know what tracking is ^
        # bit 4:        0=beep disabled, 1=beep enabled
        # ^ beeping doesn't seem to work ^
        # bit 5:        0=locked, 1=unlocked
        # bit 6:        0=output disabled, 1=output enabled
        # bit 7:        N/A
        # parse status; it looks like '\x12' for example, so we need to get each bit
        
        status = self.query("STATUS?")
        status = [bool(int(x)) for x in bin(ord(status))[2:].zfill(8)][::-1]
        # make a dictionary
        status_dict = {}
        status_dict['CH1'] = 'CV' if status[0] else 'CC'
        status_dict['CH2'] = 'CV' if status[1] else 'CC'
        if status[2] == 0 and status[3] == 0:
            tracking = 'Independent'
        elif status[2] == 0 and status[3] == 1:
            tracking = 'Series'
        elif status[2] == 1 and status[3] == 1:
            tracking = 'Parallel'
        else:
            raise RuntimeError('Tracking mode not recognized. Probably parsing wrong.')
        status_dict['Tracking'] = tracking
        status_dict['Beep'] = status[4]
        status_dict['Unlocked'] = status[5]
        status_dict['Output Enabled'] = status[6]
        #return status
        return status_dict

    def set_voltage(self, voltage):
        cmd = "VSET1:{}".format(voltage)
        return self.write(cmd)
    
    def get_voltage(self):
        cmd = "VSET1?"
        return float(self.query(cmd))
    
    def measure_voltage(self):
        cmd = "VOUT1?"
        return float(self.query(cmd))
    
    def set_current(self, current):
        cmd = "ISET1:{}".format(current)
        return self.write(cmd)

    def get_current(self):
        cmd = "ISET1?"
        return float(self.query(cmd))
    
    def measure_current(self):
        cmd = "IOUT1?"
        return float(self.query(cmd))
    
    def enable_beep(self):
        cmd = "BEEP1"
        return self.write(cmd)
    
    def disable_beep(self):
        cmd = "BEEP0"
        return self.write(cmd)
    
    def enable_output(self):
        cmd = "OUT1"
        return self.write(cmd)
    
    def disable_output(self):
        cmd = "OUT0"
        return self.write(cmd)
    
    def enable_current_protection(self):
        cmd = "OCP1"
        return self.write(cmd)
    
    def disable_current_protection(self):
        cmd = "OCP0"
        return self.write(cmd)