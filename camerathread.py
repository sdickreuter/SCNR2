import sys
import time

import numpy as np
import ximea as xi
from qtpy import QtCore


class CameraThread(QtCore.QObject):
    ImageReadySignal = QtCore.Signal(np.ndarray)
    exposure_us = 150000
    #mutex = QtCore.QMutex()
    enabled = False

    def __init__(self,xflip = False,yflip = False, parent=None):
        if getattr(self.__class__, '_has_instance', False):
            RuntimeError('Cannot create another instance of Camera')
        self.__class__._has_instance = True

        self.yflip = yflip
        self.xflip = xflip

        self.isinitialized = False
        super(CameraThread, self).__init__(parent)
        self._cam = None
        try:
            self.abort = False
            self.thread = QtCore.QThread()
            num_dev = xi.get_device_count()

            if num_dev > 0:
                print(xi.get_device_info(0, 'device_name'))

                self._cam = xi.Xi_Camera(DevID=0)
                self._cam.set_debug_level("Error")
                self._cam.set_param('exposure', self.exposure_us)
                self._cam.set_param('aeag', 0)
                self._cam.set_param('exp_priority', 0)
                self._cam.set_binning(2, skipping=False)
                #self._cam.set_param('imgdataformat',2) # RGB24
                #self._cam.set_param('imgdataformat', 6) # RAW16 (monochrome)
                self._cam.set_param('imgdataformat', 1) # MONO16

                #self._cam.set_param('buffers_queue_size',1)
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
        except TypeError as e:
            print(e)

    def set_exposure(self, us):
        self.exposure_us = us
        self._cam.set_param('exposure', us)

    def get_exposure(self):
        us = self._cam.get_param('exposure')
        return us

    def start(self):
        self.thread.start()

    def enable(self):
        self.enabled = True

    def disable(self):
        self.enabled = False

    @QtCore.Slot()
    def stop(self):
        self.abort = True

    def get_image(self):
        # if self.enabled:
        #     self.enabled = False
        #     img = self._cam.get_image()
        #     self.enabled = True
        # else:
        #     img = self._cam.get_image()

        img = np.array(self._cam.get_image(),dtype = np.int32)
        img = img[:,:,0] + np.left_shift(img[:,:,1],8)

        if self.xflip:
            img = np.flipud(img)
        if self.yflip:
            img = np.fliplr(img)

        return img

    def work(self):
        if self.enabled:
            img = np.array(self._cam.get_image(),dtype = np.int32)
            img = img[:,:,0] + np.left_shift(img[:,:,1],8)
            if self.xflip:
                img = np.flipud(img)
            if self.yflip:
                img= np.fliplr(img)

            self.ImageReadySignal.emit(img)

    @QtCore.Slot()
    def process(self):
        while not self.abort:
            try:
                t = self.exposure_us / 1e6
                if t > 0.1 :
                    time.sleep(t)
                else:
                    time.sleep(0.1)
                self.work()
            except:
                (type, value, traceback) = sys.exc_info()
                sys.excepthook(type, value, traceback)
        #self._cam.stop_aquisition()