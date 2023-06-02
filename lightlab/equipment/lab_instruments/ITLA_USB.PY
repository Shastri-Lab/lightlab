"""
TODO: I'm not sure this file belongs here; I'm including it while merging from the lab PC.
The EMCORE ITLAs have their own driver file. This seems to be part of the driver that should run
on the raspberry pi, and doesn't necessarily need to be included in lightlab. Find a home for this file later.
"""


import serial
import time
import struct
import os
import os.path
import time
import sys
import threading

ITLA_NOERROR = 0x00
ITLA_EXERROR = 0x01
ITLA_AEERROR = 0x02
ITLA_CPERROR = 0x03
ITLA_NRERROR = 0x04
ITLA_CSERROR = 0x05
ITLA_ERROR_SERPORT = 0x01
ITLA_ERROR_SERBAUD = 0x02

REG_Nop = 0x00
REG_Mfgr = 0x02
REG_Model = 0x03
REG_Serial = 0x04
REG_Release = 0x06
REG_Gencfg = 0x08
REG_AeaEar = 0x0B
REG_Iocap = 0x0D
REG_Ear = 0x10
REG_Dlconfig = 0x14
REG_Dlstatus = 0x15
REG_Channel = 0x30
REG_Power = 0x31
REG_Resena = 0x32
REG_Grid = 0x34
REG_Fcf1 = 0x35
REG_Fcf2 = 0x36
REG_Oop = 0x42
REG_Opsl = 0x50
REG_Opsh = 0x51
REG_Lfl1 = 0x52
REG_Lfl2 = 0x53
REG_Lfh1 = 0x54
REG_Lfh2 = 0x55
REG_Currents = 0x57
REG_Temps = 0x58
REG_Ftf = 0x62
REG_Mode = 0x90
REG_PW = 0xE0
REG_Csweepsena = 0xE5
REG_Csweepamp = 0xE4
REG_Cscanamp = 0xE4
REG_Cscanon = 0xE5
REG_Csweepon = 0xE5
REG_Csweepoffset = 0xE6
REG_Cscanoffset = 0xE6
REG_Cscansled = 0xF0
REG_Cscanf1 = 0xF1
REG_Cscanf2 = 0xF2
REG_CjumpTHz = 0xEA
REG_CjumpGHz = 0xEB
REG_CjumpSled = 0xEC
REG_Cjumpon = 0xED
REG_Cjumpoffset = 0xE6


class ITLA_USB:

    READ = 0
    WRITE = 1
    latestregister = 0
    tempport = 0
    raybin = 0
    queue = []
    maxrowticket = 0

    _error = ITLA_NOERROR
    seriallock = 0

    port = None
    sercon = None

    def __init__(self, port):
        self.port = port
        self.sercon = self.ITLAConnect(self.port, 9600)
        time.sleep(1)

    def stripString(self, input):
        outp = ''
        input = str(input)
        teller = 0
        while teller < len(input) and ord(input[teller]) > 47:
            outp = outp + input[teller]
            teller = teller + 1
        return outp

    def ITLALastError(self):
        return self._error

    def SerialLock(self):
        return self.seriallock

    def SerialLockSet(self):
        self.seriallock = 1

    def SerialLockUnSet(self):
        self.seriallock = 0
        self.queue.pop(0)

    def checksum(self, byte0, byte1, byte2, byte3):
        bip8 = (byte0 & 0x0f) ^ byte1 ^ byte2 ^ byte3
        bip4 = ((bip8 & 0xf0) >> 4) ^ (bip8 & 0x0f)
        return bip4

    def Send_command(self, byte0, byte1, byte2, byte3):
        self.sercon.write(chr(byte0).encode())
        self.sercon.write(chr(byte1).encode())
        self.sercon.write(chr(byte2).encode())
        self.sercon.write(chr(byte3).encode())

    def Receive_response(self):
        reftime = time.clock()
        while self.sercon.inWaiting() < 4:
            if time.clock() > reftime + 0.25:
                self._error = ITLA_NRERROR
                return (0xFF, 0xFF, 0xFF, 0xFF)
            time.sleep(0.0001)
        try:
            byte0 = ord(self.sercon.read(1))
            byte1 = ord(self.sercon.read(1))
            byte2 = ord(self.sercon.read(1))
            byte3 = ord(self.sercon.read(1))
        except:
            print('problem with serial communication. queue[0] =', self.queue)
            byte0 = 0xFF
            byte1 = 0xFF
            byte2 = 0xFF
            byte3 = 0xFF
        if self.checksum(byte0, byte1, byte2, byte3) == byte0 >> 4:
            self._error = byte0 & 0x03
            return byte0, byte1, byte2, byte3
        else:
            self._error = ITLA_CSERROR
            return byte0, byte1, byte2, byte3

    def Receive_simple_response(self):
        global CoBrite
        reftime = time.clock()
        while self.sercon.inWaiting() < 4:
            if time.clock() > reftime + 0.25:
                self._error = ITLA_NRERROR
                return 0xFF, 0xFF, 0xFF, 0xFF
            time.sleep(0.0001)
        byte0 = ord(self.sercon.read(1))
        byte1 = ord(self.sercon.read(1))
        byte2 = ord(self.sercon.read(1))
        byte3 = ord(self.sercon.read(1))

    def ITLAConnect(self, port, baudrate=9600):
        global CoBrite
        reftime = time.clock()
        connected = False
        try:
            self.sercon = serial.Serial(port, baudrate, timeout=1)
        except serial.SerialException:
            return ITLA_ERROR_SERPORT
        baudrate2 = 4800
        while baudrate2 < 115200:
            self.ITLA(REG_Nop, 0, 0)
            if self.ITLALastError() != ITLA_NOERROR:
                # go to next baudrate
                if baudrate2 == 4800:
                    baudrate2 = 9600
                elif baudrate2 == 9600:
                    baudrate2 = 19200
                elif baudrate2 == 19200:
                    baudrate2 = 38400
                elif baudrate2 == 38400:
                    baudrate2 = 57600
                elif baudrate2 == 57600:
                    baudrate2 = 115200
                self.sercon.close()
                self.sercon = serial.Serial(port, baudrate2, timeout=1)
            else:
                return self.sercon
        self.sercon.close()
        return ITLA_ERROR_SERBAUD

    def ITLA(self, register, data, rw):
        lock = threading.Lock()
        lock.acquire()
        rowticket = self.maxrowticket + 1
        self.maxrowticket = self.maxrowticket + 1
        self.queue.append(rowticket)
        lock.release()
        while self.queue[0] != rowticket:
            rowticket = rowticket
        if rw == 0:
            byte2 = int(data / 256)
            byte3 = int(data - byte2 * 256)
            self.latestregister = register
            self.Send_command(int(self.checksum(0, register, byte2, byte3)) * 16, register, byte2, byte3)
            test = self.Receive_response()
            b0 = test[0]
            b1 = test[1]
            b2 = test[2]
            b3 = test[3]
            if (b0 & 0x03) == 0x02:
                test = self.AEA(b2 * 256 + b3)
                lock.acquire()
                self.queue.pop(0)
                lock.release()
                return test
            lock.acquire()
            self.queue.pop(0)
            lock.release()
            return b2 * 256 + b3
        else:
            byte2 = int(data / 256)
            byte3 = int(data - byte2 * 256)
            self.Send_command(int(self.checksum(1, register, byte2, byte3)) * 16 + 1, register, byte2, byte3)
            test = self.Receive_response()
            lock.acquire()
            self.queue.pop(0)
            lock.release()
            return test[2] * 256 + test[3]

    def ITLA_send_only(self, register, data, rw):
        rowticket = self.maxrowticket + 1
        self.maxrowticket = self.maxrowticket + 1
        self.queue.append(rowticket)
        while self.queue[0] != rowticket:
            time.sleep(.1)
        self.SerialLockSet()
        if rw == 0:
            self.latestregister = register
            self.Send_command(int(self.checksum(0, register, 0, 0)) * 16, register, 0, 0)
            self.Receive_simple_response()
            self.SerialLockUnSet()
        else:
            byte2 = int(data / 256)
            byte3 = int(data - byte2 * 256)
            self.Send_command(int(self.checksum(1, register, byte2, byte3)) * 16 + 1, register, byte2, byte3)
            self.Receive_simple_response()
            self.SerialLockUnSet()

    def AEA(self, bytes):
        outp = ''
        while bytes > 0:
            self.Send_command(int(self.checksum(0, REG_AeaEar, 0, 0)) * 16, REG_AeaEar, 0, 0)
            test = self.Receive_response()
            outp = outp + chr(test[2])
            outp = outp + chr(test[3])
            bytes = bytes - 2
        return outp

    def ITLAFWUpgradeStart(self, raydata, salvage=0):
        # set the baudrate to maximum and reconfigure the serial connection
        if salvage == 0:
            ref = self.stripString(self.ITLA(REG_Serial, 0, 0))
            if len(ref) < 5:
                print('problems with communication before start FW upgrade')
                return self.sercon, 'problems with communication before start FW upgrade'
            self.ITLA(REG_Resena, 0, 1)
        self.ITLA(REG_Iocap, 64, 1)  # bits 4-7 are 0x04 for 115200 baudrate
        # validate communication with the laser
        self.tempport = self.sercon.portstr
        self.sercon.close()
        self.sercon = serial.Serial(self.tempport, 115200, timeout=1)
        if self.stripString(self.ITLA(REG_Serial, 0, 0)) != ref:
            return (self.sercon, 'After change baudrate: serial discrepancy found. Aborting. ' + str(
                self.stripString(self.ITLA(REG_Serial, 0, 0))) + ' ' + str(params.serial))
        # load the ray file
        self.raybin = raydata
        if len(self.raybin) & 0x01: self.raybin.append('\x00')
        self.ITLA(REG_Dlconfig, 2, 1)  # first do abort to make sure everything is ok
        # print ITLALastError()
        if self.ITLALastError() != ITLA_NOERROR:
            return self.sercon, 'After dlconfig abort: error found. Aborting. ' + str(self.ITLALastError())
        # initiate the transfer; INIT_WRITE=0x0001; TYPE=0x1000; RUNV=0x0000
        # temp=ITLA(self.sercon,REG_Dlconfig,0x0001 ^ 0x1000 ^ 0x0000,1)
        # check temp for the correct feedback
        self.ITLA(REG_Dlconfig, 3 * 16 * 256 + 1, 1)  # initwrite=1; type =3 in bits 12:15
        # print ITLALastError()
        if self.ITLALastError() != ITLA_NOERROR:
            return self.sercon, 'After dlconfig init_write: error found. Aborting. ' + str(self.ITLALastError())
        return self.sercon, ''

    def ITLAFWUpgradeWrite(self, count):
        # start writing bits
        teller = 0
        while teller < count:
            self.ITLA_send_only(REG_Ear, struct.unpack('>H', self.raybin[teller:teller + 2])[0], 1)
            teller = teller + 2
        self.raybin = self.raybin[count:]
        # write done. clean up
        return ('')

    def ITLAFWUpgradeComplete(self):
        time.sleep(0.5)
        self.sercon.flushInput()
        self.sercon.flushOutput()
        self.ITLA(REG_Dlconfig, 4, 1)  # done (bit 2)
        if self.ITLALastError() != ITLA_NOERROR:
            return self.sercon, 'After dlconfig done: error found. Aborting. ' + str(self.ITLALastError())
        # init check
        self.ITLA(REG_Dlconfig, 16, 1)  # init check bit 4
        if self.ITLALastError() == ITLA_CPERROR:
            while (self.ITLA(REG_Nop, 0, 0) & 0xff00) > 0:
                time.sleep(0.5)
        elif self.ITLALastError() != ITLA_NOERROR:
            return self.sercon, 'After dlconfig done: error found. Aborting. ' + str(self.ITLALastError())
        # check for valid=1
        temp = self.ITLA(REG_Dlstatus, 0, 0)
        if temp & 0x01 == 0x00:
            return self.sercon, 'Dlstatus not good. Aborting. '
            # write concluding dlconfig
        self.ITLA(REG_Dlconfig, 3 * 256 + 32, 1)  # init run (bit 5) + runv (bit 8:11) =3
        if self.ITLALastError() != ITLA_NOERROR:
            return self.sercon, 'After dlconfig init run and runv: error found. Aborting. ' + str(self.ITLALastError())
        time.sleep(1)
        # set the baudrate to 9600 and reconfigure the serial connection
        self.ITLA(REG_Iocap, 0, 1)  # bits 4-7 are 0x0 for 9600 baudrate
        self.sercon.close()
        # validate communication with the laser
        self.sercon = serial.Serial(self.tempport, 9600, timeout=1)
        ref = self.stripString(self.ITLA(REG_Serial, 0, 0))
        if len(ref) < 5:
            return (self.sercon, 'After change back to 9600 baudrate: serial discrepancy found. Aborting. ' + str(
                self.stripString(self.ITLA(REG_Serial, 0, 0))) + ' ' + str(params.serial))
        return self.sercon, ''

    def ITLASplitDual(self, input, rank):
        teller = rank * 2
        return ord(input[teller]) * 256 + ord(input[teller + 1])

    def ITLASetFreq(self, freq):
        '''
        Set laser wavelength
        :param freq: target wavelength in units of THz
        :return: None
        '''
        thz = int(freq)
        ghz = 1000 * (freq - thz)
        print(self.ITLA(0x35, thz, 1))
        print(self.ITLA(0x36, 10 * ghz, 1))

    def ITLASetPower(self, power):
        '''
        Set laser power
        :param power: target power in units of dBm
        :return:
        '''
        print(self.ITLA(0x31, 100 * power, 1))

    def ITLAEnable(self):
        print(self.ITLA(0x32, 8, 1))

    def ITLADisable(self):
        print(self.ITLA(0x32, 0, 1))
