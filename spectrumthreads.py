import sys

import matplotlib.pyplot as plt
import numpy as np
import progress
import scipy.optimize as opt
from PyQt5.QtCore import pyqtSlot, QThread, pyqtSignal, QObject
from scipy.signal import savgol_filter
import time

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
    #buf = np.subtract(buf, l)
    #buf = buf * gauss(x, 1, 600, 500, 0)

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
        print("New "+ self.__class__.__name__ +" created: "+str(id(self)))

    def start(self):
        self.thread.start()

    @pyqtSlot()
    def stop(self):
        self.abort = True
        #self.spectrometer.AbortAcquisition()

        self.thread.wait(self.spectrometer.exposure_time*1000+500)
        #self.thread.quit()
        #print("Done with thread")

    def __del__(self):
        self.__class__.has_instance = False

    def work(self):
        pass

    @pyqtSlot()
    def process(self):
        while not self.abort:
            try:
                self.work()
            except:
                (type, value, traceback) = sys.exc_info()
                sys.excepthook(type, value, traceback)
                self.stop()

class LiveThread(MeasurementThread):

    def work(self):
        try:
            self.specSignal.emit(self.spec)
        except TypeError as e:
            print(e)
            print("Communication out of sync, try again")

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

    def work(self):
        try:
            self.specSignal.emit(self.spec)
        except TypeError as e:
            print(e)
            print("Communication out of sync, try again")

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
        self.spec = self.spectrometer.TakeSingleTrack()
        if self.spec is not None:
            print('Spectrum aquired' +str(self.spec.shape))
            self.mean = (self.mean + self.spec)  # / 2
            self.progress.next()
            self.progressSignal.emit(self.progress.percent, str(self.progress.eta_td))
            self.i += 1
            self.specSignal.emit(self.mean / (self.i))
        else :
            self.stop()
            print("Communication out of sync, try again")
        if self.i >= (self.number_of_samples):
            self.progressSignal.emit(100, str(self.progress.eta_td))
            self.finishSignal.emit(self.mean / (self.number_of_samples))
            self.stop()

class LockinThread(MeasurementThread):
    def __init__(self, spectrometer, settings, stage, parent=None):
        self.number_of_samples = settings.number_of_samples
        self.stage = stage
        self.settings = settings
        super(LockinThread, self).__init__(spectrometer)
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
            d = np.abs(np.fft.rfft(self.lockin[i, :]))
            f = np.fft.rfftfreq(d.shape[0])
            res[i] = (d[(f < self.settings.f*2+self.settings.f/10)])[-1]

        fig = plt.figure()
        ax = fig.add_subplot(111)
        indices= [300,800,1200,1600]
        for i in indices:
            x = np.arange(0, self.number_of_samples)
            ref = np.cos(2 * np.pi * x * self.settings.f*2+np.pi)
            buf = self.lockin[i, :]
            buf = buf - np.min(buf)
            ax.plot(x, buf/np.max(buf))
        #ax.plot(x, ref/np.max(ref), 'g-')
        plt.savefig("search_max/lockin.png")
        plt.close()

        return res

    def work(self):

        ref = np.cos(2 * np.pi * self.i * self.settings.f)#+1
        self.move_stage(ref)
        spec = self.spectrometer.TakeSingleTrack()
        self.lockin[:, self.i] = spec

        self.specSignal.emit(self.lockin[:, self.i])
        self.progress.next()
        self.progressSignal.emit(self.progress.percent, str(self.progress.eta_td))
        self.i += 1
        if self.i >= self.number_of_samples:
            self.progressSignal.emit(100, str(self.progress.eta_td))
            self.spec = self.calc_lockin()
            self.specSignal.emit(self.spec)
            self.finishSignal.emit(self.lockin)
            self.stage.moveabs(x=self.startpos[0], y=self.startpos[1], z=self.startpos[2])
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

    def work(self):
        self.search()
        x, y, z = self.stage.last_pos()
        self.finishSignal.emit(np.array([x, y]))
        self.stop()

    def stop(self):
        #super(SearchThread, self).stop()
        self.abort = True
        self.thread.wait(self.settings.search_integration_time*1000+500)

    def search(self):

        def plot(title, popt, perr, pos, measured):
            fig = plt.figure()
            ax = fig.add_subplot(111)
            ax.plot(pos, measured, 'bo')
            x = np.linspace(min(pos), max(pos))
            if not popt is None:
                ax.text(0.1, 0.9, str(round(popt[1],3)) + ' +- ' + str(round(perr[1],3)), ha='left', va='center', transform=ax.transAxes)
                ax.plot(x, gauss(x, popt[0], popt[1], popt[2], popt[3]), 'g-')
                ax.set_title(title)
            plt.savefig("search_max/search" + str(j) + ".png")
            plt.close()


        def search_direction(direction, pos):
            measured = np.zeros(self.settings.rasterdim)

            for k in range(len(pos)):
                if direction == "x":
                    self.stage.moveabs(x=pos[k])
                elif  direction == "y":
                    self.stage.moveabs(y=pos[k])
                if self.abort:
                    self.stage.moveabs(x=startpos[0], y=startpos[1])
                    return None, None, None
                spec = self.spectrometer.TakeSingleTrack()
                spec = smooth(self.wl, spec)
                self.specSignal.emit(spec)
                measured[k] = np.max(spec[100:1900])
                #measured[k] = np.sum(spec)

            maxind = np.argmax(measured[2:(len(pos))])
            minval = np.min(measured)
            maxval = np.max(measured)
            initial_guess = (maxval - minval, pos[maxind], self.settings.sigma, minval)
            try:
                popt, pcov = opt.curve_fit(gauss, pos[2:(len(pos))], measured[2:(len(pos))], p0=initial_guess)
                perr = np.diag(pcov)
                if perr[0] > 1000 or perr[1] > 1 or perr[2] > 50:
                    print("Could not determine particle position: Variance too big")
                    print(perr)
                elif popt[0] < 0.5:
                    print("Could not determine particle position: Peak too small")
                elif popt[1] < (min(pos) - 0.5) or popt[1] > (max(pos) + 0.5):
                    print("Could not determine particle position: Peak outside bounds")
                elif popt[2] < self.settings.sigma/2:
                    print("Could not determine particle position: Peak to narrow")
                else:
                    return popt, perr, measured
            except RuntimeError as e:
                print(e)
                print("Could not determine particle position: Fit error")
            return None, None, measured


        self.spectrometer.SetExposureTime(self.settings.search_integration_time)
        spec = self.spectrometer.TakeSingleTrack()

        spec = smooth(self.wl, spec)

        self.stage.query_pos()
        startpos = self.stage.last_pos()


        d = np.linspace(-self.settings.rasterwidth, self.settings.rasterwidth, self.settings.rasterdim)

        ontargetx = False
        ontargety = False

        repetitions = 4
        self.progress = progress.Progress(max=repetitions)
        for j in range(repetitions):
            self.stage.query_pos()
            origin = self.stage.last_pos()

            if j % 2:
                pos = d + origin[0]
                dir = "x"
            else:
                pos = d + origin[1]
                dir = "y"

            popt, perr, measured = search_direction(dir, pos)

            if popt is not None:
                if j % 2:
                    dx = float(popt[1])
                    if dx-startpos[0] > 1.0:
                        print("Position to far from start, skipping")
                        self.stage.moveabs(x=startpos[0])
                    else:
                        self.stage.moveabs(x=dx)
                        if perr[1] < 0.01:
                            ontargetx = True
                else:
                    dy = float(popt[1])
                    if dy-startpos[1] > 1.0:
                        print("Position to far from start, skipping result")
                        self.stage.moveabs(y=startpos[1])
                    else:
                        self.stage.moveabs(y=dy)
                        if perr[1] < 0.01:
                            ontargety = True

                plot(dir,popt, perr, pos, measured)

                if ontargetx and ontargety:
                    print("Particle localized, terminating early")
                    break

            else:
                if j % 2:
                    self.stage.moveabs(x=startpos[0])
                else:
                    self.stage.moveabs(y=startpos[1])
                plot(dir, None, None, pos, measured)

            if self.abort:
                self.stage.moveabs(x=startpos[0], y=startpos[1])
                return False

            self.progress.next()
            self.progressSignal.emit(self.progress.percent, str(self.progress.eta_td))

        self.spectrometer.SetExposureTime(self.settings.integration_time)



class ScanThread(MeasurementThread):
    def __init__(self, spectrometer, settings, scanning_points, labels,stage, parent=None):
        try:
            self.spectrometer = spectrometer
            self.scanning_points = scanning_points
            self.settings = settings
            self.stage = stage
            self.i = 0
            self.n = scanning_points.shape[0]
            self.positions = np.zeros((self.n, 2))
            self.labels = labels
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
    def __init__(self, spectrometer, settings, scanning_points, labels, stage, parent=None):
        super(ScanSearchThread, self).__init__(spectrometer, settings, scanning_points, labels, stage)
        self.searchthread = SearchThread(self.spectrometer, self.settings, self.stage, self)
        self.searchthread.specSignal.connect(self.specslot)
        self.searchthread.finishSignal.connect(self.searchfinishslot)

    def stop(self):
        self.searchthread.stop()
        super(ScanSearchThread, self).stop()

    def __del__(self):
        #self.searchthread.specSignal.disconnect(self.specslot)
        super(ScanSearchThread, self).__del__()

    def intermediatework(self):
        self.searchthread.search()

    @pyqtSlot(np.ndarray)
    def specslot(self, spec):
        self.specSignal.emit(spec)

    @pyqtSlot(np.ndarray)
    def searchfinishslot(self, pos):
        print(pos)


class ScanLockinThread(ScanThread):
    saveSignal = pyqtSignal(np.ndarray, str, np.ndarray, bool, bool)

    def __init__(self, spectrometer, settings, scanning_points, stage, parent=None):
        super(ScanThread, self).__init__(spectrometer, settings, scanning_points, None, stage)
        # __init__(self, spectrometer, settings, stage, parent=None)
        self.meanthread = LockinThread(spectrometer, settings, stage, self)
        self.meanthread.finishSignal.connect(self.lockinfinished)
        self.meanthread.specSignal.connect(self.specslot)

    def stop(self):
        if self.meanthread is not None:
            self.meanthread.stop()
            self.meanthread.thread.wait(self.settings.integration_time*1000+500)
            self.meanthread = None
        super(ScanThread, self).stop()


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

    def __init__(self, spectrometer, settings, scanning_points, labels, stage, parent=None):
        super(ScanMeanThread, self).__init__(spectrometer, settings, scanning_points, labels, stage)
        self.initMeanThread()

    def stop(self):
        # if self.meanthread is not None:
        #     self.meanthread.stop()
        #     self.meanthread.wait(self.settings.integration_time*1000+500)
        #     self.meanthread = None
        super(ScanMeanThread, self).stop()
        #self.meanthread.finishSignal.disconnect()
        #self.meanthread.specSignal.disconnect()
        #self.saveSignal.disconnect()

    # def __del__(self):
    #     #self.meanthread.finishSignal.disconnect()
    #     #self.meanthread.specSignal.disconnect()
    #     #self.saveSignal.disconnect()
    #     super(ScanMeanThread, self).__del__()

    def initMeanThread(self):
        self.meanthread = MeanThread(self.spectrometer, self.settings.number_of_samples, self)
        self.meanthread.finishSignal.connect(self.meanfinished)
        self.meanthread.specSignal.connect(self.specslot)
        self.meanthread.init()

    def intermediatework(self):
        self.meanthread.init()
        self.meanthread.process()
        # self.initMeanThread()
        # self.meanthread.start()
        #self.meanthread.thread.wait()
        # while not self.meanthread.thread.isFinished():
        #     time.sleep(0.1)
        # try:
        #     self.meanthread.stop()
        #     self.meanthread = None
        # except Exception as e:
        #     print(e)
        #while not self.proceed:
        #    time.sleep(0.1)
        #self.meanthread.process()

    @pyqtSlot(np.ndarray)
    def specslot(self, spec):
        self.specSignal.emit(spec)

    @pyqtSlot(np.ndarray)
    def meanfinished(self, spec):
        if self.labels is not None:
            self.saveSignal.emit(spec, self.labels[self.i] + ".csv", self.positions[self.i, :], False, False)
        else:
            self.saveSignal.emit(spec,str(self.i).zfill(5) + ".csv", self.positions[self.i, :], False, False)


class ScanSearchMeanThread(ScanMeanThread):
    def __init__(self, spectrometer, settings, scanning_points, labels, stage, parent=None):
        super(ScanSearchMeanThread, self).__init__(spectrometer, settings, scanning_points, labels, stage)
        self.searchthread = SearchThread(self.spectrometer, self.settings, self.stage, self)
        self.searchthread.specSignal.connect(self.specslot)

    def stop(self):
        self.meanthread.stop()
        self.meanthread.thread.wait(self.settings.integration_time * 1000 + 500)
        self.meanthread = None
        self.searchthread.stop()
        self.searchthread.thread.wait(self.settings.integration_time*1000+500)
        self.searchthread = None
        super(ScanMeanThread, self).stop()

    # def __del__(self):
    #     self.stop()
    #     #self.searchthread.specSignal.disconnect()
    #     super(ScanMeanThread, self).__del__()

    def intermediatework(self):
        self.searchthread.search()
        self.meanthread.init()
        self.meanthread.process()
