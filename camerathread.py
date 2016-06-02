import sys
import time

import numpy as np
import ximea as xi
from PyQt5.QtCore import pyqtSlot, QThread, pyqtSignal, QObject#, QMutex


class CameraThread(QObject):
    ImageReadySignal = pyqtSignal(np.ndarray)
    exposure_us = 100000.0
    #mutex = QMutex()
    enabled = False

    def __init__(self, parent=None):
        if getattr(self.__class__, '_has_instance', False):
            RuntimeError('Cannot create another instance of Camera')
        self.__class__._has_instance = True
        self.isinitialized = False
        super(CameraThread, self).__init__(parent)
        self._cam = None
        try:
            self.abort = False
            self.thread = QThread()
            num_dev = xi.get_device_count()

            if num_dev > 0:
                print(xi.get_device_info(0, 'device_name'))

                self._cam = xi.Xi_Camera(DevID=0)
                self._cam.set_debug_level("Warning")
                self._cam.set_param('exposure', self.exposure_us)
                self._cam.set_param('aeag', 1)
                self._cam.set_param('exp_priority', 0)
                self._cam.set_param('binning',4)
                self._cam.set_param('imgdataformat',2)
                self._cam.get_image()

                self.thread.started.connect(self.process)
                self.thread.finished.connect(self.stop)
                self.moveToThread(self.thread)
                self.isinitialized = True
        except:
            (type, value, traceback) = sys.exc_info()
            sys.excepthook(type, value, traceback)

    def __del__(self):
        self.abort = True
        self.__class__.has_instance = False
        try:
            if not self._cam is None:
                self._cam.close()
            self.ImageReadySignal.disconnect()
        except TypeError:
            pass

    def setexposure(self, us):
        self.exposure_us = us
        self._cam.set_param('exposure', us)

    def start(self):
        self.thread.start()

    def enable(self):
        self.enabled = True

    def disable(self):
        self.enabled = False

    @pyqtSlot()
    def stop(self):
        self.abort = True

    def work(self):
        if self.enabled:
            img = self._cam.get_image()
            self.ImageReadySignal.emit(img)

    @pyqtSlot()
    def process(self):
        while not self.abort:
            try:
                time.sleep(self.exposure_us / 1e6)
                self.work()
            except:
                (type, value, traceback) = sys.exc_info()
                sys.excepthook(type, value, traceback)
        #self._cam.stop_aquisition()