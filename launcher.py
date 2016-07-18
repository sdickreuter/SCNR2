import os
import sys
import time

from PyQt5.QtWidgets import QApplication


import scnr2
from spectrometerserverprocess import SpectrometerServerProcess
from spectrometerclient import SpectrometerClient
import multiprocessing as mp
import time

class GuiProcess(mp.Process):

    def __init__(self):
        mp.Process.__init__(self)

    def run(self):
        try:
            # app = QApplication([])
            # main = Example()
            # main.show()
            # main.raise_()
            # app.exec_()
            app = QApplication([])
            main = scnr2.SCNR()
            main.show()
            app.exec_()
        finally:
            pass
            # self.send_status('quit')

if __name__ == '__main__':
    # Spectrometer will only initialize in spawned process !!!
    mp.set_start_method('spawn')


    server = SpectrometerServerProcess()
    server.daemon = True
    server.start()
    time.sleep(5)

    gui = GuiProcess()
    gui.daemon = True
    gui.start()

    #client = SpectrometerClient()
    #gui = GuiProcess()
    #gui.daemon = True
    #gui.start()

    #running = True
    #while running:
    #
    #    if gui.is_alive() and server.is_alive():
    #        time.sleep(1)
    #    else:
    #        running = False

    #app = QApplication([])
    #main = scnr2.SCNR(client)
    #main.show()
    #app.exec_()


    sys.exit(0)


