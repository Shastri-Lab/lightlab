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
   #from bip_4 import BIP4_lib as blib
   from itla_msa_modules.bip_4 import BIP4_lib as blib
except:
   raise

class msa:

## emcore iTLA 1-83
    def known_address(hex_address, val, rw):
        if rw == False:
            val = 0
        ary_command = blib.BIP4(rw, hex_address, val)
        bytes_command = bytes([x for x in ary_command])
        return bytes_command
    
    def reset_enable(stat, rw):
        hex_address = 0x32 #Reset/Enable
        if stat:
            int_val = 0b00001000
        else:
            int_val = 0b00000000
        if rw == False:
            int_val = 0
        ary_command = blib.BIP4(rw, hex_address, int_val)
        bytes_command = bytes([x for x in ary_command])
        return bytes_command
    
    def device_fatal(rw):
        hex_address = 0x20 #GRID
        if rw == False:
            int_val = 0
        ary_command = blib.BIP4(rw, hex_address, int_val)
        bytes_command = bytes([x for x in ary_command])
        return bytes_command
    
    def device_warning(rw):
        hex_address = 0x21 #GRID
        if rw == False:
            int_val = 0
        ary_command = blib.BIP4(rw, hex_address, int_val)
        bytes_command = bytes([x for x in ary_command])
        return bytes_command
    
    def optical_power(int_val, rw): #100*dBm
        hex_address = 0x31 #GRID
        if rw == False:
            int_val = 0
        ary_command = blib.BIP4(rw, hex_address, int_val)
        bytes_command = bytes([x for x in ary_command])
        return bytes_command
        
    def grid_spacing(int_val, rw): #10*GHz
        hex_address = 0x34 #GRID
        if rw == False:
            int_val = 0
        ary_command = blib.BIP4(rw, hex_address, int_val)
        bytes_command = bytes([x for x in ary_command])
        return bytes_command
    
    def grid_spacing_fine(int_val, rw): #MHz
        hex_address = 0x66 #GRID
        if rw == False:
            int_val = 0
        ary_command = blib.BIP4(rw, hex_address, int_val)
        bytes_command = bytes([x for x in ary_command])
        return bytes_command
        
    def fcf1(int_val, rw): #THz
        hex_address = 0x35 #FCF1
        if rw == False:
            int_val = 0
        ary_command = blib.BIP4(rw, hex_address, int_val)
        bytes_command = bytes([x for x in ary_command])
        return bytes_command
    
    def fcf2(int_val, rw): #10*GHz
        hex_address = 0x36 #FCF2
        if rw == False:
            int_val = 0
        ary_command = blib.BIP4(rw, hex_address, int_val)
        bytes_command = bytes([x for x in ary_command])
        return bytes_command
    
    def fcf3(int_val, rw): #MHz
        hex_address = 0x67 #FCF3
        if rw == False:
            int_val = 0
        ary_command = blib.BIP4(rw, hex_address, int_val)
        bytes_command = bytes([x for x in ary_command])
        return bytes_command
    
    def ftf(int_val, rw): #MHz
        hex_address = 0x62 #FTF
        if rw == False:
            int_val = 0
        ary_command = blib.BIP4(rw, hex_address, int_val)
        bytes_command = bytes([x for x in ary_command])
        return bytes_command
    
    def channel(int_val, rw):
        hex_address = 0x30 #Channel
        if rw == False:
            int_val = 0
        ary_command = blib.BIP4(rw, hex_address, int_val)
        bytes_command = bytes([x for x in ary_command])
        return bytes_command
    
    def channelh(int_val, rw):
        hex_address = 0x65 #ChannelH
        if rw == False:
            int_val = 0
        ary_command = blib.BIP4(rw, hex_address, int_val)
        bytes_command = bytes([x for x in ary_command])
        return bytes_command

    def devtyp():
        hex_address = 0x01 #Device Type
        rw = 0
        int_val = 0
        ary_command = blib.BIP4(rw, hex_address, int_val)
        bytes_command = bytes([x for x in ary_command])
        return bytes_command
    
    def manufacturer():
        hex_address = 0x02 #Device Type
        rw = 0
        int_val = 0
        ary_command = blib.BIP4(rw, hex_address, int_val)
        bytes_command = bytes([x for x in ary_command])
        return bytes_command
    
    def model():
        hex_address = 0x03 #Device Type
        rw = 0
        int_val = 0
        ary_command = blib.BIP4(rw, hex_address, int_val)
        bytes_command = bytes([x for x in ary_command])
        return bytes_command
    
    def serno():
        hex_address = 0x04 #Device Type
        rw = 0
        int_val = 0
        ary_command = blib.BIP4(rw, hex_address, int_val)
        bytes_command = bytes([x for x in ary_command])
        return bytes_command
    
    def manufact_date():
        hex_address = 0x05 #Device Type
        rw = 0
        int_val = 0
        ary_command = blib.BIP4(rw, hex_address, int_val)
        bytes_command = bytes([x for x in ary_command])
        return bytes_command
    
    def io_capabilities():
        hex_address = 0x0d #Device Type
        rw = 0
        int_val = 0
        ary_command = blib.BIP4(rw, hex_address, int_val)
        bytes_command = bytes([x for x in ary_command])
        return bytes_command
    
    def aea_ear():
        hex_address = 0x0b #Device Type
        ReadWriteDec = 0
        int_val = 0
        ary_command = blib.BIP4(ReadWriteDec, hex_address, int_val)
        bytes_command = bytes([x for x in ary_command])
        return bytes_command

    def laser_frequency1():
        hex_address = 0x40 #LF1
        rw = 0
        int_val = 0
        ary_command = blib.BIP4(rw, hex_address, int_val)
        bytes_command = bytes([x for x in ary_command])
        return bytes_command
    
    def laser_frequency2():
        hex_address = 0x41 #LF2
        rw = 0
        int_val = 0
        ary_command = blib.BIP4(rw, hex_address, int_val)
        bytes_command = bytes([x for x in ary_command])
        return bytes_command
    
    def laser_frequency3():
        hex_address = 0x68 #LF3
        rw = 0
        int_val = 0
        ary_command = blib.BIP4(rw, hex_address, int_val)
        bytes_command = bytes([x for x in ary_command])
        return bytes_command
    
    def measured_optical_power(): #100*dBm
        hex_address = 0x42 #OOP
        rw = 0
        int_val = 0
        ary_command = blib.BIP4(rw, hex_address, int_val)
        bytes_command = bytes([x for x in ary_command])
        return bytes_command
    
    def currents():
        hex_address = 0x57 #OOP
        rw = 0
        int_val = 0
        ary_command = blib.BIP4(rw, hex_address, int_val)
        bytes_command = bytes([x for x in ary_command])
        return bytes_command
    
    def temperatures():
        hex_address = 0x58 #OOP
        rw = 0
        int_val = 0
        ary_command = blib.BIP4(rw, hex_address, int_val)
        bytes_command = bytes([x for x in ary_command])
        return bytes_command
    
    def laser_age():
        hex_address = 0x61 #OOP
        rw = 0
        int_val = 0
        ary_command = blib.BIP4(rw, hex_address, int_val)
        bytes_command = bytes([x for x in ary_command])
        return bytes_command
    
    def cap_ftf():
        hex_address = 0x4f #OOP
        rw = 0
        int_val = 0
        ary_command = blib.BIP4(rw, hex_address, int_val)
        bytes_command = bytes([x for x in ary_command])
        return bytes_command
    
    def opsl():
        hex_address = 0x50 #OOP
        rw = 0
        int_val = 0
        ary_command = blib.BIP4(rw, hex_address, int_val)
        bytes_command = bytes([x for x in ary_command])
        return bytes_command
    
    def opsh():
        hex_address = 0x51 #OOP
        rw = 0
        int_val = 0
        ary_command = blib.BIP4(rw, hex_address, int_val)
        bytes_command = bytes([x for x in ary_command])
        return bytes_command
    
    def cap_freqlow1():
        hex_address = 0x52 #OOP
        rw = 0
        int_val = 0
        ary_command = blib.BIP4(rw, hex_address, int_val)
        bytes_command = bytes([x for x in ary_command])
        return bytes_command
    
    def cap_freqlow2():
        hex_address = 0x53 #OOP
        rw = 0
        int_val = 0
        ary_command = blib.BIP4(rw, hex_address, int_val)
        bytes_command = bytes([x for x in ary_command])
        return bytes_command
    
    def cap_freqlow2():
        hex_address = 0x69 #OOP
        rw = 0
        int_val = 0
        ary_command = blib.BIP4(rw, hex_address, int_val)
        bytes_command = bytes([x for x in ary_command])
        return bytes_command
    
    def cap_freqhigh1():
        hex_address = 0x54 #OOP
        rw = 0
        int_val = 0
        ary_command = blib.BIP4(rw, hex_address, int_val)
        bytes_command = bytes([x for x in ary_command])
        return bytes_command
    
    def cap_freqhigh2():
        hex_address = 0x55 #OOP
        rw = 0
        int_val = 0
        ary_command = blib.BIP4(rw, hex_address, int_val)
        bytes_command = bytes([x for x in ary_command])
        return bytes_command
    
    def cap_freqhigh3():
        hex_address = 0x6a #OOP
        rw = 0
        int_val = 0
        ary_command = blib.BIP4(rw, hex_address, int_val)
        bytes_command = bytes([x for x in ary_command])
        return bytes_command
    
    def cap_grid():
        hex_address = 0x56 #OOP
        rw = 0
        int_val = 0
        ary_command = blib.BIP4(rw, hex_address, int_val)
        bytes_command = bytes([x for x in ary_command])
        return bytes_command

    def nop():
        hex_address = 0x00 #NOP
        rw = 0
        int_val = 0
        ary_command = blib.BIP4(rw, hex_address, int_val)
        bytes_command = bytes([x for x in ary_command])
        return bytes_command
        
    def scan_range(int_val, rw):
        hex_address = 0xe4 #FCF3
        if rw == False:
            int_val = 0
        ary_command = blib.BIP4(rw, hex_address, int_val)
        bytes_command = bytes([x for x in ary_command])
        return bytes_command
        
    def scan_speed(int_val, rw):
        hex_address = 0xf1 #FCF3
        if rw == False:
            int_val = 0
        ary_command = blib.BIP4(rw, hex_address, int_val)
        bytes_command = bytes([x for x in ary_command])
        return bytes_command
        
    def scan_cal(int_val, rw):
        hex_address = 0xf7 #FCF3
        if rw == False:
            int_val = 0
        ary_command = blib.BIP4(rw, hex_address, int_val)
        bytes_command = bytes([x for x in ary_command])
        return bytes_command
        
    def clean_mode(int_val, rw):
        hex_address = 0x90 #FCF3
        if rw == False:
            int_val = 0
        ary_command = blib.BIP4(rw, hex_address, int_val)
        bytes_command = bytes([x for x in ary_command])
        return bytes_command
        
    def clean_swp(int_val, rw):
        hex_address = 0xe5 #FCF3
        if rw == False:
            int_val = 0
        ary_command = blib.BIP4(rw, hex_address, int_val)
        bytes_command = bytes([x for x in ary_command])
        return bytes_command
        
    def read_offset(int_val, rw):
        hex_address = 0xe6 #FCF3
        if rw == False:
            int_val = 0
        ary_command = blib.BIP4(rw, hex_address, int_val)
        bytes_command = bytes([x for x in ary_command])
        return bytes_command

    def cjf1(int_val, rw): #THz
        hex_address = 0xea #CJF1
        if rw == False:
            int_val = 0
        ary_command = blib.BIP4(rw, hex_address, int_val)
        bytes_command = bytes([x for x in ary_command])
        return bytes_command
    
    def cjf2(int_val, rw): #10*GHz
        hex_address = 0xeb #CJF2
        if rw == False:
            int_val = 0
        ary_command = blib.BIP4(rw, hex_address, int_val)
        bytes_command = bytes([x for x in ary_command])
        return bytes_command
        
    def sled_temp(int_val, rw): #0.01 C
        hex_address = 0xec
        if rw == False:
            int_val = 0
        ary_command = blib.BIP4(rw, hex_address, int_val)
        bytes_command = bytes([x for x in ary_command])
        return bytes_command
        
    def drive_current(int_val, rw): #100 uA
        hex_address = 0xe9
        if rw == False:
            int_val = 0
        ary_command = blib.BIP4(rw, hex_address, int_val)
        bytes_command = bytes([x for x in ary_command])
        return bytes_command
        
    def clean_jump(int_val, rw): #Initiate clean jump
        hex_address = 0xed
        if rw == False:
            int_val = 0
        ary_command = blib.BIP4(rw, hex_address, int_val)
        bytes_command = bytes([x for x in ary_command])
        bytes_command = bytes([x for x in ary_command])
        return bytes_command
        
    def cj_err(int_val, rw): #Coded as cj_err = (value - 10000)/10 GHz
        hex_address = 0xe6
        if rw == False:
            int_val = 0
        ary_command = blib.BIP4(rw, hex_address, int_val)
        bytes_command = bytes([x for x in ary_command])
        return bytes_command
        
    def clean_jump_mitla(int_val, rw): #Clean jump register for micro itla
        hex_address = 0xd0
        if rw == False:
            int_val = 0
        ary_command = blib.BIP4(rw, hex_address, int_val)
        bytes_command = bytes([x for x in ary_command])
        return bytes_command
        
    def clean_jump_cal(int_val, rw): #Clean jump calibration register for micro itla
        hex_address = 0xd2
        if rw == False:
            int_val = 0
        ary_command = blib.BIP4(rw, hex_address, int_val)
        bytes_command = bytes([x for x in ary_command])
        return bytes_command