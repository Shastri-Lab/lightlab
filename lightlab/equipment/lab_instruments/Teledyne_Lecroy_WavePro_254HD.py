
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
        self.scope.write(f"""VBS 'app.Acquisition.Trigger.edge.level = "{trig_level}"' """)
        self.scope.write(f"""VBS 'app.WaitUntilIdle(5)' """)

    def voltage_offset(self, channel=1, v_off=0):
        self.scope.write(f"C{channel}:OFST {v_off}")
    
    def trigger4OSA(self,):
        #Set the BOSA tunable laser to 1516nm to 1564nm, with a sweep speed of 100nm/s
        #This gives 1nm every 10ms
        self.scope.write(f"TRIG_SELECT EDGE,SR,EX")
        self.scope.write(f"""VBS 'app.Acquisition.Trigger.edge.level = "0.5"' """)
        self.scope.write(f"""VBS 'app.Acquisition.Horizontal.HorScale = 50e-3' """)
        self.scope.write(f"TRIG_DELAY -220e-3")
    
    def acquire(self, channels=[1]):
        "This functions stops any current acquisition, then acquires the waveform data, and returns the trigger to auto mode"
        self.scope.write(f"""VBS 'app.acquisition.triggermode = "stopped" ' """)
        wfm = []
        for i in range(len(channels)):
            wfm.append(self.acquire_waveform(channel=channels[i]))
        self.scope.write(f"""VBS 'app.acquisition.triggermode = "auto" ' """)
        return wfm
    
    def acquire_waveform(self, channel=1):
        self.scope.write(f"C{channel}:WAVEFORM? DATA_ARRAY_1")
        waveform_data = self.scope.read_raw()
        #waveform = np.frombuffer(waveform_data, dtype=np.float32)

        #Please see page 6-21 and 6-22 for byte indices in waveform data that is sent. Note there is a 24 byte shift
        #in the actual data compared to the datasheet. These numbers should be correct, but may be different for a different model.
        VERTICAL_GAIN = np.frombuffer(waveform_data[180:184], dtype='<f')[0] #Total gain of waveform, units per lsb
        VERTICAL_OFFSET = np.frombuffer(waveform_data[184:188], dtype='<f')[0] #Total vertical offset of waveform. To get floating values from raw data: VERTICAL_GAIN * data - VERTICAL_OFFSET
        HORIZONTAL_INTERVAL = np.frombuffer(waveform_data[200:204], dtype='<f')[0] #Sampling interval, the nominal time between successive points in the data
        HORIZONTAL_OFFSET = np.frombuffer(waveform_data[204:212], dtype='double')[0] #Trigger offset in time domain for zero'th sweep of trigger, measured as seconds from trigger to zero'th data point (i.e., actual trigger delay)
        WAVE_ARRAY_1 = np.frombuffer(waveform_data[84:88], dtype='long')[0] #Length in bytes of first simple data array divided by 2 since int16 uses 2 bytes.
        data=np.frombuffer(waveform_data[370:(370+WAVE_ARRAY_1)], dtype='int8')

        v = VERTICAL_GAIN * data - VERTICAL_OFFSET
        t = HORIZONTAL_INTERVAL*range(int(WAVE_ARRAY_1)) + HORIZONTAL_OFFSET 

        return Waveform(t, v, unit='V')
    
    def set_trigger_source(self, channel='C1', coupling_type='DC'):
        assert (channel == np.array(['C1','C2','C3','C4','EXT','EX10','ETM10'])).any(), f"Channel selected {channel} is not an allowed option"
        assert (coupling_type == np.array(['DC', 'AC', 'HFREJ', 'LFREJ'])).any(), f"Coupling selected {coupling_type} is not an allowed option"
        self.scope.write(f"{channel}:TRIG_COUPLING {coupling_type}")

    def observe(self,command):
        return self.scope.query(command)
    
    def run(self):
        self.scope.write(f"""VBS 'app.acquisition.triggermode = "auto" ' """)
    def stop(self):
        self.scope.write(f"""VBS 'app.acquisition.triggermode = "stopped" ' """)
    
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
