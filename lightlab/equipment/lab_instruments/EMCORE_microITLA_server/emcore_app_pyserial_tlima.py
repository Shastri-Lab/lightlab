# -*- coding: utf-8 -*-
#!/usr/bin/env python
# coding:utf-8

# Created on Wed Jan 31 16:33:16 2018

__author__ = "Shinsuke FUJISAWA"
__copyright__ = "Copyright 2019, NEC Laboratories of America, Inc."
__credits__ = ""
__license__ = ""
__version__ = "0.0.1"
__maintainer__ = ""
__email__ = "sfujisawa@nec-labs.com"
__status__ = "developping"


try:
    from itla_msa_modules.itla_msa import msa
    import serial
    import struct
    import numpy as np
except:
   raise
   
from serial.serialutil import LF, Timeout
def read_until(self, terminator=LF, size=None):
    """\
    Read until a termination sequence is found ('\n' by default), the size
    is exceeded or until timeout occurs.
    """
    lenterm = len(terminator)
    line = bytearray()
    timeout = Timeout(self._timeout)
    while True:
        c = self.read(1)
        print('ninja-read:', c, terminator, line)
        if c:
            line += c
            if line[-lenterm:] == terminator:
                break
            if size is not None and len(line) >= size:
                break
        else:
            break
        if timeout.expired():
            break
    return bytes(line)

serial.Serial.read_until = read_until
print(serial.Serial.read)

class emcore_app:

    ## emcore iTLA 1-83
    
    def __init__(self, comm_port, baudrate, timeout, bytesize):
        self.emcore_iTLA = serial.Serial(port=comm_port, baudrate=baudrate, \
                                    timeout=timeout, bytesize=bytesize)
        self.emcore_iTLA.close()
    
    def itla_on(self):
        self.emcore_iTLA.open()
        if self.emcore_iTLA.is_open:
            self.emcore_iTLA.write(msa.reset_enable(True, 1))
            read_byte = self.emcore_iTLA.read_until()
            read_hex  = read_byte.hex()
        self.emcore_iTLA.close()
        try:
            if read_hex[-3] == '1':
                print('iTLA is turned ON. \n')
            else:
                print('debug: {0:s}'.format(read_hex))
        except:
            print('debug: {0:s}'.format(read_hex))
    
    def itla_off(self):
        self.emcore_iTLA.open()
        if self.emcore_iTLA.is_open:
            self.emcore_iTLA.write(msa.reset_enable(False, 1))
            read_byte = self.emcore_iTLA.read_until()
            read_hex  = read_byte.hex()
        self.emcore_iTLA.close()
        try:
            if read_hex[-3] == '0':
                print('iTLA is turned OFF. \n')
            else:
                print('debug: {0:s}'.format(read_hex))
        except:
            print('debug: {0:s}'.format(read_hex))
            
            
    def ask_device_ready(self):
        self.emcore_iTLA.open()
        if self.emcore_iTLA.is_open:
            self.emcore_iTLA.write(msa.nop()) #[MHz]
            print("Trying to read_until()")
            read_byte = self.emcore_iTLA.read_until()
            print("Read : " + str(read_byte))
            #read_hex  = read_byte.hex()
        self.emcore_iTLA.close()
        read_bits  = read_byte[-1]
        bit4 = format(read_bits, '08b')[3]
        if bit4 == '1':
            print('Device is ready')
        else:
            print('Device is not ready')

    def set_output_power(self, pow_dbm):
        pow_100dbm = int(100 * pow_dbm)
        self.emcore_iTLA.open()
        if self.emcore_iTLA.is_open:
            self.emcore_iTLA.write(msa.optical_power(pow_100dbm, 1))
            read_hex = self.emcore_iTLA.read_until().hex()
        self.emcore_iTLA.close()
        print('output power setting: {0:.2f}dBm, measured optical power: {1:.2f}dBm'\
              .format(int(read_hex[-4:], base=16)/100.0, self.get_output_power()))

    def set_first_channel_frequency(self, frequency_GHz):
        fcf1_val = int(frequency_GHz * 1e-3)
        fcf2_val = int((frequency_GHz - (fcf1_val * 1e3))*10)
        fcf3_val = int((frequency_GHz - fcf1_val*1e3 - fcf2_val*1e-1)*1e3)
        self.emcore_iTLA.open()
        if self.emcore_iTLA.is_open:
            self.emcore_iTLA.write(msa.fcf1(fcf1_val, 1)) #[THz]
            read_hex  = self.emcore_iTLA.read_until().hex()
        self.emcore_iTLA.close()
        read_fcf1_GHz = int(read_hex[-4:], base = 16) * 1.0e3 #[GHz]
        
        self.emcore_iTLA.open()
        if self.emcore_iTLA.is_open:
            self.emcore_iTLA.write(msa.fcf2(fcf2_val, 1)) #[10*GHz]
            read_hex  = self.emcore_iTLA.read_until().hex()
        self.emcore_iTLA.close()
        read_fcf2_GHz = int(read_hex[-4:], base = 16) / 10.0 #[GHz]
        
        self.emcore_iTLA.open()
        if self.emcore_iTLA.is_open:
            self.emcore_iTLA.write(msa.fcf3(fcf3_val, 1)) #[MHz]
            read_hex  = self.emcore_iTLA.read_until().hex()
        self.emcore_iTLA.close()
        read_fcf3_GHz = int(read_hex[-4:], base = 16) * 1.0e-3 #[GHz]
        
        fcf_GHz = read_fcf1_GHz + read_fcf2_GHz + read_fcf3_GHz
        print('First Channel Frequency: {0:.3f}GHz'.format(fcf_GHz))

    def set_ftf_frequency(self, frequency_MHz):
        self.emcore_iTLA.open()
        if self.emcore_iTLA.is_open:
            self.emcore_iTLA.write(msa.ftf(frequency_MHz, 1)) #[MHz]
        self.emcore_iTLA.close()

    def set_channel(self, channel_num, ftf):
        if isinstance(channel_num, int):
            channel1 = [channel_num, 0]
        else:
            channel1 = channel_num
        self.emcore_iTLA.open()
        if self.emcore_iTLA.is_open:
            self.emcore_iTLA.write(msa.channel(channel1[0], 1))
            read_hex = self.emcore_iTLA.read_until().hex()
            read_channel = int(read_hex[-4:],base=16)
        self.emcore_iTLA.close()
        
        self.emcore_iTLA.open()
        if self.emcore_iTLA.is_open:
            self.emcore_iTLA.write(msa.channelh(channel1[1], 1))
            read_hexh = self.emcore_iTLA.read_until().hex()
            read_channelh = int(read_hexh[-4:],base=16)
        self.emcore_iTLA.close()
        
        self.emcore_iTLA.open()
        if self.emcore_iTLA.is_open:
            self.emcore_iTLA.write(msa.ftf(ftf, 1))
            read_hex = self.emcore_iTLA.read_until().hex()
            read_ftf = int(read_hex[-4:],base=16)
        self.emcore_iTLA.close()
        
        print('channel setting: {0:d}, channelH setting: {1:d}, FTF setting: {2:d}, measured_frequency: {3:.2f}GHz'\
              .format(read_channel, read_channelh, read_ftf, self.get_channel_frequency()))    
        
    def get_output_power(self):
        self.emcore_iTLA.open()
        if self.emcore_iTLA.is_open:
            self.emcore_iTLA.write(msa.measured_optical_power())
            read_hex = self.emcore_iTLA.read_until().hex()
        self.emcore_iTLA.close()
        measured_optical_power_dBm = int(read_hex[-4:], base=16)/100.0
        return measured_optical_power_dBm

    def get_first_channel_frequency(self):
        self.emcore_iTLA.open()
        if self.emcore_iTLA.is_open:
            self.emcore_iTLA.write(msa.fcf1(0, 0)) #[THz]
            read_hex  = self.emcore_iTLA.read_until().hex()
        self.emcore_iTLA.close()
        read_fcf1_GHz = int(read_hex[-4:], base = 16) * 1.0e3 #[GHz]
        
        self.emcore_iTLA.open()
        if self.emcore_iTLA.is_open:
            self.emcore_iTLA.write(msa.fcf2(0, 0)) #[10*GHz]
            read_hex  = self.emcore_iTLA.read_until().hex()
        self.emcore_iTLA.close()
        read_fcf2_GHz = int(read_hex[-4:], base = 16) / 10.0 #[GHz]
        
        self.emcore_iTLA.open()
        if self.emcore_iTLA.is_open:
            self.emcore_iTLA.write(msa.fcf3(0, 0)) #[MHz]
            read_hex  = self.emcore_iTLA.read_until().hex()
        self.emcore_iTLA.close()
        read_fcf3 = int(read_hex[-4:], base = 16) #[MHz]
        if read_fcf3 > 2**15:
            read_fcf3 = read_fcf3 - 2**16
        read_fcf3_GHz = read_fcf3 * 1.0e-3
        
        fcf_GHz = read_fcf1_GHz + read_fcf2_GHz + read_fcf3_GHz
        return fcf_GHz

    def get_channel_frequency(self):
        self.emcore_iTLA.open()
        if self.emcore_iTLA.is_open:
            self.emcore_iTLA.write(msa.laser_frequency1()) #[THz]
            read_hex  = self.emcore_iTLA.read_until().hex()
        self.emcore_iTLA.close()
        read_lc1_GHz = int(read_hex[-4:], base = 16) * 1.0e3 #[GHz]
        
        self.emcore_iTLA.open()
        if self.emcore_iTLA.is_open:
            self.emcore_iTLA.write(msa.laser_frequency2()) #[10*GHz]
            read_hex  = self.emcore_iTLA.read_until().hex()
        self.emcore_iTLA.close()
        read_lc2_GHz = int(read_hex[-4:], base = 16) / 10.0 #[GHz]
        
        self.emcore_iTLA.open()
        if self.emcore_iTLA.is_open:
            self.emcore_iTLA.write(msa.laser_frequency3()) #[MHz]
            read_hex  = self.emcore_iTLA.read_until().hex()
        self.emcore_iTLA.close()
        read_lc3 = int(read_hex[-4:], base = 16)
        if read_lc3 > 2**15:
            read_lc3 = read_lc3 - 2**16
        read_lc3_GHz = read_lc3 * 1.0e-3 
        lc_GHz = read_lc1_GHz + read_lc2_GHz + read_lc3_GHz
        return lc_GHz

    def get_ftf_frequency(self):
        self.emcore_iTLA.open()
        if self.emcore_iTLA.is_open:
            self.emcore_iTLA.write(msa.ftf(0, 0)) #[MHz]
            read_hex  = self.emcore_iTLA.read_until().hex()
        self.emcore_iTLA.close()
        read_ftf_MHz = int(read_hex[-4:], base = 16) #[MHz]
        if read_ftf_MHz > 2**15:
            read_ftf_MHz = read_ftf_MHz-2**16
        return read_ftf_MHz

    def get_device_type(self):
        self.emcore_iTLA.open()
        if self.emcore_iTLA.is_open:
            self.emcore_iTLA.write(msa.devtyp()) 
            read_hex  = self.emcore_iTLA.read_until().hex()
            num_byte = int(read_hex[4:], base=16)
            str_cap = ''
            for ind in range(num_byte//2):
                self.emcore_iTLA.write(msa.aea_ear()) 
                read_hex  = self.emcore_iTLA.read_until().hex()
                str_cap += bytes.fromhex(read_hex[4:]).decode('utf-8')
            self.emcore_iTLA.write(msa.aea_ear()) 
            read_byte = self.emcore_iTLA.read_until()
            read_hex  = read_byte.hex()
        self.emcore_iTLA.close()
        if bin(read_byte[0])[-2:]=='01' and read_byte[-2:].hex() == '0000':
            print(str_cap)
            return str_cap
        else:
            print('debug: {0:s}'.format(read_hex))

    def get_manufacturer(self):
        self.emcore_iTLA.open()
        if self.emcore_iTLA.is_open:
            self.emcore_iTLA.write(msa.manufacturer()) 
            read_hex  = self.emcore_iTLA.read_until().hex()
            num_byte = int(read_hex[4:], base=16)
            str_cap = ''
            for ind in range(num_byte//2):
                self.emcore_iTLA.write(msa.aea_ear()) 
                read_hex  = self.emcore_iTLA.read_until().hex()
                str_cap += bytes.fromhex(read_hex[4:]).decode('utf-8')
            self.emcore_iTLA.write(msa.aea_ear()) 
            read_byte = self.emcore_iTLA.read_until()
            read_hex  = read_byte.hex()
        self.emcore_iTLA.close()
        if bin(read_byte[0])[-2:]=='01' and read_byte[-2:].hex() == '0000':
            print(str_cap)
        else:
            print('debug: {0:s}'.format(read_hex))

    def get_serial_number(self):
        self.emcore_iTLA.open()
        if self.emcore_iTLA.is_open:
            self.emcore_iTLA.write(msa.serno())
            read_hex  = self.emcore_iTLA.read_until().hex()
            num_byte = int(read_hex[4:], base=16)
            str_cap = ''
            for ind in range(int(np.around(num_byte/2))):
                print('ninja2', read_hex)
                self.emcore_iTLA.write(msa.aea_ear()) 
                read_hex  = self.emcore_iTLA.read_until().hex()
                str_cap += bytes.fromhex(read_hex[4:]).decode('utf-8')
            self.emcore_iTLA.write(msa.aea_ear()) 
            read_byte = self.emcore_iTLA.read_until()
            read_hex  = read_byte.hex()
        self.emcore_iTLA.close()
        print('ninja3', read_byte)
        if bin(read_byte[0])[-2:]=='01' and read_byte[-2:].hex() == '0000':
            print(str_cap[:num_byte])
        else:
            print('debug: {0:s}'.format(read_hex))

    def get_manufactured_date(self):
        self.emcore_iTLA.open()
        if self.emcore_iTLA.is_open:
            self.emcore_iTLA.write(msa.manufact_date())
            read_hex  = self.emcore_iTLA.read_until().hex()
            num_byte = int(read_hex[4:], base=16)
            str_cap = ''
            for ind in range(num_byte//2):
                self.emcore_iTLA.write(msa.aea_ear()) 
                read_hex  = self.emcore_iTLA.read_until().hex()
                str_cap += bytes.fromhex(read_hex[4:]).decode('utf-8')
            self.emcore_iTLA.write(msa.aea_ear()) 
            read_byte = self.emcore_iTLA.read_until()
            read_hex  = read_byte.hex()
        self.emcore_iTLA.close()
        if bin(read_byte[0])[-2:]=='01' and read_byte[-2:].hex() == '0000':
            print(str_cap)
        else:
            print('debug: {0:s}'.format(read_hex))

    def get_io_capabilities(self):
        self.emcore_iTLA.open()
        if self.emcore_iTLA.is_open:
            self.emcore_iTLA.write(msa.io_capabilities())
            read_hex  = self.emcore_iTLA.read_until().hex()
        self.emcore_iTLA.close()
        print(read_hex)

    def get_device_errors(self):
        self.emcore_iTLA.open()
        if self.emcore_iTLA.is_open:
            self.emcore_iTLA.write(msa.device_fatal(0))
            read_hex  = self.emcore_iTLA.read_until().hex()
        self.emcore_iTLA.close()
        print(read_hex)
        self.emcore_iTLA.open()
        if self.emcore_iTLA.is_open:
            self.emcore_iTLA.write(msa.device_warning(0))
            read_hex  = self.emcore_iTLA.read_until().hex()
        self.emcore_iTLA.close()
        print(read_hex)

    def get_module_monitors(self):
        # get temperature
        self.emcore_iTLA.open()
        if self.emcore_iTLA.is_open:
            self.emcore_iTLA.write(msa.temperatures())
            read_hex  = self.emcore_iTLA.read_until().hex()
            num_byte = int(read_hex[4:], base=16)
            temp_cap = []
            for ind in range(int(np.around(num_byte/2))):
                self.emcore_iTLA.write(msa.aea_ear()) 
                read_byte = self.emcore_iTLA.read_until()
                temp_cap.append(struct.unpack('>h',read_byte[-2:])[0]/100)
            self.emcore_iTLA.write(msa.aea_ear())
            read_byte = self.emcore_iTLA.read_until()
            read_hex  = read_byte.hex()
        self.emcore_iTLA.close()
        if bin(read_byte[0])[-2:]=='01' and read_byte[-2:].hex() == '0000':
            print('Diode T: {0:.2f}C, Case T: {1:.2f}C'.format(*temp_cap))
        else:
            print('debug: {0:s}'.format(read_hex))
        
        # get current
        self.emcore_iTLA.open()
        if self.emcore_iTLA.is_open:
            self.emcore_iTLA.write(msa.currents())
            read_hex  = self.emcore_iTLA.read_until().hex()
            num_byte = int(read_hex[4:], base=16)
            current_cap = []
            for ind in range(num_byte//2):
                self.emcore_iTLA.write(msa.aea_ear()) 
                read_byte = self.emcore_iTLA.read_until()
                current_cap.append(struct.unpack('>h',read_byte[-2:])[0]/10)
            self.emcore_iTLA.write(msa.aea_ear()) 
            read_byte = self.emcore_iTLA.read_until()
            read_hex  = read_byte.hex()
        self.emcore_iTLA.close()
        if bin(read_byte[0])[-2:]=='01' and read_byte[-2:].hex() == '0000':
            print('TEC current: {0:.1f}mA, Diode current: {1:.1f}mA'.format(*current_cap))
        else:
            print('debug: {0:s}'.format(read_hex))
        
        # get laser age
        self.emcore_iTLA.open()
        if self.emcore_iTLA.is_open:
            self.emcore_iTLA.write(msa.laser_age())
            age_hex  = self.emcore_iTLA.read_until().hex()
        self.emcore_iTLA.close()
        print('LASER Age: {0:d}%'.format(int(age_hex[-2:], base=16)))

    def get_power_capabilities(self):
        self.emcore_iTLA.open()
        if self.emcore_iTLA.is_open:
            self.emcore_iTLA.write(msa.opsh())
            read_byte = self.emcore_iTLA.read_until()
        self.emcore_iTLA.close()
        powh = struct.unpack('>h',read_byte[-2:])[0]/100
        self.emcore_iTLA.open()
        if self.emcore_iTLA.is_open:
            self.emcore_iTLA.write(msa.opsl())
            read_byte = self.emcore_iTLA.read_until()
        self.emcore_iTLA.close()
        powl = struct.unpack('>h',read_byte[-2:])[0]/100
        print('Power: {0:.1f}dBm - {1:.1f}dBm'.format(powl, powh))

    def get_grid_capabilities(self):
        self.emcore_iTLA.open()
        if self.emcore_iTLA.is_open:
            self.emcore_iTLA.write(msa.cap_grid())
            read_byte = self.emcore_iTLA.read_until()
        self.emcore_iTLA.close()
        print('Grid: {0:.1f}MHz'.format(struct.unpack('>H',read_byte[-2:])[0]*100))

    def get_ftf_capabilities(self):
        self.emcore_iTLA.open()
        if self.emcore_iTLA.is_open:
            self.emcore_iTLA.write(msa.cap_ftf())
            read_byte = self.emcore_iTLA.read_until()
        self.emcore_iTLA.close()
        print('Frequency Tuning: {0:d}MHz'.format(struct.unpack('>H',read_byte[-2:])[0]))
        
    def get_frequency_capabilities(self):
        self.emcore_iTLA.open()
        if self.emcore_iTLA.is_open:
            self.emcore_iTLA.write(msa.cap_freqhigh1())
            read_byte = self.emcore_iTLA.read_until()
        self.emcore_iTLA.close()
        lfh1 = struct.unpack('>H',read_byte[-2:])[0]
        
        self.emcore_iTLA.open()
        if self.emcore_iTLA.is_open:
            self.emcore_iTLA.write(msa.cap_freqhigh2())
            read_byte = self.emcore_iTLA.read_until()
        self.emcore_iTLA.close()
        lfh2 = struct.unpack('>H',read_byte[-2:])[0]*1e-4
        
        """
        self.emcore_iTLA.open()
        if self.emcore_iTLA.is_open:
            self.emcore_iTLA.write(msa.cap_freqhigh3())
            read_byte = self.emcore_iTLA.read_until()
        self.emcore_iTLA.close()
        lfh3 = struct.unpack('>H',read_byte[-2:])[0]*1e-6
        """
        
        lfh = lfh1 + lfh2 #+ lfh3
        
        self.emcore_iTLA.open()
        if self.emcore_iTLA.is_open:
            self.emcore_iTLA.write(msa.cap_freqlow1())
            read_byte = self.emcore_iTLA.read_until()
        self.emcore_iTLA.close()
        lfl1 = struct.unpack('>H',read_byte[-2:])[0]
        
        self.emcore_iTLA.open()
        if self.emcore_iTLA.is_open:
            self.emcore_iTLA.write(msa.cap_freqlow2())
            read_byte = self.emcore_iTLA.read_until()
        self.emcore_iTLA.close()
        lfl2 = struct.unpack('>H',read_byte[-2:])[0]*1e-4
        
        """
        self.emcore_iTLA.open()
        if self.emcore_iTLA.is_open:
            self.emcore_iTLA.write(msa.cap_freqlow3())
            read_byte = self.emcore_iTLA.read_until()
        self.emcore_iTLA.close()
        lfl3 = struct.unpack('>H',read_byte[-2:])[0]*1e-6
        """
        
        lfl = lfl1 + lfl2 #+ lfl3
        
        print('Frequency Range: {0:.3f}THz - {1:.3f}THz'.format(lfl, lfh))


    def port_close(self):
        if self.emcore_iTLA.is_open:
            self.emcore_iTLA.close()
        if self.emcore_iTLA.is_open==False:
            print('port closed. \n')



"""
with serial.Serial('COM2', 9600, timeout=3, bytesize=8) as emcore_iTLA:
    emcore_iTLA.write(reset_enable(True, 1))
    




#%%

with serial.Serial('COM2', 9600, timeout=3, bytesize=8) as emcore_iTLA:
    emcore_iTLA.write(channelh(0, 0))
    read_hex  = emcore_iTLA.read_until().hex()
    read_channelh = int(read_hex[-4:], base = 16)

with serial.Serial('COM2', 9600, timeout=3, bytesize=8) as emcore_iTLA:
    emcore_iTLA.write(channel(0, 0))
    read_hex  = emcore_iTLA.read_until().hex()
    read_channel = int(read_hex[-4:], base = 16)

with serial.Serial('COM2', 9600, timeout=3, bytesize=8) as emcore_iTLA:
    emcore_iTLA.write(channelh(15, 1)) #[THz]

with serial.Serial('COM2', 9600, timeout=3, bytesize=8) as emcore_iTLA:
    emcore_iTLA.write(channelh(0, 0))
    read_hex  = emcore_iTLA.read_until().hex()
    read_channelh = int(read_hex[-4:], base = 16)

with serial.Serial('COM2', 9600, timeout=3, bytesize=8) as emcore_iTLA:
    emcore_iTLA.write(channel(1, 1))

with serial.Serial('COM2', 9600, timeout=3, bytesize=8) as emcore_iTLA:
    emcore_iTLA.write(nop())
    read_hex  = emcore_iTLA.read_until().hex()

with serial.Serial('COM2', 9600, timeout=3, bytesize=8) as emcore_iTLA:
    emcore_iTLA.write(channelh(0, 0))
    read_hex  = emcore_iTLA.read_until().hex()
    read_channelh = int(read_hex[-4:], base = 16)

with serial.Serial('COM2', 9600, timeout=3, bytesize=8) as emcore_iTLA:
    emcore_iTLA.write(channel(0, 0))
    read_hex  = emcore_iTLA.read_until().hex()
    read_channel = int(read_hex[-4:], base = 16)

with serial.Serial('COM2', 9600, timeout=3, bytesize=8) as emcore_iTLA:
    emcore_iTLA.write(laser_frequency1())
    read_hex  = emcore_iTLA.read_until().hex()
    read_lf1 = int(read_hex[-4:], base = 16)

with serial.Serial('COM2', 9600, timeout=3, bytesize=8) as emcore_iTLA:
    emcore_iTLA.write(laser_frequency2())
    read_hex  = emcore_iTLA.read_until().hex()
    read_lf2 = int(read_hex[-4:], base = 16)/10.0

with serial.Serial('COM2', 9600, timeout=3, bytesize=8) as emcore_iTLA:
    emcore_iTLA.write(laser_frequency3())
    read_hex  = emcore_iTLA.read_until().hex()
    read_lf3 = int(read_hex[-4:], base = 16)


#%%

with serial.Serial('COM2', 9600, timeout=3, bytesize=8) as emcore_iTLA:
    emcore_iTLA.write(devtyp())
    read_hex  = emcore_iTLA.read_until().hex()
    
with serial.Serial('COM2', 9600, timeout=3, bytesize=8) as emcore_iTLA:
    emcore_iTLA.write(aea_ear())
    read_hex  = emcore_iTLA.read_until().hex()


str(bytes(read_hex[-2:]), 'utf-8')

#%%
# get iTLA information

with serial.Serial('COM2', 9600, timeout=3, bytesize=8) as emcore_iTLA:
    emcore_iTLA.write(grid_spacing(0, 0)) #[10 * GHz]
    read_hex  = emcore_iTLA.read_until().hex()
    read_grid = int(read_hex[-4:], base = 16)/10.0


with serial.Serial('COM2', 9600, timeout=3, bytesize=8) as emcore_iTLA:
    emcore_iTLA.write(grid_spacing_fine(0, 0)) #[MHz]
    read_hex  = emcore_iTLA.read_until().hex()
    read_grid2 = int(read_hex[-4:], base = 16)

with serial.Serial('COM2', 9600, timeout=3, bytesize=8) as emcore_iTLA:
    emcore_iTLA.write(reset_enable(False, 1))
"""
