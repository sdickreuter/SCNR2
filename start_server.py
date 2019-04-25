import sys
from qtpy import QtCore,QtWidgets,QtGui
import time

class gui(QtWidgets.QMainWindow):

    def __init__(self):
        super(gui, self).__init__()

    def dataReady(self):
        cursor = self.output.textCursor()
        cursor.movePosition(cursor.End)
        cursor.insertText(str(self.process.readAll(), 'utf-8'))
        self.output.ensureCursorVisible()

    def callProgram(self):
        # run the process
        # `start` takes the exec and a list of arguments
        #self.process.start('ping',['-c 10','127.0.0.1'])
        self.process.start('python', ['spectrometer_server.py'])

    def exitProgram(self):
        self.process.terminate()

        #print('not running '+str(QtCore.QProcess.NotRunning))
        while self.process.state() != QtCore.QProcess.NotRunning:
            loop = QtCore.QEventLoop()
            QtCore.QTimer.singleShot(500, loop.quit)
            loop.exec_()
        loop = None
        super(gui, self).close()

    def closeEvent(self, event):
        close = QtWidgets.QMessageBox.question(self,
                                     "QUIT",
                                     "Sure?",
                                      QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        if close == QtWidgets.QMessageBox.Yes:
            self.exitProgram()
            event.accept()
        else:
            event.ignore()

    def initUI(self):
        self.setWindowFlags(QtCore.Qt.CustomizeWindowHint)
        # Layout are better for placing widgets
        layout = QtWidgets.QHBoxLayout()
        self.closeButton = QtWidgets.QPushButton('Exit')
        self.closeButton.clicked.connect(self.exitProgram)

        self.output = QtWidgets.QTextEdit()

        layout.addWidget(self.output)
        layout.addWidget(self.closeButton)

        centralWidget = QtWidgets.QWidget()
        centralWidget.setLayout(layout)
        self.setCentralWidget(centralWidget)

        self.setGeometry(0, 0, 700, 400)

        self.setWindowTitle("Spectrometer Server")

        finish = QtWidgets.QAction("Quit", self)
        finish.triggered.connect(self.closeEvent)

        # QProcess object for external app
        self.process = QtCore.QProcess(self)
        # QProcess emits `readyRead` when there is data to be read
        self.process.readyRead.connect(self.dataReady)


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    ui=gui()
    ui.initUI()
    ui.callProgram()
    ui.show()
    sys.exit(app.exec_())