__author__ = 'sei'

from spectrumthreads import *
import numpy as np
from datetime import datetime
from qtpy import QtCore
import time
from AndorSpectrometer import Spectrometer

# eol={"win32":"\n", 'linux':"\n" }
# platform=sys.platform
# eol= eol[platform]
eol = "\n"


class Spectrum(QtCore.QObject):
    specSignal = QtCore.Signal(np.ndarray)
    updatePositions = QtCore.Signal(np.ndarray)

    updateStatus = QtCore.Signal(str)
    updateProgress = QtCore.Signal(float)
    disableButtons = QtCore.Signal()
    enableButtons = QtCore.Signal()
    set_autofocus_ontarget = QtCore.Signal(bool)
    set_searchmax_ontarget = QtCore.Signal(bool)

    def __init__(self, spectrometer, stage, settings):
        super(Spectrum, self).__init__(None)
        self.spectrometer = None

        self.settings = settings
        self.stage = stage
        self.spectrometer = spectrometer
        
        self._cycle_time_start = 60
        self._data = None
        self.prev_time = None

        # variables for storing the spectra
        self.lamp = None
        self.dark = None
        self.mean = None
        self.bg = None
        self.lockin = None

        self._spec = None

        self.worker = None

    def __del__(self):
        if not self.worker is None:
            self.worker.stop()
            self.worker = None

    def correct_spectrum(self, spec):
        if not self.dark is None and not self.lamp is None and not self.bg is None:
            return (spec - self.bg) / (self.lamp - self.dark)

        elif not self.dark is None and not self.lamp is None:
            return 1 - ( (spec - self.dark) / (self.lamp - self.dark) )

        elif not self.dark is None:
            return spec - self.dark

        elif not self.bg is None:
            return spec - self.bg

        else:
            return spec


    @QtCore.Slot(float, str)
    def progressCallback(self, progress, eta):
        self.updateProgress.emit(progress)
        self.updateStatus.emit('ETA: ' + eta)

    @QtCore.Slot(np.ndarray)
    def specCallback(self, spec):
        self._spec = spec
        self.specSignal.emit(spec)

    def get_wl(self):
        return self.spectrometer.GetWavelength()

    def stop_process(self):
        try:
            self.worker.stop()
            self.thread.quit()
            # if  self.workingthread.thread.wait(self.settings.integration_time*1000+500):
            #     self.workingthread = None
            # else:
            #     print("problem with thread")
            print(self.thread.wait())
            self.thread = None
            #self._spectrometer.AbortAcquisition()
        except Exception as e:
            print(e)
        self.enableButtons.emit()

    def start_process(self, worker):
        self.thread = QtCore.QThread(self)
        worker.moveToThread(self.thread)
        self.thread.started.connect(worker.process)
        self.thread.finished.connect(worker.stop)
        self.thread.start()


    def start_autofocus(self):
        self.worker = AutoFocusThread(self.spectrometer, self.settings, self.stage)
        self.worker.finishSignal.connect(self.finishedAutofocus)
        self.worker.progressSignal.connect(self.progressCallback)
        #self.worker.specSignal.connect(self.specCallback)
        self.start_process(self.worker)


    def take_live(self):

        self.worker = LiveThread(self.spectrometer)
        self.worker.specSignal.connect(self.specCallback)
        self.start_process(self.worker)

    def take_live_image(self):
        # self.workingthread = LiveThread(self.getspecthread)
        self.worker = ImageThread(self.spectrometer)
        self.worker.specSignal.connect(self.specCallback)
        self.start_process(self.worker)

    def take_live_fullimage(self):
        # self.workingthread = LiveThread(self.getspecthread)
        self.worker = FullImageThread(self.spectrometer)
        self.worker.specSignal.connect(self.specCallback)
        self.start_process(self.worker)

    @QtCore.Slot(np.ndarray)
    def finishedLockinCallback(self, spec):
        self.stop_process()
        self.lockin = spec
        #self.enableButtons.emit()
        self.updateStatus.emit('Lockin Spectrum acquired')

    @QtCore.Slot(np.ndarray)
    def finishedTimeSeriesCallback(self, spec):
        self.stop_process()
        # self.enableButtons.emit()
        self.updateStatus.emit('Lockin Spectrum acquired')

    @QtCore.Slot(np.ndarray)
    def finishedDarkCallback(self, spec):
        self.stop_process()
        self.dark = spec
        #self.enableButtons.emit()
        self.updateStatus.emit('Dark Spectrum acquired')

    @QtCore.Slot(np.ndarray)
    def finishedLampCallback(self, spec):
        self.stop_process()
        self.lamp = spec
        #self.enableButtons.emit()
        self.updateStatus.emit('Lamp Spectrum acquired')

    @QtCore.Slot(np.ndarray)
    def finishedMeanCallback(self, spec):
        self.stop_process()
        self.mean = spec
        #self.enableButtons.emit()
        self.updateStatus.emit('Mean Spectrum acquired')

    @QtCore.Slot(np.ndarray)
    def finishedBGCallback(self, spec):
        self.stop_process()
        self.bg = spec
        #self.enableButtons.emit()
        self.updateStatus.emit('Background Spectrum acquired')

    def startMeanThread(self):
        self.worker = MeanThread(self.spectrometer, self.settings.number_of_samples)
        self.worker.specSignal.connect(self.specCallback)
        self.worker.progressSignal.connect(self.progressCallback)

    def take_dark(self):
        self.startMeanThread()
        self.worker.finishSignal.connect(self.finishedDarkCallback)
        self.start_process(self.worker)

    def take_lamp(self):
        self.startMeanThread()
        self.worker.finishSignal.connect(self.finishedLampCallback)
        self.start_process(self.worker)

    def take_mean(self):
        self.startMeanThread()
        self.worker.finishSignal.connect(self.finishedMeanCallback)
        self.start_process(self.worker)

    def take_bg(self):
        self.startMeanThread()
        self.worker.finishSignal.connect(self.finishedBGCallback)
        self.start_process(self.worker)

    def take_lockin(self):
        self.worker = LockinThread(self.spectrometer, self.settings, self.stage)
        self.worker.specSignal.connect(self.specCallback)
        self.worker.progressSignal.connect(self.progressCallback)
        self.worker.finishSignal.connect(self.finishedLockinCallback)
        self.start_process(self.worker)

    def take_series(self, savedir):
        self.save_path = savedir
        self.save_data(savedir)

        self.worker = TimeSeriesThread(self.spectrometer, self.settings.number_of_samples)

        self.worker.specSignal.connect(self.specCallback)
        self.worker.progressSignal.connect(self.progressCallback)
        #self.worker.saveSignal.connect(self.save_spectrum)
        self.worker.saveSignal.connect(self.save_timeseries_data)
        self.worker.finishSignal.connect(self.finishedTimeSeriesCallback)
        self.start_process(self.worker)


    def search_max(self):
        print(self.settings.search_integration_time)
        self.worker = SearchThread(self.spectrometer, self.settings, self.stage, self.lamp, self.dark, self.bg)
        self.worker.specSignal.connect(self.specCallback)
        self.worker.progressSignal.connect(self.progressCallback)
        self.worker.finishSignal.connect(self.finishedSearch)
        self.start_process(self.worker)

    def scan_search_max(self, pos, labels):
        # self.stage.query_pos()
        # x, y, z = self.stage.last_pos()
        # pos = np.matrix([[x, y]])
        self.positions = pos
        self.save_path = "search_max/"
        self.worker = ScanSearchThread(self.spectrometer, self.settings, pos, labels, self.stage, self.lamp, self.dark, self.bg)
        self.worker.specSignal.connect(self.specCallback)
        self.worker.progressSignal.connect(self.progressCallback)
        self.worker.finishSignal.connect(self.finishedScanSearch)
        self.start_process(self.worker)

    @QtCore.Slot(np.ndarray)
    def finishedAutofocus(self, pos):
        #self._spectrometer.SetCentreWavelength(self.settings.centre_wavelength)
        #self._spectrometer.SetSlitWidth(self.settings.slit_width)
        self.stop_process()
        #self.enableButtons.emit()
        if len(pos) > 0:
            self.set_autofocus_ontarget.emit(True)
        self.updateStatus.emit('Autofocus finished')

    @QtCore.Slot(np.ndarray)
    def finishedSearch(self, pos):
        self.stop_process()
        #self.enableButtons.emit()
        if len(pos) > 0:
            self.set_searchmax_ontarget.emit(True)
        self.updateStatus.emit('Search finished')

    @QtCore.Slot(np.ndarray)
    def finishedScanSearch(self, pos):
        grid, = plt.plot(self.positions[:, 0], self.positions[:, 1], "r.")
        search, = plt.plot(pos[:, 0], pos[:, 1], "bx")
        plt.legend([grid, search], ["Calculated Grid", "Searched Positions"], bbox_to_anchor=(0., 1.02, 1., .102),
                   loc=3, ncol=2, mode="expand", borderaxespad=0.)
        plt.savefig(self.save_path + "grid.png")
        plt.close()
        #self.enableButtons.emit()
        self.stop_process()
        self.updateStatus.emit('Scan Search finished')
        self.updatePositions.emit(pos)

    def take_scan(self, positions, labels, savedir, with_lockin, with_search):
        self.save_path = savedir
        self.save_data(savedir)
        self.positions = positions
        if with_lockin:
            return True
        elif with_search:
            self.worker = ScanSearchMeanThread(self.spectrometer, self.settings, positions, labels, self.stage, self.lamp, self.dark, self.bg)
        else:
            self.worker = ScanMeanThread(self.spectrometer, self.settings, positions, labels, self.stage)
            #self.workingthread = ScanThread(self._spectrometer, self.settings, positions, self.stage)

        self.worker.finishSignal.connect(self.finishedScanMean)
        self.worker.saveSignal.connect(self.save_spectrum)
        self.worker.specSignal.connect(self.specCallback)
        self.worker.progressSignal.connect(self.progressCallback)
        self.start_process(self.worker)

    def take_scan3d(self, positions, file):
        self.positions = positions
        self.worker = Scan3DThread(self.spectrometer, self.settings, positions, file, self.stage)

        self.worker.finishSignal.connect(self.finishedScan3d)
        #self.workingthread.saveSignal.connect(self.save_spectrum)
        self.worker.specSignal.connect(self.specCallback)
        self.worker.progressSignal.connect(self.progressCallback)
        self.start_process(self.worker)


    @QtCore.Slot(np.ndarray)
    def finishedScan3d(self):
        #self.enableButtons.emit()
        self.stop_process()
        self.updateStatus.emit('Scan Mean finished')


    @QtCore.Slot(np.ndarray)
    def finishedScanMean(self, pos):
        grid, = plt.plot(self.positions[:, 0], self.positions[:, 1], "r.")
        search, = plt.plot(pos[:, 0], pos[:, 1], "bx")
        plt.legend([grid, search], ["Calculated Grid", "Searched Positions"], bbox_to_anchor=(0., 1.02, 1., .102),
                   loc=3, ncol=2, mode="expand", borderaxespad=0.)
        plt.savefig(self.save_path + "grid.png")
        plt.close()
        #self.enableButtons.emit()
        self.stop_process()
        self.updateStatus.emit('Scan Mean finished')

    def save_data(self, prefix):
        self.save_path = prefix
        # filename = self._gen_filename()
        # if not self._data is None:
        #    cols = ('t', 'ref') + tuple(map(str, np.round(self._wl, 1)))
        #    data = pandas.DataFrame(self._data, columns=cols)
        #    data.to_csv(prefix + 'spectrum_' + filename, header=True, index=False)
        if not self.dark is None:
            self.save_spectrum(self.dark, 'dark.csv', None, False, False)
        if not self.lamp is None:
            self.save_spectrum(self.lamp, 'lamp.csv', None, False, False)
        if not self.mean is None:
            self.save_spectrum(self.mean, 'normal.csv', None, False, False)
        if not self.bg is None:
            self.save_spectrum(self.bg, 'background.csv', None, False, False)
        if not self.lockin is None:
            #self.save_spectrum(self.lockin, 'lockin.csv', None, True, False)
            self.save_lockin_data(self.lockin, 'lockin.csv')

    @QtCore.Slot(np.ndarray, str, np.ndarray, bool, bool)
    def save_spectrum(self, spec, filename, pos, islockin, isfullPath):
        wl = self.spectrometer.GetWavelength()
        data = np.append(np.round(wl, 1).reshape(wl.shape[0], 1), spec.reshape(spec.shape[0], 1), 1)
        if isfullPath:
            f = open(filename, 'w')
        else:
            f = open(self.save_path + filename, 'w')

        f.write(str(datetime.now().day).zfill(2) + "." + str(datetime.now().month).zfill(2) + "." + str(
            datetime.now().year) + eol)
        f.write(str(datetime.now().hour).zfill(2) + ":" + str(datetime.now().minute).zfill(2) + ":" + str(
            datetime.now().second).zfill(2) + ":" + str(datetime.now().microsecond).zfill(2) + eol)
        f.write("integration time [s]" + eol)
        f.write(str(self.settings.integration_time) + eol)
        f.write("number of samples" + eol)
        f.write(str(self.settings.number_of_samples) + eol)
        if islockin:
            f.write("amplitude" + eol)
            f.write(str(self.settings.amplitude) + eol)
            f.write("frequency" + eol)
            f.write(str(self.settings.f) + eol)
        else:
            f.write(eol)
            f.write(eol)
            f.write(eol)
            f.write(eol)

        if pos is not None:
            if len(pos) > 0:
                f.write("x" + eol)
                f.write(str(pos[0]) + eol)
                f.write("y" + eol)
                f.write(str(pos[1]) + eol)
            else:
                f.write(eol)
                f.write(eol)
                f.write(eol)
                f.write(eol)
        else:
            f.write(eol)
            f.write(eol)
            f.write(eol)
            f.write(eol)

        f.write(eol)
        f.write("wavelength,counts" + eol)
        for i in range(len(data)):
            f.write(str(data[i][0]) + "," + str(data[i][1]) + eol)

        f.close()

    @QtCore.Slot(np.ndarray, str)
    def save_lockin_data(self, spec, filename):
        wl = self.spectrometer.GetWavelength()
        data = np.hstack((np.round(wl, 1).reshape(wl.shape[0], 1), spec))
        np.savetxt(self.save_path + filename, data, delimiter="\t")


    @QtCore.Slot(np.ndarray, str)
    def save_timeseries_data(self, spec, filename):
        wl = self.spectrometer.GetWavelength()
        wl = np.append([0.0],wl)
        data = np.hstack((np.round(wl, 1).reshape(wl.shape[0], 1), spec))
        np.savetxt(self.save_path + filename, data, delimiter="\t")


    def reset(self):
        self.dark = None
        self.lamp = None
        self.lockin = None
        self.mean = None
        self.bg = None

    # def plot_last_mean(self):
    #     spec = self.correct_spectrum(self.mean)
    #
    #     try:
    #         os.mkdir(savedir + "overview/")
    #     except:
    #         pass