from sqlite3 import connect
import time
from contextlib import contextmanager
import numpy as np
from math import log
from math import sqrt
from time import sleep
import matplotlib.pyplot as plt
import zmq

IP_ADDR = "dione"
IP_PORT = 5555

TIMEOUT = 20
MAX_ATTEMPTS = 100

context = zmq.Context()
socket = context.socket(zmq.REQ)

@contextmanager
def zmq_connected(ip_addr, ip_port):
    # connect to controller via ZMQ at port 5555
    with socket.connect(f"tcp://{ip_addr}:{ip_port}") as connected_socket:
        yield connected_socket

# send command and return the controller's response
def command(cmd, ip_addr=IP_ADDR, ip_port=IP_PORT):
    with zmq_connected(ip_addr, ip_port) as socket:
        #write command 
        socket.send(cmd.encode())

        response = socket.recv_multipart()
        response = "".join([rep.decode() for rep in response]).splitlines()
        if "ERROR" in response[-1]:
            raise RuntimeError(response)
        response = response[1:-1]

        for line in response:
            print(line)

        return response

# send multiple commands and return the controller's response
def commands(cmds, ip_addr=IP_ADDR, ip_port=IP_PORT):
    if (isinstance(cmds, str)):
        cmds = [cmds]
    rtns = []
    for cmd in cmds:
        rtn = command(cmd, ip_addr, ip_port)
        rtns.append(rtn)
    return rtns

# reset the board (cmd = "*RST")
def reset():
    cmd = "*RST"
    return cmd

# reset the channel (cmd = "ch:RST:")
def reset_ch(ch):
    cmd = "{}:RST:".format(ch)
    return cmd

RANGE_5V_UNI        =  "5V_UNI"
RANGE_5V_BIP        =  "5V_BIP"
RANGE_20mA_UNI      =  "20mA_UNI"
RANGE_20mA_BIP      =  "20mA_BIP"
ALLOWED_MODES = [RANGE_5V_UNI, RANGE_5V_BIP, RANGE_20mA_UNI, RANGE_20mA_BIP]

# set the output range of a designated channel (cmd = "ch:CONF:md")
def set_config_mode(ch, md):
    cmd = "{}:CONF:{}".format(ch,md)
    return cmd

def get_config_mode(ch):
    cmd = "{}:CONF?".format(ch)
    return cmd

# set the output current of a designated channel (cmd = "ch:I:current")
def set_current(ch, value):
    cmd = "{}:I:{}".format(ch,value)
    return cmd

# set the output voltage of a designated channel (cmd = "ch:V:voltage")
def set_voltage(ch, value):
    cmd = "{}:V:{}".format(ch,value)
    return cmd

# enable or disable channel (cmd = "ch:EN:0/1")
def set_enable(ch, enable:bool):
    if enable:
        cmd = "{}:EN:1".format(ch)
    else:
        cmd = "{}:EN:0".format(ch)
    return cmd

def get_enable(ch):
    cmd = "{}:EN?".format(ch)
    return cmd


# perform a measurement from a designated channel (cmd = "ch:MEAS:md")
MEAS_V = "V"
MEAS_I = "I"
def measure(ch, md):
    cmd = "{}:MEAS:".format(ch)+md
    return cmd

# Extract measured result
def measured_result(rtn):
    return float(rtn[0].split(',')[0])

# SMU Instrument class
class IMEBuild_SMU:

    def __init__(self, channel, host=IP_ADDR, port=IP_PORT):
        self.host = host
        self.port = port
        self.channel = int(channel)

    def set_voltage(self, voltage):
        cmd = set_voltage(self.channel, voltage)
        return command(cmd, self.host, self.port)

    def set_current(self, current_ma):
        cmd = set_current(self.channel, current_ma)
        return command(cmd, self.host, self.port)

    def set_config_mode(self, mode):
        if mode not in ALLOWED_MODES:
            raise RuntimeError(f"Invalid config mode. Expected one of {ALLOWED_MODES} but got {mode} instead.")
        cmd = set_config_mode(self.channel, mode)
        return command(cmd, self.host, self.port)

    def enable_output(self):
        cmd = set_enable(self.channel, True)
        return command(cmd, self.host, self.port)

    def disable_output(self):
        cmd = set_enable(self.channel, False)
        return command(cmd, self.host, self.port)

    def measure_voltage(self):
        cmd = measure(self.channel, MEAS_V)
        return measured_result(command(cmd, self.host, self.port))

    def measure_current(self):
        cmd = measure(self.channel, MEAS_I)
        return measured_result(command(cmd, self.host, self.port))
    
    def reset(self):
        cmd = reset_ch(self.channel)
        return command(cmd, self.host, self.port)