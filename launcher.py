import os
import subprocess

from PyQt5.QtCore import pyqtSlot, QThread, QObject
from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox

from gui.launcher_main import Ui_MainWindow

import spectrometer_server




class Launcher(QMainWindow):
    server = None
    p_gui = None
    p_server = None

    def __init__(self, parent=None):
        super(Launcher, self).__init__(parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.ui.spectrometerButton.clicked.connect(self.initialize)

        self.ui.quitButton.clicked.connect(self.quit)

        self.ui.startButton.clicked.connect(self.start)

    def __del__(self):
        if not self.p_server is None:
            self.p_server.kill()
        if not self.p_gui is None:
            self.p_gui.kill()

    @pyqtSlot()
    def quit(self):
        self.server = None
        self.close()

    @pyqtSlot()
    def initialize(self):
        self.ui.spectrometerButton.setDisabled(True)
        #self.server = spectrometer_server.SpectrometerServer()
        self.p_server = subprocess.Popen(['python', 'spectrometer_server.py'])
        self.ui.startButton.setEnabled(True)


    @pyqtSlot()
    def start(self):

        if self.p_gui is None:
            self.p_gui = subprocess.Popen(['python', 'scnr2.py'])
            #self.p = subprocess.Popen(['python'],shell=True)
        else:
            if not self.p_gui.poll() is  None:
                self.p_gui = subprocess.Popen(['python', 'scnr2.py'])
                #self.p = subprocess.Popen(['python'], shell=True)
            else:
                QMessageBox.critical(self, 'Error', "Graphical User Interface seems to be already running.\nIf the Problem persists please restart the computer.", QMessageBox.Ok)


if __name__ == '__main__':
    import sys

    try:
        app = QApplication(sys.argv)
        main = Launcher()
        main.show()
    except Exception as e:
        print(e)

        sys.exit(1)

    try:
        res = app.exec()
    except Exception as e:
        print(e)
        sys.exit(1)
    finally:
        # if init_spectrometer:
        #    spectrometer.Shutdown()
        # spectrometer = None
        pass
    sys.exit(0)
