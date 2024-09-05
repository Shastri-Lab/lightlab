import numpy as np
import time
from paramiko import SSHClient
from scp import SCPClient
import sys

def progress(filename, size, sent):
    sys.stdout.write("%s's progress: %.2f%%   \r" % (filename, float(sent)/float(size)*100) )

class DLPDLCR2000EVM():
    def __init__(self, name=None, address='miranda',pwd='miranda', **kwargs):
        '''
        '''
        self.name=name
        self.address=address
        self.pwd=pwd
    
    def show_image(self, path2image=None, timer=1):
        with SSHClient() as ssh:
            ssh.load_system_host_keys()
            ssh.connect(self.address, 22, 'debian', self.pwd, timeout=3)

            with SCPClient(ssh.get_transport(), progress=progress) as scp:
                scp.put(path2image, '~/bin/test.png')
            
            (stdin, stdout, stderr) = ssh.exec_command(f'bash /usr/local/bin/display-image.sh {timer}')
            print(stdin)
            print(stdout)
            print(stderr)
