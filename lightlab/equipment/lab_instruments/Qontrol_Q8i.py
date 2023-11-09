##
# Author: hughmor; adapted from driver by Qontrol
# https://github.com/takeqontrol/api/tree/master
##

from . import VISAInstrumentDriver
from lightlab.equipment.abstract_drivers import Configurable
from lightlab.laboratory.instruments import Keithley

import numpy as np
import time
import re
from lightlab import logger

from pyvisa import VisaIOError

ERROR_FORMAT = '[A-Za-z]{1,3}(\d+):(\d+)'

class Qontrol_Q8i(VISAInstrumentDriver): #, Configurable
    ''' A Qontrol Q8i driver for BP8.

        `Manual: <TODO: add link>`__

        Capable of sourcing current and measuring voltage

    '''

    # TODO: add instrument category: Keithley? must standardize function names...

    __baud_rate = 115200 # this is critical to make VISA work with qontrol
    _timeout = 500  # ms
    
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

        # Initialize communication with board and ready it
        VISAInstrumentDriver.__init__(self, name=name, address=address, baud=self.__baud_rate, ID_STR="id?", **kwargs)
        self._session_object.termination = '\n'
        self._session_object.timeout = self._timeout
        self.clear()
        #Configurable.__init__(self, headerIsOptional=False, verboseIsOptional=False)

        self.startup()

        logger.info("Qontroller '{:}' initialised with firmware {:} and {:} channels".format(self.device_id, self.firmware, self.n_chs) ) # TODO: I don't know if logger.log is correct syntax
        
        # self.v = None				# Channel voltages (direct access)
        # self.i = None				# Channel currents (direct access)
        # self.vmax = None			# Channel voltages (direct access)
        # self.imax = None			# Channel currents (direct access)
        # self.binary_mode = False	# Communicate in binary

    def startup(self):
        # Get device info
        id_string = self.query('id?')
        #id_string = self.instrID()
        ob = re.match('.*((?:'+ERROR_FORMAT+')|(?:\w+\d\w*-[0-9a-fA-F\*]+)).*', id_string)
        device_id = ob.groups()[0]
        self.device_id = device_id
        self.firmware = self.query('firmware?')
        self._lifetime = self.query("lifetime?")

        # Force a reset of the daisy chain
        self.write('nup=0')
        while True:
            try:
                line = self.read()
            except VisaIOError:
                break
            # if line != 'OK': # TODO: finish checking for good initialization
            #     raise RuntimeError('Got weird output from Qontrol: {:}'.format(line))
            
        # Ask for number of upstream devices, parse it
        self.write('nupall?')
        chain = []
        while True:
            try:
                line = self.read()
            except VisaIOError:
                break
            #print(line)
            op = re.match('(?:([^:\s]+)\s*:\s*(\d+)\n*)*', line)
            if op is None:
                value = (None,)
                # TODO: should maybe raise an error?
            else:
                value = op.groups()
            #print(value)
            chain.append(value)

        # Initialize daisy chain
        self.chain = []
        for i in range(len(chain)):
                ob = re.match('\x00*([^-\x00]+)-([0-9a-fA-F\*]+)', chain[i][0])
                device_id = chain[i][0]
                device_type = ob.groups()[0]
                device_serial = ob.groups()[1]
                try:
                    index = int(chain[i][1])
                except ValueError:
                    index = -1
                    print ('Qontroller.__init__: Warning: Unable to determine daisy chain index of device with ID {:}.'.format(device_id))
            
                # Scan out number of channels from device type
                ob = re.match('[^\d]+(\d*)[^\d]*', device_type)
                try:
                    n_chs = int(ob.groups()[0])
                except ValueError:
                    n_chs = -1
                    print ('Qontroller.__init__: Warning: Unable to determine number of channels of device at daisy chain index {:}.'.format(index))
            
                self.chain.append({
                    'device_id':device_id,
                    'device_type':device_type,
                    'device_serial':device_serial,
                    'n_chs':n_chs,
                    'index':index
                    })

        # Get number of channels from chain
        self.n_chs = sum([device['n_chs'] for device in chain])

        # Set up configuration (full scale voltage and current)
        _vfull = self.query("vfull?")
        ob = re.match('(?:\+|-|)([\d\.]+) V', _vfull)
        self.v_full = float(ob.groups()[0])
        # match = re.search(r'([-+]?\d+\.\d+)', _vfull)
        # self.v_full = float(match.group(1)) if match else None
        _ifull = self.query("ifull?")
        ob = re.match('(?:\+|-|)([\d\.]+) mA', _ifull)
        self.i_full = float(ob.groups()[0])
        # match = re.search(r'([-+]?\d+\.\d+)', _ifull)
        # self.i_full = float(match.group(1)) if match else None

    def close(self):
        self.disconnect()

    def disconnect(self):
        self.clear()
        super().close()

    def wait(self, bigMsTimeout=10000):
        #TODO: implement the changes needed in visa_object.py to make this work (qontrol has nonstandard instrument codes; see the changes I made to make this driver work)
        raise NotImplementedError("Function wait() is not implemented for qontrol driver.")

### REIMPLEMENT ALL THESE FUNCTIONS BASED ON QONTROL API
    
    def reset_voltage(self,channel=0):
        self._q.v[channel] = 0
        reply_string=("Channel "+str(channel)+". Voltage Reset to 0V.")
        logger.info(reply_string)

    def reset_current(self,channel=0):
        self._q.i[channel] = 0
        reply_string=("Channel "+str(channel)+". Current Reset to 0A.")
        logger.info(reply_string)

    def reset_voltage_all(self):
        self._q.v[:] = 0
        reply_string=("All Channels. Voltage Reset to 0V.")
        logger.info(reply_string)

    def reset_current_all(self):
        self._q.i[:] = 0
        reply_string=("All Channels. Current Reset to 0A.")
        logger.info(reply_string)

    def setCurrent(self, channel, currAmps):
        self._q.i[channel] = currAmps
        reply_string=("Channel "+str(channel)+". Current set to: "+ str(currAmps)+"A.")
        logger.info(reply_string) #TODO

    def setVoltage(self, channel, voltVolts):
        self._q.v[channel] = voltVolts
        reply_string=("Channel "+str(channel)+". Voltage set to: "+ str(voltVolts)+"V.")
        logger.info(reply_string) #TODO

    def getCurrent(self, channel):
        meas_current = self._q.i[channel]
        reply_string=("Channel "+str(channel)+". Current is: "+ str(meas_current)+"A.")
        logger.info(reply_string)
        return meas_current

    def getVoltage(self, channel):
        meas_voltage = self._q.v[channel]
        reply_string=("Channel "+str(channel)+". Voltage is: "+ str(meas_voltage)+"V.")
        logger.info(reply_string)
        return meas_voltage

    def measVoltage(self, channel):
        return self.getVoltage(channel)

    def measCurrent(self, channel):
        return self.getCurrent(channel)

    #TODO: I think these range functions are a bad idea. just remove and let the user set the range manually
    def reset_voltage_range(self,channel1=0,channel2=1):
        self._q.v[channel1:channel2] = 0
        reply_string=("Channel "+str(channel1)+" to Channel "+str(channel2)+ ". Voltage Reset to 0V.")
        logger.info(reply_string)

    def reset_current_range(self,channel1=0,channel2=1):
        self._q.i[channel1:channel2] = 0
        reply_string=("Channel "+str(channel1)+" to Channel "+str(channel2)+ ". Current Reset to 0A.")
        logger.info(reply_string)

    def disconnect(self):
        self._q.close()
        reply_string=("Disconnect.")
        logger.info(reply_string)

    def test_command(self):
        reply_string = 'This is a Test Command.'
        logger.info(reply_string)
