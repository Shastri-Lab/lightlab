from . import VISAInstrumentDriver
from lightlab.laboratory.instruments import OpticalSpectrumAnalyzer

import socket
import numpy as np
from lightlab.util.data import Spectrum
from lightlab import visalogger as logger
import struct
import time

WIDEST_WLRANGE = [1516, 1565]

_APPS = ('BOSA', 'TLS', 'CA', 'MAIN')
_AVG_COUNTS = ('4', '8', '12', '32', 'CONT')
_SPEED_MODES = ('HR', 'HS')
_CA_MEASUREMENTS = ('IL', 'RL', 'IL&RL')
_CA_POLARIZATIONS = ('1', '2', 'INDEP', 'SIMUL')


class Aragon_BOSA_400(VISAInstrumentDriver):
    """Aragon BOSA 400 Optical Spectrum Analyzer.

    Supports BOSA, TLS, and CA applications via standard SCPI commands.

    Transport is auto-detected from the address format:
      - ``GPIB0::1::INSTR`` → VISA/GPIB mode (via VISAInstrumentDriver)
      - ``TCPIP0::192.168.1.100::5025::SOCKET`` → raw TCP socket mode

    Usage: :ref:`/ipynbs/Hardware/OpticalSpectrumAnalyzer.ipynb`
    """

    instrument_category = OpticalSpectrumAnalyzer
    MAGIC_TIMEOUT = 30

    _wlRange = None
    _currApp = None

    def __init__(self, name='BOSA 400 OSA', address=None, **kwargs):
        # Detect TCP mode from address
        self._use_tcp = False
        self._tcp_host = None
        self._tcp_port = None
        self._tcp_socket = None
        self._tcp_started = False

        if address is not None and 'TCPIP' in address.upper():
            self._use_tcp = True
            # Parse VISA-style TCP address: TCPIP0::host::port::SOCKET
            parts = address.split('::')
            self._tcp_host = parts[1]
            self._tcp_port = int(parts[2])
            # Default to persistent connection for TCP
            kwargs['tempSess'] = kwargs.pop('tempSess', False)
        else:
            # Default to temporary sessions for VISA
            kwargs['tempSess'] = kwargs.pop('tempSess', True)

        super().__init__(name=name, address=address, **kwargs)

    # ------------------------------------------------------------------
    # TCP helpers
    # ------------------------------------------------------------------

    def _ensure_tcp_connected(self):
        """Create and connect the TCP socket if not already connected."""
        if self._tcp_socket is not None:
            return
        self._tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._tcp_socket.settimeout(self.MAGIC_TIMEOUT)
        self._tcp_socket.connect((self._tcp_host, self._tcp_port))
        logger.debug('TCP connected to %s:%s', self._tcp_host, self._tcp_port)

    def _tcp_disconnect(self):
        """Close the TCP socket if open."""
        if self._tcp_socket is not None:
            try:
                self._tcp_socket.close()
            except OSError:
                pass
            self._tcp_socket = None
            logger.debug('TCP disconnected from %s:%s',
                         self._tcp_host, self._tcp_port)

    def _tcp_recv(self):
        """Read from the TCP socket until a newline is received.

        Returns:
            str: the received data with trailing ``\\r\\n`` stripped.
        """
        buf = ''
        while True:
            data = self._tcp_socket.recv(19200)
            buf += data.decode()
            if '\n' in buf:
                break
        return buf.rstrip('\r\n')

    # ------------------------------------------------------------------
    # Session lifecycle overrides
    # ------------------------------------------------------------------

    def open(self):
        if self._use_tcp:
            self._ensure_tcp_connected()
            if not self._tcp_started:
                self._tcp_started = True
                self.startup()
                # Re-ensure connection in case startup triggered a close
                self._ensure_tcp_connected()
        else:
            super().open()

    def close(self):
        if self._use_tcp:
            self._tcp_disconnect()
            self._tcp_started = False
        else:
            super().close()

    # ------------------------------------------------------------------
    # Communication overrides
    # ------------------------------------------------------------------

    def write(self, writeStr):
        if self._use_tcp:
            try:
                self._ensure_tcp_connected()
                self._tcp_socket.sendall((writeStr + '\r\n').encode())
                logger.debug('%s:%s - W - %s',
                             self._tcp_host, self._tcp_port, writeStr)
                # The instrument replies OK\r\n to write commands; consume it
                confirm = self._tcp_recv()
                if confirm != 'OK':
                    logger.warning('Unexpected write response for %r: %r',
                                   writeStr, confirm)
            finally:
                if self.tempSess:
                    self._tcp_disconnect()
        else:
            self._session_object.write(writeStr)

    def query(self, queryStr, withTimeout=None):
        if self._use_tcp:
            try:
                self._ensure_tcp_connected()
                if withTimeout is not None:
                    self._tcp_socket.settimeout(withTimeout)
                self._tcp_socket.sendall((queryStr + '\r\n').encode())
                logger.debug('%s:%s - Q - %s',
                             self._tcp_host, self._tcp_port, queryStr)
                retStr = self._tcp_recv()
                logger.debug('Query Read - %s', retStr)
                if withTimeout is not None:
                    self._tcp_socket.settimeout(self.MAGIC_TIMEOUT)
            finally:
                if self.tempSess:
                    self._tcp_disconnect()
            return retStr
        else:
            return self._session_object.query(queryStr, withTimeout=withTimeout)

    # ------------------------------------------------------------------
    # Instrument methods
    # ------------------------------------------------------------------

    def startup(self):
        idn = self.query('*IDN?')
        logger.info('%s identified: %s', self.name, idn)
        self._currApp = self.query('INST:STAT:MODE?').strip()

    def stop(self):
        self._currApp = self.query('INST:STAT:MODE?').strip()
        if self._currApp == 'TLS':
            self.write('SENS:SWITCH OFF')
        else:
            self.write('INST:STAT:RUN 0')

    def start(self):
        self._currApp = self.query('INST:STAT:MODE?').strip()
        if self._currApp == 'TLS':
            self.write('SENS:SWITCH ON')
        else:
            self.write('INST:STAT:RUN 1')

    def application(self, app=None):
        """Switch to a BOSA application mode.

        Args:
            app: One of 'BOSA', 'TLS', 'CA', 'MAIN'
        """
        if app is None:
            return
        if app not in _APPS:
            raise ValueError("app must be one of {}".format(_APPS))
        if app != 'MAIN':
            if self._currApp != 'MAIN':
                self.application('MAIN')
            self.write('INST:STAT:MODE ' + app)
            time.sleep(1)
            self.start()
            time.sleep(4)
            if app == 'TLS':
                time.sleep(25)
        else:
            self.stop()
            self.write('INST:STAT:MODE MAIN')
        self._currApp = app

    def getWLrangeFromHardware(self):
        stop_wl = float(self.query('SENS:WAV:STOP?'))
        start_wl = float(self.query('SENS:WAV:STAR?'))
        return [stop_wl, start_wl]

    @property
    def wlRange(self):
        if self._wlRange is None:
            self._wlRange = self.getWLrangeFromHardware()
        return self._wlRange

    @wlRange.setter
    def wlRange(self, newRange):
        newRangeClipped = np.clip(newRange, a_min=1516, a_max=1565)
        if np.any(newRange != newRangeClipped):
            logger.warning('Requested OSA wlRange out of range. Got %s', newRange)
        self.write('SENS:WAV:STAR ' + str(np.min(newRangeClipped)) + ' NM')
        self.write('SENS:WAV:STOP ' + str(np.max(newRangeClipped)) + ' NM')
        self._wlRange = self.getWLrangeFromHardware()
        time.sleep(15)

    def _read_trace_ascii(self):
        """Read trace data in ASCII format.

        Returns:
            list of float: interleaved wavelength and power values
        """
        self.write('FORM ASCII')
        raw = self.query('TRAC?')
        return [float(x) for x in raw.split(',')]

    def _read_trace_real(self):
        """Read trace data in REAL (binary double) format.

        Only supported in VISA/GPIB mode.

        Returns:
            list of [wavelength, power] pairs
        """
        if self._use_tcp:
            raise NotImplementedError(
                "REAL trace format is not supported over TCP. Use form='ASCII'.")

        self.write('FORM REAL')
        num_points = int(self.query('TRACE:DATA:COUNT?'))
        msg_length = num_points * 2 * 8  # 2 doubles per point, 8 bytes each

        try:
            self.open()
            self.mbSession.write('TRAC?')
            raw = self.mbSession.read_bytes(msg_length, chunk_size=None,
                                            break_on_termchar=False)
        finally:
            if self.tempSess:
                self.close()

        trace = []
        for i in range(num_points):
            wl = struct.unpack('d', raw[i * 16:i * 16 + 8])[0]
            pwr = struct.unpack('d', raw[i * 16 + 8:(i + 1) * 16])[0]
            trace.append([wl, pwr])
        return trace

    def spectrum(self, form='REAL'):
        """Acquire a spectrum from the OSA.

        Args:
            form: 'ASCII' or 'REAL' (default 'REAL').
                  TCP connections only support 'ASCII'.

        Returns:
            Spectrum: wavelength (nm) vs power (dBm)
        """
        if form == 'ASCII':
            data = self._read_trace_ascii()
            x = data[0::2]
            y = data[1::2]
        elif form == 'REAL':
            data = self._read_trace_real()
            x = [pt[0] for pt in data]
            y = [pt[1] for pt in data]
        else:
            raise ValueError("form must be 'ASCII' or 'REAL'")
        return Spectrum(x, y, inDbm=True)

    def CAParam(self, avgCount='CONT', sMode='HR', noiseZero=False):
        """Configure Component Analyzer parameters.

        Args:
            avgCount: Averaging count - one of '4', '8', '12', '32', 'CONT'
                      Can also pass an int (4, 8, 12, 32).
            sMode: Speed mode - 'HR' (high resolution) or 'HS' (high speed)
            noiseZero: If True, perform noise zeroing
        """
        if isinstance(avgCount, int):
            avgCount = str(avgCount)
        if not isinstance(avgCount, str):
            raise TypeError("avgCount must be a string or int")
        if avgCount not in _AVG_COUNTS:
            raise ValueError("avgCount must be one of {}".format(_AVG_COUNTS))

        if not isinstance(sMode, str):
            raise TypeError("sMode must be a string")
        if sMode not in _SPEED_MODES:
            raise ValueError("sMode must be one of {}".format(_SPEED_MODES))

        if not isinstance(noiseZero, bool):
            raise TypeError("noiseZero must be a bool")

        if self._currApp != 'CA':
            raise RuntimeError("Must be in CA application mode. Current: {}".format(self._currApp))

        self.write('SENS:AVER:COUN ' + avgCount)
        self.write('SENS:AVER:STAT ON')
        self.write('SENS:WAV:SMOD ' + sMode)
        if noiseZero:
            self.write('SENS:NOIS')

    def CAInput(self, meas='IL', pol='1'):
        """Set Component Analyzer input parameters.

        Args:
            meas: Measurement type - 'IL', 'RL', or 'IL&RL'
            pol: Polarization - '1', '2', 'INDEP', or 'SIMUL'
        """
        if meas not in _CA_MEASUREMENTS:
            raise ValueError("meas must be one of {}".format(_CA_MEASUREMENTS))
        if pol not in _CA_POLARIZATIONS:
            raise ValueError("pol must be one of {}".format(_CA_POLARIZATIONS))
        self.write('INP:SPAR ' + meas)
        self.write('INP:POL ' + pol)

    def TLSwavelength(self, waveLength=None):
        """Set the TLS wavelength.

        Args:
            waveLength: Wavelength in nm
        """
        if waveLength is None:
            raise ValueError("waveLength must be specified")
        if self._currApp != 'TLS':
            raise RuntimeError("Must be in TLS application mode. Current: {}".format(self._currApp))
        self.write('SENS:SWITCH ON')
        self.write('SENS:WAV:STAT ' + str(waveLength) + ' NM')
