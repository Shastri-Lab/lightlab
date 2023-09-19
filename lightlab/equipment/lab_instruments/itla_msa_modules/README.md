# Steps to get the Pure Photonics Lasers working on the server:
1. SSH into the raspberry pi:
```
ssh pi@<raspberry_pi_ip>
```
2. Clone the lightlab repo into the home directory:
```
cd ~
git clone git@github.com:Shastri-Lab/lightlab.git
```
3. Install the lightlab package:
```
cd lightlab
pip install -e .
```
4. Run the laser service installation script (this will install the laser service and enable it to run on startup):
```
cd equipment/lab_instruments/itla_msa_modules
sudo ./install_laser_service.sh
```
if you run into an issue with the above command, you made need to make the script executable and run the installation again:
```
sudo chmod +x install_laser_service.sh
sudo ./install_laser_service.sh
```
5. Reboot the raspberry pi:
```
sudo reboot
```

Now the server-side code should be installed and running. You can now run the laser code from your experiment as normal!