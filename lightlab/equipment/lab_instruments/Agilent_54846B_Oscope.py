from . import VISAInstrumentDriver
from lightlab.equipment.abstract_drivers import kf
from lightlab.util.data import Waveform
import pyvisa as visa

import numpy as np
import matplotlib.pyplot as plt

class Agilent_54846B_Oscope (kf.VisaManager, VISAInstrumentDriver):

    def __init__(self, name='Infiniium Oscilloscope', address=None, **kwargs):
        VISAInstrumentDriver.__init__(self, name=name, address=address, **kwargs)
        self.interface = visa.ResourceManager().open_resource(address)
        self.FlexDCA = kf.VisaManager(address=address, scpi_echo=False)
        self.interface.timeout = 20000

    def __del__(self):
        self.FlexDCA.close()

    def configure_Oscope_pattern(self, channel, scale=None):
        """ Installs a simulated module and prepares FlexDCA for
        measurements.
        """
        self.FlexDCA.query('*OPC?')
        self.FlexDCA.write('*RST')
        self.FlexDCA.write('*CLS')
        self.FlexDCA.write(':SYSTem:HEADer OFF')
        self.FlexDCA.write(':TIMebase:REFerence CENTer;RANGe 5e-3;POSition 20e-6')
        self.FlexDCA.write(f':CHANnel{channel}:RANGe 1.6;OFFSet -400e-3')
        self.FlexDCA.write(f':TRIGger:EDGE:SOURce CHANnel{channel};SLOPe POSitive')
        self.FlexDCA.write(f':TRIGger:LEVel CHANnel{channel},-0.40')
        self.FlexDCA.write(':ACQuire:MODE RTIMe;AVERage OFF')
        self.FlexDCA.write(':ACQuire:POINts 32768')
        print(self.FlexDCA.query(':ACQuire:POINts?'))
        self.FlexDCA.write(':AUTOSCALE;*OPC?')
        self.FlexDCA.write(':STOP')
#:WAVeform:YRANge?
    def get_yrange(self, channel):
        message = ':WAVeform:YRANge?'
        self.FlexDCA.write(':SYSTem:HEADer OFF')
        self.FlexDCA.write(':WAVeform:FORMat WORD')
        self.FlexDCA.write(':WAVeform:BYTeorder MSBFirst')
        # self.FlexDCA.write(message)
        # yrange = self.interface.read_raw()
        yrange = self.interface.query_binary_values(message, datatype='s', container=list, is_big_endian=True, header_fmt='empty', data_points=1)
        return yrange

    def get_pattern_info(self, channel):
        message = ':SYSTem:SETup?'
        self.FlexDCA.write(':SYSTem:HEADer OFF')
        self.FlexDCA.write(':SYSTem:SETup?')
        set_up = self.interface.read_raw()
        set_up = self.FlexDCA.query_binary_values(message, datatype='p', container=list, is_big_endian=True, header_fmt='ieee')
        return set_up
        
    def get_waveform_data(self, channel):
        self.FlexDCA.write(':SYSTem:HEADer OFF')
        self.FlexDCA.write(f':WAVeform:SOURce CHANnel{channel}')
        self.FlexDCA.write(':WAVeform:FORMat WORD')
        self.FlexDCA.write(':WAVeform:BYTeorder MSBFirst')
        # data = self.FlexDCA.query(':WAVeform:DATA?')
        # self.FlexDCA.write(':WAVeform:DATA?')
        message = ':WAVeform:DATA?'
        data = self.interface.query_binary_values(message, datatype='h', container=list, is_big_endian=True, header_fmt='ieee', chunk_size=32768, data_points=2048)
        return data
        
    def acquire_pattern(self, channel, scale=None):
        self.configure_Oscope_pattern(channel, scale)
        values = self.get_pattern_info(channel)
        data = self.get_waveform_data(channel)
        self.FlexDCA.write(':RUN')
        return data, values