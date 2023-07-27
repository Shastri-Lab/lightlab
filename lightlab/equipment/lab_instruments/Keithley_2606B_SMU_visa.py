from . import VISAInstrumentDriver
from lightlab.laboratory.instruments import Keithley
import pyvisa as visa
import numpy as np
import time
from lightlab import logger


class Keithley_2606B_SMU_USB(VISAInstrumentDriver):
    # instrument_category = Keithley
    #TODO: combine with Keithley_2606B_SMU.py (one driver for USB and TCP/IP)

    tsp_node = None
    channel = None
    inst = None

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
            channel: str = None,
            **visa_kwargs
    ):
        """
        Args:
            channel: 'A' or 'B'
        """

        if channel is None:
            logger.warning("Forgot to select a channel: either 'A', or 'B'")
        elif channel not in ("A", "B", "a", "b"):
            raise RuntimeError("Select a channel: either 'A', or 'B'")
        else:
            self.channel = channel.upper()

        # self.tsp_node = tsp_node

        visa_kwargs["tempSess"] = visa_kwargs.pop("tempSess", True)
        VISAInstrumentDriver.__init__(self, name=name, address=address, **visa_kwargs)

    def first_startup(self):
        print('Keithley Initializing for 10 Seconds...')
        time.sleep(10)
        print(self._query(''))
        print('Initialized!')

    def _query(self, queryStr):
        # print(f'Message Sent: {queryStr}')
        self.query('*OPC?')
        self.write(queryStr)
        time.sleep(0.5)
        received_msg = self.query(':SYST:ERR?')
#         i = 0
#         received_msg = ""
#         while i < 1024:  # avoid infinite loop
#             recv_str = self.inst.read_raw(1024).decode("utf-8")
#             received_msg += recv_str
#             if recv_str.endswith("\n"):
#                 break
#             time.sleep(1)
#             i += 1
        # print(f'Message Received: {received_msg.rstrip()}')
        return received_msg.rstrip()
        
    def SMUquery(self, queryStr, expected_talker=None):
        ret = self._query(queryStr)
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

    def smu_string(self):
        if self.channel.upper() == "A":
            return "smua"
        elif self.channel.upper() == "B":
            return "smub"
        else:
            raise RuntimeError(
                "Unexpected channel: {}, should be 'A' or 'B'".format(self.channel)
            )
            
    def query_print(self, query_string, expected_talker=None):
        time.sleep(0.1)
        query_string = "print(" + query_string + ")"
        return self.SMUquery(query_string, expected_talker=expected_talker)

    def smu_reset(self):
        self.write("{smu_ch}.reset()".format(smu_ch=self.smu_string()))

    def smu_defaults(self):
        self.write("{smuX}.source.offfunc = 0".format(smuX=self.smu_string()))  # 0 or smuX.OUTPUT_DCAMPS: Source 0 A
        self.write("{smuX}.source.offmode = 0".format(
            smuX=self.smu_string()))  # 0 or smuX.OUTPUT_NORMAL: Configures the source function according to smuX.source.offfunc attribute
        self.write(
            "{smuX}.source.highc = 1".format(smuX=self.smu_string()))  # 1 or smuX.ENABLE: Enables high-capacitance mode
        # self.write("{smuX}.sense = 0".format(smuX=self.smu_full_string))  # 0 or smuX.SENSE_LOCAL: Selects local sense (2-wire)
        self.set_sense_mode(sense_mode="local")

    def startup(self):
        self.smu_reset()
        self.smu_defaults()
        self.write("waitcomplete()")
        time.sleep(0.01)
        self.query_print('"startup complete."', expected_talker="startup complete.")

    def set_sense_mode(self, sense_mode="local"):
        ''' Set sense mode. Defaults to local sensing. '''
        if sense_mode == "remote":
            sense_mode = 1  # 1 or smuX.SENSE_REMOTE: Selects remote sense (4-wire)
        elif sense_mode == "local":
            sense_mode = 0  # 0 or smuX.SENSE_LOCAL: Selects local sense (2-wire)
        else:
            sense_mode = 0  # 0 or smuX.SENSE_LOCAL: Selects local sense (2-wire)

        self.write("{smuX}.sense = {sense_mode}".format(smuX=self.smu_string(), sense_mode=sense_mode))

    def _configCurrent(self, currAmps):
        currAmps = float(currAmps)
        if currAmps >= 0:
            currAmps = np.clip(currAmps, a_min=1e-9, a_max=1.0)
        else:
            currAmps = np.clip(currAmps, a_min=-1, a_max=-1e-9)
        self.write(
            "{smuX}.source.leveli = {c}".format(smuX=self.smu_string(), c=currAmps)
        )
        self._latestCurrentVal = currAmps

    def _configVoltage(self, voltVolts):
        voltVolts = float(voltVolts)
        self.write(
            "{smuX}.source.levelv = {v}".format(smuX=self.smu_string(), v=voltVolts)
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
        curr = self.query_print("{smuX}.source.leveli".format(smuX=self.smu_string()))
        return float(curr)

    def getVoltage(self):
        volt = self.query_print("{smuX}.source.levelv".format(smuX=self.smu_string()))
        return float(volt)

    def setProtectionVoltage(self, protectionVoltage):
        protectionVoltage = float(protectionVoltage)
        self.write(
            "{smuX}.source.limitv = {v}".format(smuX=self.smu_string(), v=protectionVoltage)
        )

    def setProtectionCurrent(self, protectionCurrent):
        protectionCurrent = float(protectionCurrent)
        self.write(
            "{smuX}.source.limiti = {c}".format(smuX=self.smu_string(), c=protectionCurrent)
        )

    @property
    def compliance(self):
        return self.query_print("{smuX}.source.compliance".format(smuX=self.smu_string())) == "true"

    def measVoltage(self):
        retStr = self.query_print("{smuX}.measure.v()".format(smuX=self.smu_string()))
        v = float(retStr)
        if self.compliance:
            logger.warning('Keithley compliance voltage of %s reached', self.protectionVoltage)
            logger.warning('You are sourcing %smW into the load.', v * self._latestCurrentVal * 1e-3)
        return v

    def measCurrent(self):
        retStr = self.query_print("{smuX}.measure.i()".format(smuX=self.smu_string()))
        i = float(retStr)  # second number is current always
        if self.compliance:
            logger.warning('Keithley compliance current of %s reached', self.protectionCurrent)
            logger.warning('You are sourcing %smW into the load.', i * self._latestVoltageVal * 1e-3)
        return i

    @property
    def protectionVoltage(self):
        volt = self.query_print("{smuX}.source.limitv".format(smuX=self.smu_string()))
        return float(volt)

    @property
    def protectionCurrent(self):
        curr = self.query_print("{smuX}.source.limiti".format(smuX=self.smu_string()))
        print(curr)
        return float(curr)

    def enable(self, newState=None):
        ''' get/set enable state
        '''
        if newState is not None:
            while True:
                self.write(
                    "{smuX}.source.output = {on_off}".format(smuX=self.smu_string(), on_off=1 if newState else 0))
                time.sleep(0.1)
                self.query_print("\"output configured\"", expected_talker="output configured")
                time.sleep(0.5)
                retVal = self.query_print("{smuX}.source.output".format(smuX=self.smu_string()))
                is_on = float(retVal) == 1
                if bool(newState) == is_on:
                    break
        else:
            retVal = self.query_print("{smuX}.source.output".format(smuX=self.smu_string()))
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

        self.write("{smuX}.source.func = {code}".format(smuX=self.smu_string(), code=source_mode_code))
        self.write("{smuX}.source.autorange{Y} = 1".format(smuX=self.smu_string(), Y=source_mode_letter))
        self.write("{smuX}.measure.autorange{Y} = 1".format(smuX=self.smu_string(), Y=measure_mode_letter))

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
