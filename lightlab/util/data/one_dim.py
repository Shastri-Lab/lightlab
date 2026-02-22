''' One-dimensional data structures with substantial processing abilities
'''
import matplotlib.pyplot as plt
import numpy as np
from scipy import signal
from lightlab import logger
from IPython import display
import lightlab.util.io as io

from .peaks import findPeaks, ResonanceFeature
from .basic import rms
from .function_inversion import interpInverse

# Speed of light in nm*GHz (c = 299792458 m/s → nm·GHz)
_C_NM_GHZ = 299_792_458


def prbs_generator(characteristic, state):
    ''' Generator of PRBS bits.

        Example:
        polynomial = 0b1000010001  # 1 + X^5 + X^9
        seed = 0b111100000

        The above parameters will give you a PRBS9 bit sequence.
        Note: it might be inverted compared to the official definition,
        i.e., 1s are 0s and vice versa.
    '''

    def compute_parity(n):
        parity = False
        while n > 0:
            parity ^= (n & 1)
            n >>= 1

        return parity  # odd means True

    order = characteristic.bit_length() - 1
    while True:
        result = state & 1
        state += (compute_parity(state & characteristic) << order)
        state >>= 1
        yield result


def prbs_pattern(polynomial, seed, length=None):
    ''' Returns an array containing a sequence of a PRBS pattern.

    If length is not set, the sequence will be 2^n-1 long, corresponding
    to the repeating pattern of the PRBS sequence.
    '''
    order = polynomial.bit_length() - 1

    if length is None:
        length = 2 ** order - 1

    from itertools import islice
    prbs_pattern = list(islice(iter(prbs_generator(polynomial, seed)), length))
    return ~np.array(prbs_pattern, dtype=bool)


# Standard PRBS characteristic polynomials for prbs_pattern().
# Derived from ITU-T polynomials of the form x^N + x^k + 1.
# Encoding: (1 << N) | (1 << (k-1)) | 1
_PRBS_POLYNOMIALS = {
    7:  (1 << 7)  | (1 << 5)  | 1,  # x^7 + x^6 + 1
    9:  (1 << 9)  | (1 << 4)  | 1,  # x^9 + x^5 + 1
    11: (1 << 11) | (1 << 8)  | 1,  # x^11 + x^9 + 1
    15: (1 << 15) | (1 << 13) | 1,  # x^15 + x^14 + 1
    23: (1 << 23) | (1 << 17) | 1,  # x^23 + x^18 + 1
    31: (1 << 31) | (1 << 27) | 1,  # x^31 + x^28 + 1
}


class MeasuredFunction(object):  # pylint: disable=eq-without-hash
    ''' Array of x,y points.
        This is the workhorse class of ``lightlab`` data structures.
        Examples can be found throughout Test notebooks.

        Supports many kinds of operations:

        1. Data access (``mf(x)``, ``len(mf)``, ``mf[i]``, :meth:`getData`)
            Calling the object with x-values interpolates and returns y-values.

        2. Storage (:meth:`copy`, :meth:`save`, :meth:`load`, :meth:`loadFromFile`)
            see method docstrings

        3. x-axis signal processing (:meth:`getSpan`, :meth:`crop`, :meth:`shift`, :meth:`flip`, :meth:`resample`, :meth:`uniformlySample`)
            see method docstrings

        4. y-axis signal processing (:meth:`getRange`, :meth:`clip`, :meth:`debias`, :meth:`unitRms`, :meth:`getMean`, :meth:`moment`)
            see method docstrings

        5. Advanced signal processing (:meth:`invert`, :meth:`lowPass`, :meth:`centerOfMass`, :meth:`findResonanceFeatures`)
            see method docstrings

        6. Binary math (``+``, ``-``, ``*``, ``/``, ``==``)
            Operands must be either
                * the same subclass of MeasuredFunction, or
                * scalar numbers, or
                * functions/bound methods: these must be callable with one argument that is an ndarray

            If both are MeasuredFunction, the domain used will be the smaller of the two

        7. Plotting (:meth:`simplePlot`)
            Args and Kwargs are passed to pyplot's plot function.
            Supports live plotting for notebooks

        8. Others (:meth:`deleteSegment`, :meth:`splice`)
            see method docstrings
    '''

    # https://stackoverflow.com/questions/14619449/how-can-i-override-comparisons-between-numpys-ndarray-and-my-type
    __array_priority__ = 100  # have numpy call the __*add__ functions first instead of trying to iterate

    absc = None  #: abscissa, a.k.a. the x-values or domain
    ordi = None  #: ordinate, a.k.a. the y-values

    def __init__(self, abscissaPoints, ordinatePoints, unsafe=False):
        '''
            Args:
                abscissaPoints (array): abscissa, a.k.a. independent variable, a.k.a. domain
                ordinatePoints (array): ordinate, a.k.a. dependent variable, a.k.a. range
                unsafe (bool): if True, faster, give it 1-D np.ndarrays of the same length, or you will get weird errors later on
        '''
        if unsafe:
            self.absc = abscissaPoints
            self.ordi = ordinatePoints
        else:
            checkVals = [None, None]
            for iv, arr in enumerate((abscissaPoints, ordinatePoints)):
                if isinstance(arr, np.ndarray):
                    if arr.ndim > 1:
                        raise ValueError(
                            'Must be a one dimensional array. Got shape ' + str(arr.shape))
                    if arr.ndim == 0:
                        arr = np.array([arr])
                    checkVals[iv] = arr.copy()
                elif isinstance(arr, (list, tuple)):
                    checkVals[iv] = np.array(arr)
                elif np.isscalar(arr):
                    checkVals[iv] = np.array([arr])
                else:
                    raise TypeError('Unsupported type: ' + str(type(arr)) +
                                    '. Need np.ndarray, scalar, list, or tuple')
            self.absc, self.ordi = tuple(checkVals)
            if self.absc.shape != self.ordi.shape:
                raise ValueError('Shapes do not match. Got ' +
                                 str(self.absc.shape) + ' and ' + str(self.ordi.shape))

    # Data structuring and usage stuff

    def __call__(self, testAbscissa=None):
        ''' Interpolates the discrete function

            Args:
                testAbscissa (array): test points in the domain

            Returns:
                testOrdinate (array): interpolated output values
        '''
        if np.isscalar(self.absc):
            return self.ordi[0]
        return np.interp(testAbscissa, self.absc, self.ordi)

    def __len__(self):
        return len(self.absc)

    def __iter__(self):
        raise TypeError("{} is not iterable".format(self.__class__.__qualname__))

    def __getitem__(self, sl):
        ''' Slice or index this function.

            Args:
                sl (int, slice, ndarray): integer, slice, boolean mask, or integer array

            Returns:
                (MeasuredFunction/<childClass>): sliced version
        '''
        if isinstance(sl, np.ndarray) and sl.dtype == bool:
            pass  # boolean mask indexing
        elif isinstance(sl, np.ndarray) and np.issubdtype(sl.dtype, np.integer):
            pass  # integer array indexing
        elif type(sl) not in [int, slice]:
            raise ValueError('MeasuredFunction [] only works with integers, slices, '
                             'and numpy arrays. Got ' + str(type(sl)) + '.')
        newAbsc = self.absc[sl]
        newOrdi = self.ordi[sl]
        return self._newOfSameSubclass(newAbsc, newOrdi)

    def getData(self):
        ''' Gives a tuple of the enclosed array data.

            It is copied, so you can do what you want with it

            Returns:
                tuple(array,array): the enclosed data
        '''
        return np.copy(self.absc), np.copy(self.ordi)

    def copy(self):
        ''' Gives a copy, so that further operations can be performed without side effect.

            Returns:
                (MeasuredFunction/<childClass>): new object with same properties
        '''
        return self._newOfSameSubclass(self.absc, self.ordi)

    def save(self, savefile):
        io.saveMat(savefile, {'absc': self.absc, 'ordi': self.ordi})

    @classmethod
    def load(cls, savefile):
        dataDict = io.loadMat(savefile)
        absc = dataDict['absc']
        ordi = dataDict['ordi']
        return cls(absc, ordi)

    def simplePlot(self, *args, livePlot=False, **kwargs):
        r''' Plots on the current axis

        Args:
            livePlot (bool): if True, displays immediately in IPython notebook
            \*args (tuple): arguments passed through to ``pyplot.plot``
            \*\*kwargs (dict): arguments passed through to ``pyplot.plot``

        Returns:
            Whatever is returned by ``pyplot.plot``
        '''
        curve = plt.plot(*(self.getData() + args), **kwargs)
        plt.autoscale(enable=True, axis='x', tight=True)
        if 'label' in kwargs.keys():
            plt.legend()
        if livePlot:
            display.display(plt.gcf())
            display.clear_output(wait=True)
        return curve

    # Simple data handling operations

    def _newOfSameSubclass(self, newAbsc, newOrdi):
        ''' Helper functions that ensures proper inheritance of other methods.

            Returns a new object of the same type and
            with the same metadata (i.e. everything but absc and ordi) as self.

            This is useful for many kinds of operations where the returned
            MeasuredFunction or ChildClass is further processed

            Args:
                newAbsc (array): abscissa of new MeasuredFunction
                newOrdi (array): ordinate of new MeasuredFunction

            Returns:
                (MeasuredFunction): new object, which is a child class of MeasuredFunction
        '''
        newObj = type(self)(newAbsc.copy(), newOrdi.copy(), unsafe=True)
        for attr, val in self.__dict__.items():
            if attr not in ['absc', 'ordi']:
                newObj.__dict__[attr] = val
        return newObj

    def subsample(self, newAbscissa):
        ''' Returns a new MeasuredFunction sampled at given points.
        '''
        new_ordi = self.__call__(newAbscissa)
        return self._newOfSameSubclass(newAbscissa, new_ordi)

    def getSpan(self):
        ''' The span of the domain

            Returns:
                (list[float,float]): the minimum and maximum abscissa points
        '''
        return [min(self.absc), max(self.absc)]

    def abs(self):
        ''' Computes the absolute value of the measured function.
        '''
        return abs(self)

    def mean(self):
        return self.getMean()

    def max(self):
        ''' Returns the maximum value of the ordinate axis, ignoring NaNs.'''
        return np.nanmax(self.ordi)

    def argmax(self):
        ''' Returns the abscissa value at which the ordinate is maximum. '''
        return self.absc[np.argmax(self.ordi)]

    def min(self):
        ''' Returns the minimum value of the ordinate axis, ignoring NaNs.'''
        return np.nanmin(self.ordi)

    def argmin(self):
        ''' Returns the abscissa value at which the ordinate is minimum. '''
        return self.absc[np.argmin(self.ordi)]

    def getRange(self):
        ''' The span of the ordinate

            Returns:
                (list[float,float]): the minimum and maximum values
        '''
        return [min(self.ordi), max(self.ordi)]

    def crop(self, segment):
        ''' Crop abscissa to segment domain.

            Args:
                segment (list[float,float]): the span of the new abscissa domain

            Returns:
                MeasuredFunction: new object
        '''
        min_segment, max_segment = segment
        absc_span = self.getSpan()

        if min_segment is None:
            min_segment = absc_span[0]

        if max_segment is None:
            max_segment = absc_span[1]

        # Just in case the user accidentally flipped the segment order
        min_segment, max_segment = min(min_segment, max_segment), max(min_segment, max_segment)

        if min_segment <= absc_span[0] and max_segment >= absc_span[1]:
            # do nothing
            return self.copy()
        mask = (self.absc >= min_segment) & (self.absc <= max_segment)
        return self._newOfSameSubclass(self.absc[mask], self.ordi[mask])

    def clip(self, amin, amax):
        ''' Clip ordinate to min/max range

            Args:
                amin (float): minimum value allowed in the new MeasuredFunction
                amax (float): maximum value allowed in the new MeasuredFunction

            Returns:
                MeasuredFunction: new object
        '''
        return self._newOfSameSubclass(self.absc, np.clip(self.ordi, amin, amax))

    def shift(self, shiftBy):
        ''' Shift abscissa. Good for biasing wavelengths.

            Args:
                shiftBy (float): the number that will be added to the abscissa

            Returns:
                MeasuredFunction: new object
        '''
        return self._newOfSameSubclass(self.absc + shiftBy, self.ordi)

    def flip(self):
        ''' Flips the abscissa, BUT DOES NOTHING the ordinate.

            Usually, this is meant for spectra centered at zero.
            I.e.: flipping would be the same as negating abscissa

            Returns:
                MeasuredFunction: new object
        '''
        return self._newOfSameSubclass(self.absc[::-1], self.ordi)

    def reverse(self):
        ''' Flips the ordinate, keeping abscissa in order

            Returns:
                MeasuredFunction: new object
        '''
        return self._newOfSameSubclass(self.absc, self.ordi[::-1])

    def debias(self):
        ''' Removes mean from the function

            Returns:
                MeasuredFunction: new object
        '''
        bias = np.mean(self.ordi)
        return self._newOfSameSubclass(self.absc, self.ordi - bias)

    def unitRms(self):
        ''' Returns function with unit RMS or power
        '''
        rmsVal = rms(self.debias().ordi)
        return self * (1 / rmsVal)

    def getMean(self):
        return np.mean(self.ordi)

    def getMedian(self):
        return np.median(self.ordi)

    def getVariance(self):
        return np.var(self.ordi)

    def getStd(self):
        return np.std(self.ordi)

    def resample(self, nsamp=100):
        ''' Resample over the same domain span, but with a different number of points.

            Args:
                nsamp (int): number of samples in the new object

            Returns:
                MeasuredFunction: new object
        '''
        newAbsc = np.linspace(*self.getSpan(), int(nsamp))
        return self._newOfSameSubclass(newAbsc, self(newAbsc))

    def uniformlySample(self):
        ''' Makes sure samples are uniform

            Returns:
                MeasuredFunction: new object
        '''
        dxes = np.diff(self.absc)
        if all(dxes == dxes[0]):
            return self
        else:
            return self.resample(len(self))

    def addPoint(self, xyPoint):
        ''' Adds the (x, y) point to the stored absc and ordi

            Args:
                xyPoint (tuple): x and y values to be inserted

            Returns:
                None: it modifies this object
        '''
        x, y = xyPoint
        i = np.searchsorted(self.absc, x)
        self.absc = np.insert(self.absc, i, x)
        self.ordi = np.insert(self.ordi, i, y)

    # Signal processing stuff

    def correlate(self, other):
        ''' Correlate signals with scipy.signal.correlate.

            Only full mode and direct method is supported for now.
        '''
        new_abscissa = type(self)._maxAbsc(self, other)

        # ensure that they are uniformly sampled
        dxes = np.diff(new_abscissa)
        dx = dxes[0]
        assert np.allclose(dxes, dx)  # sometimes there are numerical errors in floats

        N = len(new_abscissa)

        from scipy.signal import correlate
        self_ordi, other_ordi = self(new_abscissa), other(new_abscissa)
        self_ordi_norm = (self_ordi - np.mean(self_ordi)) # TODO: queens version divided by std using: `/ np.std(self_ordi)`
        self_ordi_norm /= np.linalg.norm(self_ordi_norm)
        other_ordi_norm = (other_ordi - np.mean(other_ordi))
        other_ordi_norm /= np.linalg.norm(other_ordi_norm)

        correlated_ordi = correlate(self_ordi_norm,
                                    other_ordi_norm,
                                    mode="full", method="direct")
        offset_abscissa = np.arange(-N + 1, N, 1) * dx
        return self._newOfSameSubclass(offset_abscissa, correlated_ordi)

    def lowPass(self, windowWidth=None, mode=None):
        import warnings
        warnings.warn("lowPass is deprecated. Use lowPassButterworth or movingAverage instead.",
                      DeprecationWarning, stacklevel=2)
        if mode is not None:
            logger.warning("lowPass was renamed to movingAverage. Now it is an actual Butterworth low-pass filter.")
        return self.lowPassButterworth(1 / windowWidth)

    def movingAverage(self, windowWidth=None, mode='valid'):
        ''' Low pass filter performed by convolving a moving average window.

            The convolutional ``mode`` can be one of the following string tokens
                * 'valid': the new span is reduced, but data is good looking
                * 'same': new span is the same as before, but there are edge artifacts

            Args:
                windowWidth (float): averaging window width in units of the abscissa
                mode (str): convolutional mode

            Returns:
                MeasuredFunction: new object
        '''
        if windowWidth is None:
            windowWidth = (max(self.absc) - min(self.absc)) / 10
        dx = abs(np.diff(self.absc[0:2])[0])
        windPts = int(windowWidth / dx)
        if windPts % 2 == 0:  # Make sure windPts is odd so that basis doesn't shift
            windPts += 1
        if windPts >= np.size(self.ordi):
            raise Exception('windowWidth is ' + str(windPts) +
                            ' wide, which is bigger than the data itself (' + str(np.size(self.ordi)) + ')')

        filt = np.ones(windPts) / windPts
        invalidIndeces = int((windPts - 1) / 2)

        if mode == 'valid':
            newAbsc = self.absc[invalidIndeces:-invalidIndeces].copy()
            newOrdi = np.convolve(filt, self.ordi, mode='valid')
        elif mode == 'same':
            newAbsc = self.absc.copy()
            newOrdi = self.ordi.copy()
            newOrdi[invalidIndeces:-invalidIndeces] = np.convolve(filt, self.ordi, mode='valid')
        return self._newOfSameSubclass(newAbsc, newOrdi)

    def butterworthFilter(self, fc, order, btype):
        ''' Applies a Butterworth filter to the signal.

        Side effects: the waveform will be resampled to have equally-sampled points.

        Args:
            fc (float): cutoff frequency of the filter (cf. input to signal.butter)

        Returns:
            New object containing the filtered waveform
        '''

        uniformly_sampled = self.uniformlySample()
        x, y = uniformly_sampled.absc, uniformly_sampled.ordi
        dxes = np.diff(x)
        sampling_rate = 1 / dxes[0]
        fc = np.array(fc)

        b, a = signal.butter(order, fc * 2, btype, fs=sampling_rate)  # construct the filter
        # compute initial condition such that the filtered y starts with the same value as y
        zi = signal.lfilter_zi(b, a)

        # applies the filter to the ordinate y if it is a low pass filter
        if btype.startswith('low'):
            ordi_filtered, _ = signal.lfilter(b, a, y, zi=zi * y[0])
        # cheat and debias the signal prior to high pass filtering
        # this prevents the initial filtered signal to start from zero
        else:
            mean_y = np.mean(y)
            ordi_filtered, _ = signal.lfilter(b, a, y - mean_y, zi=zi * 0)

        uniformly_sampled.ordi = ordi_filtered
        return uniformly_sampled

    def lowPassButterworth(self, fc, order=1):
        ''' Applies a low-pass Butterworth filter to the signal.

        Side effects: the waveform will be resampled to have equally-sampled points.

        Args:
            fc (float): cutoff frequency of the filter

        Returns:
            New object containing the filtered waveform
        '''

        return self.butterworthFilter(fc, order, 'lowpass')

    def highPassButterworth(self, fc, order=1):
        ''' Applies a high-pass Butterworth filter to the signal.

        Side effects: the waveform will be resampled to have equally-sampled points.

        Args:
            fc (float): cutoff frequency of the filter

        Returns:
            New object containing the filtered waveform
        '''

        return self.butterworthFilter(fc, order, 'highpass')

    def bandPassButterworth(self, fc, order=1):
        ''' Applies a high-pass Butterworth filter to the signal.

        Side effects: the waveform will be resampled to have equally-sampled points.

        Args:
            fc (length-2 float sequence): cutoff frequency of the filter

        Returns:
            New object containing the filtered waveform
        '''

        return self.butterworthFilter(fc, order, 'bandpass')

    def deleteSegment(self, segment):
        ''' Removes the specified segment from the abscissa.

            This means calling within this segment will give the first-order interpolation of its edges.

            Usually, deleting is followed by splicing in some new data in this span

            Args:
                segment (list[float,float]): span over which to delete stored points

            Returns:
                MeasuredFunction: new object
        '''
        nonNullInds = np.logical_or(self.absc < min(segment), self.absc > max(segment))
        newAbsc = self.absc[nonNullInds]
        return self._newOfSameSubclass(newAbsc, self(newAbsc))

    def splice(self, other, segment=None):
        ''' Returns a Spectrum that is this one,
            except with the segment replaced with the other one's data

            The abscissa of the other matters.
            There is nothing changing (abscissa, ordinate) point pairs,
            only moving them around from ``other`` to ``self``.

            If segment is not specified, uses the full domain of the other

            Args:
                other (MeasuredFunction): the origin of new data
                segment (list[float,float]): span over which to do splice stored points

            Returns:
                MeasuredFunction: new object
        '''
        if segment is None:
            segment = other.getSpan()
        spliceInds = np.logical_and(self.absc > min(segment), self.absc < max(segment))
        newOrdi = self.ordi.copy()
        newOrdi[spliceInds] = other(self.absc[spliceInds])
        return self._newOfSameSubclass(self.absc, newOrdi)

    def invert(self, yVals, directionToDescend=None):
        ''' Descends down the function until yVal is reached in ordi. Returns the absc value

            If the function is peaked, you should specify a direction to descend.

            If the function is approximately monotonic, don't worry about it.

            Args:
                yVals (scalar, ndarray): array of y values to descend to
                directionToDescend (['left', 'right', None]): use if peaked function to tell which side.
                    Not used if monotonic

            Returns:
                (scalar, ndarray): corresponding x values
        '''
        maxInd = np.argmax(self.ordi)
        minInd = np.argmin(self.ordi)
        if directionToDescend is None:
            if minInd < maxInd:
                directionToDescend = 'left'
            else:
                directionToDescend = 'right'
        if np.isscalar(yVals):
            yValArr = np.array([yVals])
        else:
            yValArr = yVals
        xValArr = np.zeros(yValArr.shape)
        for iVal, y in enumerate(yValArr):
            xValArr[iVal] = interpInverse(*self.getData(),
                                          startIndex=maxInd,
                                          direction=directionToDescend,
                                          threshVal=y)
        if np.isscalar(yVals):
            return xValArr[0]
        else:
            return xValArr

    def centerOfMass(self):
        ''' Returns abscissa point where mass is centered '''
        deb = self.debias().clip(0, None)
        weighted = np.multiply(*deb.getData())
        com = np.sum(weighted) / np.sum(deb.ordi)
        return com

    def moment(self, order=2, relativeGauss=False):
        ''' The order'th moment of the function

            Args:
                order (integer): the polynomial moment of inertia. Don't trust the normalization of > 2'th order.
                    order = 1: mean
                    order = 2: variance
                    order = 3: skew
                    order = 4: kurtosis

            Returns:
                (float): the specified moment
        '''
        mean = np.mean(self.ordi)
        if order == 1:
            return mean
        variance = np.mean(np.power(self.ordi - mean, 2))
        if order == 2:
            return variance
        std = np.sqrt(variance)
        if order == 3:
            skew = np.mean(np.power(self.ordi - mean, 3))
            skew /= std ** 3
            return skew
        if order == 4:
            kurtosis = np.mean(np.power(self.ordi - mean, 4))
            kurtosis /= variance ** 2
            if relativeGauss:
                kurtosis -= 3
            return kurtosis
        # Generic fallback for higher orders
        return np.mean(np.power(self.ordi - mean, order)) / std ** order

    def findResonanceFeatures(self, **kwargs):
        r''' A convenient wrapper for :func:`~lightlab.util.data.peaks.findPeaks`

            Args:
                \*\*kwargs: passed to :func:`~lightlab.util.data.peaks.findPeaks`

            Returns:
                list[ResonanceFeature]: the detected features as nice objects
        '''
        mFun = self.uniformlySample()
        dLam = np.diff(mFun.getSpan())[0] / len(mFun)

        xArr, yArr = mFun.getData()

        # Use the class-free peakfinder on arrays
        pkInds, pkIndWids = findPeaks(yArr, **kwargs)

        # Translate back into units of the original MeasuredFunction
        pkLambdas = xArr[pkInds]
        pkAmps = yArr[pkInds]
        pkWids = pkIndWids * dLam

        # Package into resonance objects
        try:
            isPeak = kwargs['isPeak']
        except KeyError:
            isPeak = True
        resonances = np.empty(len(pkLambdas), dtype=object)
        for iPk in range(len(resonances)):
            resonances[iPk] = ResonanceFeature(
                pkLambdas[iPk], pkWids[iPk], pkAmps[iPk], isPeak=isPeak)
        return resonances

    # Mathematics

    def _binMathHelper(self, other):
        ''' returns the new abcissa and a tuple of arrays: the ordinates to operate on
        '''
        try:
            ab = other.absc
        except AttributeError:  # in other.absc
            pass
        else:
            if np.all(ab == self.absc):
                newAbsc = self.absc
                ords = (self.ordi, other.ordi)
            else:
                newAbsc = type(self)._minAbsc(self, other)
                ords = (self(newAbsc), other(newAbsc))
            return newAbsc, ords

        newAbsc = self.absc
        try:
            other = float(other)
        except TypeError:  # not an int, float, or np.ndarry with all singleton dimensions
            pass
        else:
            ords = (self.ordi, other * np.ones(len(newAbsc)))
            return newAbsc, ords

        try:
            othOrd = other(newAbsc)
        except TypeError:  # not callable
            pass
        else:
            ords = (self.ordi, othOrd)
            return newAbsc, ords

        # time to fail
        if isinstance(other, np.ndarray):
            raise TypeError('Cannot do binary math with MeasuredFunction and numpy array')
        for obj in (self, other):
            if isinstance(obj.ordi, MeasuredFunction):
                raise TypeError('You have an ordinate that is a MeasuredFunction!' +
                                ' This is a common error. It\'s in ' + str(obj))
        raise TypeError('Unsupported types for binary math: ' +
                        type(self).__name__ + ', ' + type(other).__name__)

    def norm(self, ord=None):
        # TODO recompute norm taking into account the possibility that the
        # abscissa is not uniformly sampled.
        return np.linalg.norm(self.ordi - np.mean(self.ordi), ord=ord)

    @staticmethod
    def _minAbsc(fa, fb):
        ''' Get the overlapping abscissa of two MeasuredFunctions.
        '''
        fa_span = fa.getSpan()
        fb_span = fb.getSpan()

        min_absc, max_absc = [max(fa_span[0], fb_span[0]), min(fa_span[1], fb_span[1])]
        dxa = np.mean(np.abs(np.diff(np.sort(fa.absc))))
        dxb = np.mean(np.abs(np.diff(np.sort(fb.absc))))
        new_dx = min(dxa, dxb)

        newAbsc = np.arange(min_absc, max_absc + new_dx, new_dx)
        return newAbsc

    @staticmethod
    def _maxAbsc(fa, fb):
        """ Gets a compact abscissa that includes the domains of both fa and fb.

            Assumes that the returned abscissa is uniformly sampled.
            self.correlate depends on this assumption.
        """
        fa_span = fa.getSpan()
        fb_span = fb.getSpan()

        min_absc, max_absc = [min(fa_span[0], fb_span[0]), max(fa_span[1], fb_span[1])]
        dxa = np.mean(np.abs(np.diff(np.sort(fa.absc))))
        dxb = np.mean(np.abs(np.diff(np.sort(fb.absc))))
        new_dx = min(dxa, dxb)

        newAbsc = np.arange(min_absc, max_absc + new_dx, new_dx)
        return newAbsc

    def __sub__(self, other):
        ''' Returns the subtraction of the two functions, in the domain of the shortest abscissa object.
        The other object can also be a scalar '''
        newAbsc, ords = self._binMathHelper(other)
        return self._newOfSameSubclass(newAbsc, ords[0] - ords[1])

    def __rsub__(self, other):
        newAbsc, ords = self._binMathHelper(other)
        return self._newOfSameSubclass(newAbsc, ords[1] - ords[0])

    def __add__(self, other):
        ''' Returns the addition of the two functions, in the domain of the shortest abscissa object.
        The other object can also be a scalar '''
        newAbsc, ords = self._binMathHelper(other)
        return self._newOfSameSubclass(newAbsc, ords[0] + ords[1])

    def __abs__(self):
        ''' Returns a new object where the abscissa contains the absolute value of the old one.
        '''
        abs_ordi = np.abs(self.ordi)
        return self._newOfSameSubclass(self.absc, abs_ordi)

    def __radd__(self, other):
        return self.__add__(other)

    def __mul__(self, other):
        ''' Returns the product of the two functions, in the domain of the shortest abscissa object.
        The other object can also be a scalar '''
        newAbsc, ords = self._binMathHelper(other)
        return self._newOfSameSubclass(newAbsc, ords[0] * ords[1])

    def __pow__(self, power):
        ''' Returns the result of exponentiation. Can only exponentiate
        with a float number.
        '''

        absc = self.absc.copy()
        ordi = self.ordi.copy()
        try:
            new_ordi = ordi ** power  # uses numpy's power overload
        except ValueError as err:
            raise ValueError("Invalid power {} (not a number)".format(power)) from err

        return self._newOfSameSubclass(absc, new_ordi)

    def __rmul__(self, other):
        return self.__mul__(other)

    def __truediv__(self, other):
        newAbsc, ords = self._binMathHelper(other)
        return self._newOfSameSubclass(newAbsc, ords[0] / ords[1])

    def __rtruediv__(self, other):
        newAbsc, ords = self._binMathHelper(other)
        return self._newOfSameSubclass(newAbsc, ords[1] / ords[0])

    def __neg__(self):
        ''' Returns a new object with negated ordinate. '''
        return self._newOfSameSubclass(self.absc, -self.ordi)

    def __eq__(self, other):
        if isinstance(self, type(other)):
            return np.all(self.absc == other.absc) and np.all(self.ordi == other.ordi)
        return self.ordi == other

    def __repr__(self):
        try:
            return "{}({:d} pts)".format(self.__class__.__qualname__, len(self))
        except TypeError:  # len(self fails)
            return "{}({:f},{:f})".format(self.__class__.__qualname__, self.absc, self.ordi)

    # Analysis methods

    def fft(self):
        ''' Single-sided FFT magnitude spectrum.

            Uniformly resamples the function, computes the real FFT,
            and returns the magnitude as a MeasuredFunction.

            Returns:
                MeasuredFunction: frequency vs magnitude
        '''
        uniform = self.uniformlySample()
        dx = np.diff(uniform.absc[:2])[0]
        N = len(uniform)
        spectrum = np.fft.rfft(uniform.ordi)
        freqs = np.fft.rfftfreq(N, d=dx)
        magnitude = np.abs(spectrum) * 2.0 / N
        magnitude[0] /= 2.0  # DC component not doubled
        return MeasuredFunction(freqs, magnitude)

    def psd(self, nperseg=None):
        ''' Power spectral density via Welch's method.

            Args:
                nperseg (int): segment length for Welch. Defaults to len/8.

            Returns:
                MeasuredFunction: frequency vs power spectral density
        '''
        uniform = self.uniformlySample()
        dx = np.diff(uniform.absc[:2])[0]
        fs = 1.0 / dx
        if nperseg is None:
            nperseg = max(len(uniform) // 8, 8)
        freqs, Pxx = signal.welch(uniform.ordi, fs=fs, nperseg=nperseg)
        return MeasuredFunction(freqs, Pxx)

    def integrate(self, segment=None):
        ''' Numerical integration via the trapezoidal rule.

            Args:
                segment (list[float,float], optional): integration bounds.
                    If None, integrates over the full domain.

            Returns:
                float: the integral value
        '''
        if segment is not None:
            cropped = self.crop(segment)
            return np.trapz(cropped.ordi, cropped.absc)
        return np.trapz(self.ordi, self.absc)

    def cumIntegrate(self):
        ''' Cumulative trapezoidal integration.

            Returns:
                MeasuredFunction: cumulative integral
        '''
        from scipy.integrate import cumulative_trapezoid
        cum = cumulative_trapezoid(self.ordi, self.absc, initial=0)
        return self._newOfSameSubclass(self.absc, cum)

    def derivative(self):
        ''' Numerical differentiation using np.gradient.

            Returns:
                MeasuredFunction: the derivative
        '''
        dydx = np.gradient(self.ordi, self.absc)
        return self._newOfSameSubclass(self.absc, dydx)

    def zeroCrossings(self, level=0.0):
        ''' Find abscissa values where the ordinate crosses a level.

            Linearly interpolates between adjacent points that straddle
            the level.

            Args:
                level (float): the threshold level

            Returns:
                ndarray: abscissa values of crossings
        '''
        shifted = self.ordi - level
        sign_changes = np.where(np.diff(np.sign(shifted)))[0]
        crossings = np.empty(len(sign_changes))
        for i, idx in enumerate(sign_changes):
            x0, x1 = self.absc[idx], self.absc[idx + 1]
            y0, y1 = shifted[idx], shifted[idx + 1]
            crossings[i] = x0 - y0 * (x1 - x0) / (y1 - y0)
        return crossings

    def estimateFrequency(self):
        ''' Estimate the dominant frequency from zero crossings.

            Each pair of consecutive zero crossings is half a period.

            Returns:
                float: estimated frequency
        '''
        crossings = self.zeroCrossings(level=np.mean(self.ordi))
        if len(crossings) < 2:
            return 0.0
        half_periods = np.diff(crossings)
        avg_period = 2.0 * np.mean(half_periods)
        return 1.0 / avg_period

    def histogram(self, bins='auto', density=False):
        ''' Amplitude histogram of the ordinate.

            Args:
                bins: passed to np.histogram
                density (bool): if True, normalize to a probability density

            Returns:
                MeasuredFunction: bin centers vs counts (or density)
        '''
        counts, bin_edges = np.histogram(self.ordi, bins=bins, density=density)
        bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2.0
        return MeasuredFunction(bin_centers, counts.astype(float))


class Spectrum(MeasuredFunction):
    ''' Adds handling of linear/dbm units.

        Use :meth:`lin` and :meth:`dbm` to make sure what you're getting
        what you expect for things like binary math and peakfinding, etc.
    '''

    def __init__(self, nm, power, inDbm=True, unsafe=False):
        '''
            Args:
                nm (array): abscissa
                power (array): ordinate
                inDbm (bool): is the ``power`` in linear or dbm units?
        '''
        super().__init__(nm, power, unsafe=unsafe)
        self._inDbm = inDbm

    @property
    def inDbm(self):
        ''' Is it in dbm units currently?

            Returns:
                bool:
        '''
        try:
            return self._inDbm
        except AttributeError:
            self._inDbm = self._Spectrum__inDbm
            return self._inDbm

    def lin(self):
        ''' The spectrum in linear units

            Returns:
                Spectrum: new object
        '''
        if not self.inDbm:
            return type(self)(self.absc.copy(), self.ordi.copy(), inDbm=False)
        else:
            return type(self)(self.absc.copy(), 10 ** (self.ordi.copy() / 10), inDbm=False)

    def db(self):
        ''' The spectrum in decibel units

            Returns:
                Spectrum: new object
        '''
        if self.inDbm:
            return type(self)(self.absc.copy(), self.ordi.copy(), inDbm=True)
        else:
            clippedOrdi = np.clip(self.ordi, 1e-12, None)
            return type(self)(self.absc.copy(), 10 * np.log10(clippedOrdi), inDbm=True)

    def _binMathHelper(self, other):
        ''' Adds a check to make sure lin/db is in the same state '''
        if type(other) is type(self) and other.inDbm is not self.inDbm:
            raise Exception('Can not do binary math on Spectra in different formats')
        return super()._binMathHelper(other)

    def simplePlot(self, *args, livePlot=False, **kwargs):
        ''' More often then not, this is db vs. wavelength, so label it
        '''
        super().simplePlot(*args, livePlot=livePlot, **kwargs)
        plt.xlabel('Wavelength (nm)')
        plt.ylabel('Transmission ({})'.format('dB' if self.inDbm else 'lin'))

    # Peak and trough related

    def refineResonanceWavelengths(self, filtShapes, seedRes=None, isPeak=None):
        ''' Convolutional resonance correction to get very robust resonance wavelengths

            Does the resonance finding itself, unless an initial approximation is provided.

            Also, has some special options for ``Spectrum`` types to make sure db/lin is optimal

            Args:
                filtShapes (list[MeasuredFunction]): shapes of each resonance. Must be in order of ascending abscissa/wavelength
                seedRes (list[ResonanceFeature]): rough approximation of resonance properties. If None, this method will find them.
                isPeak (bool): required to do peak finding, but not used if ``seedRes`` is specified

            Returns:
                list[ResonanceFeature]: the detected and refined features as nice objects

            Todo:
                take advantage of fft convolution for speed
        '''
        if seedRes is None:
            if isPeak is None:
                raise Exception('If seed resonance is not specified, isPeak must be specified.')
            seedRes = self.findResonanceFeatures(expectedCnt=len(filtShapes), isPeak=isPeak)
        else:
            isPeak = seedRes[0].isPeak
        fineRes = np.array([r.copy() for r in seedRes])

        useFilts = filtShapes.copy()
        if type(self) == Spectrum:
            # For Spectrum objects only
            if isPeak:
                spectFun = self.lin()
            else:
                spectFun = 1 - self.lin()
            for i in range(len(filtShapes)):
                if type(filtShapes[i]).__name__ != 'Spectrum':
                    raise Exception(
                        'If calling object is Spectrum, the filter shapes must also be Spectrum types')
                if isPeak:
                    useFilts[i] = filtShapes[i].lin()
                else:
                    useFilts[i] = 1 - filtShapes[i].lin()
        else:
            spectFun = self

        confidence = 1000
        for i, r in enumerate(fineRes):
            thisFilt = useFilts[i]
            cropWind = max(thisFilt.absc) * np.array([-1, 1])
            subSpect = spectFun.shift(-r.lam).crop(cropWind)
            basis = subSpect.absc
            convArr = np.convolve(subSpect(basis), thisFilt(basis)[::-1], 'same')
            lamOffset = basis[np.argmax(convArr)]
            fineRes[i].lam = r.lam + lamOffset
            thisConf = np.max(convArr) / np.sum(thisFilt(basis) ** 2)
            confidence = min(confidence, thisConf)
        return fineRes, confidence

    def findResonanceFeatures(self, **kwargs):
        r''' Overloads :meth:`.MeasuredFunction.findResonanceFeatures` to make sure it's in db scale

            Args:
                \*\*kwargs: kwargs passed to :mod:`~lightlab.util.data.peaks.findPeaks`

            Returns:
                list[ResonanceFeature]: the detected features as nice objects
        '''
        kwargs['isDb'] = True
        return MeasuredFunction.findResonanceFeatures(self.db(), **kwargs)

    def peakWavelength(self):
        ''' Wavelength at maximum optical power.

            Returns:
                float: wavelength (nm) at the peak
        '''
        return self.absc[np.argmax(self.db().ordi)]

    def bandwidth(self, dB_below_peak=3.0):
        ''' N-dB bandwidth of the spectrum.

            Finds where the dB spectrum crosses (peak - dB_below_peak) and
            returns the width between the first and last crossing.

            Args:
                dB_below_peak (float): dB level below peak to measure bandwidth

            Returns:
                float: bandwidth in nm
        '''
        db_spec = self.db()
        peak_power = np.max(db_spec.ordi)
        threshold = peak_power - abs(dB_below_peak)
        crossings = db_spec.zeroCrossings(level=threshold)
        if len(crossings) < 2:
            return 0.0
        return crossings[-1] - crossings[0]

    def totalPower(self):
        ''' Integrated optical power.

            Returns:
                float: total power (integral of linear spectrum)
        '''
        return self.lin().integrate()

    def osnr(self, signal_bw=0.1, noise_bw=0.1, noise_offset=None):
        ''' Optical signal-to-noise ratio.

            Measures signal power around the peak vs noise power at an offset.

            Args:
                signal_bw (float): bandwidth (nm) around the peak for signal measurement
                noise_bw (float): bandwidth (nm) for noise measurement
                noise_offset (float): offset (nm) from peak for noise measurement.
                    Defaults to 5x signal_bw.

            Returns:
                float: OSNR in dB
        '''
        if noise_offset is None:
            noise_offset = 5.0 * signal_bw
        lin_spec = self.lin()
        peak_nm = self.peakWavelength()

        signal_seg = [peak_nm - signal_bw / 2, peak_nm + signal_bw / 2]
        signal_power = lin_spec.crop(signal_seg).integrate()

        noise_seg = [peak_nm + noise_offset - noise_bw / 2,
                     peak_nm + noise_offset + noise_bw / 2]
        noise_power = lin_spec.crop(noise_seg).integrate()

        if noise_power <= 0:
            return float('inf')
        return 10.0 * np.log10(signal_power / noise_power)

    def GHz(self):
        ''' Convert to SpectrumGHz '''
        GHz = _C_NM_GHZ / self.absc
        sort_idx = np.argsort(GHz)
        return SpectrumGHz(GHz[sort_idx], self.ordi[sort_idx].copy(), inDbm=self.inDbm)

    def __repr__(self):
        fmt = 'dB' if self.inDbm else 'lin'
        try:
            return "{}({:d} pts, {})".format(self.__class__.__qualname__, len(self), fmt)
        except TypeError:
            return "{}({})".format(self.__class__.__qualname__, fmt)


class SpectrumGHz(Spectrum):
    ''' Spectrum with GHz units in the abscissa

    Use :meth:`lin` and :meth:`dbm` to make sure what you're getting
    what you expect for things like binary math and peakfinding, etc.
    '''

    def __init__(self, GHz, power, inDbm=True, unsafe=False):
        '''
            Args:
                GHz (array): abscissa
                power (array): ordinate
                inDbm (bool): is the ``power`` in linear or dbm units?
        '''
        MeasuredFunction.__init__(self, GHz, power, unsafe=unsafe)
        self._inDbm = inDbm

    def simplePlot(self, *args, livePlot=False, **kwargs):
        ''' More often then not, this is db vs. wavelength, so label it
        '''
        super().simplePlot(*args, livePlot=livePlot, **kwargs)
        plt.xlabel('Frequency (GHz)')
        plt.ylabel('Transmission ({})'.format('dB' if self.inDbm else 'lin'))

    def nm(self):
        ''' Convert to Spectrum '''
        nm = _C_NM_GHZ / self.absc
        sort_idx = np.argsort(nm)
        return Spectrum(nm[sort_idx], self.ordi[sort_idx].copy(), inDbm=self.inDbm)


class Waveform(MeasuredFunction):
    ''' Typically used for time, voltage functions.
        This is very similar to what is referred to as a "signal."

        Use the unit attribute to set units different than Volts.

        Has class methods for generating common time-domain signals.

        Supports optional statistical envelopes (min/max/std) for representing
        ensemble measurements. Use :meth:`fromEnsemble` to build from multiple waveforms.
    '''

    unit = None

    def __init__(self, t, v, unit='V', unsafe=False,
                 min_envelope=None, max_envelope=None,
                 std_envelope=None, n_samples=None):
        super().__init__(t, v, unsafe=unsafe)
        self.unit = unit
        self._min_envelope = np.asarray(min_envelope) if min_envelope is not None else None
        self._max_envelope = np.asarray(max_envelope) if max_envelope is not None else None
        self._std_envelope = np.asarray(std_envelope) if std_envelope is not None else None
        self._n_samples = n_samples
        self._raw_bundle = None

    @property
    def has_statistics(self):
        ''' True if any envelope data is present and valid. '''
        return any(self._check_envelope(e) is not None
                   for e in (self._min_envelope, self._max_envelope, self._std_envelope))

    def _check_envelope(self, arr):
        ''' Return arr if it matches current abscissa length, else None. '''
        if arr is not None and len(arr) == len(self.absc):
            return arr
        return None

    @property
    def mean_envelope(self):
        ''' The mean waveform (alias for ordi). '''
        return self.ordi

    @property
    def min_envelope(self):
        return self._check_envelope(self._min_envelope)

    @property
    def max_envelope(self):
        return self._check_envelope(self._max_envelope)

    @property
    def std_envelope(self):
        return self._check_envelope(self._std_envelope)

    @property
    def n_samples(self):
        return self._n_samples

    @property
    def raw_bundle(self):
        return self._raw_bundle

    @classmethod
    def fromEnsemble(cls, waveforms, keep_raw=True, unit='V'):
        ''' Build a Waveform with statistics from an ensemble of waveforms.

            Args:
                waveforms: list of Waveform (or MeasuredFunction), or a FunctionBundle
                keep_raw (bool): if True, store the raw bundle for later access
                unit (str): unit label for the resulting Waveform

            Returns:
                Waveform: with mean as ordi and min/max/std envelopes populated
        '''
        from .two_dim import FunctionBundle
        if isinstance(waveforms, FunctionBundle):
            bundle = waveforms
        else:
            bundle = FunctionBundle(list(waveforms))

        mean_ordi = np.mean(bundle.ordiMat, axis=0).A1
        min_ordi = np.min(bundle.ordiMat, axis=0).A1
        max_ordi = np.max(bundle.ordiMat, axis=0).A1
        std_ordi = np.std(np.asarray(bundle.ordiMat), axis=0).flatten()

        obj = cls(bundle.absc, mean_ordi, unit=unit,
                  min_envelope=min_ordi, max_envelope=max_ordi,
                  std_envelope=std_ordi, n_samples=bundle.nDims)
        if keep_raw:
            obj._raw_bundle = bundle
        return obj

    def simplePlot(self, *args, livePlot=False, show_envelope=True,
                   envelope_alpha=0.2, envelope_style='minmax', **kwargs):
        ''' Plot the waveform, optionally with shaded envelope.

            Args:
                show_envelope (bool): draw min/max or std shading if statistics are present
                envelope_alpha (float): transparency of the shaded region
                envelope_style (str): 'minmax' or 'std'
        '''
        curve = super().simplePlot(*args, livePlot=False, **kwargs)
        ax = plt.gca()
        ax.set_xlabel('Time (s)')
        ax.set_ylabel('Amplitude ({})'.format(self.unit))

        if show_envelope and self.has_statistics and curve:
            color = curve[0].get_color()
            if envelope_style == 'minmax' and self.min_envelope is not None and self.max_envelope is not None:
                ax.fill_between(self.absc, self.min_envelope, self.max_envelope,
                                color=color, alpha=envelope_alpha)
            elif envelope_style == 'std' and self.std_envelope is not None:
                ax.fill_between(self.absc, self.ordi - self.std_envelope,
                                self.ordi + self.std_envelope,
                                color=color, alpha=envelope_alpha)

        if livePlot:
            display.display(plt.gcf())
            display.clear_output(wait=True)
        return curve

    def __repr__(self):
        try:
            return "{}({:d} pts, {})".format(self.__class__.__qualname__, len(self), self.unit)
        except TypeError:
            return "{}({})".format(self.__class__.__qualname__, self.unit)

    @classmethod
    def pulse(cls, tArr, tOn, tOff):
        vForm = np.zeros(len(tArr))
        vForm[tArr > tOn] = 1.
        vForm[tArr > tOff] = 0.
        return cls(tArr, vForm)

    @classmethod
    def whiteNoise(cls, tArr, rmsPow):
        vForm = np.random.randn(len(tArr))
        firstRms = rms(vForm)
        return cls(tArr, vForm * np.sqrt(rmsPow / firstRms))

    @classmethod
    def nrz(cls, order=7, baud_rate=1e9, n_symbols=None, samples_per_symbol=64):
        ''' Generate an NRZ (Non-Return-to-Zero) PRBS waveform.

            Args:
                order (int): PRBS order (7, 9, 11, 15, 23, or 31)
                baud_rate (float): symbol rate in Hz
                n_symbols (int): number of bits. Defaults to 2^order - 1 (one full period)
                samples_per_symbol (int): time-domain samples per bit

            Returns:
                Waveform: NRZ waveform with values in {0, 1}
        '''
        if order not in _PRBS_POLYNOMIALS:
            raise ValueError('Unsupported PRBS order {}. '
                             'Supported: {}'.format(order, sorted(_PRBS_POLYNOMIALS)))
        polynomial = _PRBS_POLYNOMIALS[order]
        seed = (1 << order) - 1
        bits = prbs_pattern(polynomial, seed, length=n_symbols)

        v = np.repeat(bits.astype(float), samples_per_symbol)
        dt = 1.0 / (baud_rate * samples_per_symbol)
        t = np.arange(len(v)) * dt
        return cls(t, v, unit='a.u.')

    @classmethod
    def pam(cls, n_levels=4, order=7, baud_rate=1e9, n_symbols=None, samples_per_symbol=64):
        ''' Generate a PAM-N (Pulse Amplitude Modulation) PRBS waveform.

            Groups PRBS bits into log2(n_levels) bits per symbol, mapping
            each group to one of n_levels equally-spaced amplitude levels.

            Args:
                n_levels (int): number of amplitude levels (must be a power of 2, e.g. 4 for PAM-4)
                order (int): PRBS order (7, 9, 11, 15, 23, or 31)
                baud_rate (float): symbol rate in Hz
                n_symbols (int): number of PAM symbols. Defaults to (2^order - 1) // bits_per_symbol
                samples_per_symbol (int): time-domain samples per symbol

            Returns:
                Waveform: PAM-N waveform with values normalized to [0, 1]
        '''
        bits_per_symbol = int(np.log2(n_levels))
        if 2 ** bits_per_symbol != n_levels:
            raise ValueError('n_levels must be a power of 2, got {}'.format(n_levels))
        if order not in _PRBS_POLYNOMIALS:
            raise ValueError('Unsupported PRBS order {}. '
                             'Supported: {}'.format(order, sorted(_PRBS_POLYNOMIALS)))

        polynomial = _PRBS_POLYNOMIALS[order]
        seed = (1 << order) - 1

        if n_symbols is None:
            n_bits = 2 ** order - 1
        else:
            n_bits = n_symbols * bits_per_symbol
        bits = prbs_pattern(polynomial, seed, length=n_bits)

        # Trim to a multiple of bits_per_symbol
        n_bits_used = (len(bits) // bits_per_symbol) * bits_per_symbol
        bits = bits[:n_bits_used]

        # Group bits into symbols and compute integer level
        bit_groups = bits.reshape(-1, bits_per_symbol)
        powers = 2 ** np.arange(bits_per_symbol)[::-1]
        symbols = bit_groups.astype(int) @ powers

        # Normalize to [0, 1]
        levels = symbols / (n_levels - 1)

        v = np.repeat(levels, samples_per_symbol)
        dt = 1.0 / (baud_rate * samples_per_symbol)
        t = np.arange(len(v)) * dt
        return cls(t, v, unit='a.u.')

    # Analysis methods

    def foldToEye(self, symbol_period, n_symbols=None):
        ''' Fold the waveform into an eye diagram.

            Each symbol period becomes a separate trace in a FunctionBundle.

            Args:
                symbol_period (float): duration of one symbol in seconds
                n_symbols (int): number of symbols to fold. Defaults to all complete symbols.

            Returns:
                FunctionBundle: each element is one symbol period
        '''
        from .two_dim import FunctionBundle
        t0 = self.absc[0]
        total_duration = self.absc[-1] - t0
        max_symbols = int(total_duration / symbol_period)
        if n_symbols is None:
            n_symbols = max_symbols
        else:
            n_symbols = min(n_symbols, max_symbols)

        traces = []
        eye_t = np.linspace(0, symbol_period, int(symbol_period / np.mean(np.diff(self.absc))) + 1)
        for i in range(n_symbols):
            start = t0 + i * symbol_period
            end = start + symbol_period
            segment = self.crop([start, end])
            # Remap to [0, symbol_period]
            trace = MeasuredFunction(segment.absc - start, segment.ordi)
            traces.append(MeasuredFunction(eye_t, trace(eye_t)))
        return FunctionBundle(traces)

    def _transitionTime(self, low_pct, high_pct, rising):
        ''' Helper for rise/fall time measurement.

            Args:
                low_pct (float): lower threshold fraction (0-1)
                high_pct (float): upper threshold fraction (0-1)
                rising (bool): True for rise time, False for fall time

            Returns:
                float: transition time
        '''
        lo = np.min(self.ordi)
        hi = np.max(self.ordi)
        amplitude = hi - lo
        low_level = lo + low_pct * amplitude
        high_level = lo + high_pct * amplitude

        low_crossings = self.zeroCrossings(level=low_level)
        high_crossings = self.zeroCrossings(level=high_level)

        if len(low_crossings) == 0 or len(high_crossings) == 0:
            return 0.0

        times = []
        if rising:
            for lc in low_crossings:
                # Find the next high crossing after this low crossing
                candidates = high_crossings[high_crossings > lc]
                if len(candidates) > 0:
                    times.append(candidates[0] - lc)
        else:
            for hc in high_crossings:
                # Find the next low crossing after this high crossing
                candidates = low_crossings[low_crossings > hc]
                if len(candidates) > 0:
                    times.append(candidates[0] - hc)

        if len(times) == 0:
            return 0.0
        return np.median(times)

    def riseTime(self, low_pct=0.1, high_pct=0.9):
        ''' Measure the 10-90% (or custom) rise time.

            Returns the median rise time across all detected rising edges.

            Args:
                low_pct (float): lower threshold as fraction of amplitude
                high_pct (float): upper threshold as fraction of amplitude

            Returns:
                float: rise time in abscissa units
        '''
        return self._transitionTime(low_pct, high_pct, rising=True)

    def fallTime(self, low_pct=0.1, high_pct=0.9):
        ''' Measure the 10-90% (or custom) fall time.

            Returns the median fall time across all detected falling edges.

            Args:
                low_pct (float): lower threshold as fraction of amplitude
                high_pct (float): upper threshold as fraction of amplitude

            Returns:
                float: fall time in abscissa units
        '''
        return self._transitionTime(low_pct, high_pct, rising=False)

    def snr(self):
        ''' Signal-to-noise ratio in dB.

            Computed as 20*log10(mean / std) on the ordinate.

            Returns:
                float: SNR in dB
        '''
        mean_val = np.mean(self.ordi)
        std_val = np.std(self.ordi)
        if std_val == 0:
            return float('inf')
        return 20.0 * np.log10(abs(mean_val) / std_val)

    def qFactor(self, n_levels=2):
        ''' Q-factor from histogram level separation.

            Uses histogram peak detection to find level means and standard
            deviations. For a 2-level signal, Q = (mu1 - mu0) / (sigma0 + sigma1).

            Args:
                n_levels (int): number of amplitude levels (default 2 for NRZ)

            Returns:
                float: Q-factor (linear)
        '''
        from scipy.signal import find_peaks as sp_find_peaks

        hist = self.histogram(bins=100, density=True)
        # Find peaks in the histogram
        peak_indices, _ = sp_find_peaks(hist.ordi, distance=len(hist) // (n_levels + 1))

        if len(peak_indices) < 2:
            # Fallback: split ordinate at midpoint
            mid = (np.min(self.ordi) + np.max(self.ordi)) / 2.0
            low_vals = self.ordi[self.ordi < mid]
            high_vals = self.ordi[self.ordi >= mid]
            if len(low_vals) == 0 or len(high_vals) == 0:
                return 0.0
            mu0, sigma0 = np.mean(low_vals), np.std(low_vals)
            mu1, sigma1 = np.mean(high_vals), np.std(high_vals)
        else:
            # Use the two most prominent peaks
            peak_centers = hist.absc[peak_indices]
            sorted_centers = np.sort(peak_centers)
            boundaries = (sorted_centers[:-1] + sorted_centers[1:]) / 2.0

            # For 2-level: split at boundary
            boundary = boundaries[0]
            low_vals = self.ordi[self.ordi < boundary]
            high_vals = self.ordi[self.ordi >= boundary]
            mu0, sigma0 = np.mean(low_vals), np.std(low_vals)
            mu1, sigma1 = np.mean(high_vals), np.std(high_vals)

        denom = sigma0 + sigma1
        if denom == 0:
            return float('inf')
        return abs(mu1 - mu0) / denom

    def estimateBER(self, n_levels=2):
        ''' Estimate bit error rate from Q-factor.

            BER = 0.5 * erfc(Q / sqrt(2))

            Args:
                n_levels (int): number of amplitude levels

            Returns:
                float: estimated BER
        '''
        from scipy.special import erfc
        Q = self.qFactor(n_levels=n_levels)
        if Q == float('inf'):
            return 0.0
        return 0.5 * erfc(Q / np.sqrt(2.0))
