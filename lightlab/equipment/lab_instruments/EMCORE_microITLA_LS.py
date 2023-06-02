#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Oct 10 11:16:12 2019

@author: pi

Create a pseudo-driver that sends NEC commands to server for execution

TODO: incorporate safety checks from experiment notebooks into driver.
e.g. waiting for power stabilization, checking for timeouts and errors, checking if frequency is valid, etc.
"""

import zmq

class EMCORE_microITLA_LS():
    '''
        Single EMCORE microITLA laser source
        Provides array-based and dict-based setters/getters for
            * whether laser is on or off (``enableState``)
            * tunable wavelength output (``wls``)
            * output power in dBm (``powers``)s
            
        Args

        The client must be in the same local network as the server
        "Bank" behaviour is handled at the server level

        Usage: :ref: make ipybn example
    '''
    #instrument_category = LaserSource

    # Time it takes to equilibrate on different changes, in seconds
    #sleepOn = dict(OUT=3, WAVE=30, LEVEL=5)

    #powerRange = np.array([-20, 13])

    def __init__(self, address, serial_number=None, **kwargs):
            self.serial_number = serial_number
            self.address = address # address of the RPi server ('europa', 'callisto', or specific IP)
            
    def request(self, command):
        ''' General-purpose Request-Reply with client
        
            Args:
                command (str): command to execute on server

            Returns:
                (str): output of the command on server side
        '''
        # Establish connection
        context = zmq.Context()
        socket = context.socket(zmq.REQ)
        socket.connect("tcp://{0}:5555".format(self.address))
        
        try:
            # Encrypt the serialnumber/command/arguments pair in a single string
            request_string = self.serial_number + str("___") + command
            # Send command, formatted as [SerialNumber, command]
            socket.send(str.encode(request_string))
            # Wait for and return response
            reply = socket.recv()
            reply_str = reply.decode()
        except: 
            reply_str = "Communication failed"
            pass
        
        # Clean communication exit
        socket.close()
        context.destroy()
        return reply_str
    
    def get_serial_number(self):
        return self.request("get_serial_number")
    
    def itla_on(self):
        return self.request("itla_on")
    
    def itla_off(self):
        return self.request("itla_off")
                        
    def ask_device_ready(self):
        return self.request("ask_device_ready")

    def set_output_power(self, pow_dbm):
        return self.request("set_output_power___{0}".format(pow_dbm))

    def set_first_channel_frequency(self, frequency_GHz):
        return self.request("set_first_channel_frequency___{0}".format(frequency_GHz))

    def set_ftf_frequency(self, frequency_MHz):
        return self.request("set_ftf_frequency___{0}".format(frequency_MHz))

    # UNTESTED
    #def set_channel(self, channel_num, ftf):
    #    return self.request("set_channel___{0}___{1}".format(channel_num, ftf))

    def get_output_power(self):
        return self.request("get_output_power")

    def get_first_channel_frequency(self):
        return self.request("get_first_channel_frequency")

    def get_channel_frequency(self):
        return self.request("get_channel_frequency")

    def get_ftf_frequency(self):
        return self.request("get_ftf_frequency")

    def get_device_type(self):
        return self.request("get_device_type")

    def get_manufacturer(self):
        return self.request("get_manufacturer")

    def get_manufactured_date(self):
        return self.request("get_manufactured_date")

    def get_io_capabilities(self):
        return self.request("get_io_capabilities")

    def get_device_errors(self):
        return self.request("get_device_errors")

    def get_module_monitors(self):
        return self.request("get_module_monitors")

    def get_power_capabilities(self):
        return self.request("get_power_capabilities")

    def get_grid_capabilities(self):
        return self.request("get_grid_capabilities")

    def get_ftf_capabilities(self):
        return self.request("get_ftf_capabilities")

    def get_frequency_capabilities(self):
        return self.request("get_frequency_capabilities")

    def port_close(self):
        return self.request("port_close")
    
    def clean_jump(self, start_f, target_f, map_file='1550_map.txt'):
        return self.request(f"clean_jump___{start_f}___{target_f}___{map_file}")
        
    def clean_jump_micro_itla(self, target_index):
        return self.request(f"clean_jump_micro_itla___{target_index}")
        
    def clean_jump_micro_itla_cal(self, start_f, grid, set_points):
        return self.request(f"clean_jump_micro_itla_cal___{start_f}___{grid}___{set_points}")

   
if __name__ == '__main__':
    server_address = '192.168.1.108'

    serialnums = ['CRTMK2G0H1']
    for sn in serialnums:
        laser = EMCORE_microITLA_LS(server_address, serial_number=sn)
        print(f'Accessed laser SN:{laser.get_serial_number()}')
        print(laser.set_first_channel_frequency(193475))
        print('----')
