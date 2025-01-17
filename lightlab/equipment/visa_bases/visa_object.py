# import visa as pyvisa
import pyvisa
import time
from lightlab import visalogger as logger
from .driver_base import InstrumentSessionBase

OPEN_RETRIES = 5

CR = '\r'
LF = '\n'


class VISAObject(InstrumentSessionBase):
    '''
        Abstract class for something that communicates via messages
        (GPIB/USB/Serial/TCPIP/etc.). It handles message-based sessions
        in a way that provides a notion of object permanence to the
        connection with a particular address.

        It acts like a ``pyvisa`` message-based session, but it is
        not a subclass; it is a wrapper. It only contains one (at at time).
        That means VISAObject can offer extra opening, closing,
        session management, and error reporting features.

        This class relies on pyvisa to work
    '''

    mbSession = None
    resMan = None
    _open_retries = 0
    _termination = CR + LF
    __timeout = None
    _ID_STR = '*IDN?'

    def __init__(self, address=None, tempSess=False, baud=None, ID_STR=None, write_termination=None, read_termination=None, data_bits=None, stop_bits=None, parity=None, timeout=None):
        '''
            Args:
                tempSess (bool): If True, the session is opened and closed every time there is a command
                address (str): The full visa address
        '''
        self.tempSess = tempSess
        self.resMan = None
        self.mbSession = None
        self.address = address
        self._open_retries = 0
        self.__timeout = timeout
        self._baud = baud
        self.termination = write_termination

        self._read_term = read_termination
        self._data_bits = data_bits
        self._stop_bits = stop_bits
        self._parity = parity

        if ID_STR is not None:
            self._ID_STR = ID_STR

    def open(self):
        '''
            Open connection with 5 retries.
        '''
        if self.mbSession is not None:
            return
        if self.address is None:
            raise RuntimeError("Attempting to open connection to unknown address.")
        if self.resMan is None:
            self.resMan = pyvisa.ResourceManager()
        try:
            self.mbSession = self.resMan.open_resource(self.address)
            self.mbSession.write_termination = self.termination
            if self._baud is not None:
                self.mbSession.baud_rate = self._baud
            if self._read_term is not None:
                self.mbSession.read_termination = self._read_term
            if self._data_bits is not None:
                self.mbSession.data_bits = self._data_bits
            if self._stop_bits is not None:
                self.mbSession.stop_bits = self._stop_bits
            if self._parity is not None:
                self.mbSession.parity = self._parity
            if not self.tempSess:
                logger.debug('Opened %s', self.address)
        except pyvisa.VisaIOError as err:
            logger.warning('There was a problem opening the VISA %s... Error code: %s',
                           self.address, err.error_code)
            if self._open_retries < OPEN_RETRIES:
                self._open_retries += 1
                time.sleep(0.5 * self._open_retries)
                logger.warning('Trying again... (try = %s/%s)', self._open_retries, OPEN_RETRIES)
                self.open()
            else:
                logger.error(err)
                raise
        else:
            if self._open_retries != 0:
                logger.warning('Found it!')
            self._open_retries = 0

    def close(self):
        if self.mbSession is None:
            return
        try:
            self.mbSession.close()
        except pyvisa.VisaIOError:
            logger.error('There was a problem closing the VISA %s', self.address)
            raise
        self.mbSession = None
        if not self.tempSess:
            logger.debug('Closed %s', self.address)

    def write(self, writeStr):
        try:
            self.open()
            try:
                self.mbSession.write(writeStr)
            except Exception:
                logger.error('Problem writing to %s', self.address)
                raise
            logger.debug('%s - W - %s', self.address, writeStr)
        finally:
            if self.tempSess:
                self.close()

    def query(self, queryStr, withTimeout=None):
        retStr = None
        try:
            self.open()
            logger.debug('%s - Q - %s', self.address, queryStr)
            toutOrig = self.timeout
            try:
                if withTimeout is not None:
                    self.timeout = withTimeout
                retStr = self.mbSession.query(queryStr)
                if withTimeout is not None:
                    self.timeout = toutOrig
            except Exception:
                logger.error('Problem querying to %s', self.address)
                # self.close()
                raise
            retStr = retStr.rstrip()
            logger.debug('Query Read - %s', retStr)
        finally:
            if self.tempSess:
                self.close()
        return retStr

    # def query_binary(self, queryStr):
    #     ret_bytes = None
    #     try:
    #         self.mbSession = self.resMan.open_resource(self.address)
    #         ret_bytes = self.mbSession.query_binary_values(queryStr)
    #     finally:
    #         self.mbSession.close()
    #         self.mbSession = None
    #     return ret_bytes

    def instrID(self):
        r"""Returns the \*IDN? string"""
        return self.query(self._ID_STR)

    @property
    def timeout(self):
        if self.__timeout is None:
            if self.mbSession is None:
                try:
                    self.open()
                    self.__timeout = self.mbSession.get_visa_attribute(
                        pyvisa.constants.VI_ATTR_TMO_VALUE)  # None means default
                finally:
                    if self.tempSess:
                        self.close()
            else:
                self.__timeout = self.mbSession.get_visa_attribute(
                    pyvisa.constants.VI_ATTR_TMO_VALUE)  # None means default
        return self.__timeout

    @timeout.setter
    def timeout(self, newTimeout):
        if self.mbSession is None:
            raise Exception(
                'This mbSession is None. Perhaps you are setting timeout when the session is closed temporarily')
        self.mbSession.set_visa_attribute(
            pyvisa.constants.VI_ATTR_TMO_VALUE, newTimeout)
        self.__timeout = newTimeout

    def wait(self, bigMsTimeout=10000):
        self.query('*OPC?', withTimeout=bigMsTimeout)

    def LLO(self):
        raise NotImplementedError()

    def LOC(self):
        raise NotImplementedError()

    def clear(self):
        if self.mbSession is None:
            try:
                self.open()
                self.mbSession.clear()
            finally:
                self.close()
        else:
            self.mbSession.clear()

    def query_raw_binary(self):
        raise NotImplementedError()

    def spoll(self):
        raise NotImplementedError()

    @property
    def termination(self):
        if self.mbSession is not None:
            self._termination = self.mbSession.write_termination
        return self._termination

    @termination.setter
    def termination(self, value):
        if value is None:
            value = self._termination
        if value in (CR, LF, CR + LF, ''):
            self._termination = value
        else:
            raise ValueError("Termination must be one of these: CR, CRLF, LR, ''")
        if self.mbSession is not None:
            self.mbSession.write_termination = value
