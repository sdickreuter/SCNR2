import os
import sys
import time
import multiprocessing as mp
import queue

from PyQt5.QtCore import pyqtSlot, QTimer
from PyQt5.QtWidgets import QApplication, QMainWindow
import pyqtgraph as pg
import numpy as np
import ctypes

#import scnr2
from statusprocess import StatusProcess
from spectrometerprocess import SpectrometerProcess, SpectrometerController

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
