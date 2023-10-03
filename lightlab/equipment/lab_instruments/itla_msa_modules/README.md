# Steps to get the Pure Photonics Lasers working on the server:
1. SSH into the raspberry pi:
```
ssh pi@<raspberry_pi_ip>
```
2. Clone the lightlab repo into the home directory (you will have to have set up git credentials on the server to authenticate into the `lightlab` repo—alternatively, you can download the repo as a zip file and manually upload this to the Raspberry Pi, then unzip it):
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
cd lightlab/equipment/lab_instruments/itla_msa_modules
./install_service.sh
```
if you run into an issue with the above command, you made need to make the script executable and run the installation again:
```
sudo chmod +x install_service.sh
./install_service.sh
```
5. Reboot the raspberry pi:
```
sudo reboot
```

Now the server-side code should be installed and running. You can now run the laser code from your experiment as normal! To see the output of the laser service (for example, to see the serial number of all the connected lasers), you can run:
```
cat ~/lightlab/lightlab/equipment/lab_instruments/itla_msa_modules/server_stdout.log
```
If you connect or disconnect lasers, you will need to restart the laser service for the changes to take effect:
```
sudo systemctl restart microITLA_server.service
```
