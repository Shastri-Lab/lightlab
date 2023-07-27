from . import VISAInstrumentDriver
from lightlab.equipment.abstract_drivers import kf
from lightlab.util.data import Waveform
import pyvisa as visa

import numpy as np
import matplotlib.pyplot as plt


# TODO: write a new driver for this sampling scope...
# The Agilent driver works well though so just importing
from .Agilent_54846B_Oscope import Agilent_54846B_Oscope as Keysight_N1000