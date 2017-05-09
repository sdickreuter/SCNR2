import os
import subprocess

from qtpy.QtCore import pyqtSlot, QThread, QObject
from qtpy.QtWidgets import QApplication, QMainWindow, QMessageBox

from gui.launcher_main import Ui_MainWindow

import signal

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
        pass
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
        self.p_server = subprocess.Popen(['python', 'spectrometer_server.py'],stdout=subprocess.PIPE)#,creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
        #print('Started Server at:' + str(self.p_server.pid))
        #Read two lines from stdout, then spectrometer will be initialized
        print(self.p_server.stdout.readline())
        out = self.p_server.stdout.readline()
        print(out)
        if out != b'Spectrometer initialized !\n':
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

    res = 0
    try:
        res = app.exec()
    except Exception as e:
        print(e)
    finally:
        if not main.p_server is None:
            main.p_server.send_signal(signal.SIGINT)
            #main.p_server.wait(10)
            main.p_server.terminate()
            main.p_server.kill()
            #app.p_server.send_signal(signal.SIGTERM)
        if not main.p_gui is None:
            main.p_gui.send_signal(signal.SIGINT)
            #main.p_gui.wait(10)
            main.p_gui.terminate()
            main.p_gui.kill()
        # if init_spectrometer:
        #    spectrometer.Shutdown()
        # spectrometer = None
        #pass

    sys.exit(res)

