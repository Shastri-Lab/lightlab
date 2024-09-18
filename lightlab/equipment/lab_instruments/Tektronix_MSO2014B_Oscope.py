from . import VISAInstrumentDriver
from lightlab.equipment.abstract_drivers import TekScopeAbstract
from lightlab.laboratory.instruments import Oscilloscope


class Tektronix_MSO2014B_Oscope(VISAInstrumentDriver, TekScopeAbstract):
    ''' Slow MSO scope. See abstract driver for description

        `Manual <http://websrv.mece.ualberta.ca/electrowiki/images/8/8b/MSO4054_Programmer_Manual.pdf>`__

        Usage: :any:`/ipynbs/Hardware/Oscilloscope.ipynb`

    '''
    instrument_category = Oscilloscope

    totalChans = 4
    _recLenParam = 'HORIZONTAL:RECORDLENGTH'
    _clearBeforeAcquire = True
    _measurementSourceParam = 'SOURCE1'
    _runModeParam = 'ACQUIRE:STOPAFTER'
    _runModeSingleShot = 'SEQUENCE'
    _yScaleParam = 'YMULT'

    def __init__(self, name='The MSO scope', address=None, **kwargs):
        VISAInstrumentDriver.__init__(self, name=name, address=address, timeout=10000, write_termination='\n', **kwargs)
        TekScopeAbstract.__init__(self)

    def wfmDb(self):  # pylint: disable=arguments-differ
        print('wfmDb is not working yet with DPOs')
