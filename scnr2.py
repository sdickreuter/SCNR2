

from PyQt5.QtCore import pyqtSlot, QTimer, QSocketNotifier, QAbstractTableModel, Qt, QVariant, QModelIndex
from PyQt5.QtWidgets import QApplication, QMainWindow, QSizePolicy, QVBoxLayout, QFileDialog, QInputDialog
import pyqtgraph as pg

import numpy as np

from PyQt5 import uic
Ui_MainWindow = uic.loadUiType("gui/main.ui")[0]

#from gui.main import Ui_MainWindow

import PIStage

import spectrum
import settings
import dialogs
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


        # init spectrum stuff
        #self.spectrum = spectrum.Spectrum(None, self.settings, None, None, None, None)

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


        # init Settings Dialog
        self.settings_dialog = dialogs.Settings_Dialog(self.settings)
        self.settings_dialog.updateSignal.connect(self.update_settings)
        self.update_settings()

        # init Slit Width Dialog
        self.slit_dialog = dialogs.SlitWidth_Dialog(10) # TODO: read out slit width and use as parameter
        self.slit_dialog.changeSlitSignal.connect(self.update_slit)


# ----- Settings Dialog Stuff

    # Slot for Settings Dialog
    @pyqtSlot()
    def update_settings(self):
        #self.spectrum._spectrometer.integration_time_micros(self.settings.integration_time * 1000)
        pass

    # Button For Settings Dialog
    @pyqtSlot()
    def on_settings_clicked(self):
        self.settings_dialog.show()

# ----- END Settings Dialog Stuff

# ----- Slit Width Dialog Stuff

    # Slot for Settings Dialog
    @pyqtSlot(int)
    def update_slit(self,slitwidth):
        print(slitwidth)
        #self.spectrum.setSlitWidth(slitwidth)

    # Button For Settings Dialog
    @pyqtSlot()
    def on_slit_clicked(self):
        self.slit_dialog.show()

# ----- END Slit Width Dialog Stuff

# ----- Slots for Camera Stuff

    @pyqtSlot(np.ndarray)
    def update_camera(self, img):
        self.img.setImage(img)

    @pyqtSlot(int)
    def on_lefttab_changed(self, index):
        if index == 1:
            self.cam.enable()
        if index == 0:
            self.cam.disable()

# ----- END Slots for Camera Stuff


if __name__ == '__main__':
    import sys

    app = QApplication(sys.argv)
    main = SCNR()
    main.show()
    sys.exit(app.exec_())