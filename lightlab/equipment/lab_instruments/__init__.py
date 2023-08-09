from ..visa_bases import VISAInstrumentDriver

# instruments that are not VISA instruments
from .Qontrol_Q8i import Qontrol_Q8i
from .IMEBuild_SMU_v4 import IMEBuild_SMU
from .Aragon_BOSA_400_Ether import Aragon_BOSA_400_Ether
from .EMCORE_microITLA_LS import EMCORE_microITLA_LS
from .Hantek_HDG6202B import HantekAWG
from .Keysight_86100D_Oscope import Keysight_86100D_Oscope

# This imports all of the modules in this folder
# As well as all their member classes that are VISAInstrumentDriver
import importlib
import pkgutil


class BuggyHardware(Exception):
    ''' Not all instruments behave as they are supposed to.
        This might be lab specific. atait is not sure exactly how to deal with that.
    '''


for _, modname, _ in pkgutil.walk_packages(path=__path__,  # noqa
                                           prefix=__name__ + '.'):
    _temp = importlib.import_module(modname)
    for k, v in _temp.__dict__.items():
        if k[0] != '_' and type(v) is not type:
            try:
                mro = v.mro()
            except AttributeError:
                continue
            if VISAInstrumentDriver in mro:
                globals()[k] = v
            if Qontrol_Q8i in mro:
                globals()[k] = v
            if IMEBuild_SMU in mro:
                globals()[k] = v
            if Aragon_BOSA_400_Ether in mro:
                globals()[k] = v
            if EMCORE_microITLA_LS in mro:
                globals()[k] = v
            if HantekAWG in mro:
                globals()[k] = v
            if Keysight_86100D_Oscope in mro:
                globals()[k] = v
            
            # if k == 'IMEBuild_SMU' or k == 'Qontrol_Q8i': #TODO: not sure if this works how I want
            #     # TODO: make IMEBuild a subclass of VISAInstrumentDriver or make a different XXXInstrumentDriver for this?
            #     # TODO: is this also an issue for EMCORE_microITLA_LS? These are both RPi instruments so should have a common interface... Look at ArduinoInstrument, could make an RPiInstrument
            #     # TODO: What about TCP version of Keithley 2606B? I think it is a VISA instrument but maybe shouldn't be?
            #     globals()[k] = v

# Disable tests for the following packages
experimental_instruments = [
    'Aragon_BOSA_400_Queens',
    'Lakeshore_Model336',
]