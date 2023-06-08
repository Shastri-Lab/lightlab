##
# Author: hughmor; adapted from code by Mustafa (UBC)
##

from . import VISAInstrumentDriver
from lightlab.equipment.abstract_drivers import Configurable
from lightlab.laboratory.instruments import Keithley

import numpy as np
import time
from lightlab import logger

import qontrol #TODO: add this as a dependency

# TODO: this class is untested. I ported from SiEPIC's siepicQontrol.py
class Qontrol_Q8i(VISAInstrumentDriver, Configurable):
    ''' A Qontrol Q8i driver for BP8.

        `Manual: <TODO: add link>`__

        Capable of sourcing current and measuring voltage

    '''
    instrument_category = Keithley # using keithley as it implements many of the same methods
    autoDisable = None  # in seconds. TODO: NOT IMPLEMENTED
    _latestCurrentVal = 0
    _latestVoltageVal = 0
    currStep = None
    voltStep = None
    rampStepTime = 0.01  # in seconds.

    def __init__(self, name=None, address=None, **kwargs):
        '''
            Args:
                currStep (float): amount to step if ramping in current mode. Default (None) is no ramp
                voltStep (float): amount to step if ramping in voltage mode. Default (None) is no ramp
                rampStepTime (float): time to wait on each ramp step point
        '''
        self.currStep = kwargs.pop("currStep", None)
        self.voltStep = kwargs.pop("voltStep", None)
        self.rampStepTime = kwargs.pop("rampStepTime", 0.01)

        VISAInstrumentDriver.__init__(self, name=name, address=address, **kwargs) #TODO: is this needed when I am initializing the qontrol object later?
        Configurable.__init__(self, headerIsOptional=False, verboseIsOptional=False)
        self._q = qontrol.QXOutput(serial_port_name = address, response_timeout = 0.1) #TODO: make the driver only single channel?
        logger.log("Qontroller '{:}' initialised with firmware {:} and {:} channels".format(self._q.device_id, self._q.firmware, self._q.n_chs) ) # TODO: I don't know if logger.log is correct syntax
   
    def setCurrent(self, channel, currAmps):
        self._q.i[channel] = currAmps
        reply_string=("Channel "+str(channel)+". Current set to: "+ str(currAmps)+"A.")
        logger.log(reply_string) #TODO

    def setVoltage(self, channel, voltVolts):
        self._q.v[channel] = voltVolts
        reply_string=("Channel "+str(channel)+". Voltage set to: "+ str(voltVolts)+"V.")
        logger.log(reply_string) #TODO

    def getCurrent(self, channel):
        meas_current = self._q.i[channel]
        reply_string=("Channel "+str(channel)+". Current is: "+ str(meas_current)+"A.")
        logger.log(reply_string)
        return meas_current

    def getVoltage(self, channel):
        meas_voltage = self._q.v[channel]
        reply_string=("Channel "+str(channel)+". Voltage is: "+ str(meas_voltage)+"V.")
        logger.log(reply_string)
        return meas_voltage

    def measVoltage(self, channel):
        return self.getVoltage(channel)

    def measCurrent(self, channel):
        return self.getCurrent(channel)
    
    def reset_voltage(self,channel=0):
        self._q.v[channel] = 0
        reply_string=("Channel "+str(channel)+". Voltage Reset to 0V.")
        logger.log(reply_string)

    def reset_current(self,channel=0):
        self._q.i[channel] = 0
        reply_string=("Channel "+str(channel)+". Current Reset to 0A.")
        logger.log(reply_string)

    def reset_voltage_all(self):
        self._q.v[:] = 0
        reply_string=("All Channels. Voltage Reset to 0V.")
        logger.log(reply_string)

    def reset_current_all(self):
        self._q.i[:] = 0
        reply_string=("All Channels. Current Reset to 0A.")
        logger.log(reply_string)

    #TODO: I think these range functions are a bad idea. just remove and let the user set the range manually
    def reset_voltage_range(self,channel1=0,channel2=1):
        self._q.v[channel1:channel2] = 0
        reply_string=("Channel "+str(channel1)+" to Channel "+str(channel2)+ ". Voltage Reset to 0V.")
        logger.log(reply_string)

    def reset_current_range(self,channel1=0,channel2=1):
        self._q.i[channel1:channel2] = 0
        reply_string=("Channel "+str(channel1)+" to Channel "+str(channel2)+ ". Current Reset to 0A.")
        logger.log(reply_string)

    def disconnect(self):
        self._q.close()
        reply_string=("Disconnect.")
        logger.log(reply_string)

    def test_command(self):
        reply_string = 'This is a Test Command.'
        logger.log(reply_string)
