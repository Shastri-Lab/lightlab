# PurePhotonics Laser Guide

## Overview
The lasers from PurePhotonics are USB devices that are run using a Raspberry Pi as a host computer. The lightlab driver `lightlab.equipment.lab_instruments.EMCORE_microITLA_LS` is the main driver that users should interact with to control the lasers. All the Raspberry Pis are set up to automatically run the server script `lightlab/equipment/lab_instruments/EMCORE_microITLA_LS_server/EMCORE_microITLA_LS_server.py` as a Linux service that executes when the Pi boots up; this script interfaces with all the laser modules connected via USB and handles communication with the user's commands sent using the main lightlab driver. 

### Driver Instructions
For day to day use, you should not need to interact with the Raspberry Pi. You need only use the driver commands in your experiment's Jupyter Notebook. An example of the basic functionality of the lasers is shown in the following snippet:
```python
from lightlab.equipment.lab_instruments import EMCORE_microITLA_LS
from scipy.constants import c

rpi = 'ganymede' # use the name of the raspberry pi, or its IP address
sn = 'CRTML3C01B' # use the SN of the laser you are connecting to
laser = EMCORE_microITLA_LS(address=rpi, serial_number=sn)

# set laser output power (see max and min power in docs)
laser.set_output_power(16.0) # in dBm

# set laser frequency (see frequency range in docs)
wavelength = 1550.0 # nm
frequency = c / wavelength
laser.set_first_channel_frequency(frequency) # in GHz

# turn the output on
laser.itla_on()

# run this line a few times to see the output power ramp up to the final value
print(f"The laser is on! The wavelength is set to {wavelength:.1f} nm and the power is currently {laser.get_output_power():.2f} dBm")

# turn the output off
laser.itla_off()
```

If you are having connection issues or if you are plugging in a new laser, you may need to SSH into the Raspberry Pi controlling your laser. You can see the log file of the server script using
```
cat ~/lightlab/lightlab/equipment/lab_instruments/EMCORE_microITLA_LS_server/server_stdout.log
```
which will show the log of the commands received from the various clients using lasers on this Pi. Any time the server is reloaded and the script reboots, the log file will show the list of the serial numbers of lasers that are successfully connected. If you need to reboot the server script manually, this can be done using
```
sudo systemctl restart microITLA_server.service
```
You can also just check the status of the service using
```
sudo systemctl status microITLA_server.service
```

## Instructions for setting up a new Pi
If you add a brand new Raspberry Pi to control new lasers, you will need to follow these instructions to get it set up consistently with the rest of the Pis in the lab. The following instructions explain how to clone lightlab on the Pi and install the server script as a Linux service so that it executes automatically on boot.

1. SSH into the raspberry pi:
```
ssh pi@<raspberry_pi_ip>
```
2. Clone the lightlab repo into the home directory (you will have to have set up a Github SSH key on the raspberry pi to authenticate into the `lightlab` repo—alternatively, you can download the repo as a zip file and manually upload this to the Raspberry Pi, then unzip it):
```
cd ~
git clone git@github.com:Shastri-Lab/lightlab.git
```
3. Install the lightlab package:
```
cd lightlab
pip3 install -e .
```
4. Run the laser service installation script (this will install the laser service and enable it to run on startup):
```
cd lightlab/equipment/lab_instruments/EMCORE_microITLA_server
./install_service.sh
```
5. Reboot the raspberry pi:
```
sudo reboot
```

Now the server-side code should be installed and running. You can now run the laser code from your experiment as normal! To see the output of the laser service (for example, to see the serial number of all the connected lasers), you can run:
```
cat ~/lightlab/lightlab/equipment/lab_instruments/EMCORE_microITLA_LS_server/server_stdout.log
```
If you connect or disconnect lasers, you will need to restart the laser service for the changes to take effect:
```
sudo systemctl restart microITLA_server.service
```
