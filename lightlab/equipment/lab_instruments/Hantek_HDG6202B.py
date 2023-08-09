"""
Please note, most of this code was written by ChaptGPT3 with prompts created by Marcus.

TODO:
- Add Pulse and triangular waveform functionality (see pg. 43 of SCPI protocol manual)

"""

from . import VISAInstrumentDriver
import pyvisa as visa
import logging

# create logger
log = logging.getLogger(__name__)

class HantekAWG:
    """Class to control Hantek Arbitrary Waveform Generator"""
    def __init__(self, address, channel):
        """Initialize device at given VISA address"""
        self.address = address
        self.channel = channel
        self.protVolt = 1 #sets the protection voltage to 1V by default
        self.amplitude = 0
        self.offset = 0
        rm = visa.ResourceManager()
        self.inst = rm.open_resource(address)
        self.inst.read_termination = '\n'
        self.inst.write_termination = '\n'
        print(self.inst.query('*IDN?'))

    def write(self, command=None):
        """Write SCPI command to device"""
        if command is not None:
            log.debug("Sending command '" + command + "' using USB interface...")
            try:
                self.inst.write(command)
            except Exception as e:
                log.exception("Could not send data, command %r",command)
                print(e)
                raise e

        #
        #self.inst.write(command)

    def read(self):
        """Read response from device"""
        return self.inst.read()

    def set_output(self, state):
        """Set output ON/OFF (0 or 1)"""
        if state:
            send_state='ON'
        else:
            send_state='OFF'
        self.write('OUTPUT%d %s' % (self.channel, send_state) )
        print('OUTPUT%d %s' % (self.channel, send_state))

    def set_waveform(self, waveform):
        """Set waveform (SIN, SQUARE, RAMP)"""
        self.write('SOURCE%d:FUN %s' % (self.channel, waveform))

    def set_frequency(self, frequency):
        """Set frequency in Hz"""
        self.write('SOURCE%d:FREQ %f' % (self.channel, frequency))

    def set_amplitude(self, amplitude):
        """Set amplitude in volts"""
        if (amplitude+self.offset) > self.protVolt:
            print("Warning: Amplitude+offset exceeds protection limit. Either increase protection limit or lower voltage to change source output")
        else:
            self.write('SOURCE%d:VOLT %f' % (self.channel, amplitude))
            self.amplitude

    def set_offset(self, offset):
        """Set offset in volts"""
        if (self.amplitude+offset) > self.protVolt:
            print("Warning: Amplitude+offset exceeds protection limit. Either increase protection limit or lower voltage to change source output")
        else:
            self.write('SOURCE%d:VOLT:OFFS %f' % (self.channel, offset) )
            self.offset=offset

    def protectionVoltage(self, limit):
        self.protVolt = limit

    def close(self):
        """Close device connection"""
        self.inst.close()