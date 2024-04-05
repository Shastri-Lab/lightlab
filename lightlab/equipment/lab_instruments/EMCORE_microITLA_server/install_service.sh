#!/bin/bash

# Set variables for service template
USERNAME=$(whoami)
GROUPNAME=$(id -gn)
USER_HOME=$(eval echo ~$USERNAME)

# Substitute variables in template service and install
sed "s|%USERNAME%|$USERNAME|g; s|%GROUPNAME%|$GROUPNAME|g; s|%USER_HOME%|$USER_HOME|g" microITLA_server.service.template > microITLA_server.service
sudo mv microITLA_server.service /etc/systemd/system/microITLA_server.service

# Reload systemd and enable service
sudo systemctl daemon-reload
sudo systemctl enable microITLA_server
sudo systemctl start microITLA_server
sudo systemctl status microITLA_server
