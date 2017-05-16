import sys

import matplotlib.pyplot as plt
import numpy as np
import progress
import scipy.optimize as opt
from scipy import signal
from qtpy import QtCore
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


class MeasurementThread(QtCore.QObject):
    specSignal = QtCore.Signal(np.ndarray)
    progressSignal = QtCore.Signal(float, str)
    finishSignal = QtCore.Signal(np.ndarray)


    def __init__(self, spectrometer, parent=None):
        if getattr(self.__class__, '_has_instance', False):
            RuntimeError('Cannot create another instance')
            #return None
        self.__class__._has_instance = True
        try:
            super(MeasurementThread, self).__init__(parent)
            self.spectrometer = spectrometer
            self.abort = False
        except:
            (type, value, traceback) = sys.exc_info()
            sys.excepthook(type, value, traceback)
        self.spec = np.zeros(self.spectrometer._width)
        print("New "+ self.__class__.__name__ +" created: "+str(id(self)))

    @QtCore.Slot()
    def stop(self):
        self.abort = True
        #self.thread.wait(self.spectrometer.exposure_time*1000+500)
        #self.thread.wait()
        #self.spectrometer.AbortAcquisition()
        #self.thread.quit()
        #print("Done with thread")

    def __del__(self):
        self.__class__.has_instance = False

    @QtCore.Slot()
    def work(self):
        pass

    @QtCore.Slot()
    def process(self):
        try:
            while not self.abort:
                self.work()
        except Exception as e:
            print(e)
            (type, value, traceback) = sys.exc_info()
            sys.excepthook(type, value, traceback)
            self.stop()

class LiveThread(MeasurementThread):

    @QtCore.Slot()
    def work(self):
        try:
            self.specSignal.emit(self.spec)
        except TypeError as e:
            print(e)
            print("Communication out of sync, try again")

    @QtCore.Slot()
    def process(self):
        try:
            while not self.abort:
                self.spec = self.spectrometer.TakeSingleTrack()
                self.work()
        except Exception as e:
            print(e)
            (type, value, traceback) = sys.exc_info()
            sys.excepthook(type, value, traceback)


class ImageThread(MeasurementThread):

    def work(self):
        try:
            self.specSignal.emit(self.spec)
        except TypeError as e:
            print(e)
            print("Communication out of sync, try again")

    @QtCore.Slot()
    def process(self):
        while not self.abort:
            try:
                if not self.abort:
                    self.spec = self.spectrometer.TakeImageofSlit()
                else:
                    print("Image Thread aborted")
                    print(self.spec)
                if not self.abort:
                    self.work()
                else:
                    print("Image Thread aborted")
                    print(self.spec)
            except:
                (type, value, traceback) = sys.exc_info()
                sys.excepthook(type, value, traceback)


class AutoFocusThread(MeasurementThread):

    def focus(self):
        def calc_f(dist=2):
            img = self.spectrometer.TakeSingleTrack(raw=True)
            n, m = img.shape
            f = 0
            for i in range(n):
                f += np.sum(np.square(np.subtract(img[n, :], np.roll(img[n, :], dist))))

        self.stage.query_pos()
        startpos = self.stage.last_pos()
        d = np.linspace(-self.settings.rasterwidth, self.settings.rasterwidth, self.settings.rasterdim)
        pos = d * self.settings.zmult + startpos[2]
        focus = np.zeros(self.settings.rasterdim)
        for k in range(len(pos)):
            self.stage.moveabs(z=startpos[2]+pos[k])
            focus[k] = calc_f()
            if self.abort:
                break

        fig = plt.figure()
        ax = fig.add_subplot(111)
        ax.plot(pos, focus, 'bo')
        plt.savefig("search_max/autofocus.png")
        plt.close()

    @QtCore.Slot()
    def process(self):
        while not self.abort:
            try:
                if not self.abort:
                    self.focus()
                else:
                    print("Autofocus Thread aborted")
                    print(self.spec)
            except:
                (type, value, traceback) = sys.exc_info()
                sys.excepthook(type, value, traceback)




class FullImageThread(MeasurementThread):

    def work(self):
        try:
            self.specSignal.emit(self.spec)
        except TypeError as e:
            print(e)
            print("Communication out of sync, try again")

    @QtCore.Slot()
    def process(self):
        while not self.abort:
            try:
                if not self.abort:
                    self.spec = self.spectrometer.TakeFullImage()
                else:
                    print("Image Thread aborted")
                    print(self.spec)
                if not self.abort:
                    self.work()
                else:
                    print("Image Thread aborted")
                    print(self.spec)
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
            self.mean = (self.mean + self.spec)  # / 2
            self.progress.next()
            self.progressSignal.emit(self.progress.percent, str(self.progress.eta_td))
            self.i += 1
            if not self.abort:
                self.specSignal.emit(self.mean / (self.i))
        else :
            self.stop()
            print("Communication out of sync, try again")
        if self.i >= (self.number_of_samples):
            if not self.abort:
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
        x = np.arange(0, self.number_of_samples)
        #ref = np.cos(2 * np.pi * x * self.settings.f*2)
        #ref2 = np.cos(2 * np.pi * x * self.settings.f*2+np.pi/2)

        ref = signal.sawtooth(2 * np.pi * x * self.settings.f*2,0.5)
        ref2 = signal.sawtooth(2 * np.pi * x * self.settings.f * 2 + np.pi / 2,0.5)

        #ref = np.cos(2 * np.pi * x * self.settings.f)
        #ref2 = np.cos(2 * np.pi * x * self.settings.f+np.pi/2)

        res = np.zeros(self.spectrometer._width)
        res_amp = np.zeros(self.spectrometer._width)
        res_phase = np.zeros(self.spectrometer._width)
        x2 = np.zeros(self.spectrometer._width)
        y2 = np.zeros(self.spectrometer._width)
        for ind in range(self.spectrometer._width):
            #d = np.absolute(np.fft.rfft(self.lockin[ind, :]*ref))
            #f = np.fft.rfftfreq(d.shape[0])
            #res[ind] = (d[(f < self.settings.f*2+self.settings.f/10)])[-1]
            #d = np.absolute(np.fft.rfft(self.lockin[ind, :] * ref))
            #res[ind] = d[0]
            x2[ind] = np.sum(self.lockin[ind, :] * ref) / len(ref)
            y2[ind] = np.sum(self.lockin[ind, :] * ref2) / len(ref2)
            #res_phase[ind] = np.angle(x2 + 1j * y2)
            #res_amp[ind] = np.abs(x2 + 1j * y2)
            #res[ind] = np.abs(x2 + 1j * y2) * (np.pi - np.abs(res_phase[ind]))


        # res_phase = np.angle(x2 + 1j * y2)
        # res_amp = np.abs(x2 + 1j * y2)
        #
        # p0 = -1 * res_phase[np.argmax(res_amp)]
        # rotMatrix = np.array([[np.cos(p0), -np.sin(p0)], [np.sin(p0), np.cos(p0)]])
        # print(rotMatrix)
        # for ind in range(len(x2)):
        #     buf = np.array([x2[ind],y2[ind]])
        #     buf = np.dot(rotMatrix,buf)
        #     x2[ind] = buf[0]
        #     y2[ind] = buf[1]

        res_phase = np.angle(x2 + 1j * y2)
        res_amp = np.abs(x2 + 1j * y2)
        #res = np.abs(x2 + 1j * y2) * (np.pi - np.abs(res_phase))
        res = res_amp * (np.abs(res_phase))
        #print(res_phase[np.argmax(res_amp)])



        fig = plt.figure()
        ax = fig.add_subplot(111)
        indices= [300,800,1200,1600]
        for i,ind in enumerate(indices):
            buf = self.lockin[ind, :]
            buf = buf - np.min(buf)
            ax.plot(x, buf/np.max(buf)+i)
            ax.plot(x, ref/ref.max()+i)
        #ax.plot(x, ref/np.max(ref), 'g-')
        plt.savefig("search_max/traces.png")
        plt.close()


        # fig = plt.figure()
        # ax = fig.add_subplot(111)
        # indices= [1000]
        # for i,ind in enumerate(indices):
        #     d = np.absolute(np.fft.rfft(self.lockin[ind, :]))
        #     f = np.fft.rfftfreq(x.shape[0])
        #     ax.plot(f, d/d.max()  +i)
        #
        # plt.axvline(x=self.settings.f)
        # plt.axvline(x=self.settings.f*2)
        # plt.savefig("search_max/fft.png")
        # plt.close()

        res_phase = np.abs(res_phase)

        fig = plt.figure()
        ax = fig.add_subplot(111)
        ax.plot(self.spectrometer.GetWavelength(), res_phase / res_phase.max())  # /lamp[mask])
        ax.plot(self.spectrometer.GetWavelength(), res_amp / res_amp.max())
        plt.savefig("search_max/lockin_nopsd.png")
        plt.close()

        fig = plt.figure()
        ax = fig.add_subplot(111)
        ax.plot(self.spectrometer.GetWavelength(), res_phase / res_phase.max())  # /lamp[mask])
        ax.plot(self.spectrometer.GetWavelength(),res / res.max())
        plt.savefig("search_max/lockin.png")
        plt.close()


        return res

    def work(self):

        #ref = np.cos(2 * np.pi * self.i * self.settings.f)
        ref = signal.sawtooth(2 * np.pi * self.i * self.settings.f,0.5)
        #ref = (np.cos(2 * np.pi * self.i * self.settings.f)+1)/2

        self.move_stage(ref)
        spec = self.spectrometer.TakeSingleTrack()
        self.lockin[:, self.i] = spec

        if not self.abort:
            self.specSignal.emit(self.lockin[:, self.i])
            self.progress.next()
            self.progressSignal.emit(self.progress.percent, str(self.progress.eta_td))
            self.i += 1
        else:
            return
        if self.i >= self.number_of_samples:
            self.progressSignal.emit(100, str(self.progress.eta_td))
            self.spec = self.calc_lockin()
            self.specSignal.emit(self.spec)
            self.finishSignal.emit(self.lockin)
            self.stage.moveabs(x=self.startpos[0], y=self.startpos[1], z=self.startpos[2])
            self.stop()

class SearchThread(MeasurementThread):
    def __init__(self, spectrometer, settings, stage, ref_spec = None, dark_spec = None, bg_spec=None, parent=None):
        try:
            self.settings = settings
            self.stage = stage
            self.ref_spec = ref_spec
            self.dark_spec = dark_spec
            self.bg_spec = bg_spec
            super(SearchThread, self).__init__(spectrometer)
            self.wl = self.spectrometer.GetWavelength()
        except:
            (type, value, traceback) = sys.exc_info()
            sys.excepthook(type, value, traceback)

    def work(self):
        self.search()
        if not self.abort:
            x, y, z = self.stage.last_pos()
            self.finishSignal.emit(np.array([x, y]))
        else:
            return
        self.stop()

    def get_spec(self):
        spec = self.spectrometer.TakeSingleTrack()

        if not self.dark_spec is None and not self.ref_spec is None and not self.bg_spec is None:
            return (spec - self.bg_spec) / (self.ref_spec - self.dark_spec)

        elif not self.dark_spec is None and not self.ref_spec is None:
            return 1 - ( (spec - self.dark_spec) / (self.ref_spec - self.dark_spec) )

        elif not self.dark_spec is None:
            return spec - self.dark_spec

        elif not self.bg_spec is None:
            return spec - self.bg_spec

        else:
            return spec

    def search(self):

        def plot(title, popt, perr, pos, measured, maxwl):
            fig = plt.figure()
            ax = fig.add_subplot(111)
            ax.plot(pos, measured, 'bo')
            x = np.linspace(min(pos), max(pos))
            if not popt is None:
                ax.text(0.1, 0.9, str(round(popt[1],3)) + ' +- ' + str(round(perr[1],3)), ha='left', va='center', transform=ax.transAxes)
                ax.plot(x, gauss(x, popt[0], popt[1], popt[2], popt[3]), 'g-')
                ax.set_title(title)
            if not maxwl is None:
                ax2 = ax.twinx()
                ax2.plot(pos, maxwl, 'r.')
                ax2.set_ylabel('maxwl', color='r')
                ax2.tick_params('y', colors='r')
            plt.savefig("search_max/search" + str(j) + ".png")
            plt.close()


        def search_direction(direction, pos):
            measured = np.zeros(self.settings.rasterdim)
            maxwl = np.zeros(self.settings.rasterdim)

            for k in range(len(pos)):
                if direction == "x":
                    self.stage.moveabs(x=pos[k])
                    sigma_start = self.settings.sigma
                elif  direction == "y":
                    self.stage.moveabs(y=pos[k])
                    sigma_start = self.settings.sigma
                elif direction == "z":
                    self.stage.moveabs(z=pos[k])
                    sigma_start = self.settings.sigma*self.settings.zmult/2
                if self.abort:
                    self.stage.moveabs(x=startpos[0], y=startpos[1],z=startpos[2])
                    return None, None, None, None
                if self.settings.correct_search:
                    spec = self.get_spec()
                else:
                    spec = self.spectrometer.TakeSingleTrack()
                spec = smooth(self.wl, spec)
                self.specSignal.emit(spec)
                #measured[k] = np.max(spec[100:1900])
                measured[k] = np.sum(spec[100:1900])
                maxwl[k] = self.spectrometer.GetWavelength()[np.argmax(spec)]

            maxind = np.argmax(measured[2:(len(pos))])
            minval = np.min(measured)
            maxval = np.max(measured)
            initial_guess = (maxval - minval, pos[maxind], sigma_start, minval)
            try:
                popt, pcov = opt.curve_fit(gauss, pos[2:(len(pos))], measured[2:(len(pos))], p0=initial_guess)
                perr = np.diag(pcov)
                #if perr[0] > 1e10 or perr[1] > 1 or perr[2] > 50:
                if perr[1] > 1:
                    print("Could not determine particle position: Variance too big")
                    print(perr)
                #elif popt[0] < *0.1:
                #    print("Could not determine particle position: Peak too small")
                elif popt[1] < (min(pos) - 2.0) or popt[1] > (max(pos) + 2.0):
                    print("Could not determine particle position: Peak outside bounds")
                elif popt[2] < self.settings.sigma/100:
                    print("Could not determine particle position: Peak to narrow")
                else:
                    return popt, perr, measured, maxwl
            except RuntimeError as e:
                print(e)
                print("Could not determine particle position: Fit error")
            return None, None, measured, None


        self.spectrometer.SetExposureTime(self.settings.search_integration_time)
        spec = self.spectrometer.TakeSingleTrack()
        if spec is None:
            self.abort = True
            return False

        #spec = smooth(self.wl, spec)

        self.stage.query_pos()
        startpos = self.stage.last_pos()


        d = np.linspace(-self.settings.rasterwidth, self.settings.rasterwidth, self.settings.rasterdim)

        ontargetx = False
        ontargety = False
        ontargetz = False

        repetitions = 6
        self.progress = progress.Progress(max=repetitions)

        for j in range(repetitions):
            self.stage.query_pos()
            origin = self.stage.last_pos()

            if j in np.arange(0,repetitions,3):
                pos = d + origin[0]
                dir = "x"
            elif j in np.arange(1,repetitions,3):
                pos = d + origin[1]
                dir = "y"
            elif j in np.arange(2,repetitions,3):
                pos = d * self.settings.zmult + origin[2]
                dir = "z"

            print("Iteration #: "+str(j)+"  Direction "+dir )

            popt, perr, measured, maxwl = search_direction(dir, pos)

            if self.abort:
                self.stage.moveabs(x=startpos[0], y=startpos[1],z=startpos[2])
                return False

            if popt is not None:
                if j in np.arange(0,repetitions,3):
                    dx = float(popt[1])
                    if dx-startpos[0] > self.settings.rasterwidth:
                        print("Position to far from start, skipping")
                        self.stage.moveabs(x=startpos[0])
                    else:
                        self.stage.moveabs(x=dx)
                        if perr[1] < 0.01 and ontargetz:
                            ontargetx = True
                elif j in np.arange(1,repetitions,3):
                    dy = float(popt[1])
                    if dy-startpos[1] > self.settings.rasterwidth:
                        print("Position to far from start, skipping")
                        self.stage.moveabs(y=startpos[1])
                    else:
                        self.stage.moveabs(y=dy)
                        if perr[1] < 0.01 and ontargetz:
                            ontargety = True
                elif j in np.arange(2, repetitions, 3):
                    dz = float(popt[1])
                    if dz - startpos[2] > self.settings.rasterwidth*self.settings.zmult:
                        print("Position to far from start, skipping")
                        self.stage.moveabs(z=startpos[2])
                    else:
                        self.stage.moveabs(z=dz)
                        if perr[1] < 0.01:
                            ontargetz = True

                plot(dir,popt, perr, pos, measured, maxwl)

                if ontargetx and ontargety and ontargetz:
                    print("Particle localized, terminating early")
                    break

            else:
                if j in np.arange(0, repetitions, 3):
                    self.stage.moveabs(x=startpos[0])
                elif j in np.arange(1, repetitions, 3):
                    self.stage.moveabs(y=startpos[1])
                elif j in np.arange(2, repetitions, 3):
                    self.stage.moveabs(z=startpos[2])
                plot(dir, None, None, pos, measured, None)


            self.progress.next()
            self.progressSignal.emit(self.progress.percent, str(self.progress.eta_td))

        self.spectrometer.SetExposureTime(self.settings.integration_time)


class Scan3DThread(MeasurementThread):
    def __init__(self, spectrometer, settings, scanning_points, file,stage, parent=None):
        try:
            self.spectrometer = spectrometer
            self.scanning_points = scanning_points
            self.settings = settings
            self.stage = stage
            self.i = 0
            self.n = scanning_points.shape[0]
            self.positions = np.zeros((self.n, 3))
            self.file = file
            self.f = None
            self.progress = progress.Progress(max=self.n)
            self.wl = spectrometer.GetWavelength()
            super(Scan3DThread, self).__init__(spectrometer)
            self.initMeanThread()
        except:
            (type, value, traceback) = sys.exc_info()
            sys.excepthook(type, value, traceback)
            print(type)
            print(value)

    @QtCore.Slot()
    def process(self):
        print("Taking "+str(self.n)+" spectra")
        with open(self.file, 'w') as self.f:
            self.f.write("x,y,z,")# + "\r\n")
            for i in range(len(self.wl)):
                self.f.write(str(self.wl[i])+",")
            self.f.write("\r\n")
            while not self.abort:
                try:
                    self.work()
                except:
                    (type, value, traceback) = sys.exc_info()
                    sys.excepthook(type, value, traceback)
                    self.stop()

    @QtCore.Slot(np.ndarray)
    def meanfinished(self, spec):
        self.f.write(str(self.scanning_points[self.i, 0]) + "," +str(self.scanning_points[self.i, 1]) + "," +str(self.scanning_points[self.i, 2]) + ",")
        for i in range(len(spec)):
            self.f.write(str(spec[i]) + ",")
        self.f.write("\r\n")

    @QtCore.Slot()
    def stop(self):
        self.meanthread.stop()
        #self.meanthread.thread.wait(self.settings.integration_time*1000+500)
        self.meanthread = None
        super(Scan3DThread, self).stop()

    def initMeanThread(self):
        self.meanthread = MeanThread(self.spectrometer, self.settings.number_of_samples, self)
        self.meanthread.finishSignal.connect(self.meanfinished)
        self.meanthread.specSignal.connect(self.specslot)
        self.meanthread.init()

    def intermediatework(self):
        if not self.abort:
            self.meanthread.init()
        if not self.abort:
            self.meanthread.process()

    def work(self):
        self.stage.moveabs(x=self.scanning_points[self.i, 0], y=self.scanning_points[self.i, 1],z=self.scanning_points[self.i, 2])
        if not self.abort:
            self.intermediatework()
        else:
            return False
        x, y, z = self.stage.last_pos()
        self.positions[self.i, 0] = x
        self.positions[self.i, 1] = y
        self.positions[self.i, 2] = z
        self.progress.next()
        self.progressSignal.emit(self.progress.percent, str(self.progress.eta_td))
        self.i += 1
        if self.i >= self.n:
            self.progressSignal.emit(100, str(self.progress.eta_td))
            self.finishSignal.emit(np.array([]))
            self.stop()

    @QtCore.Slot(np.ndarray)
    def specslot(self, spec):
        self.specSignal.emit(spec)




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
        if not self.abort:
            self.intermediatework()
        else:
            return False
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
    def __init__(self, spectrometer, settings, scanning_points, labels, stage, ref_spec = None, dark_spec = None, bg_spec=None, parent=None):
        super(ScanSearchThread, self).__init__(spectrometer, settings, scanning_points, labels, stage)
        self.searchthread = SearchThread(self.spectrometer, self.settings, self.stage,ref_spec,dark_spec,bg_spec, self)
        self.searchthread.specSignal.connect(self.specslot)
        self.searchthread.finishSignal.connect(self.searchfinishslot)

    @QtCore.Slot()
    def stop(self):
        self.searchthread.stop()
        super(ScanSearchThread, self).stop()
        self.searchthread = None

    def __del__(self):
        #self.searchthread.specSignal.disconnect(self.specslot)
        super(ScanSearchThread, self).__del__()

    def intermediatework(self):
        self.searchthread.search()

    @QtCore.Slot(np.ndarray)
    def specslot(self, spec):
        self.specSignal.emit(spec)

    @QtCore.Slot(np.ndarray)
    def searchfinishslot(self, pos):
        print(pos)


class ScanLockinThread(ScanThread):
    saveSignal = QtCore.Signal(np.ndarray, str, np.ndarray, bool, bool)

    def __init__(self, spectrometer, settings, scanning_points, stage, parent=None):
        super(ScanThread, self).__init__(spectrometer, settings, scanning_points, None, stage)
        # __init__(self, spectrometer, settings, stage, parent=None)
        self.meanthread = LockinThread(spectrometer, settings, stage, self)
        self.meanthread.finishSignal.connect(self.lockinfinished)
        self.meanthread.specSignal.connect(self.specslot)

    @QtCore.Slot()
    def stop(self):
        self.meanthread.stop()
        #self.meanthread.thread.wait(self.settings.integration_time*1000+500)
        super(ScanThread, self).stop()
        self.meanthread = None


    def intermediatework(self):
        if not self.abort:
            self.meanthread.init()
        if not self.abort:
            self.meanthread.process()

    @QtCore.Slot(np.ndarray)
    def specslot(self, spec):
        self.specSignal.emit(spec)

    @QtCore.Slot(np.ndarray)
    def lockinfinished(self, spec):
        self.saveSignal.emit(self.lockin, str(self.i).zfill(5) + "_lockin.csv", self.positions[self.i, :], False, False)


class ScanMeanThread(ScanThread):
    saveSignal = QtCore.Signal(np.ndarray, str, np.ndarray, bool, bool)

    def __init__(self, spectrometer, settings, scanning_points, labels, stage, parent=None):
        super(ScanMeanThread, self).__init__(spectrometer, settings, scanning_points, labels, stage)
        self.initMeanThread()

    @QtCore.Slot()
    def stop(self):
        self.meanthread.stop()
        #self.meanthread.wait(self.settings.integration_time*1000+500)
        super(ScanMeanThread, self).stop()
        self.meanthread = None

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
        if not self.abort:
            self.meanthread.init()
        if not self.abort:
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

    @QtCore.Slot(np.ndarray)
    def specslot(self, spec):
        self.specSignal.emit(spec)

    @QtCore.Slot(np.ndarray)
    def meanfinished(self, spec):
        if self.labels is not None:
            self.saveSignal.emit(spec, self.labels[self.i] + ".csv", self.positions[self.i, :], False, False)
        else:
            self.saveSignal.emit(spec,str(self.i).zfill(5) + ".csv", self.positions[self.i, :], False, False)


class ScanSearchMeanThread(ScanMeanThread):
    def __init__(self, spectrometer, settings, scanning_points, labels, stage, ref_spec = None, dark_spec = None, bg_spec=None, parent=None):
        super(ScanSearchMeanThread, self).__init__(spectrometer, settings, scanning_points, labels, stage)
        self.searchthread = SearchThread(self.spectrometer, self.settings, self.stage,ref_spec,dark_spec,bg_spec,self)
        self.searchthread.specSignal.connect(self.specslot)

    @QtCore.Slot()
    def stop(self):
        self.meanthread.stop()
        self.searchthread.stop()
        #self.meanthread.thread.wait(self.settings.integration_time * 1000 + 500)
        #self.searchthread.thread.wait(self.settings.integration_time*1000+500)
        super(ScanMeanThread, self).stop()
        self.searchthread = None
        self.meanthread = None

    # def __del__(self):
    #     self.stop()
    #     #self.searchthread.specSignal.disconnect()
    #     super(ScanMeanThread, self).__del__()

    def intermediatework(self):
        if not self.abort:
            self.searchthread.search()
        if not self.abort:
            self.meanthread.init()
        if not self.abort:
            self.meanthread.process()
        #self.searchthread.start()
        #self.searchthread.stop()
        #self.meanthread.init()
        #self.meanthread.start()
        #self.meanthread.stop()