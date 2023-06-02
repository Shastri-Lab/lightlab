# -*- coding: utf-8 -*-
"""
TODO: I think this file can be removed. Was this the example program provided by the vendor?
@ZhimuG do you know? -@hughmor
"""




import socket
import logging
import struct
import matplotlib.pyplot as plt
import time
import pyvisa as visa

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

    

    

class BOSA:

    """ class BOSA: driver used to communicate with BOSA equipment"""

    def __init__(self, interfaceType, location, portNo = 10000, IDN=True, Reset = False):

        """create the BOSA object and tries to establish a connection with the equipment

            Parameters:

                interfaceType -> LAN, GPIB interface utilyzed in connection

                location      -> IP address or GPIB address of equipment.

                portN         -> no of the port where the interface is open (LAN)

        """

        self.interfaceType = interfaceType

        self.location = location

        self.portNo = portNo

        

        self.activeTrace = None

        

        if(interfaceType.lower() == "lan"):

           

            log.info("Connection to BOSA using Lan interface on %r",location)

            try:

                self.connectLan()

            except Exception as e:

                log.exception("Could not connect to BOSA device")

                print(e)

                raise e

                return

        elif(interfaceType.lower() == "gpib"):

            log.info("GPIB interface chosen to connect BOSA on %r",location)

            try:

                self.interface = visa.ResourceManager().open_resource(location)

            except Exception as e:

                log.exception("couldn't connect to device")

                print(e)

                raise e

                return

            log.info("Connected to device.")

        else:

            log.error("Interface Type " + interfaceType + " not valid")

            raise Exception("interface type invalid")

            return

        if(IDN):

            try:

                log.debug("Sending IDN to device...")

                self.write("*IDN?")

            except Exception as e:

                log.exception("Could not send *IDN? device")

                print(e)

                raise e



            log.debug("IDN send, waiting response...")

            try:

                response = self.read()

            except Exception as e:

                log.exception("Could read response from device")

                print(e)

                raise e

            

            print("IDN= " + response)

            

        if(Reset):

            try:

                log.info("resting device")

                self.write("*RST")

            except Exception as e:

                log.exception("Could not reset device")

                print(e)

                raise e

            

    def __del__(self):

        try:

            if(self.interfaceType == "LAN"):

                self.interface.close()

            elif(self.interfaceType == "GPIB"):

                self.interface.close()

        except Exception as e:

            log.warning("could not close interface correctly: exception %r", e.message)

    

    def connectLan(self):

        """ connect the instrument to a LAN """

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

        log.info("BOSA ready!")

        

    def write(self, command):

        """ write to equiment: independent of the interface

            Parameters:

                command -> data to send to device + \r\n

        """

        if(self.interfaceType.lower() == "lan"):

            log.debug("Sending command '" + command + "' using LAN interface...")

            try:

                self.interface.sendall( (command + "\r\n").encode())

            except Exception as e:

                log.exception("Could not send data, command %r",command)

                print(e)

                raise e

        elif(self.interfaceType.lower() == "gpib"):

            log.debug("Sending command '" + command + "' using GPIB interface...")

            try:

                self.interface.write(command)

            except Exception as e:

                log.exception("Could not send data, command %r",command)

                print(e)

                raise e

                

    def read(self):

        """ read something from device"""

        message = ""

        if(self.interfaceType.lower() == "lan"):

            log.debug("Reading data using LAN interface...")

            while(1):

                try:
                    data = self.interface.recv(115200)
                    message += data.decode()

                except Exception as e:

                    log.exception("Could not read data")

                    print(e)

                    raise e

                if("\n" in message):

                    break

            log.debug("All data readed!")

        elif(self.interfaceType.lower() == "gpib"):

            log.debug("Reading data using GPIB interface...")

            while(1):

                try:

                    message = self.interface.read()

                    if(message!=''):
                        break
                
                except Exception as e:

                    log.exception("Could not read data")

                    print(e)

                    raise e

#                if("\n" in message):
#
#                    break

            log.debug("All data readed!")

        log.debug("Data received: " + message)

        return message



    def ask(self, command):

        """ writes and reads data"""

        data = ""

        self.write(command)

        data = self.read()

        return data

    def ask_TRACE_REAL(self):

        """ writes and reads data"""


        self.write("FORM REAL")
        
        NumPoints=int(self.ask("TRACE:DATA:COUNT?"))

        data = ""

        self.write("TRAC?")

        data = self.read_TRACE_REAL(NumPoints)

        return data
    
    def ask_TRACE_ASCII(self):

        """ writes and reads data"""

        data = ""
        self.write("FORM ASCII")

        self.write("TRAC?")
        data = self.read_TRACE_ASCII()


        return data
    
    def ask_TRACE(self, interface):
    
        if(self.interfaceType.lower() == "lan"):
            data = self.ask_TRACE_REAL(numPoints)
         
        elif(self.interfaceType.lower() == "gpib"):
            data = self.ask_TRACE_ASCII()
        return data


    def read_TRACE_REAL(self,numPoints):

        """ read something from device"""

        response_byte_array=b''
        msgLength = int(numPoints*2*8) # 8 Bytes (double) and 2 values, wavelength and power.

        log.debug("Reading data using LAN interface...")

        while(1):

            try:
                if (msgLength<19200):
                    Byte_data = self.interface.recv(msgLength)
                else:
                    Byte_data = self.interface.recv(19200)

                response_byte_array= b''.join([response_byte_array, Byte_data])
                read_length=len(Byte_data)
                msgLength=msgLength-read_length

            except Exception as e:

                log.exception("Could not read data")

                print(e)

                raise e

            if(msgLength==0):
                break

        c, r = 2, int(numPoints);
        Trace= [[0 for x in range(c)] for x in range(r)]
        for x in range(0,int(numPoints)):
            Trace[x][0]=struct.unpack('d', response_byte_array[(x)*16:(x)*16+8])
            Trace[x][1] = struct.unpack('d', response_byte_array[(x) * 16+8:(x+1) * 16 ])

        return Trace

    def read_TRACE_ASCII(self):

        """ read something from device"""
        log.debug("Reading data using GPIB interface...")

        while(1):

            try:
                
                Byte_data = self.interface.read_ascii_values(converter='f', separator=',', container=list,delay=None)
            
                if((Byte_data != '')):
                    break
                
            except Exception as e:

                log.exception("Could not read data")

                print(e)

                raise e

        return Byte_data
    
    
    def read_TRACE(self,interface,numPoints):
     
        if(self.interfaceType.lower() == "lan"):
            self.read_TRACE_REAL(numPoints)
         
        elif(self.interfaceType.lower() == "gpib"):
            self.read_TRACE_REAL_GPIB()
         
         

if __name__ == "__main__":

    
    rm = visa.ResourceManager()
    rm.list_resources()
    print(rm.list_resources())
    
    address = 'GPIB0::4::INSTR'
    BOSA = BOSA("gpib", address)
    
    BOSA.write('INST:STAT:RUN 0')
    BOSA.write('INST:STAT:MODE MAIN')
    time.sleep(3)
    BOSA.write('INST:STAT:MODE BOSA')
    BOSA.write('INST:STAT:RUN 1')
    
    Trace = BOSA.ask_TRACE("gpib")

    x=list()
    y=list()

    for i in range(0,len(Trace),2):
       x.append(Trace[i])
       y.append(Trace[i+1])


    plt.plot(x,y)
    plt.show()
