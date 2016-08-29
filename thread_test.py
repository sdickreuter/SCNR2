import settings
import PIStage
import spectrometer_client
from spectrumthreads import *
from PyQt5.QtCore import pyqtSlot
from PyQt5.QtWidgets import QApplication, QWidget, QMainWindow, QTextEdit
from PyQt5.QtGui import QTextCursor
import numpy as np
import time



class Test(QMainWindow):

    def __init__(self):
        super(Test, self).__init__()
        self.initUI()

        self.settings = settings.Settings()
        self.spectrometer = spectrometer_client.SpectrometerClient()
        self.stage = PIStage.E545(self.settings.stage_ip, self.settings.stage_port)
        #self.stage = PIStage.Dummy()
        self.n = 0
        self.startThread()


    def initUI(self):

        self.textEdit = QTextEdit(self)
        self.textEdit.setFocus()
        self.textEdit.setReadOnly(True)
        self.textEdit.setLineWrapMode(QTextEdit.NoWrap)

        self.font = self.textEdit.font()
        self.font.setFamily("Courier")
        self.font.setPointSize(10)

        self.resize(700, 800)
        self.setWindowTitle('Test')
        self.setCentralWidget(self.textEdit)
        self.show()
        self.addText("BLA\n")


    def startThread(self):
        #positions = np.array([[10, 10], [15, 15]])
        #self.workingthread = ScanMeanThread(self.spectrometer, self.settings, positions, self.stage)
        self.workingthread = LockinThread(self.spectrometer, self.settings, self.stage)
        self.workingthread.finishSignal.connect(self.finishedCallback)
        #self.workingthread.saveSignal.connect(self.saveCallback)
        self.workingthread.specSignal.connect(self.specCallback)
        self.workingthread.progressSignal.connect(self.progressCallback)
        self.workingthread.start()

    def addText(self, text):
        self.textEdit.moveCursor(QTextCursor.End)
        self.textEdit.setCurrentFont(self.font)
        #self.textEdit.setTextColor(color)

        self.textEdit.insertPlainText(text)

        sb = self.textEdit.verticalScrollBar()
        sb.setValue(sb.maximum())


    @pyqtSlot(np.ndarray)
    def finishedCallback(self, pos):
        self.addText("Thread finished\n")
        self.addText(str(pos)+"\n")
        try:
            self.workingthread.stop()
            self.workingthread = None
        except Exception as e:
            print(e)
        self.n += 1
        if self.n < 2:
            time.sleep(0.3)
            self.startThread()

    @pyqtSlot(np.ndarray, str, np.ndarray, bool, bool)
    def saveCallback(self, spec, filename, pos, lockin, fullPath):
        self.addText("Save requested\n")
        self.addText(filename+"\n")

    @pyqtSlot(np.ndarray)
    def specCallback(self, spec):
        self.addText("Spectrum ready\n")

    @pyqtSlot(float, str)
    def progressCallback(self, progress, eta):
        self.addText('ETA: ' + eta+"\n")


if __name__ == '__main__':
    import sys
    try:
        app = QApplication(sys.argv)
        main = Test()
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
        print(res)
    sys.exit(res)
