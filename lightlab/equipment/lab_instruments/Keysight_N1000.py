from . import VISAInstrumentDriver
from lightlab.equipment.abstract_drivers import kf
from lightlab.util.data import Waveform
import pyvisa as visa

import numpy as np
import matplotlib.pyplot as plt


# TODO: write a new driver for this sampling scope...
# The Agilent driver works well though so just importing and wrapping
from .Agilent_54846B_Oscope import Agilent_54846B_Oscope

class Keysight_N1000(Agilent_54846B_Oscope):
    pass
