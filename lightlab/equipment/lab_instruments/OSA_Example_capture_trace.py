# -*- coding: utf-8 -*-
"""
TODO: I think this file can be removed. Was this the example program provided by the vendor?
@ZhimuG do you know? -@hughmor
"""




import socket

import logging
import  struct
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

                self.interface.write(command + "\r\n")

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
                    data = self.interface.recv(19200)
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

                except Exception as e:

                    log.exception("Could not read data")

                    print(e)

                    raise e

                if("\n" in message):

                    break

            log.debug("All data readed!")

        log.debug("Data received: " + message)

        return message



    def ask(self, command):

        """ writes and reads data"""

        data = ""

        self.write(command)

        data = self.read()

        return data

    def ask_TRACE_REAL(self, numPoints):

        """ writes and reads data"""

        data = ""

        self.write("TRAC?")

        data = self.read_TRACE_REAL(numPoints)

        return data



    def read_TRACE_REAL(self,numPoints):

        """ read something from device"""

        response_byte_array=b''
        msgLength = int(numPoints*2*8) # 8 Bytes (double) and 2 values, wavelength and power.

        log.debug("Reading data using LAN interface...")

        while(1):

            try:
                if(self.interfaceType.lower() == "lan"):
                    if (msgLength<19200):
                        Byte_data = self.interface.recv(msgLength)
                    else:
                        Byte_data = self.interface.recv(19200)
                elif(self.interfaceType.lower() == "gpib"):
                    Byte_data = self.interface.read()

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



       

        

if __name__ == "__main__":

    print("Starting")

    IP= 'GPIB0::4::INSTR';
    BOSA = BOSA("GPIB", IP);
    
    print(BOSA.ask("INST:STAT:MODE MAIN"))  # Change BOSA to the application selector
    time.sleep(2)
    print(BOSA.ask("INST:STAT:MODE BOSA")) # Enter BOSA mode
    
#    print(osa.ask("INST:STAT:MODE TLS")) # Enter TLS mode
#        
#    print(osa.ask("INST:STAT:MODE CA")) # Enter CA mode
    time.sleep(1)


    print(BOSA.ask("INST:STAT:RUN 1")) # Run 1/0 to start/stops the application

    
    BOSA.ask("FORM ASCII")

    NumPoints=int(BOSA.ask("TRACE:DATA:COUNT?"))

    BOSA.ask("FORM REAL")

    Trace = BOSA.ask_TRACE_REAL(NumPoints)

    x=[0]*NumPoints
    y=[0]*NumPoints

    for i in range(0,NumPoints):
       x[i]=  Trace[i][0]
       y[i] = Trace[i][1]


    plt.plot(x,y)
    plt.show()

    BOSA.ask("FORM ASCII")
    
    
 ### Another example 
 
 
#    Running=BOSA.ask("INSTRUMENT:STATE:RUN?").replace("\r\n","")
#    
#    if (Running=="OFF"):
#         BOSA.ask("INSTRUMENT:STATE:RUN 1")
#         print("Starting sweep...")
#    
#         OpCompleted=int(BOSA.ask("*opc?"))
#    
#         while(OpCompleted==0):
#             time.sleep(0.1)
#             OpCompleted=int(BOSA.ask("*opc?"))
#    
#    print ("The BOSA is ready")
#    
#    print ("Now I hold the sweeping")
#    BOSA.ask("INSTRUMENT:STATE:HOLD 1")
#    
#    holding=BOSA.ask("INSTRUMENT:STATE:HOLD?")
#    print("Holding is " + holding)
#    time.sleep(5)
#    print("Finally, I resume the sweeping")
#    BOSA.ask("INSTRUMENT:STATE:HOLD 0")
#    holding = BOSA.ask("INSTRUMENT:STATE:HOLD?")
#    print("Holding is " + holding)
#    



