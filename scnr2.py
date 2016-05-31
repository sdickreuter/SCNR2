

from PyQt5.QtCore import pyqtSlot, QTimer, QSocketNotifier, QAbstractTableModel, Qt, QVariant, QModelIndex
from PyQt5.QtWidgets import QApplication, QMainWindow, QSizePolicy, QVBoxLayout, QFileDialog, QInputDialog
import pyqtgraph as pg

from PyQt5 import uic
#from sys import path
#Ui_MainWindow = uic.loadUiType("ui"+path.sep+"SCNR_main.ui")[0]
Ui_MainWindow = uic.loadUiType("gui/main.ui")[0]

import camera

class SCNR(QMainWindow):
    _window_title = "SCNR"
    _heartbeat = 100  # ms delay at which the plot/gui is refreshed, and the gamepad moves the stage

    def __init__(self, parent=None):
        super(SCNR, self).__init__(parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        # init camera stuff
        self.gv = pg.GraphicsView()
        self.vb = pg.ViewBox()
        self.img = pg.ImageItem()
        self.vb.addItem(self.img)
        self.gv.setCentralWidget(self.vb)
        self.l = QVBoxLayout(self.ui.imgwidget)
        self.l.addWidget(self.gv)
        self.cam = camera.Camera()




        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update)
        self.timer.start(50)


    def update(self):
        self.img.setImage(self.cam.getimage())


if __name__ == '__main__':
    import sys

    app = QApplication(sys.argv)
    main = SCNR()
    main.show()
    sys.exit(app.exec_())