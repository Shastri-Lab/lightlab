"""
TODO: merge this file with the other Aragon_BOSA_400.py and Aragon_BOSA_400_Queens.py
There should only be one driver.
"""


import socket
import numpy as np
from lightlab.util.data import Spectrum
import pyvisa as visa
import time
import logging
import struct
WIDEST_WLRANGE = [1516, 1565]

# create logger
log = logging.getLogger(__name__)

if(len(log.handlers) == 0): # check if the logger already exists
    # create logger
    log.setLevel(logging.INFO)
    # create console handler and set level to debug
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    # create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    # add formatter to ch
    ch.setFormatter(formatter)
    # add ch to logger
    log.addHandler(ch)
    
class Aragon_BOSA_400_Ether (object):
    
    __apps = np.array(['BOSA', 'TLS', 'CA', 'MAIN'])
    __wlRange = None
    __currApp = None
    __avg = np.array(['4', '8', '12', '32', 'CONT'])
    __sMode = np.array(['HR', 'HS'])
    __CAmeasurement = np.array(['IL', 'RL', 'IL&RL'])
    __CAPolarization = np.array(['1', '2', 'INDEP', 'SIMUL'])
    MAGIC_TIMEOUT = 30

    def __init__(self,location,portNo, **kwargs):
        self.location = location
        self.portNo = portNo
        self.activeTrace = None

        log.info("Connection to OSA using Lan interface on %r",location)
        try:
            self.connectLan()
        except Exception as e:
            log.exception("Could not connect to OSA device")
            print(e)
            raise e
            return
        

    def __del__(self):
        try:
            self.interface.close()
        except Exception as e:
            log.warning("Could not close instrument correctly: exception %r", e.message)
    
    def close(self):
        self.__del__()

    def connectLan(self):
        #""" connect the instrument to a LAN """
        log.debug("creating socket")
        self.interface = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.interface.settimeout(30)

        try:
            log.debug("Connecting to remote socket...")
            self.interface.connect((self.location, self.portNo))
        except Exception as e:
            log.exception("Could not connection to remote socket")
            print(e)
            raise e

        log.debug("Connected to remote socket")
        log.info("OSA ready!")
            
    def stop(self):
        self.__currApp = str(self.ask('INST:STAT:MODE?'))
        if (self.__currApp == 'TLS'):
            self.write('SENS:SWITCH OFF')
            confirm=self.read()
            if confirm!='OK\r\n':
                print('error')
                print(confirm)
        else:
            self.write('INST:STAT:RUN 0')
            confirm=self.read()
            if confirm!='OK\r\n':
                print('error')
                print(confirm)
        
    def start(self):
        self.__currApp = str(self.ask('INST:STAT:MODE?'))
        if (self.__currApp == 'TLS'):
            self.write('SENS:SWITCH ON')
            confirm=self.read()
            if confirm!='OK\r\n':
                print('error')
                print(confirm)
        else:
            self.write('INST:STAT:RUN 1')
            confirm=self.read()
            if confirm!='OK\r\n':
                print('error')
                print(confirm)

    def startup(self):
        print(self.ask('*IDN?'))
        WithReturn=str(self.ask('INST:STAT:MODE?'))
        self.__currApp = WithReturn[:-2]
        print('Current application is ' + self.__currApp + '.')
        print('Please choose application from ["BOSA", "TLS", "CA", "MAIN"]')

    def write(self, command=None):
        if command is not None:
            log.debug("Sending command '" + command + "' using LAN interface...")
            try:
                self.interface.sendall( (command + "\r\n").encode())
            except Exception as e:
                log.exception("Could not send data, command %r",command)
                print(e)
                raise e

    def read(self):
        message = ""
        log.debug("Reading data using LAN interface...")
        while(1):
            try:
                data = self.interface.recv(19200)
                message += data.decode()
            except Exception as e:
                log.exception("Could not read data")
                print(e)
                raise e
            if("\n" in message):
                break
            log.debug("All data read!")
        log.debug("Data received: " + message)
        return message
    
    def readnoend(self): # TODO: this function could be cleaned up with previous one to remove duplication
        message = ""
        log.debug("Reading data using LAN interface...")
        try:
            data = self.interface.recv(19200)
            message += data.decode()
        except Exception as e:
            log.exception("Could not read data")
            print(e)
            raise e

        log.debug("All data read!")
        log.debug("Data received: " + message)
        return message
        
    def ask(self, command):

        """ writes and reads data"""

        data = ""
        self.write(command)
        data = self.read()
        return data
        
    def application(self, app=None):
        if app is not None and app in self.__apps:
            try:
                if app != 'MAIN':
                    if self.__currApp != 'MAIN':
                        self.application('MAIN')
                    self.write('INST:STAT:MODE ' + str(app))
                    confirm=self.read()
                    if confirm!='OK\r\n':
                        print('error')
                        print(confirm)
                    time.sleep(1)
                    self.start()
                    time.sleep(4)
                    if (str(app) == 'TLS'):
                        time.sleep(25)
                else:
                    self.stop()
                    self.write('INST:STAT:MODE ' + str(app))
                    confirm=self.read()
                    if confirm!='OK\r\n':
                        print('error')
                        print(confirm)
            except Exception as e:
                self.__currApp = None
                log.exception("Could not choose the application")
                print(e)
                raise e
        else:
            log.exception(f"`app` should be one of {self.__apps}")

    def getWLrangeFromHardware(self):
        return (
            float(self.ask("SENS:WAV:STOP?")),
            float(self.ask("SENS:WAV:STAR?"))
        )

    @property
    def wlRange(self):
        if self.__wlRange is None:
            self.__wlRange = self.getWLrangeFromHardware()
        return self.__wlRange

    @wlRange.setter
    def wlRange(self, newRange):
        newRangeClipped = np.clip(newRange, a_min=1516, a_max=1565)
        if np.any(newRange != newRangeClipped):
            print('Warning: Requested OSA wlRange out of range. Got', newRange)
        self.write("SENS:WAV:STAR " + str(np.min(newRangeClipped)) + " NM")
        confirm = self.read()
        if confirm != 'OK\r\n': # TODO: change this to log message
            print('error')
            print(confirm)
        self.write("SENS:WAV:STOP " + str(np.max(newRangeClipped)) + " NM")
        confirm = self.read()
        if confirm != 'OK\r\n':
            print('error')
            print(confirm)
        self.__wlRange = self.getWLrangeFromHardware()
        time.sleep(15)

    def ask_TRACE_ASCII(self):

        """ writes and reads data"""

        data = ""
        self.write("FORM ASCII")
        confirm=self.read()
        if confirm!='OK\r\n':
            print('error')
            print(confirm)
        self.write("TRAC?")
        data = self.read_TRACE_ASCII()
        return data
        
    def ask_TRACE_REAL(self):
        print("This code does not work please use ASCII")
        #data = ""
        #self.write("FORM REAL")
        #confirm=self.read()
        #if confirm!='OK\r\n':
        #    print('error')
        #    print(confirm)
        #self.write("TRACE:DATA:COUNT?")
        #answer=self.readnoend()
        #try: 
        #    NumPoints = int(answer)
        #except Exception as e:
        #    log.exception("Could not read data")
        #    print(e)
        #    print(answer)
        #    print("Are you sure the OSA is taking data?")
        #    print("This command takes data from the OSA, but doesn't start a sweep")
        #    raise e
        #self.write("TRAC?")
        #data = self.read_TRACE_REAL_LAN(NumPoints)
        data=[]
        return data
        
    def read_TRACE_ASCII(self):

        """ read something from device"""
          
        message = ""
        log.debug("Reading data using LAN interface...")
        while(1):
            try:
                data = self.interface.recv(19200)
                message += data.decode('ascii')
                         
            except Exception as e:
                log.exception("Could not read data")
                print(e)
                raise e
            if("\n" in message):
                break
            log.debug("All data readed!")
        log.debug("Data received: " + message)
        message=message[:-2]
        Traced=message.split(",")
        Trace=[float(x) for x in Traced]
        return Trace

    def read_TRACE_REAL_LAN(self,numPoints):
    
        """ read something from device"""
        message = ""
        log.debug("Reading data using LAN interface...")
        msgLength = int(numPoints*2*8)
        while(1):
            try:
                data = self.interface.recv(4096)
                message += data.decode()
                         
            except Exception as e:
                log.exception("Could not read data")
                print(e)
                raise e
            if("\n" in message):
                break
        print(message)
        log.debug("All data readed!")
        log.debug("Data received: " + message)
        c, r = 2, int(numPoints)
        Trace= [[0 for x in range(c)] for x in range(r)]
        for x in range(0,int(numPoints)):
            Trace[x][0]=struct.unpack('d', message[(x)*16:(x)*16+8])
            Trace[x][1] = struct.unpack('d', message[(x) * 16+8:(x+1) * 16 ])
        log.debug("Data Converted" )
        return Trace
        
    def spectrum(self, form='ASCII'):
        x=list()
        y=list()
        if(form=='ASCII'):
            data = self.ask_TRACE_ASCII()
            for i in range(0,len(data),2):
                x.append(data[i])
                y.append(data[i+1])
        elif(form=='REAL'):
            print("REAL is broken Please use ASCII Thank you")
            #data = self.ask_TRACE_REAL()
            #for i in range(0,len(data),1):
            #    x.append(data[i][0])
            #    y.append(data[i][1])
        else:
            log.exception("Please choose form 'REAL' or 'ASCII'")
        return Spectrum(x, y, inDbm=True)

    def CAParam(self, avgCount='CONT', avg_is_on = False, sMode='HR', noiseZero=False):
        if type(avgCount) is int:
            avgCount = str(avgCount)
        if type(avgCount) is not str:
            log.exception("avgCount must be a string or int")
            raise TypeError("avgCount must be a string or int")
        if avgCount not in self.__avg:
            avgCount = 'CONT'
            log.exception(f"\nFor average count, please choose from {self.__avg}. Using CONT.\n")
        
        if type(sMode) is not str:
            log.exception("sMode must be a string")
            raise TypeError("sMode must be a string")
        if sMode not in self.__sMode:
            sMode = 'HR'
            log.exception(f"\nFor speed(?) mode, please choose from {self.__sMode}. Using HR.\n")

        if type(noiseZero) is not bool:
            log.exception("noiseZero must be a bool")
            raise TypeError("noiseZero must be a bool")

        if self.__currApp == 'CA' and avgCount in self.__avg and sMode in self.__sMode:
            try:
                self.write('SENS:AVER:COUN ' + avgCount)
                confirm=self.read()
                if confirm!='OK\r\n':
                    print('error')
                    print(confirm)
                if avg_is_on:
                    self.write('SENS:AVER:STAT ON')
                else:
                    self.write('SENS:AVER:STAT OFF')
                confirm=self.read()
                if confirm!='OK\r\n':
                    print('error')
                    print(confirm)
                self.write('SENS:WAV:SMOD ' + sMode)
                confirm=self.read()
                if confirm!='OK\r\n':
                    print('error')
                    print(confirm)
                if noiseZero:
                    self.write('SENS:NOIS')
                    confirm=self.read()
                    if confirm!='OK\r\n':
                        print('error')
                        print(confirm)
            except Exception as e:
                log.exception("Could not set CA parameter")
                print(e)
                raise e
        else:
            log.exception("\nFor average count, please choose from ['4','8','12','32','CONT']\nFor speed mode, please choose from ['HR','HS']")
    
    def CAInput(self, meas='IL', pol='1'):
        if meas in self.__CAmeasurement and pol in self.__CAPolarization:
            try:
                self.write('INP:SPAR '+meas)
                confirm=self.read()
                if confirm!='OK\r\n':
                    print('error')
                    print(confirm)
                self.write('INP:POL '+pol)
                confirm=self.read()
                if confirm!='OK\r\n':
                    print('error')
                    print(confirm)
            except Exception as e:
                log.exception("Could not set input parameters to CA")
                print(e)
                raise e
        else:
            print("\nFor measurement type, please choose from ['IL', 'RL', 'IL&RL']\nFor polarization, please choose from ['1', '2', 'INDEP', 'SIMUL']")
    
    def TLSwavelength(self, waveLength=None):
        if waveLength is not None and self.__currApp == 'TLS':
            try:
                self.write('SENS:SWITCH ON')
                confirm=self.read()
                if confirm!='OK\r\n':
                    print('error')
                    print(confirm)
                self.write('SENS:WAV:STAT '+str(waveLength)+' NM')
                confirm=self.read()
                if confirm!='OK\r\n':
                    print('error')
                    print(confirm)
            except Exception as e:
                log.exception("Could not set the wavelength for TLS")
                print(e)
                raise e
        else:
            print("Please specify the wavelength and choose application TLS")