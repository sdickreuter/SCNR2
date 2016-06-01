

from PyQt5.QtCore import pyqtSlot, QTimer, QSocketNotifier, QAbstractTableModel, Qt, QVariant, QModelIndex
from PyQt5.QtWidgets import QApplication, QMainWindow, QSizePolicy, QVBoxLayout, QFileDialog, QInputDialog
import pyqtgraph as pg

import numpy as np

#from PyQt5 import uic
#Ui_MainWindow = uic.loadUiType("gui/main.ui")[0]

from gui.main import Ui_MainWindow

import PIStage

import settings
import camerathread
import gamepadthread

class SCNR(QMainWindow):
    _window_title = "SCNR2"
    _heartbeat = 100  # ms delay at which the plot/gui is refreshed, and the gamepad moves the stage

    def __init__(self, parent=None):
        super(SCNR, self).__init__(parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)


        # init settings
        self.settings = settings.Settings()


        # init camera stuff
        self.gv = pg.GraphicsView()
        self.vb = pg.ViewBox()
        self.img = pg.ImageItem()
        self.vb.addItem(self.img)
        self.gv.setCentralWidget(self.vb)
        self.l = QVBoxLayout(self.ui.camwidget)
        self.l.addWidget(self.gv)
        try:
            self.cam = camerathread.CameraThread()
        except:
            print("Error initializing Camera")
        if self.cam.isinitialized:
            self.cam.ImageReadySignal.connect(self.update_camera)
            self.cam.start()
        else:
            self.cam = None
            self.ui.tabWidget.setEnabled(False)
            print("Could not initialize Camera")

        # init stage
        try:
            #self.stage = PIStage.E545(self.settings.stage_ip, self.settings.stage_port)
            self.stage = PIStage.E545('127.0.0.1', self.settings.stage_port)
        except:
            self.stage = None
            #self.stage = PIStage.Dummy()
            #print("Could not initialize PIStage, using Dummy instead")
        if not self.stage is None:
            if self.stage.is_initialized:
                self.ui.scanning_tab.setEnabled(True)
                self.ui.searchmax_button.setEnabled(True)
                self.ui.stage_frame.setEnabled(True)
            else:
                self.stage = None

        # init Gamepad
        try:
            self.padthread = gamepadthread.GamepadThread()
        except:
            print("Error initializing Gamepad")
        if self.padthread.isinitialized:
            self.padthread.BSignal.connect(self.on_search_clicked)
            self.padthread.XSignal.connect(self.on_addpos_clicked)
            self.padthread.YSignal.connect(self.on_stepup_clicked)
            self.padthread.ASignal.connect(self.on_stepdown_clicked)
            self.padthread.start()
            self.timer = QTimer(self)
            self.timer.timeout.connect(self.check_pad_analog)
            self.timer.start(100)
        else:
            self.padthread = None
            print("Could not initialize Gamepad")

    @pyqtSlot(np.ndarray)
    def update_camera(self, img):
        self.img.setImage(img)


if __name__ == '__main__':
    import sys

    app = QApplication(sys.argv)
    main = SCNR()
    main.show()
    sys.exit(app.exec_())