import sys

import matplotlib.pyplot as plt
from matplotlib import ticker
import numpy as np
import progress
import scipy.optimize as opt
from scipy import signal
from qtpy import QtCore
from scipy.signal import savgol_filter
from skimage import img_as_float,img_as_int
from skimage import restoration
from skimage import filters
from skimage import morphology
from skimage import feature
from scipy import ndimage, special
import time
import peakutils

#  modified from: http://stackoverflow.com/questions/21566379/fitting-a-2d-gaussian-function-using-scipy-optimize-curve-fit-valueerror-and-m#comment33999040_21566831
def gauss2D(pos, amplitude, xo, yo, fwhm, offset):
    sigma = fwhm / 2.3548
    g = offset + amplitude * np.exp(
        -(np.power(pos[0] - xo, 2.) + np.power(pos[1] - yo, 2.)) / (2 * np.power(sigma, 2.)))
    return g.ravel()


# def Airy2D(xdata_tuple, amplitude, xo, yo, sigma_x, sigma_y, theta, offset):
#     (x, y) = xdata_tuple
#     a = (np.cos(theta) ** 2) / (2 * sigma_x ** 2) + (np.sin(theta) ** 2) / (2 * sigma_y ** 2)
#     b = -(np.sin(2 * theta)) / (4 * sigma_x ** 2) + (np.sin(2 * theta)) / (4 * sigma_y ** 2)
#     c = (np.sin(theta) ** 2) / (2 * sigma_x ** 2) + (np.cos(theta) ** 2) / (2 * sigma_y ** 2)
#     g = offset + amplitude * (
#         np.exp(- (a * ((x - xo) ** 2) + 2 * b * (x - xo) * (y - yo) + c * ((y - yo) ** 2))) ** 2)
#     return g.ravel()

def Airy2D(xdata_tuple, amplitude, xo, yo, sigma,offset):
    (x, y) = xdata_tuple
    r = np.sqrt(np.square(x-xo)+np.square(y-yo))
    g = amplitude*np.square(np.pi*np.square(sigma)*special.j0(np.pi*sigma*r)/(np.pi*sigma))+offset
    return g.ravel()


def twoAiry2D(xdata_tuple, amplitude, xo1, yo1, xo2, yo2, sigma,offset):
    g1 = Airy2D(xdata_tuple,amplitude,xo1,yo1,sigma,offset)
    g2 = Airy2D(xdata_tuple, amplitude, xo2, yo2, sigma, offset)
    g = g1-g2
    return g.ravel()

def twoGauss2D(xdata_tuple, amplitude, xo1, yo1, xo2, yo2, sigma,offset):
    g1 = gauss2D(xdata_tuple,amplitude,xo1,yo1,sigma,offset)
    g2 = gauss2D(xdata_tuple, amplitude, xo2, yo2, sigma, offset)
    g = g1-g2
    return g.ravel()

def twoGauss(xdata_tuple, amplitude1,amplitude2, xo1, xo2, sigma,offset):
    g1 = gauss(xdata_tuple,amplitude1,xo1,sigma,offset)
    g2 = gauss(xdata_tuple, amplitude2, xo2, sigma, offset)
    g = g1+g2
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
        super(MeasurementThread, self).__init__(parent)
        self.spectrometer = spectrometer
        self.abort = False
        self.spec = np.zeros(self.spectrometer._width)
        #print("New "+ self.__class__.__name__ +" created: "+str(id(self)))

    @QtCore.Slot()
    def stop(self):
        self.abort = True

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
    def __init__(self, spectrometer, single = False, parent=None):
        super(LiveThread, self).__init__(spectrometer,parent)
        self.single = single

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
                if self.single:
                    self.abort=True
                    self.finishSignal.emit(np.zeros(0))
        except Exception as e:
            print(e)
            (type, value, traceback) = sys.exc_info()
            sys.excepthook(type, value, traceback)


class ImageThread(MeasurementThread):
    def __init__(self, spectrometer, single = False, parent=None):
        super(ImageThread, self).__init__(spectrometer,parent)
        self.single = single

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
            if self.single:
                self.abort = True
                self.finishSignal.emit(np.zeros(0))


class ImageMeanThread(MeasurementThread):
    def __init__(self, spectrometer, number_of_samples, parent=None):
        self.number_of_samples = number_of_samples
        super(ImageMeanThread, self).__init__(spectrometer)
        self.init()

    def init(self):
        self.progress = progress.Progress(max=self.number_of_samples)
        self.mean = None
        self.i = 0
        self.abort = False

    def work(self):
        self.spec = self.spec = self.spectrometer.TakeImageofSlit()
        if self.mean is None:
            self.mean = np.zeros(self.spec.shape)

        if self.spec is not None:
            self.mean = (self.mean + self.spec)  # / 2
            self.progress.next()
            self.progressSignal.emit(self.progress.percent, str(self.progress.eta_td))
            self.i += 1
            if not self.abort:
                self.specSignal.emit(self.mean / (self.i))
        else:
            self.stop()
            print("Communication out of sync, try again")
        if self.i >= (self.number_of_samples):
            if not self.abort:
                self.progressSignal.emit(100, str(self.progress.eta_td))
                self.finishSignal.emit(self.mean / (self.number_of_samples))
                self.stop()


class FullImageThread(MeasurementThread):

    def __init__(self, spectrometer, single = False, parent=None):
        super(FullImageThread, self).__init__(spectrometer,parent)
        self.single = single

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
                    self.spec = np.flipud(self.spectrometer.TakeFullImage())
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
            if self.single:
                self.abort = True
                self.finishSignal.emit(np.zeros(0))

class FullImageMeanThread(MeasurementThread):
    def __init__(self, spectrometer, number_of_samples, parent=None):
        self.number_of_samples = number_of_samples
        super(FullImageMeanThread, self).__init__(spectrometer)
        self.init()

    def init(self):
        self.progress = progress.Progress(max=self.number_of_samples)
        self.mean = None
        self.i = 0
        self.abort = False

    def work(self):
        self.spec = np.flipud(self.spectrometer.TakeFullImage())
        if self.mean is None:
            self.mean = np.zeros(self.spec.shape)

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




class AutoFocusThread(MeasurementThread):
    def __init__(self, spectrometer, settings, stage ,parent=None):
        self.stage = stage
        self.settings = settings
        super(AutoFocusThread, self).__init__(spectrometer)
        # self.searchthread = None


    def focus(self):
        def calc_f(plot = False):

            amp = 0
            sigma = 0

            if self.settings.autofocus_mode == 'brightfield':
                self.spectrometer.SetMinVertReadout(32)
                self.spectrometer.SetSlitWidth(self.settings.slit_width)
                self.spectrometer.SetExposureTime(self.settings.search_integration_time)
                self.stage.moverel(dy=-1.0)
                time.sleep(0.3)
                buf = self.spectrometer.TakeSingleTrack(raw=True)
                self.stage.moverel(dy=+2.0)
                time.sleep(0.3)
                img = self.spectrometer.TakeSingleTrack(raw=True)
                self.stage.moverel(dy=-1.0)
                img -= buf
                dist = 7
                #img = ndimage.median_filter(img, 3)
                img = ndimage.median_filter(img, footprint=morphology.disk(3), mode="mirror")
                #img = ndimage.gaussian_filter(img, 2)
                img = ndimage.gaussian_filter(img, 1)

                try:

                    img = np.sum(img, axis=0)
                    x = np.arange(img.shape[0])
                    #img = img - (img[0]+img[-1])/2
                    #img = img / 2000

                    amp = np.abs((img.max()-img.min()))
                    sigma = 1 #img.max()+img.min()

                    plt.plot(x,img)
                    plt.title(amp/sigma)
                    plt.savefig("search_max/autofocus_image.png")
                    plt.close()

                except (RuntimeError, ValueError) as e:
                    print(e)
                    return 0
                return amp/sigma

            elif self.settings.autofocus_mode == 'gauss' \
                    or self.settings.autofocus_mode == 'gaussexport' \
                    or self.settings.autofocus_mode == 'gausswidth':
                self.spectrometer.SetExposureTime(self.settings.search_integration_time)

                self.spectrometer.SetSlitWidth(300)
                self.spectrometer.SetCentreWavelength(0)

                img = self.spectrometer.TakeSingleTrack(raw=True)[self.settings.min_ind_img:self.settings.max_ind_img, :]

                #img = ndimage.median_filter(img, footprint=morphology.disk(3), mode="mirror")
                #img = ndimage.median_filter(img, 2)
                img = ndimage.gaussian_filter(img, 1)


                x = np.arange(img.shape[0])
                y = np.arange(img.shape[1])
                x, y = np.meshgrid(x, y)
                xdata = (x.ravel(), y.ravel())
                ydata = img.T.ravel()

                coordinates = feature.peak_local_max(img, min_distance=20, exclude_border=2)
                if len(coordinates) < 1:
                    coordinates = [img.shape[1] / 2, img.shape[0] / 2]
                else:
                    coordinates = coordinates[0]

                try:
                    initial_guess = ( np.max(img) - np.min(img), coordinates[0], coordinates[1], 1, np.mean(img))
                    bounds = ((0, 0, 0, 0, -np.inf),
                              (np.inf, x.max(), y.max(), np.inf, np.inf))
                    popt, pcov = opt.curve_fit(gauss2D, xdata, ydata, p0=initial_guess, bounds=bounds)#, method='dogbox')
                    amp = popt[0]
                    sigma = popt[3]
                    perr =np.sqrt(np.diag(pcov))


                    plt.imshow(img.T)
                    plt.title('amp: '+str(np.round(amp,2))+' +- '+str(np.round(perr[0],5))+' | sigma: ' +str(np.round(sigma,2))+' +- '+str(np.round(perr[3],5)))
                    plt.savefig("search_max/autofocus_image.png")
                    plt.close()

                    if perr[3]/popt[3] > 0.1:
                        sigma = np.NaN
                        amp = np.NaN
                    if perr[0]/popt[0] > 0.1:
                        sigma = np.NaN
                        amp = np.NaN


                    if self.settings.autofocus_mode == 'gaussexport':
                        self.stage.query_pos()
                        plt.imshow(img.T)
                        plt.savefig("search_max/zmisc/"+str(np.round(self.stage.last_pos()[2],2))+".png")
                        plt.close()

                        np.savetxt("search_max/zmisc/"+str(np.round(self.stage.last_pos()[2],2))+".txt",img)

                        self.spectrometer.SetCentreWavelength(self.settings.centre_wavelength)
                        self.spectrometer.SetExposureTime(self.settings.integration_time)
                        #self.spectrometer.SetMinVertReadout(1)
                        self.spectrometer.SetMinVertReadout(self.settings.minvertreadout)
                        self.spectrometer.SetSlitWidth(self.settings.slit_width)

                        # self.searchthread = SearchThread(self.spectrometer, self.settings, self.stage)
                        # # self.searchthread.specSignal.connect(self.specslot)
                        # # self.searchthread.finishSignal.connect(self.search_finished)
                        # self.searchthread.search()
                        # self.searchthread.stop()
                        # self.searchthread = None
                        # self.stage.query_pos()

                        np.savetxt("search_max/zmisc/"+str(np.round(self.stage.last_pos()[2],2))+"_pos.txt",self.stage.last_pos())

                        spec = self.spectrometer.TakeSingleTrack()
                        wl = self.spectrometer.GetWavelength()
                        data = np.append(np.round(wl, 1).reshape(wl.shape[0], 1), spec.reshape(spec.shape[0], 1), 1)
                        with open("search_max/zmisc/"+str(np.round(self.stage.last_pos()[2],2))+"_spec.txt", 'w') as f:
                            f.write("wavelength,counts" + '\n')
                            for i in range(len(data)):
                                f.write(str(data[i][0]) + "," + str(data[i][1]) + '\n')

                        self.spectrometer.SetCentreWavelength(0)
                        self.spectrometer.SetExposureTime(self.settings.search_integration_time)
                        #self.spectrometer.SetMinVertReadout(20)
                        #self.spectrometer.SetMinVertReadout(1)
                        self.spectrometer.SetMinVertReadout(self.settings.minvertreadout)
                        self.spectrometer.SetSlitWidth(300)



                except (RuntimeError,ValueError) as e:
                    print(e)
                    plt.imshow(img.T)
                    plt.title('no fit')
                    plt.savefig("search_max/autofocus_image.png")
                    plt.close()

                    return 0
                if self.settings.autofocus_mode == 'gauss':
                    return amp/sigma
                elif self.settings.autofocus_mode == 'gausswidth':
                    return 1/sigma

            elif self.settings.autofocus_mode == 'maximum':
                self.spectrometer.SetCentreWavelength(0)
                self.spectrometer.SetExposureTime(self.settings.search_integration_time)

                # nikon arthur
                # self.spectrometer.SetMinVertReadout(16)
                # self.spectrometer.SetSlitWidth(150)

                # freespace
                #self.spectrometer.SetMinVertReadout(20)
                #self.spectrometer.SetMinVertReadout(1)
                self.spectrometer.SetMinVertReadout(self.settings.minvertreadout)
                self.spectrometer.SetSlitWidth(300)

                img = self.spectrometer.TakeSingleTrack(raw=True)[self.settings.min_ind_img:self.settings.max_ind_img,
                      :]

                # img = ndimage.median_filter(img, footprint=morphology.disk(3), mode="mirror")
                # img = ndimage.median_filter(img, 2)
                img = ndimage.gaussian_filter(img, 1)

                img = ndimage.median_filter(img, 2)
                amp = np.abs((img.max() - img.min()))

                plt.imshow(img.T)
                plt.title(str(np.abs((img.max() - img.mean()))))
                plt.savefig("search_max/autofocus_image.png")
                plt.close()

                return amp

            elif self.settings.autofocus_mode == 'zscan':
                self.spectrometer.SetExposureTime(self.settings.search_integration_time)
                spec = self.spectrometer.TakeSingleTrack()
                wl = self.spectrometer.GetWavelength()
                mask = (wl < (self.settings.zscan_centre+self.settings.zscan_width)) & (wl > (self.settings.zscan_centre-self.settings.zscan_width))
                spec = spec[mask]
                return np.mean(spec)


            else:
                print('Error setting Autofocus Mode !!!')


        self.stage.query_pos()
        startpos = self.stage.last_pos()
        d = np.linspace(-self.settings.rasterwidth, self.settings.rasterwidth, self.settings.rasterdim)
        pos = d * self.settings.zmult + startpos[2]

        focus = np.zeros(self.settings.rasterdim)

        self.progress = progress.Progress(max=len(pos))
        for k in range(len(pos)):
            self.stage.moveabs(z=pos[k])
            focus[k] = calc_f()

            self.progress.next()
            self.progressSignal.emit(self.progress.percent, str(self.progress.eta_td))

            if self.abort:
                self.stage.moveabs(z=startpos[2])
                self.spectrometer.SetCentreWavelength(self.settings.centre_wavelength)
                self.spectrometer.SetExposureTime(self.settings.integration_time)
                #self.spectrometer.SetMinVertReadout(1)
                self.spectrometer.SetMinVertReadout(self.settings.minvertreadout)
                self.spectrometer.SetSlitWidth(self.settings.slit_width)
                self.finishSignal.emit(np.array([]))
                self.stop()
                return



        valid_indices = focus > 0.01*np.nanmax(focus)
        focus = focus[valid_indices]
        pos = pos[valid_indices]
        focus -= focus.min()
        focus /= focus.max()

        focus_filt = savgol_filter(focus,3,1)
        maxind = np.argmax(focus)
        minval = np.min(focus)
        maxval = np.max(focus)


        # initial_guess = (maxval - minval, pos[maxind], 2.0, minval)
        # popt = None
        # try:
        #     popt, pcov = opt.curve_fit(gauss, pos, focus_filt, p0=initial_guess)
        #     perr = np.diag(pcov)
        #     # if perr[0] > 1e10 or perr[1] > 1 or perr[2] > 50:
        #     if perr[1] > 1:
        #         print("Could not determine focus: Variance too big")
        #         print(perr)
        #         popt = None
        #     # elif popt[0] < *0.1:
        #     #    print("Could not determine particle position: Peak too small")
        #     elif popt[1] < (min(pos) - 2.0) or popt[1] > (max(pos) + 2.0):
        #         print("Could not determine focus: Peak outside bounds")
        #         popt = None
        #     elif np.abs(popt[2]) < self.settings.sigma / 10000:
        #         print("Could not determine focus: Peak to narrow")
        #         popt = None
        #     #else:
        #         #return popt, perr, measured, maxwl
        # except RuntimeError as e:
        #     print(e)
        #     print("Could not determine focus: Fit error")
        #     popt = None

        indexes = peakutils.indexes(focus_filt, thres=0.5, min_dist=5)
        #print(pos[indexes])
        if len(indexes)>0:

            peakx = peakutils.interpolate(pos, focus_filt, ind=indexes,width=2)
            peaky = focus_filt[indexes]
            sorted_ind = np.argsort(peaky)
            peakx = peakx[sorted_ind[0]]
            peaky = peaky[sorted_ind[0]]


        x = np.linspace(min(pos), max(pos))
        fig = plt.figure()
        ax = fig.add_subplot(111)

        # if popt is not None:
        #     ax.text(0.1, 0.9, str(round(popt[1], 3)) + ' +- ' + str(round(perr[1], 3)), ha='left', va='center',
        #             transform=ax.transAxes)
        #     ax.plot(x, gauss(x, popt[0], popt[1], popt[2], popt[3]), 'g-')

        if len(indexes) > 0:
            print(peakx)
            ax.text(peakx, peaky/focus.max(), str(round(peakx, 3)), ha='left', va='center')
            ax.scatter(peakx,peaky/focus.max(),s=100,c="Red")

        ax.set_title("Focus")
        #ax.plot(pos, sigma, '.')
        #ax.plot(pos, focus, '.')
        ax.plot(pos, focus, 'o')
        ax.plot(pos, focus_filt, 'x')
        plt.savefig("search_max/autofocus.png")
        plt.close()

        # if popt is not None:
        #     self.stage.moveabs(z=popt[1])
        #     calc_f(plot=True)
        #     self.finishSignal.emit(np.array([popt[1],perr[1]]))
        # else:
        #     self.stage.moveabs(z=startpos[2])
        #     self.finishSignal.emit(np.array([]))

        if (len(indexes) > 0) and (peakx>1.0) :
            self.stage.moveabs(z=peakx)
            calc_f(plot=True)
            self.finishSignal.emit(np.array([peakx,0.0]))
        else:
            print("ERROR: Could not find focus position")
            self.stage.moveabs(z=startpos[2])
            self.finishSignal.emit(np.array([]))

        self.spectrometer.SetCentreWavelength(self.settings.centre_wavelength)
        #self.spectrometer.SetMinVertReadout(1)
        self.spectrometer.SetMinVertReadout(self.settings.minvertreadout)
        self.spectrometer.SetSlitWidth(self.settings.slit_width)
        self.spectrometer.SetExposureTime(self.settings.integration_time)


        self.stop()

    def work(self):
        self.focus()
        self.stop()




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

class TimeSeriesThread(MeasurementThread):
    saveSignal = QtCore.Signal(np.ndarray, str)

    def __init__(self, spectrometer, number_of_samples, parent=None):
        self.number_of_samples = number_of_samples
        super(TimeSeriesThread, self).__init__(spectrometer)
        self.init()

    def init(self):
        self.progress = progress.Progress(max=self.number_of_samples)
        self.i = 0
        self.abort = False
        self.series = np.zeros((self.spectrometer._width+1, self.number_of_samples), dtype=np.float)
        self.starttime = time.perf_counter()

    def work(self):
        spec = self.spectrometer.TakeSingleTrack()
        if spec is not None:
            self.series[0,self.i] = time.perf_counter() - self.starttime
            self.series[1:,self.i] = spec
            self.progress.next()
            self.progressSignal.emit(self.progress.percent, str(self.progress.eta_td))
            #self.saveSignal.emit(spec, str(self.i).zfill(5) + ".csv", np.array([]), False, False)
            self.i += 1
            if not self.abort:
                self.specSignal.emit(spec)
        else :
            self.stop()
            print("Communication out of sync, try again")
        if self.i >= (self.number_of_samples):
            if not self.abort:
                self.progressSignal.emit(100, str(self.progress.eta_td))
                self.saveSignal.emit(self.series, "timeseries.csv")
                self.finishSignal.emit(spec)
                self.stop()


class EndlessSeriesThread(MeasurementThread):
    saveSignal = QtCore.Signal(np.ndarray)

    def __init__(self, spectrometer, stage, settings,parent=None):
        super(EndlessSeriesThread, self).__init__(spectrometer)
        self.stage = stage
        self.settings = settings
        self.searchthread = None
        self.autofocusthread = None
        self.i = 0

    def stop(self):
        self.abort = True
        if self.searchthread is not None:
            self.searchthread.stop()
        if self.autofocusthread is not None:
            self.autofocusthread.stop()


    @QtCore.Slot(np.ndarray)
    def autofocus_finished(self, pos):
       with open("search_max/scan_status.txt", "a") as f:
            f.write(str(self.i)+': ')
            if len(pos) == 2:
                f.write("autofocus successful, ")
                f.write(str(round(pos[0],3))+' +- '+str(round(pos[1],5)))
            else:
                f.write("autofocus failed")
            f.write(' | ')

    @QtCore.Slot(np.ndarray)
    def search_finished(self, pos):
        with open("search_max/scan_status.txt", "a") as f:
            if len(pos) == 4:
                f.write("search successful, ")
                f.write("x:" + str(round(pos[0], 3)) + ' +- ' + str(round(pos[1], 5)))
                f.write(" y:" + str(round(pos[2], 3)) + ' +- ' + str(round(pos[3], 5)))
            else:
                f.write("search failed")
            f.write('\n')


    def work(self):
        #if self.i % 5 == 0:
        if not self.abort:
            self.autofocusthread = AutoFocusThread(self.spectrometer,self.settings,self.stage, self)
            self.autofocusthread.finishSignal.connect(self.autofocus_finished)
            self.autofocusthread.focus()
            self.autofocusthread.stop()
            self.autofocusthread = None

        if not self.abort:
            self.searchthread = SearchThread(self.spectrometer, self.settings, self.stage,None,None,None,self)
            self.searchthread.finishSignal.connect(self.search_finished)
            self.searchthread.search()
            self.searchthread.stop()
            self.searchthread = None


        if not self.abort:
            spec = self.spectrometer.TakeSingleTrack()
            if spec is not None:
                self.i += 1
                for i in range(self.settings.number_of_samples - 1):
                    spec += self.spectrometer.TakeSingleTrack()
                spec /= self.settings.number_of_samples

                if not self.abort:
                    self.specSignal.emit(spec)
                    self.saveSignal.emit(spec)
            else :
                self.stop()
                print("Communication out of sync, try again")

        if self.abort:
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
                ax.text(0.1, 0.9, str(round(popt[1],3)) + ' +- ' + str(round(perr[1],6)), ha='left', va='center', transform=ax.transAxes)
                ax.plot(x, gauss(x, popt[0], popt[1], popt[2], popt[3]), 'g-')
                ax.set_title(title)
            if not maxwl is None:
                ax2 = ax.twinx()
                ax2.plot(pos, maxwl, 'r.')
                ax2.set_ylabel('maxwl', color='r')
                ax2.tick_params('y', colors='r')
            plt.savefig("search_max/search_"+title+'_'+ str(j) + ".png")
            plt.close()


        def search_direction(direction, pos):
            measured = np.zeros(self.settings.rasterdim)
            maxwl = np.zeros(self.settings.rasterdim)

            for k in range(len(pos)):
                if direction == "x":
                    self.stage.moveabs(x=pos[k])
                elif  direction == "y":
                    self.stage.moveabs(y=pos[k])

                if self.abort:
                    self.stage.moveabs(x=startpos[0], y=startpos[1])
                    return None, None, None, None

                if self.settings.correct_search:
                    spec = self.get_spec()
                else:
                    spec = self.spectrometer.TakeSingleTrack()
                #spec = smooth(self.wl, spec)
                spec = savgol_filter(spec, 51, 1)
                self.specSignal.emit(spec)
                #measured[k] = np.max(spec[100:1900])
                measured[k] = np.sum(spec[100:1900])
                maxwl[k] = self.spectrometer.GetWavelength()[np.argmax(spec)]

            measured = savgol_filter(measured, 3, 1)
            maxind = np.argmax(measured)
            minval = np.min(measured)
            maxval = np.max(measured)
            sigma_start = self.settings.sigma
            initial_guess = (maxval - minval, pos[maxind], sigma_start, minval)
            try:
                popt, pcov = opt.curve_fit(gauss, pos, measured, p0=initial_guess)
                perr = np.diag(pcov)
                #if perr[0] > 1e10 or perr[1] > 1 or perr[2] > 50:
                if perr[1] > 1:
                    print("Could not determine particle position: Variance too big")
                    print(perr)
                #elif popt[0] < *0.1:
                #    print("Could not determine particle position: Peak too small")
                elif popt[1] < (min(pos) - 2.0) or popt[1] > (max(pos) + 2.0):
                    print("Could not determine particle position: Peak outside bounds")
                    print(popt)
                elif np.abs(popt[2]) < self.settings.sigma/100:
                    print("Could not determine particle position: Peak to narrow ")
                    print(popt)
                else:
                    return popt, perr, measured, maxwl
            except RuntimeError as e:
                print(e)
                print("Could not determine particle position: Fit error")
            return None, None, measured, None

        self.spectrometer.SetMinVertReadout(1)
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

        repetitions = 4
        self.progress = progress.Progress(max=repetitions)

        for j in range(repetitions):
            self.stage.query_pos()
            origin = self.stage.last_pos()

            if j in np.arange(0,repetitions,2):
                pos = d + origin[0]
                dir = "x"
            elif j in np.arange(1,repetitions,2):
                pos = d + origin[1]
                dir = "y"

            print("Iteration #: "+str(j)+"  Direction "+dir )

            popt, perr, measured, maxwl = search_direction(dir, pos)

            if self.abort:
                self.stage.moveabs(x=startpos[0], y=startpos[1])
                return False

            if popt is not None:
                if j in np.arange(0,repetitions,2):
                    dx = float(popt[1])
                    if dx-startpos[0] > self.settings.rasterwidth:
                        print("Position to far from start, skipping")
                        self.stage.moveabs(x=startpos[0])
                    else:
                        self.stage.moveabs(x=dx)
                        if perr[1] < 0.01:
                            ontargetx = True
                            targetx = np.array([popt[1],perr[1]])
                elif j in np.arange(1,repetitions,2):
                    dy = float(popt[1])
                    if dy-startpos[1] > self.settings.rasterwidth:
                        print("Position to far from start, skipping")
                        self.stage.moveabs(y=startpos[1])
                    else:
                        self.stage.moveabs(y=dy)
                        if perr[1] < 0.01:
                            ontargety = True
                            targety = np.array([popt[1],perr[1]])

                plot(dir,popt, perr, pos, measured, maxwl)

                if ontargetx and ontargety:
                    print("Particle localized, terminating early")
                    break

            else:
                if j in np.arange(0, repetitions, 2):
                    self.stage.moveabs(x=startpos[0])
                elif j in np.arange(1, repetitions, 2):
                    self.stage.moveabs(y=startpos[1])
                plot(dir, None, None, pos, measured, None)

            self.progress.next()
            self.progressSignal.emit(self.progress.percent, str(self.progress.eta_td))

        if ontargetx and ontargety:
            self.finishSignal.emit(np.append(targetx, targety))
        else:
            self.finishSignal.emit(np.array([]))

        self.spectrometer.SetExposureTime(self.settings.integration_time)
        self.spectrometer.SetMinVertReadout(self.settings.minvertreadout)


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
            self.stage.query_pos()
            self.starting_position = self.stage.last_pos()
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
        self.stage.moveabs(x=self.scanning_points[self.i, 0], y=self.scanning_points[self.i, 1],z=self.starting_position[2])
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
        self.autofocusthread = AutoFocusThread(self.spectrometer,self.settings,self.stage, self)
        self.autofocusthread.finishSignal.connect(self.focusfinishslot)

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
        self.autofocusthread.focus()
        self.searchthread.search()

    @QtCore.Slot(np.ndarray)
    def specslot(self, spec):
        self.specSignal.emit(spec)

    @QtCore.Slot(np.ndarray)
    def searchfinishslot(self, pos):
        print(pos)

    @QtCore.Slot(np.ndarray)
    def focusfinishslot(self, arr):
        pass


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
        if self.meanthread is not None:
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


class ScanTimeSeriesThread(ScanThread):
    saveSignal = QtCore.Signal(np.ndarray, str, np.ndarray, bool, bool)

    def __init__(self, spectrometer, settings, scanning_points, labels, stage, parent=None):
        super(ScanTimeSeriesThread, self).__init__(spectrometer, settings, scanning_points, labels, stage)
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
    def __init__(self, spectrometer, settings, scanning_points, labels, stage, with_search, with_autofocus, ref_spec = None, dark_spec = None, bg_spec=None, parent=None):
        super(ScanSearchMeanThread, self).__init__(spectrometer, settings, scanning_points, labels, stage)
        self.ref_spec = ref_spec
        self.dark_spec = dark_spec
        self.bg_spec = bg_spec
        self.searchthread = None
        self.meanthread = None
        self.autofocusthread = None
        #self.autofocusthread.finishSignal.connect(self.focusfinishslot)
        self.with_search = with_search
        self.with_autofocus = with_autofocus


    @QtCore.Slot()
    def stop(self):
        self.abort = True
        if self.searchthread is not None:
            self.searchthread.stop()
        if self.autofocusthread is not None:
            self.autofocusthread.stop()
        if self.meanthread is not None:
            self.meanthread.stop()
        #self.meanthread.thread.wait(self.settings.integration_time * 1000 + 500)
        #self.searchthread.thread.wait(self.settings.integration_time*1000+500)
        #super(ScanMeanThread, self).stop()
        #self.autofocusthread = None
        #self.searchthread = None
        #self.meanthread = None
        #super(ScanSearchMeanThread, self).stop()

    # def __del__(self):
    #     self.stop()
    #     #self.searchthread.specSignal.disconnect()
    #     super(ScanMeanThread, self).__del__()

    @QtCore.Slot(np.ndarray)
    def autofocus_finished(self, pos):
       with open("search_max/scan_status.txt", "a") as f:
            f.write(self.labels[self.i]+': ')
            if len(pos) == 2:
                f.write("autofocus successful, ")
                f.write(str(round(pos[0],3))+' +- '+str(round(pos[1],5)))
            else:
                f.write("autofocus failed")
            f.write(' | ')

    @QtCore.Slot(np.ndarray)
    def search_finished(self, pos):
        with open("search_max/scan_status.txt", "a") as f:
            if len(pos) == 4:
                f.write("search successful, ")
                f.write("x:" + str(round(pos[0], 3)) + ' +- ' + str(round(pos[1], 5)))
                f.write(" y:" + str(round(pos[2], 3)) + ' +- ' + str(round(pos[3], 5)))
            else:
                f.write("search failed")
            f.write('\n')

    def intermediatework(self):
        if (not self.abort) and (self.with_search):
            self.searchthread = SearchThread(self.spectrometer, self.settings, self.stage,self.ref_spec,self.dark_spec,self.bg_spec,self)
            self.searchthread.specSignal.connect(self.specslot)
            self.searchthread.finishSignal.connect(self.search_finished)
            self.searchthread.search()
            self.searchthread.stop()
            self.searchthread = None

        if (not self.abort) and (self.with_autofocus):
            self.autofocusthread = AutoFocusThread(self.spectrometer,self.settings,self.stage, self)
            self.autofocusthread.finishSignal.connect(self.autofocus_finished)
            self.autofocusthread.focus()
            self.autofocusthread.stop()
            self.autofocusthread = None

        # if (not self.abort) and (self.with_search):
        #     self.searchthread = SearchThread(self.spectrometer, self.settings, self.stage,self.ref_spec,self.dark_spec,self.bg_spec,self)
        #     self.searchthread.specSignal.connect(self.specslot)
        #     self.searchthread.finishSignal.connect(self.search_finished)
        #     self.searchthread.search()
        #     self.searchthread.stop()
        #     self.searchthread = None

        if not self.abort:
            self.initMeanThread()
            self.meanthread.init()
            self.meanthread.process()
            self.meanthread = None

        #self.searchthread.start()
        #self.searchthread.stop()
        #self.meanthread.init()
        #self.meanthread.start()
        #self.meanthread.stop()



class ScanSearchTimeSeriesThread(ScanMeanThread):
    def __init__(self, spectrometer, settings, scanning_points, labels, stage, ref_spec = None, dark_spec = None, bg_spec=None, parent=None):
        super(ScanSearchMeanThread, self).__init__(spectrometer, settings, scanning_points, labels, stage)
        self.ref_spec = ref_spec
        self.dark_spec = dark_spec
        self.bg_spec = bg_spec
        self.searchthread = None
        self.seriesthread = None
        self.autofocusthread = None
        #self.autofocusthread.finishSignal.connect(self.focusfinishslot)



    @QtCore.Slot()
    def stop(self):
        if self.searchthread is not None:
            self.searchthread.stop()
        if self.autofocusthread is not None:
            self.autofocusthread.stop()
        if self.meanthread is not None:
            self.meanthread.stop()
        #self.meanthread.thread.wait(self.settings.integration_time * 1000 + 500)
        #self.searchthread.thread.wait(self.settings.integration_time*1000+500)
        #super(ScanMeanThread, self).stop()
        #self.autofocusthread = None
        #self.searchthread = None
        #self.meanthread = None
        #super(ScanSearchMeanThread, self).stop()
        self.abort = True

    # def __del__(self):
    #     self.stop()
    #     #self.searchthread.specSignal.disconnect()
    #     super(ScanMeanThread, self).__del__()

    @QtCore.Slot(np.ndarray)
    def autofocus_finished(self, pos):
       with open("search_max/scan_status.txt", "a") as f:
            f.write(self.labels[self.i]+': ')
            if len(pos) == 2:
                f.write("autofocus successful, ")
                f.write(str(round(pos[0],3))+' +- '+str(round(pos[1],5)))
            else:
                f.write("autofocus failed")
            f.write(' | ')

    @QtCore.Slot(np.ndarray)
    def search_finished(self, pos):
        with open("search_max/scan_status.txt", "a") as f:
            if len(pos) == 4:
                f.write("search successful, ")
                f.write("x:" + str(round(pos[0], 3)) + ' +- ' + str(round(pos[1], 5)))
                f.write(" y:" + str(round(pos[2], 3)) + ' +- ' + str(round(pos[3], 5)))
            else:
                f.write("search failed")
            f.write('\n')

    def intermediatework(self):
        if not self.abort:
            self.autofocusthread = AutoFocusThread(self.spectrometer,self.settings,self.stage, self)
            self.autofocusthread.finishSignal.connect(self.autofocus_finished)
            self.autofocusthread.focus()
            self.autofocusthread.stop()
            self.autofocusthread = None

        if not self.abort:
            self.searchthread = SearchThread(self.spectrometer, self.settings, self.stage,self.ref_spec,self.dark_spec,self.bg_spec,self)
            self.searchthread.specSignal.connect(self.specslot)
            self.searchthread.finishSignal.connect(self.search_finished)
            self.searchthread.search()
            self.searchthread.stop()
            self.searchthread = None

        if not self.abort:
            self.initMeanThread()
            self.meanthread.init()
            self.meanthread.process()
            self.meanthread = None
