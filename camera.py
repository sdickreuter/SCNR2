from PyQt5.QtCore import pyqtSlot, QThread, QMutex, QWaitCondition, pyqtSignal, QObject, QTimer
import sys
import numpy as np
import ximea as xi
import time

class Camera(QObject):
    ImageReadySignal = pyqtSignal(np.ndarray)
    exposure_us = 10000.0


    def __init__(self, parent=None):
        if getattr(self.__class__, '_has_instance', False):
            RuntimeError('Cannot create another instance of Camera')
        self.__class__._has_instance = True

        try:
            super(Camera, self).__init__(parent)
            self.abort = False
            self.thread = QThread()
            print(xi.get_device_count())
            print(xi.get_device_info(0, 'device_name'))

            self._cam = xi.Xi_Camera(DevID=0)
            self._cam.set_debug_level("Warning")
            self._cam.set_param('exposure', self.exposure_us)
            self._cam.set_param('aeag', 1)
            self._cam.set_param('exp_priority', 0)

            self.thread.started.connect(self.process)
            self.thread.finished.connect(self.stop)
            self.moveToThread(self.thread)
        except:
            (type, value, traceback) = sys.exc_info()
            sys.excepthook(type, value, traceback)

    def __del__(self):
        self.abort = True
        self._cam.close()
        self.__class__.has_instance = False
        try:
            self.ImageReadySignal.disconnect()
        except TypeError:
            pass

    def getimage(self):
        return self._cam.get_image()

    def setexposure(self,us):
        self.exposure_us = us
        self._cam.set_param('exposure', us)

    def start(self):
        self.thread.start()

    @pyqtSlot()
    def stop(self):
        self.abort = True

    def work(self):
        img = self._cam.get_image()
        self.ImageReadySignal.emit(img)

    @pyqtSlot()
    def process(self):
        while not self.abort:
            try:
                time.sleep(self.exposure_us/1e6)
                self.work()
            except:
                (type, value, traceback) = sys.exc_info()
                sys.excepthook(type, value, traceback)








class GamepadThread(QObject):
    ASignal = pyqtSignal()
    BSignal = pyqtSignal()
    XSignal = pyqtSignal()
    YSignal = pyqtSignal()

    def __init__(self, parent=None):
        if getattr(self.__class__, '_has_instance', False):
            RuntimeError('Cannot create another instance')
        self.__class__._has_instance = True
        try:
            super(GamepadThread, self).__init__(parent)
            self.abort = False
            self.thread = QThread()
            #try:
            self.pad = pygamepad.Gamepad()
            #except:
            #    print("Could not initialize Gamepad")
            #    self.pad = None
            #else:
            self.thread.started.connect(self.process)
            self.thread.finished.connect(self.stop)
            self.moveToThread(self.thread)
        except:
            (type, value, traceback) = sys.exc_info()
            sys.excepthook(type, value, traceback)

    def start(self):
        self.thread.start(QThread.HighPriority)

    @pyqtSlot()
    def stop(self):
        self.abort = True

    def check_Analog(self):
        return (self.pad.get_analogL_x(),self.pad.get_analogL_y())

    def __del__(self):
        self.__class__.has_instance = False
        try:
            self.ASignal.disconnect()
            self.BSignal.disconnect()
            self.XSignal.disconnect()
            self.YSignal.disconnect()
        except TypeError:
            pass
        self.abort = True

    def work(self):
        self.pad._read_gamepad()
        if self.pad.changed:
            if self.pad.A_was_released():
                self.ASignal.emit()
            if self.pad.B_was_released():
                self.BSignal.emit()
            if self.pad.X_was_released():
                self.XSignal.emit()
            if self.pad.Y_was_released():
                self.YSignal.emit()

    @pyqtSlot()
    def process(self):
        while not self.abort:
            try:
                self.work()
            except:
                (type, value, traceback) = sys.exc_info()
                sys.excepthook(type, value, traceback)
