import os
import subprocess

from PyQt5.QtCore import pyqtSlot, QThread, QObject
from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox

from gui.launcher_main import Ui_MainWindow

import spectrometer_server


class ServerThread(QObject):
    server = None

    def __init__(self, parent = None):
        if getattr(self.__class__, '_has_instance', False):
            RuntimeError('Cannot create another instance')
            #return None
        self.__class__._has_instance = True
        try:
            super(ServerThread, self).__init__(parent)
            self.thread = QThread(parent)
            self.moveToThread(self.thread)
            #self.thread.started.connect(self.process)
        except:
            (type, value, traceback) = sys.exc_info()
            sys.excepthook(type, value, traceback)

    def start(self):
        self.thread.start()

    @pyqtSlot()
    def stop(self):
        self.thread.quit()
        self.thread.wait(5000)

    def __del__(self):
        self.__class__.has_instance = False
        self.server = None




class Launcher(QMainWindow):
    server = None
    p_gui = None
    p_server = None
    #serverthread = None
    #server = None

    def __init__(self, parent=None):
        super(Launcher, self).__init__(parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.ui.spectrometerButton.clicked.connect(self.initialize)

        self.ui.quitButton.clicked.connect(self.quit)

        self.ui.startButton.clicked.connect(self.start)

    def __del__(self):
        #if not self.p_server is None:
        #    self.p_server.kill()
        if not self.p_gui is None:
            self.p_gui.kill()
        #if not self.serverthread is None:
        #    self.serverthread.stop()
        #    self.serverthread = None


    @pyqtSlot()
    def quit(self):
        self.close()

    @pyqtSlot()
    def initialize(self):
        self.ui.spectrometerButton.setDisabled(True)
        #self.server = spectrometer_server.SpectrometerServer()
        self.p_server = subprocess.Popen(['python', 'spectrometer_server.py'])
        proc = subprocess.Popen(...)
        try:
            outs, errs = proc.communicate(timeout=320)
        except subprocess.TimeoutExpired:
            QMessageBox.critical(self, 'Error', "Could not initialize Spectrometer!", QMessageBox.Ok)
            raise RuntimeError()

        #self.server = spectrometer_server.SpectrometerServer()
        #self.serverthread = ServerThread()
        #self.serverthread.thread.started.connect(self.server.run)
        #self.serverthread.start()
        #try:
        #    self.serverthread = ServerThread()
        #except Exception as e:
        #    print(e)
        #    self.ui.spectrometerButton.setEnabled(True)
        #    return
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
