import zmq
from contextlib import contextmanager
import numpy as np

context = zmq.Context()
#  Socket to talk to server
socket = context.socket(zmq.REQ)

def convert2temp(bytes2):
    integer_value = int.from_bytes(bytes2, byteorder='big')
    voltage = integer_value * (2**-16) * 3 #the three is because there is 3V used as the reference voltage in the ADC
    print(voltage)
    return np.interp(voltage, volt_array, temp_array)

temp_array = np.flip(np.array([1.4,1.5,1.6,1.7,1.8,1.9,2,2.1,2.2,2.3,2.4,2.5,2.6,2.7,2.8,2.9,3,3.1,3.2,3.3,3.4,3.5,3.6,3.7,3.8,3.9, 
                       4,4.2,4.4,4.6,4.8,5,5.2,5.4,5.6,5.8,6,6.5,7,7.5,8,8.5,9,9.5,10,10.5,11,11.5,12,12.5,13,13.5,14,14.5,
                       15,15.5,16,16.5,17,17.5,18,18.5,19,19.5,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,
                       40,42,44,46,48,50,52,54,56,58,60,65,70,75,77.35,80,85,90,100,110,120,130,140,150,160,170,180,190,200,
                       210,220,230,240,250,260,270,273,280,290,300,310,320,330,340,350,360,370,380,390,400,410,420,430,440,
                       450,460,470,480,490,500]))
volt_array = np.flip(np.array([1.64429,1.64299,1.64157,1.64003,1.63837,1.6366,1.63472,1.63274,1.63067,1.62852,1.62629,1.624,1.62166,
                       1.61928,1.61687,1.61445,1.612,1.60951,1.60697,1.60438,1.60173,1.59902,1.59626,1.59344,1.59057,1.58764,
                       1.58465,1.57848,1.57202,1.56533,1.55845,1.55145,1.54436,1.53721,1.53,1.52273,1.51541,1.49698,1.47868,
                       1.46086,1.44374,1.42747,1.41207,1.39751,1.38373,1.37065,1.3582,1.34632,1.33499,1.32416,1.31381,1.3039,
                       1.29439,1.28526,1.27645,1.26794,1.25967,1.25161,1.24372,1.23596,1.2283,1.2207,1.21311,1.20548,1.197748,
                       1.181548,1.162797,1.140817,1.125923,1.119448,1.115658,1.11281,1.110421,1.108261,1.106244,1.104324,1.102476,
                       1.100681,1.09893,1.097216,1.095534,1.093878,1.092244,1.090627,1.089024,1.085842,1.082669,1.079492,1.076303,
                       1.073099,1.069881,1.06665,1.063403,1.060141,1.056862,1.048584,1.040183,1.031651,1.027594,1.022984,1.014181,
                       1.005244,0.986974,0.968209,0.949,0.92939,0.909416,0.889114,0.868518,0.847659,0.82656,0.805242,0.78372,0.762007,
                       0.740115,0.718054,0.695834,0.673462,0.650949,0.628302,0.621141,0.605528,0.582637,0.559639,0.536542,0.513361,
                       0.490106,0.46676,0.443371,0.41996,0.396503,0.373002,0.349453,0.325839,0.302161,0.278416,0.254592,0.230697,
                       0.206758,0.182832,0.15901,0.13548,0.112553,0.090681]))

class Fakeshorev4r3:
    def __init__(self, ip_address, ip_port=5559):
        self.ip_address = ip_address
        self.ip_port = ip_port

    @contextmanager
    def zmq_connected(self):
        # connect to controller via ZMQ at port 5559
        with socket.connect(f"tcp://{self.ip_address}:{self.ip_port}") as connected_socket:
            yield connected_socket

    def command(self, cmd, ip_port=5559):
        with self.zmq_connected() as socket:
            #write command 
            socket.send(cmd)
            response = socket.recv()
        return response

    def reset(self):
        response = self.command(b"RESET")
        if response == b"ADC was reset":
            print("Reset Successful")

    def idn(self):
        response = self.command(b"*IDN?")
        print(response) #should print b'N'
    
    def output_current(self):
        response = self.command(b"OUTPUTCURRENT")
        print(response)
    
    def read_voltage_channel1(self):
        response = self.command(b"READADC1")
        return response      

    def read_voltage_channel2(self):
        response = self.command(b"READADC2")
        return response
    
    def get_temp1(self):
        return convert2temp(self.read_voltage_channel1())
    
    def get_temp2(self):
        return convert2temp(self.read_voltage_channel2())
