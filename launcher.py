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

    def __init__(self, queue):
        mp.Process.__init__(self)
        self.queue = queue

    def run(self):
        try:
            # app = QApplication([])
            # main = Example()
            # main.show()
            # main.raise_()
            # app.exec_()
            app = QApplication([])
            main = scnr2.SCNR(self.queue)
            main.show()
            app.exec_()
        finally:
            pass
            # self.send_status('quit')

if __name__ == '__main__':
    # Spectrometer will only initialize in spawned process !!!
    mp.set_start_method('spawn')

    queue = mp.Queue()

    server = SpectrometerServerProcess(queue)
    server.daemon = True
    server.start()
    time.sleep(30)

    #gui = GuiProcess()
    #gui.daemon = True
    #gui.start()

    #client = SpectrometerClient(queue)
    #print(client.test())
    #print("Starting GUI")
    #gui = GuiProcess(queue)
    #gui.daemon = True
    #gui.start()

    #running = True
    #while running:
    #
    #    if gui.is_alive() and server.is_alive():
    #        time.sleep(1)
    #    else:
    #        running = False

    app = QApplication([])
    main = scnr2.SCNR(queue)
    main.show()
    app.exec_()


    sys.exit(0)


