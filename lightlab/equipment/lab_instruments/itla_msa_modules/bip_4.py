# -*- coding: utf-8 -*-
#!/usr/bin/env python
# coding:utf-8

# Created on Wed Jan 31 16:33:16 2018

__author__ = "Shinsuke FUJISAWA"
__copyright__ = "Copyright 2019, NEC Laboratories of America, Inc."
__credits__ = ""
__license__ = ""
__version__ = "0.0.1"
__maintainer__ = ""
__email__ = "sfujisawa@nec-labs.com"
__status__ = "developping"


try:
   import numpy as np
except:
   raise

class BIP4_lib:

    def BIP4(ReadWriteDec,registerHex,dude):
        def de2bi(d,n):
            power = 2**np.arange(n-1,-1,-1)
            bits = np.floor((d%(2*power))/power).astype(np.int)
            return bits
        
        
        #de2bi(3000,16)
        
        def bi2de(d,n):
            power = 2**np.arange(n-1,-1,-1)
            decimal = np.sum(d[:,np.newaxis]*power[np.newaxis,:],axis=-1) 
            return decimal
        
        
    #    Arg=42;
    #    registerHex=50;
    #    ReadWriteDec=0;
    #    
    #    dude = Arg
        
        dude=np.round(dude);
        
        if dude < 0:
           dude=65536+dude; 
        
        Arg16bits = de2bi(dude,16)
        data1=Arg16bits[0:8];
        data2=Arg16bits[8::];
        
        frameByte = [de2bi(ReadWriteDec,8), de2bi(registerHex,8),data1,data2]
        
        frameByteOut=frameByte;
        
        Byte0f=de2bi(15,8);
        Bytef0=de2bi(240,8);      
        
        
        bip8 = ( ( (frameByte[0] & Byte0f) ^ frameByte[1] ) ^ frameByte[2] ) ^ frameByte[3]
        
        bip8And0f=bip8 & Byte0f
        bip8Andf0=bip8 & Bytef0
        bip8Andf0ShiftRight=np.zeros(8).astype(np.int)
        bip4ShiftLeft = np.zeros_like(bip8Andf0ShiftRight)
        bip8Andf0ShiftRight[4::]=bip8Andf0[0:4]
        bip4=bip8And0f ^ bip8Andf0ShiftRight
        bip4ShiftLeft[0:4] = bip4[4::]
        Byte1Or=frameByte[0] | bip4ShiftLeft
        frameByteOut[0]=Byte1Or
        
        
        
        Out = bi2de(np.array(frameByteOut),8)[:,0]
        return Out