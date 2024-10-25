
import pyvisa
import numpy as np
import matplotlib.pyplot as plt
from lightlab.util.data import Waveform

#PLEASE SEE maui-remote-control-and-automation-manual.pdf
#Can get it from Teledyne's Website

class WavePro254HDOscilloscope:
    def __init__(self, ip_address):
        self.ip_address = ip_address
        self.scope = None
        self.rm = pyvisa.ResourceManager()
        
    def connect(self):
        """ Connect to the oscilloscope via LAN """
        try:
            self.scope = self.rm.open_resource(f'TCPIP0::{self.ip_address}::INSTR')
            idn = self.scope.query("*IDN?")
            self.scope.timeout= 5000
            print(f"Connected to: {idn}")
        except Exception as e:
            print(f"Error connecting to oscilloscope: {e}")
            raise

    def setup_acquisition(self, channel=1, vdiv=0.2, tdiv=1e-3, trig_level=0.2):
        """ Setup the acquisition parameters """

        self.scope.write("COMM_HEADER OFF")
        self.scope.write(f"""VBS 'app.settodefaultsetup' """)
        self.scope.write(f"""VBS 'app.acquisition.triggermode = "stopped" ' """)
        self.scope.write(f"""VBS 'app.acquisition.TriggerMode = "Auto"' """)
        self.scope.write(f"""VBS 'app.Acquisition.C{channel}.View = "ON"' """)
        self.scope.write(f"""VBS 'app.Acquisition.C{channel}.VerScale = {vdiv}' """)
        self.scope.write(f"""VBS 'app.Acquisition.Horizontal.HorScale = {tdiv}' """)
        self.scope.write(f"""VBS 'app.Acquisition.TriggerMode = "Single"' """)
        self.scope.write(f"""VBS 'app.Acquisition.Trigger.edge.level = "{trig_level}"' """)
        self.scope.write(f"""VBS 'app.WaitUntilIdle(5)' """)

    def acquire_waveform(self, channel=1):
        self.scope.write(f"C{channel}:WAVEFORM? DATA_ARRAY_1")
        waveform_data = self.scope.read_raw()
        #waveform = np.frombuffer(waveform_data, dtype=np.float32)

        VERTICAL_GAIN = np.frombuffer(waveform_data[180:184], dtype='<f')[0] #Total gain of waveform, units per lsb
        VERTICAL_OFFSET = np.frombuffer(waveform_data[184:188], dtype='<f')[0] #Total vertical offset of waveform. To get floating values from raw data: VERTICAL_GAIN * data - VERTICAL_OFFSET
        HORIZONTAL_INTERVAL = np.frombuffer(waveform_data[200:204], dtype='<f')[0] #Sampling interval, the nominal time between successive points in the data
        HORIZONTAL_OFFSET = np.frombuffer(waveform_data[204:212], dtype='double')[0] #Trigger offset in time domain for zero'th sweep of trigger, measured as seconds from trigger to zero'th data point (i.e., actual trigger delay)
        WAVE_ARRAY_1 = np.frombuffer(waveform_data[84:88], dtype='long')[0] #Length in bytes of first simple data array divided by 2 since int16 uses 2 bytes.
        data=np.frombuffer(waveform_data[370:(370+WAVE_ARRAY_1)], dtype='int8')

        v = VERTICAL_GAIN * data - VERTICAL_OFFSET
        t = HORIZONTAL_INTERVAL*range(int(WAVE_ARRAY_1)) + HORIZONTAL_OFFSET 

        return Waveform(t, v, unit='V')

    def observe(self,command):
        return self.scope.query(command)
    def run(self):
        "Run"
        self.scope.write("")

    def close(self):
        """ Close the connection to the oscilloscope """
        if self.scope is not None:
            self.scope.close()
        print("Connection closed.")

# Example usage in a lightlab style:
def main():
    # Initialize the oscilloscope
    oscilloscope = WavePro254HDOscilloscope(ip_address='192.168.51.112')
    
    # Connect to the oscilloscope
    oscilloscope.connect()
    
    # Set up acquisition parameters (channel, vertical division, time base, trigger source)
    oscilloscope.setup_acquisition(channel=1, vdiv=2, tdiv=1e-3, trig_source='C1', trig_slope='Positive')
    
    # Acquire the waveform
    waveform = oscilloscope.acquire_waveform(channel=1)
    
    # Close the connection
    oscilloscope.close()

if __name__ == "__main__":
    main()
