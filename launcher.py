import os
import sys
import time
import multiprocessing as mp
import queue
#import sharedmem as shm

from PyQt5.QtCore import pyqtSlot, QTimer
from PyQt5.QtWidgets import QApplication, QMainWindow
import pyqtgraph as pg
import numpy as np
import ctypes

#import scnr2

class Example(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.statusBar().showMessage('Ready')

        self.setGeometry(300, 300, 250, 150)
        self.setWindowTitle('Statusbar')
        self.show()

class StatusProcess(mp.Process):

    def __init__(self, status_queue, command_queue):
        mp.Process.__init__(self)
        self.status_queue = status_queue
        self.command_queue = command_queue

    def send_status(self, status):
        self.status_queue.put((self.pid,status))

    def saferun(self):
        # Overwrite this method
        pass

    def run(self):
        try:
            self.saferun()
        except Exception as e:
            self.send_status(e)
            self.terminate()
            raise e
        return


class SpectrometerProcess(StatusProcess):
    spectrometer = None

    def __init__(self, status_queue, command_queue, spec):
        super(SpectrometerProcess, self).__init__(status_queue,command_queue)
        self.spec = spec

    def saferun(self):
        while True:
            msg, param = self.command_queue.get()
            print(msg + ' ' + str(param))

            if msg == '?':
                self.send_status('!')
            elif msg == 'quit':
                print('Quiting by request of client')
                # self.running = False
                raise KeyboardInterrupt()

            elif msg == 'test':
                self.spec[0] += param
                self.send_status('ok')

            elif msg == 'getwidth':
                self.send_status(self.spectrometer._width)

            elif msg == 'gettemperature':
                self.send_status(self.spectrometer.GetTemperature())

            elif msg == 'getslitwidth':
                self.send_status(self.spectrometer.GetSlitWidth())

            elif msg == 'getgratinginfo':
                self.send_status(self.spectrometer.GetGratingInfo())

            elif msg == 'getgrating':
                self.send_status(self.spectrometer.GetGrating())

            elif msg == 'setgrating':
                self.spectrometer.SetGrating(param)
                self.send_status('ok')

            elif msg == 'abortacquisition':
                self.spectrometer.AbortAcquisition()
                self.send_status('ok')

            elif msg == 'setnumberaccumulations':
                self.spectrometer.SetNumberAccumulations(param)
                self.send_status('ok')

            elif msg == 'setexposuretime':
                self.spectrometer.SetExposureTime(param)
                self.send_status('ok')

            elif msg == 'setslitwidth':
                self.spectrometer.SetSlitWidth(param)
                self.send_status('ok')

            elif msg == 'getwavelength':
                self.send_status(self.spectrometer.GetWavelength())

            elif msg == 'setfullimage':
                self.spectrometer.SetFullImage()
                self.send_status('ok')

            elif msg == 'takefullimage':
                self.send_status(self.spectrometer.TakeFullImage())

            elif msg == 'setcentrewavelength':
                self.spectrometer.SetCentreWavelength(param)
                self.send_status('ok')

            elif msg == 'setimageofslit':
                self.spectrometer.SetImageofSlit()
                self.send_status('ok')

            elif msg == 'takeimageofslit':
                self.send_status(self.spectrometer.TakeImageofSlit())

            elif msg == 'setsingletrack':
                hstart, hstop = param
                self.spectrometer.SetSingleTrack(hstart, hstop)
                self.send_status('ok')

            elif msg == 'takesingletrack':
                self.send_status(self.spectrometer.TakeSingleTrack())

            else:
                self.send_status('?')



class SpectrometerController:

    def __init__(self, status_queue, command_queue):
        self.status = status_queue
        self.com = command_queue

    def make_request(self, req, param):
        self.com.put((req,param))
        pid, status = self.status.get()
        return status

    def test(self):
        return self.make_request('test',1)

    def GetWidth(self):
        return self.make_request('getwidth', None)

    def GetTemperature(self):
        return self.make_request('gettemperature',None)

    def GetSlitWidth(self):
        return self.make_request('getslitwidth',None)

    def GetGratingInfo(self):
        return self.make_request('getgratinginfo',None)

    def GetGrating(self):
        return self.make_request('getgrating',None)

    def SetGrating(self, grating):
        ret = self.make_request('setgrating',grating)
        if not ret == 'ok':
            print('Communication Error')

    def AbortAcquisition(self):
        ret = self.make_request('abortacquisition',None)
        if not ret == 'ok':
            print('Communication Error')

    def SetNumberAccumulations(self, number):
        ret = self.make_request('setnumberaccumulations',number)
        if not ret == 'ok':
            print('Communication Error')

    def SetExposureTime(self, seconds):
        ret = self.make_request('setexposuretime',seconds)
        if not ret == 'ok':
            print('Communication Error')

    def SetSlitWidth(self, slitwidth):
        ret = self.make_request('setslitwidth',slitwidth)
        if not ret == 'ok':
            print('Communication Error')

    def _GetWavelength(self):
        return self.make_request('getwavelength',None)

    def GetWavelength(self):
        return self.wl

    def SetFullImage(self):
        self.mode = 'Image'
        ret = self.make_request('setfullimage',None)
        if not ret == 'ok':
            print('Communication Error')

    def TakeFullImage(self):
        return self.make_request('takefullimage',None)

    def SetCentreWavelength(self, wavelength):
        ret = self.make_request('setcentrewavelength',wavelength)
        self.wl = self._GetWavelength()
        if not ret == 'ok':
            print('Communication Error')

    def SetImageofSlit(self):
        self.mode = 'Image'
        ret = self.make_request('setimageofslit',None)
        if not ret == 'ok':
            print('Communication Error')

    def TakeImageofSlit(self):
        return self.make_request('takeimageofslit',None)


    def SetSingleTrack(self, hstart=None, hstop=None):
        self.mode = 'SingleTrack'
        ret = self.make_request('setsingletrack',(hstart,hstop))
        if not ret == 'ok':
            print('Communication Error')

    def TakeSingleTrack(self):
        return self.make_request('takesingletrack',None)



class GuiProcess(StatusProcess):

    def __init__(self, status_queue, command_queue, spec):
        super(GuiProcess, self).__init__(status_queue,command_queue)
        self.spec = spec
        self.controller = SpectrometerController(status_queue, command_queue)

    @pyqtSlot()
    def update(self):
        print("update")
        self.controller.test()
        spec = np.ctypeslib.as_array(self.spec.get_obj())
        print(spec)
        self.curve.setData(spec)

    def saferun(self):
        try:
            # app = QApplication([])
            # main = Example()
            # main.show()
            # main.raise_()
            # app.exec_()
            app = QApplication([])
            self.p = pg.plot()
            self.p.setWindowTitle('pyqtgraph example: PlotSpeedTest')
            self.curve = self.p.plot()
            self.timer = QTimer()
            self.timer.timeout.connect(self.update)
            self.timer.start(500)
            app.exec_()
        finally:
            pass
            # self.send_status('quit')

if __name__ == '__main__':
    mp.set_start_method('spawn')

    status1 = mp.Queue()
    status2 = mp.Queue()

    com1 = mp.Queue()
    com2 = mp.Queue()

    N = 10
    spec = mp.Array(ctypes.c_double, N)

    img_shared = mp.Array(ctypes.c_double, N*N)
    #img = np.ctypeslib.as_array(img_shared.get_obj())
    #img = img.reshape(N,N)

    proc1 = SpectrometerProcess(status1,com1,spec)
    proc1.daemon = True
    proc1.start()

    proc2 = GuiProcess(status1, com1, spec)

    count = 0
    try:
        while True:

            #print(cont.make_request("?",None))
            #time.sleep(1)
            #print(cont.test())
            #print(spec)
            #time.sleep(1)

            if not proc2.is_alive():
                proc2 = GuiProcess(status1, com1,spec)
                proc2.daemon = True
                proc2.start()
            # else:
            #     try:
            #         pid, status = status2.get(block=False)
            #         print((pid,status))
            #         if status == "quit":
            #             proc2.join(1)
            #             proc2.terminate()
            #     except queue.Empty:
            #         pass
            time.sleep(1)

    except KeyboardInterrupt:
        print('Quitting')
        proc1.terminate()
        proc2.terminate()
        sys.exit(0)


# if __name__ == '__main__':
#
#     try:
#         app = QApplication(sys.argv)
#         main = scnr2.Ui_MainWindow()
#         main.show()
#     except Exception as e:
#         print(e)
#         sys.exit(1)
#
#     try:
#         res = app.exec()
#     except Exception as e:
#         print(e)
#         sys.exit(1)
#     finally:
#         pass
#
#     sys.exit(0)
