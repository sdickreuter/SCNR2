import sys

import matplotlib.pyplot as plt
import numpy as np
import progress
import scipy.optimize as opt
from PyQt5.QtCore import pyqtSlot, QThread, pyqtSignal, QObject
from scipy.signal import savgol_filter


#  modified from: http://stackoverflow.com/questions/21566379/fitting-a-2d-gaussian-function-using-scipy-optimize-curve-fit-valueerror-and-m#comment33999040_21566831
def gauss2D(pos, amplitude, xo, yo, fwhm, offset):
    sigma = fwhm / 2.3548
    xo = float(xo)
    yo = float(yo)
    g = offset + amplitude * np.exp(
        -(np.power(pos[0] - xo, 2.) + np.power(pos[1] - yo, 2.)) / (2 * np.power(sigma, 2.)))
    return g.ravel()


def gauss(x, amplitude, xo, fwhm, offset):
    sigma = fwhm / 2.3548
    xo = float(xo)
    g = offset + amplitude * np.exp(-np.power(x - xo, 2.) / (2 * np.power(sigma, 2.)))
    return g.ravel()


def smooth(x, y):
    buf = y.copy()
    buf = savgol_filter(buf, 137, 1, mode='interp')
    buf = savgol_filter(buf, 137, 1, mode='interp')

    ind1 = np.linspace(300, 319, 20, dtype=np.int)
    ind2 = np.linspace(1003, 1023, 10, dtype=np.int)
    slope = (np.mean(buf[ind2]) - np.mean(buf[ind1])) / (np.mean(x[ind2]) - np.mean(x[ind1]))
    intercept = np.mean(buf[ind1]) - slope * np.mean(x[ind1])
    l = slope * x + intercept
    buf = np.subtract(buf, l)
    buf = buf * gauss(x, 1, 600, 500, 0)

    return buf


class MeasurementThread(QObject):
    specSignal = pyqtSignal(np.ndarray)
    progressSignal = pyqtSignal(float, str)
    finishSignal = pyqtSignal(np.ndarray)


    def __init__(self, spectrometer, parent=None):
        if getattr(self.__class__, '_has_instance', False):
            RuntimeError('Cannot create another instance')
            #return None
        self.__class__._has_instance = True
        try:
            super(MeasurementThread, self).__init__(parent)
            self.spectrometer = spectrometer
            self.abort = False
            self.thread = QThread(parent)
            self.moveToThread(self.thread)
            self.thread.started.connect(self.process)
            #self.thread.finished.connect(self.stop)
        except:
            (type, value, traceback) = sys.exc_info()
            sys.excepthook(type, value, traceback)
        self.spec = np.zeros(self.spectrometer._width)

    def start(self):
        self.thread.start()

    @pyqtSlot()
    def stop(self):
        self.abort = True
        self.thread.quit()
        self.thread.wait(5000)

    def __del__(self):
        self.__class__.has_instance = False

    def work(self):
        self.specSignal.emit(self.spec)

    @pyqtSlot()
    def process(self):
        while not self.abort:
            try:
                self.spec = self.spectrometer.TakeSingleTrack()
                self.work()
            except:
                (type, value, traceback) = sys.exc_info()
                sys.excepthook(type, value, traceback)


class ImageThread(MeasurementThread):

    @pyqtSlot()
    def process(self):
        while not self.abort:
            try:
                self.spec = self.spectrometer.TakeImageofSlit()
                self.work()
            except:
                (type, value, traceback) = sys.exc_info()
                sys.excepthook(type, value, traceback)


class MeanThread(MeasurementThread):
    def __init__(self, spectrometer, number_of_samples, parent=None):
        self.number_of_samples = number_of_samples
        super(MeanThread, self).__init__(spectrometer)
        self.init()

    def init(self):
        self.progress = progress.Progress(max=self.number_of_samples)
        self.mean = np.zeros(self.spectrometer._width)
        self.i = 0
        self.abort = False

    def work(self):
        self.mean = (self.mean + self.spec)  # / 2
        self.progress.next()
        self.progressSignal.emit(self.progress.percent, str(self.progress.eta_td))
        self.i += 1
        self.specSignal.emit(self.mean / (self.i + 1))
        if self.i >= (self.number_of_samples-1):
            self.progressSignal.emit(100, str(self.progress.eta_td))
            self.finishSignal.emit(self.mean / (self.number_of_samples))
            self.stop()

class LockinThread(MeasurementThread):
    def __init__(self, spectrometer, settings, stage, parent=None):
        self.number_of_samples = settings.number_of_samples
        self.stage = stage
        self.settings = settings
        super(MeanThread, self).__init__(spectrometer)
        self.init()

    def init(self):
        self.progress = progress.Progress(max=self.number_of_samples)
        self.lockin = np.zeros((self.spectrometer._width, self.number_of_samples), dtype=np.float)
        self.i = 0
        self.stage.query_pos()
        self.startpos = self.stage.last_pos()
        self.abort = False

    def move_stage(self, dist):
        x = self.startpos[0] + self.settings.amplitude / 2 * dist * self.settings.direction_x
        y = self.startpos[1] + self.settings.amplitude / 2 * dist * self.settings.direction_y
        z = self.startpos[2] + self.settings.amplitude / 2 * dist * self.settings.direction_z
        # print "X: {0:+8.4f} | Y: {1:8.4f} | Z: {2:8.4f} || X: {3:+8.4f} | Y: {4:8.4f} | Z: {5:8.4f}".format(x,y,z,self._startx,self._starty,self._startz)
        self.stage.moveabs(x=x, y=y, z=z)

    def calc_lockin(self):
        res = np.zeros(self.spectrometer._width)
        for i in range(self.spectrometer._width):
            ref = np.cos(2 * np.pi * np.arange(0, self.number_of_samples) * self.settings.f)
            buf = ref * self.lockin[:, 1]
            buf = np.sum(buf)
            res[i] = buf
        return res

    def work(self):

        ref = np.cos(2 * np.pi * self.i * self.settings.f)
        self.move_stage(ref / 2)
        spec = self._spectrometer.intensities(correct_nonlinearity=True)
        self.lockin[:, self.i] = spec

        self.specSignal.emit(self.lockin[:, self.i])
        self.progress.next()
        self.progressSignal.emit(self.progress.percent, str(self.progress.eta_td))
        self.i += 1
        if self.i >= self.number_of_samples:
            self.progressSignal.emit(100, str(self.progress.eta_td))
            self.finishSignal.emit(self.mean / (self.number_of_samples))
            self.stop()

class SearchThread(MeasurementThread):
    def __init__(self, spectrometer, settings, stage, parent=None):
        try:
            self.settings = settings
            self.stage = stage
            super(SearchThread, self).__init__(spectrometer)
            self.wl = self.spectrometer.GetWavelength()
        except:
            (type, value, traceback) = sys.exc_info()
            sys.excepthook(type, value, traceback)

    @pyqtSlot()
    def process(self):
        while True:
            if self.abort:
                return
            try:
                self.work()
            except:
                (type, value, traceback) = sys.exc_info()
                sys.excepthook(type, value, traceback)

    def work(self):
        self.search()
        x, y, z = self.stage.last_pos()
        self.finishSignal.emit(np.array([x, y]))
        self.stop()

    def stop(self):
        super(SearchThread, self).stop()

    def search(self):
        # self.mutex.lock()
        self.spectrometer.SetExposureTime(self.settings.search_integration_time / 1000)
        # self.mutex.unlock()
        spec = self.spectrometer.TakeSingleTrack()
        spec = np.mean(spec,1)
        spec = smooth(self.wl, spec)

        self.stage.query_pos()
        startpos = self.stage.last_pos()

        minval = np.min(spec)
        maxval = np.max(spec)

        d = np.linspace(-self.settings.rasterwidth, self.settings.rasterwidth, self.settings.rasterdim)

        repetitions = 4
        self.progress = progress.Progress(max=repetitions)
        for j in range(repetitions):
            self.stage.query_pos()
            origin = self.stage.last_pos()
            measured = np.zeros(self.settings.rasterdim)
            if j is 4:
                d /= 2
            if j % 2:
                pos = d + origin[0]
            else:
                pos = d + origin[1]

            for k in range(len(pos)):
                if j % 2:
                    self.stage.moveabs(x=pos[k])
                else:
                    self.stage.moveabs(y=pos[k])
                if self.abort:
                    self.stage.moveabs(x=startpos[0], y=startpos[1])
                    return False
                spec = self.spectrometer.TakeSingleTrack()
                # spec = smooth(self.wl, spec)
                self.specSignal.emit(spec)
                # measured[k] = np.max(spec[400:800])
                measured[k] = np.sum(spec)

            maxind = np.argmax(measured[2:(len(pos))])

            initial_guess = (maxval - minval, pos[maxind], self.settings.sigma, minval)
            dx = origin[0]
            dy = origin[1]
            popt = None
            fitted = False
            try:
                popt, pcov = opt.curve_fit(gauss, pos[2:(len(pos))], measured[2:(len(pos))], p0=initial_guess)
                # popt, pcov = opt.curve_fit(gauss, pos, measured, p0=initial_guess)
                perr = np.diag(pcov)
                # print(perr)
                if perr[0] > 10000 or perr[1] > 1 or perr[2] > 1:
                    print("Could not determine particle position: Variance too big")
                elif popt[0] < 1e-1:
                    print("Could not determine particle position: Peak too small")
                elif popt[1] < (min(pos) - 0.5) or popt[1] > (max(pos) + 0.5):
                    print("Could not determine particle position: Peak outside bounds")
                else:
                    fitted = True
            except RuntimeError as e:
                print(e)
                print("Could not determine particle position: Fit error")

            if fitted:
                if j % 2:
                    dx = float(popt[1])
                else:
                    dy = float(popt[1])

            self.stage.moveabs(x=dx, y=dy)
            fig = plt.figure()
            ax = fig.add_subplot(111)
            ax.plot(pos, measured, 'bo')
            x = np.linspace(min(pos), max(pos))
            if not popt is None:
                ax.text(0.1, 0.9, str(popt[1]) + ' +- ' + str(perr[1]), ha='left', va='center', transform=ax.transAxes)
                ax.plot(x, gauss(x, popt[0], popt[1], popt[2], popt[3]), 'g-')
            plt.savefig("search_max/search" + str(j) + ".png")
            plt.close()
            self.progress.next()
            self.progressSignal.emit(self.progress.percent, str(self.progress.eta_td))
        self.spectrometer.SetExposureTime(self.settings.integration_time / 1000)
        # self.stage.query_pos()
        # spec = self.getspec()
        # self.specSignal.emit(spec)


class ScanThread(MeasurementThread):
    def __init__(self, spectrometer, settings, scanning_points, stage, parent=None):
        try:
            self.spectrometer = spectrometer
            self.scanning_points = scanning_points
            self.settings = settings
            self.stage = stage
            self.i = 0
            self.n = scanning_points.shape[0]
            self.positions = np.zeros((self.n, 2))
            self.progress = progress.Progress(max=self.n)
            super(ScanThread, self).__init__(spectrometer)
        except:
            (type, value, traceback) = sys.exc_info()
            sys.excepthook(type, value, traceback)

    def intermediatework(self):
        pass

    def work(self):
        self.stage.moveabs(x=self.scanning_points[self.i, 0], y=self.scanning_points[self.i, 1])
        self.intermediatework()
        x, y, z = self.stage.last_pos()
        self.positions[self.i, 0] = x
        self.positions[self.i, 1] = y
        self.progress.next()
        self.progressSignal.emit(self.progress.percent, str(self.progress.eta_td))
        self.i += 1
        if self.i >= self.n:
            # plt.plot(self.scanning_points[:, 0], self.scanning_points[:, 1], "r.")
            # plt.plot(self.positions[:, 0], self.positions[:, 1], "bx")
            # plt.savefig("search_max/grid.png")
            # plt.close()
            self.progressSignal.emit(100, str(self.progress.eta_td))
            self.finishSignal.emit(self.positions)
            self.stop()
            # self.spec = self.getspec()
            # self.specSignal.emit(self.spec)


class ScanSearchThread(ScanThread):
    def __init__(self, spectrometer, settings, scanning_points, stage, parent=None):
        super(ScanSearchThread, self).__init__(spectrometer, settings, scanning_points, stage)
        self.searchthread = SearchThread(self.spectrometer, self.settings, self.stage, self)
        self.searchthread.specSignal.connect(self.specslot)

    def stop(self):
        self.searchthread.stop()
        super(ScanSearchThread, self).stop()

    def __del__(self):
        self.searchthread.specSignal.disconnect(self.specslot)
        super(ScanSearchThread, self).__del__()

    def intermediatework(self):
        self.searchthread.search()

    @pyqtSlot(np.ndarray)
    def specslot(self, spec):
        self.specSignal.emit(spec)


class ScanLockinThread(ScanThread):
    saveSignal = pyqtSignal(np.ndarray, str, np.ndarray, bool, bool)

    def __init__(self, spectrometer, settings, scanning_points, stage, parent=None):
        super(ScanMeanThread, self).__init__(spectrometer, settings, scanning_points, stage)
        # __init__(self, spectrometer, settings, stage, parent=None)
        self.meanthread = LockinThread(spectrometer, settings, stage, self)
        self.meanthread.finishSignal.connect(self.lockinfinished)
        self.meanthread.specSignal.connect(self.specslot)

    def stop(self):
        self.meanthread.stop()
        super(ScanMeanThread, self).stop()

    def __del__(self):
        self.meanthread.finishSignal.disconnect(self.lockinfinished)
        self.meanthread.specSignal.disconnect(self.specslot)
        self.saveSignal.disconnect()
        super(ScanMeanThread, self).__del__()

    def intermediatework(self):
        self.meanthread.init()
        self.meanthread.process()

    @pyqtSlot(np.ndarray)
    def specslot(self, spec):
        self.specSignal.emit(spec)

    @pyqtSlot(np.ndarray)
    def lockinfinished(self, spec):
        self.saveSignal.emit(self.lockin, str(self.i).zfill(5) + "_lockin.csv", self.positions[self.i, :], False, False)


class ScanMeanThread(ScanThread):
    saveSignal = pyqtSignal(np.ndarray, str, np.ndarray, bool, bool)

    def __init__(self, spectrometer, settings, scanning_points, stage, parent=None):
        super(ScanMeanThread, self).__init__(spectrometer, settings, scanning_points, stage)
        self.meanthread = MeanThread(spectrometer, settings.number_of_samples, self)
        self.meanthread.finishSignal.connect(self.meanfinished)
        self.meanthread.specSignal.connect(self.specslot)

    def stop(self):
        self.meanthread.stop()
        super(ScanMeanThread, self).stop()

    def __del__(self):
        self.meanthread.finishSignal.disconnect(self.meanfinished)
        self.meanthread.specSignal.disconnect(self.specslot)
        self.saveSignal.disconnect()
        super(ScanMeanThread, self).__del__()

    def intermediatework(self):
        self.meanthread.init()
        self.meanthread.process()

    @pyqtSlot(np.ndarray)
    def specslot(self, spec):
        self.specSignal.emit(spec)

    @pyqtSlot(np.ndarray)
    def meanfinished(self, spec):
        self.saveSignal.emit(spec, str(self.i).zfill(5) + ".csv", self.positions[self.i, :], False, False)


class ScanSearchMeanThread(ScanMeanThread):
    def __init__(self, spectrometer, settings, scanning_points, stage, parent=None):
        super(ScanSearchMeanThread, self).__init__(spectrometer, settings, scanning_points, stage)
        self.searchthread = SearchThread(self.spectrometer, self.settings, self.stage, self)
        self.searchthread.specSignal.connect(self.specslot)

    def stop(self):
        self.searchthread.stop()
        super(ScanMeanThread, self).stop()

    def __del__(self):
        self.searchthread.specSignal.disconnect()
        super(ScanMeanThread, self).__del__()

    def intermediatework(self):
        self.searchthread.search()
        self.meanthread.init()
        self.meanthread.process()
