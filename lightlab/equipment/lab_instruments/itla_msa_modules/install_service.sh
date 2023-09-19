#!/bin/bash
cp ~/lightlab/lightlab/equipment/lab_instruments/itla_msa_modules/microITLA_server.service /etc/systemd/system/microITLA_server.service
sudo systemctl daemon-reload
sudo systemctl enable microITLA_server
sudo systemctl start microITLA_server
sudo systemctl status microITLA_server
