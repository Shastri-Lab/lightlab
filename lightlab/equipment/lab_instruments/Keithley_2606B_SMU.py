""" Driver class for Keithley 2606B.

The following programming example illustrates the setup and command
sequence of a basic source-measure procedure with the following parameters:
• Source function and range: voltage, autorange
• Source output level: 5 V
• Current compliance limit: 10 mA
• Measure function and range: current, 10 mA

-- Restore 2606B defaults.
smua.reset()
-- Select voltage source function.
smua.source.func = smua.OUTPUT_DCVOLTS
-- Set source range to auto.
smua.source.autorangev = smua.AUTORANGE_ON
-- Set voltage source to 5 V.
smua.source.levelv = 5
-- Set current limit to 10 mA.
smua.source.limiti = 10e-3
-- Set current range to 10 mA.
smua.measure.rangei = 10e-3
-- Turn on output.
smua.source.output = smua.OUTPUT_ON
-- Print and place the current reading in the reading buffer.
print(smua.measure.i(smua.nvbuffer1))
-- Turn off output.
smua.source.output = smua.OUTPUT_OFF

Supports both TCP (TSP-Link multi-device) and VISA (USB/GPIB single-device)
connections.  The connection type is auto-detected from the address format:

- Address containing ``SOCKET`` -> TCP mode (e.g. ``TCPIP0::192.168.1.100::5025::SOCKET``)
- Anything else -> VISA mode (e.g. ``USB0::...``, ``GPIB0::...``)
"""
from . import VISAInstrumentDriver
from lightlab.equipment.visa_bases.driver_base import TCPSocketConnection

import socket
import threading
import numpy as np
import time
from lightlab import logger


# Shared TCP connection pool: all Keithley channel instances on the same
# IP:port reuse a single TCP socket (the 2606B only supports one connection).
# Each entry also holds a threading.Lock to serialize access.
_connection_pool = {}  # (ip_address, port) -> {'conn': TCPSocketConnection, 'lock': threading.Lock()}


def _get_shared_connection(ip_address, port, timeout):
    """Get or create a shared TCP connection and lock for a given IP:port."""
    key = (ip_address, port)
    if key not in _connection_pool:
        _connection_pool[key] = {
            'conn': TCPSocketConnection(
                ip_address=ip_address,
                port=port,
                timeout=timeout,
            ),
            'lock': threading.Lock(),
        }
    return _connection_pool[key]['conn'], _connection_pool[key]['lock']


class Keithley_2606B_SMU(VISAInstrumentDriver):
    """ Keithley 2606B SMU instrument driver (TCP and VISA).

        `Manual: <https://download.tek.com/manual/2606B-901-01B_May_2018_Ref_Man.pdf>`__

        Capable of sourcing current and measuring voltage, as a Source
        Measurement Unit.

        Connection type is auto-detected from the address:

        - Address containing ``SOCKET`` -> TCP mode with shared socket pool.
          Requires ``tsp_node`` (1-64) for TSP-Link multi-device setups.
        - Anything else -> VISA mode (USB, GPIB, etc.) for a single
          directly-connected device.
    """

    # instrument_category left as None (inherited default).
    # The driver is used directly, not wrapped by a Keithley instrument object.

    tsp_node = None
    channel = None

    MAGIC_TIMEOUT = 10
    _latestCurrentVal = 0
    _latestVoltageVal = 0
    currStep = 0.1e-3
    voltStep = 0.3
    rampStepTime = 0.05  # in seconds.

    def __init__(
        self,
        name=None,
        address=None,
        tsp_node: int = None,
        channel: str = None,
        **visa_kwargs
    ):
        """
        Args:
            name: Instrument name.
            address: VISA address string.  If it contains ``SOCKET``, TCP
                mode is used; otherwise standard VISA (USB/GPIB).
            tsp_node: TSP-Link node number (1-64).  Required for TCP mode,
                ignored for VISA mode.
            channel: ``'A'`` or ``'B'``.
        """
        if channel is None:
            logger.warning("Forgot to select a channel: either 'A', or 'B'")
        elif channel not in ("A", "B", "a", "b"):
            raise RuntimeError("Select a channel: either 'A', or 'B'")
        else:
            self.channel = channel.upper()

        # Detect connection type from address
        self._connection_type = self._detect_connection_type(address)

        if self._connection_type == "tcp":
            if tsp_node is None:
                logger.warning("Forgot to specify a tsp_node integer number between 1 and 64.")
            elif not isinstance(tsp_node, int):
                raise RuntimeError(
                    "Please specify a tsp_node integer number between 1 and 64."
                )
            elif not 1 <= tsp_node <= 64:
                raise RuntimeError("Invalid tsp_node. Valid numbers between 1 and 64.")

        self.tsp_node = tsp_node

        self._started = False

        visa_kwargs["tempSess"] = visa_kwargs.pop("tempSess", True)
        VISAInstrumentDriver.__init__(self, name=name, address=address, **visa_kwargs)

        if self._connection_type == "tcp":
            self._init_tcp_connection(address)
        else:
            self._tcpsocket = None
            self._tcp_lock = None

    @staticmethod
    def _detect_connection_type(address):
        """Return ``'tcp'`` or ``'visa'`` based on the address format."""
        if address is not None and "SOCKET" in address.upper():
            return "tcp"
        return "visa"

    # ------------------------------------------------------------------
    # SMU addressing
    # ------------------------------------------------------------------

    @property
    def smu_string(self):
        """Return ``'smua'`` or ``'smub'`` based on the channel."""
        if self.channel.upper() == "A":
            return "smua"
        elif self.channel.upper() == "B":
            return "smub"
        else:
            raise RuntimeError(
                "Unexpected channel: {}, should be 'A' or 'B'".format(self.channel)
            )

    @property
    def smu_full_string(self):
        """Return the fully-qualified SMU string.

        - TCP/TSP-Link: ``node[N].smuX``
        - VISA (single device): ``smuX``
        """
        if self.tsp_node is not None:
            return "node[{N}].{smuX}".format(N=self.tsp_node, smuX=self.smu_string)
        return self.smu_string

    # ------------------------------------------------------------------
    # TCP socket methods (only used when _connection_type == "tcp")
    # ------------------------------------------------------------------

    def _init_tcp_connection(self, address):
        if address is not None:
            # should be something like ['TCPIP0', 'xxx.xxx.xxx.xxx', '6501', 'SOCKET']
            address_array = address.split("::")
            ip_address = address_array[1]
            port = int(address_array[2])
            self._tcpsocket, self._tcp_lock = _get_shared_connection(
                ip_address, port, self.MAGIC_TIMEOUT,
            )
        else:
            self._tcpsocket = None
            self._tcp_lock = threading.Lock()

    def _reconnect(self):
        """Force-reconnect the shared TCP socket. Caller must hold _tcp_lock."""
        self._tcpsocket.disconnect()
        self._tcpsocket.connect()

    # def _tcp_query_unlocked(self, queryStr):
    #     """Execute a query over the TCP socket.
    #     Caller must hold _tcp_lock.
    #     """
    #     with self._tcpsocket.connected() as s:
    #         s.send(queryStr)

    #         raw_socket = self._tcpsocket._socket
    #         old_timeout = raw_socket.gettimeout()
    #         try:
    #             raw_socket.settimeout(self.MAGIC_TIMEOUT)
    #             received_msg = ""
    #             i = 0
    #             while i < 1024:  # avoid infinite loop
    #                 recv_str = s.recv(1024)
    #                 if not recv_str:
    #                     raise ConnectionResetError("Remote closed connection")
    #                 received_msg += recv_str
    #                 if recv_str.endswith("\n"):
    #                     break
    #                 raw_socket.settimeout(1)
    #                 i += 1
    #         finally:
    #             raw_socket.settimeout(old_timeout)
    #         return received_msg.rstrip()
        
    def _tcp_query_unlocked(self, queryStr):
        self._tcpsocket.connect()
        self._tcpsocket._send(self._tcpsocket._socket, queryStr)
        
        raw_socket = self._tcpsocket._socket
        old_timeout = raw_socket.gettimeout()
        try:
            raw_socket.settimeout(self.MAGIC_TIMEOUT)
            received_msg = ""
            i = 0
            while i < 1024:
                recv_str = self._tcpsocket._recv(raw_socket)
                if not recv_str:
                    raise ConnectionResetError("Remote closed connection")
                received_msg += recv_str
                if recv_str.endswith("\n"):
                    break
                raw_socket.settimeout(1)
                i += 1
        finally:
            raw_socket.settimeout(old_timeout)
        return received_msg.rstrip()

    def _tcp_query(self, queryStr):
        """Query with lock and automatic reconnect on broken pipe."""
        with self._tcp_lock:
            try:
                return self._tcp_query_unlocked(queryStr)
            except (BrokenPipeError, ConnectionResetError, OSError) as e:
                logger.warning("Connection error (%s), reconnecting and retrying...", e)
                self._reconnect()
                return self._tcp_query_unlocked(queryStr)

    # def _tcp_write_unlocked(self, writeStr):
    #     """Execute a write over the TCP socket. Caller must hold _tcp_lock."""
    #     logger.debug("Sending '%s'", writeStr)
    #     with self._tcpsocket.connected() as s:
    #         s.send(writeStr)

    def _tcp_write_unlocked(self, writeStr):
        logger.debug("Sending '%s'", writeStr)
        self._tcpsocket.connect()  # ensure connected (no-op if already)
        self._tcpsocket._send(self._tcpsocket._socket, writeStr)

    def _tcp_write(self, writeStr):
        """Write with lock and automatic reconnect on broken pipe."""
        with self._tcp_lock:
            try:
                self._tcp_write_unlocked(writeStr)
            except (BrokenPipeError, ConnectionResetError, OSError) as e:
                logger.warning("Connection error (%s), reconnecting and retrying...", e)
                self._reconnect()
                self._tcp_write_unlocked(writeStr)

    # ------------------------------------------------------------------
    # Connection-type-dependent methods
    # ------------------------------------------------------------------

    def reinstantiate_session(self, *args, **kwargs):
        if getattr(self, '_connection_type', None) == "tcp":
            # No-op: we use a raw TCP socket, not a pyvisa session.
            pass
        else:
            super().reinstantiate_session(*args, **kwargs)

    def open(self):
        if self._connection_type == "tcp":
            if self.address is None:
                raise RuntimeError("Attempting to open connection to unknown address.")
            with self._tcp_lock:
                try:
                    self._tcpsocket.connect()
                except socket.error:
                    self._tcpsocket.disconnect()
                    raise
            if not self._started:
                self._started = True
                self.startup()
        else:
            super().open()

    def close(self):
        if self._connection_type == "tcp":
            self._started = False
            # Shared connection is not disconnected; other instances may be using it.
        else:
            super().close()

    def write(self, writeStr):
        if self._connection_type == "tcp":
            self._tcp_write(writeStr)
            time.sleep(0.05)
        else:
            self._session_object.write(writeStr)

    def query(self, queryStr, expected_talker=None):
        if self._connection_type == "tcp":
            ret = self._tcp_query(queryStr)
        else:
            ret = self._session_object.query(queryStr)

        if expected_talker is not None:
            if ret != expected_talker:
                log_function = logger.warning
            else:
                log_function = logger.debug
            log_function(
                "'%s' returned '%s', expected '%s'", queryStr, ret, str(expected_talker)
            )
        else:
            logger.debug("'%s' returned '%s'", queryStr, ret)
        return ret

    def instrID(self):
        if self._connection_type == "tcp":
            query_str = (
                "print([[Keithley Instruments Inc., Model ]].."
                "node[{tsp_node}].model..[[, ]]..node[{tsp_node}].serialno..[[, ]]..node[{tsp_node}].revision)".format(
                    tsp_node=self.tsp_node
                )
            )
            return self.query(query_str)
        else:
            return self._session_object.instrID()

    # ------------------------------------------------------------------
    # Common instrument methods
    # ------------------------------------------------------------------

    def query_print(self, query_string, expected_talker=None):
        if self._connection_type == "tcp":
            time.sleep(0.01)
        else:
            time.sleep(0.1)
        query_string = "print(" + query_string + ")"
        return self.query(query_string, expected_talker=expected_talker)

    def smu_reset(self):
        self.write("{smuX}.reset()".format(smuX=self.smu_full_string))

    def smu_defaults(self):
        self.write("{smuX}.source.offfunc = 0".format(smuX=self.smu_full_string))  # 0 or smuX.OUTPUT_DCAMPS: Source 0 A
        self.write("{smuX}.source.offmode = 0".format(smuX=self.smu_full_string))  # 0 or smuX.OUTPUT_NORMAL: Configures the source function according to smuX.source.offfunc attribute
        self.write("{smuX}.source.highc = 1".format(smuX=self.smu_full_string))  # 1 or smuX.ENABLE: Enables high-capacitance mode
        self.set_sense_mode(sense_mode="local")

    def startup(self):
        if self._connection_type == "tcp":
            self.tsp_startup()
        self.smu_reset()
        self.smu_defaults()
        self.write("waitcomplete()")
        time.sleep(0.01)
        self.query_print('"startup complete."', expected_talker="startup complete.")

    def is_master(self):
        """ Returns true if this TSP node is the localnode.

        The localnode is the one being interfaced with the Ethernet cable,
        whereas the other nodes are connected to it via the TSP-Link ports.
        Only meaningful in TCP/TSP-Link mode.
        """
        return self.query_print("localnode.serialno") == self.query_print(
            "node[{tsp_node}].serialno".format(tsp_node=self.tsp_node)
        )

    def get_tsp_node(self):
        """Return the TSP-Link node number currently assigned to this device."""
        return int(float(self.query_print("tsplink.node")))

    def set_tsp_node(self, node_number):
        """Assign a TSP-Link node number (1-64) to this device.

        Typically used over USB/VISA so the device can later be reached
        via TCP/TSP-Link at the configured node number.
        """
        node_number = int(node_number)
        if not 1 <= node_number <= 64:
            raise ValueError("node_number must be between 1 and 64, got {}".format(node_number))
        self.write("tsplink.node = {}".format(node_number))

    def tsp_startup(self, restart=False):
        """ Ensures that the TSP network is available.

        - Checks if tsplink.state is online.
        - If offline, send a reset().
        """
        state = self.query_print("tsplink.state")
        if state == "online" and not restart:
            return True
        elif state == "offline":
            nodes = int(float(self.query_print("tsplink.reset()")))
            logger.debug("%s TSP nodes found.", nodes)
            return True

    def set_sense_mode(self, sense_mode="local"):
        ''' Set sense mode. Defaults to local sensing. '''
        if sense_mode == "remote":
            sense_mode = 1  # 1 or smuX.SENSE_REMOTE: Selects remote sense (4-wire)
        elif sense_mode == "local":
            sense_mode = 0  # 0 or smuX.SENSE_LOCAL: Selects local sense (2-wire)
        else:
            sense_mode = 0  # 0 or smuX.SENSE_LOCAL: Selects local sense (2-wire)

        self.write("{smuX}.sense = {sense_mode}".format(smuX=self.smu_full_string, sense_mode=sense_mode))

    # SourceMeter Essential methods

    def _configCurrent(self, currAmps):
        currAmps = float(currAmps)
        if currAmps >= 0:
            currAmps = np.clip(currAmps, a_min=1e-9, a_max=1.0)
        else:
            currAmps = np.clip(currAmps, a_min=-1, a_max=-1e-9)
        self.write(
            "{smuX}.source.leveli = {c}".format(smuX=self.smu_full_string, c=currAmps)
        )
        self._latestCurrentVal = currAmps

    def _configVoltage(self, voltVolts):
        voltVolts = float(voltVolts)
        self.write(
            "{smuX}.source.levelv = {v}".format(smuX=self.smu_full_string, v=voltVolts)
        )
        self._latestVoltageVal = voltVolts

    def setCurrent(self, currAmps):
        """ This leaves the output on indefinitely """
        currTemp = self._latestCurrentVal
        if not self.enable() or self.currStep is None:
            self._configCurrent(currAmps)
        else:
            nSteps = int(np.floor(abs(currTemp - currAmps) / self.currStep))
            for curr in np.linspace(currTemp, currAmps, 2 + nSteps)[1:]:
                self._configCurrent(curr)
                time.sleep(self.rampStepTime)

    def setVoltage(self, voltVolts):
        voltTemp = self._latestVoltageVal
        if not self.enable() or self.voltStep is None:
            self._configVoltage(voltVolts)
        else:
            nSteps = int(np.floor(abs(voltTemp - voltVolts) / self.voltStep))
            for volt in np.linspace(voltTemp, voltVolts, 2 + nSteps)[1:]:
                self._configVoltage(volt)
                time.sleep(self.rampStepTime)

    def getCurrent(self):
        curr = self.query_print("{smuX}.source.leveli".format(smuX=self.smu_full_string))
        return float(curr)

    def getVoltage(self):
        volt = self.query_print("{smuX}.source.levelv".format(smuX=self.smu_full_string))
        return float(volt)

    def setProtectionVoltage(self, protectionVoltage):
        protectionVoltage = float(protectionVoltage)
        self.write(
            "{smuX}.source.limitv = {v}".format(smuX=self.smu_full_string, v=protectionVoltage)
        )

    def setProtectionCurrent(self, protectionCurrent):
        protectionCurrent = float(protectionCurrent)
        self.write(
            "{smuX}.source.limiti = {c}".format(smuX=self.smu_full_string, c=protectionCurrent)
        )

    @property
    def compliance(self):
        return (self.query_print("{smuX}.source.compliance".format(smuX=self.smu_full_string)) == "true")

    def measVoltage(self):
        retStr = self.query_print("{smuX}.measure.v()".format(smuX=self.smu_full_string))
        v = float(retStr)
        if self.compliance:
            logger.warning('Keithley compliance voltage of %s reached', self.protectionVoltage)
            logger.warning('You are sourcing %smW into the load.', v * self._latestCurrentVal * 1e-3)
        return v

    def measCurrent(self):
        retStr = self.query_print("{smuX}.measure.i()".format(smuX=self.smu_full_string))
        i = float(retStr)  # second number is current always
        if self.compliance:
            logger.warning('Keithley compliance current of %s reached', self.protectionCurrent)
            logger.warning('You are sourcing %smW into the load.', i * self._latestVoltageVal * 1e-3)
        return i

    @property
    def protectionVoltage(self):
        volt = self.query_print("{smuX}.source.limitv".format(smuX=self.smu_full_string))
        return float(volt)

    @property
    def protectionCurrent(self):
        curr = self.query_print("{smuX}.source.limiti".format(smuX=self.smu_full_string))
        return float(curr)

    def enable(self, newState=None):
        ''' get/set enable state
        '''
        if newState is not None:
            while True:
                self.write("{smuX}.source.output = {on_off}".format(smuX=self.smu_full_string, on_off=1 if newState else 0))
                time.sleep(0.1)
                self.query_print("\"output configured\"", expected_talker="output configured")
                time.sleep(0.1)
                retVal = self.query_print("{smuX}.source.output".format(smuX=self.smu_full_string))
                is_on = float(retVal) == 1
                if bool(newState) == is_on:
                    break
        else:
            retVal = self.query_print("{smuX}.source.output".format(smuX=self.smu_full_string))
            is_on = float(retVal) == 1
        return is_on

    def __setSourceMode(self, isCurrentSource):
        if isCurrentSource:
            source_mode_code = 0
            source_mode_letter = 'i'
            measure_mode_letter = 'v'
        else:
            source_mode_code = 1
            source_mode_letter = 'v'
            measure_mode_letter = 'i'

        self.write("{smuX}.source.func = {code}".format(smuX=self.smu_full_string, code=source_mode_code))
        self.write("{smuX}.source.autorange{Y} = 1".format(smuX=self.smu_full_string, Y=source_mode_letter))
        self.write("{smuX}.measure.autorange{Y} = 1".format(smuX=self.smu_full_string, Y=measure_mode_letter))

    def _smu_write(self, string):
        return self.write("{smuX}.{string}".format(smuX=self.smu_full_string, string=string))

    def _smu_query(self, string):
        return self.query_print("{smuX}.{string}".format(smuX=self.smu_full_string, string=string))

    def setVoltageMode(self, protectionCurrent=0.05):
        self.enable(False)
        self.__setSourceMode(isCurrentSource=False)
        self.setProtectionCurrent(protectionCurrent)
        self._configVoltage(0)

    def setCurrentMode(self, protectionVoltage=1):
        self.enable(False)
        self.__setSourceMode(isCurrentSource=True)
        self.setProtectionVoltage(protectionVoltage)
        self._configCurrent(0)


# Backward compatibility alias
Keithley_2606B_SMU_TCP = Keithley_2606B_SMU
