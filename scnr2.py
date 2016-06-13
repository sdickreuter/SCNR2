

from PyQt5.QtCore import pyqtSlot, QTimer, QSocketNotifier, QAbstractTableModel, Qt, QVariant, QModelIndex
from PyQt5.QtWidgets import QApplication, QMainWindow, QSizePolicy, QVBoxLayout, QFileDialog, QInputDialog
import pyqtgraph as pg

import os
import numpy as np

#from PyQt5 import uic
#Ui_MainWindow = uic.loadUiType("gui/main.ui")[0]

from gui.main import Ui_MainWindow

import PIStage
from AndorSpectrometer import Spectrometer

import spectrum
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

        # init Spectrometer
        #self.spectrometer = Spectrometer()
        self.spectrometer = None

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
            self.cam.set_exposure(self.settings.cam_exposure_time * 1000)
            self.cam.ImageReadySignal.connect(self.update_camera)
            self.cam.start()
        else:
            self.cam = None
            self.ui.left_tab.setEnabled(False)
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
            #self.padthread.BSignal.connect(self.on_search_clicked)
            #self.padthread.XSignal.connect(self.on_addpos_clicked)
            #self.padthread.YSignal.connect(self.on_stepup_clicked)
            #self.padthread.ASignal.connect(self.on_stepdown_clicked)
            self.padthread.xaxisSignal.connect(self.on_xaxis)
            self.padthread.yaxisSignal.connect(self.on_yaxis)
            self.padthread.start()
            self.timer = QTimer(self)
            #self.timer.timeout.connect(self.check_pad_analog)
            self.timer.start(100)
        else:
            self.padthread = None
            print("Could not initialize Gamepad")


        # init spectrum stuff
        self.spectrum = spectrum.Spectrum(self.spectrometer, self.stage, self.settings)
        self.spectrum.updateStatus.connect(self.on_updateStatus)
        self.spectrum.updatePositions.connect(self.on_updatePositions)
        self.spectrum.disableButtons.connect(self.on_disableButtons)
        self.spectrum.enableButtons.connect(self.on_enableButtons)

        # init grating combobox
        self.ui.grating_combobox.addItem("300 l/mm")
        self.ui.grating_combobox.addItem("1000 l/mm")
        self.ui.grating_combobox.addItem("2000 l/mm")

        # init image readout combobox
        self.ui.image_combobox.addItem("Only Slit")
        self.ui.image_combobox.addItem("Full Image")

        #init setting tab values
        self.ui.integration_time_spin.setValue(self.settings.integration_time)
        self.ui.number_of_samples_spin.setValue(self.settings.number_of_samples)
        self.ui.slitwidth_spin.setValue(10) # TODO: readout correct values from spectrometer
        self.ui.centre_wavelength_spin.setValue(650)  # TODO: readout correct values from spectrometer

    # ----- Slots for Camera Stuff

    @pyqtSlot(np.ndarray)
    def update_camera(self, img):
        self.img.setImage(img)
        #print(str(np.min(img)) + ' ' + str(np.max(img)))
        #print(img.shape)
        #print(self.cam.get_exposure())

    @pyqtSlot(int)
    def on_lefttab_changed(self, index):
        if index == 1:
            self.cam.enable()
        if index == 0:
            self.cam.disable()

# ----- END Slots for Camera Stuff


    @pyqtSlot(str)
    def on_updateStatus(self, status):
        self.ui.status.setLabel(status)

    @pyqtSlot(float)
    def on_updateProgress(self, progress):
        self.ui.progressBar.setValue(progress)

    @pyqtSlot(np.ndarray)
    def on_updatePositions(self, pos):
        self.posModel.update(pos)

    @pyqtSlot()
    def on_disableButtons(self):
        self.ui.right_tab.setDisabled(True)
        self.ui.stage_frame.setDisabled(True)
        self.ui.searchmax_button.setDisabled(True)
        self.ui.stepup_button.setDisabled(True)
        self.ui.stepup_button.setDisabled(True)
        self.ui.stop_button.setDisabled(False)

    @pyqtSlot()
    def on_enableButtons(self):
        self.ui.right_tab.setDisabled(False)
        if not self.stage is None:
            self.ui.stage_frame.setDisabled(False)
            self.ui.searchmax_button.setDisabled(False)
            self.ui.stepup_button.setDisabled(False)
            self.ui.stepup_button.setDisabled(False)
        self.ui.stop_button.setDisabled(True)
        self.pad_active = True

# ----- END Slots for Spectrum Stuff

# ----- Slots for Gamepad

    @pyqtSlot(float)
    def on_xaxis(self,x):
        print(x)

    @pyqtSlot(float)
    def on_yaxis(self,y):
        print(y)



# ----- Slots for Buttons

    @pyqtSlot()
    def on_start_scan_clicked(self):
        prefix, ok = QInputDialog.getText(self, 'Save Folder',
                                          'Enter Folder to save spectra to:')

        if ok:
            try:
                # os.path.exists(prefix)
                os.mkdir(self.savedir + prefix)
            except:
                # print("Error creating directory ."+path.sep + prefix)
                print("Error creating directory ./" + prefix)
            # path = self.savedir + prefix + path.sep
            path = self.savedir + prefix + "/"
            self.ui.status.setText("Scanning ...")
            # self.spectrum.make_scan(self.scan_store, path, self.button_searchonoff.get_active(), self.button_lockinonoff.get_active())
            self.spectrum.make_scan(self.posModel.getMatrix(), path, self.ui.checkBox_lockin.isChecked(),
                                    self.ui.checkBox_search.isChecked())
            self.disable_buttons()

    @pyqtSlot()
    def on_stop_clicked(self):
        self.ui.status.setText('Stopped')
        self.spectrum.stop_process()
        self.enable_buttons()

    @pyqtSlot()
    def on_reset_clicked(self):
        self.spectrum.reset()

    @pyqtSlot()
    def on_acquirelockin_clicked(self):
        self.ui.status.setText('Acquiring ...')
        self.spectrum.take_lockin()
        self.disable_buttons()

    @pyqtSlot()
    def on_direction_clicked(self):
        self.direction_dialog.rundialog()

    @pyqtSlot()
    def on_live_clicked(self):
        self.ui.status.setText('Liveview')
        self.spectrum.take_live()
        self.disable_buttons()

    @pyqtSlot()
    def on_searchgrid_clicked(self):
        self.ui.status.setText("Searching Max.")
        self.spectrum.scan_search_max(self.posModel.getMatrix())
        self.disable_buttons()

    @pyqtSlot()
    def on_search_clicked(self):
        self.ui.status.setText("Searching Max.")
        self.spectrum.search_max()
        self.disable_buttons()

    @pyqtSlot()
    def on_save_clicked(self):
        self.ui.status.setText("Saving Data ...")
        prefix, ok = QInputDialog.getText(self, 'Save Folder',
                                          'Enter Folder to save spectra to:')
        if ok:
            try:
                # os.path.exists(prefix)
                os.mkdir(self.savedir + prefix)
            except:
                # print("Error creating directory ."+path.sep + prefix)
                print("Error creating directory ./" + prefix)
            # path = self.savedir + prefix + path.sep
            path = self.savedir + prefix + "/"
            self.spectrum.save_data(path)

    @pyqtSlot()
    def on_saveas_clicked(self):
        self.ui.status.setText("Saving Data ...")
        save_as = QFileDialog.getSaveFileName(self, "Save currently shown Spectrum as", './spectra/', 'CSV Files (*.csv)')
        print(save_as[0])
        # prefix, ok = QInputDialog.getText(self, 'Save Folder', 'Enter Folder to save spectra to:')
        if not self.spectrum.mean is None:
            try:
                self.spectrum.save_spectrum(self.spectrum.mean, save_as[0], None, False, True)
            except:
                print("Error Saving file " + save_as[0])

    @pyqtSlot()
    def on_dark_clicked(self):
        self.ui.status.setText('Taking Dark Spectrum')
        self.spectrum.take_dark()
        self.disable_buttons()

    @pyqtSlot()
    def on_lamp_clicked(self):
        self.ui.status.setText('Taking Lamp Spectrum')
        self.spectrum.take_lamp()
        self.disable_buttons()

    @pyqtSlot()
    def on_mean_clicked(self):
        self.ui.status.setText('Taking Normal Spectrum')
        self.spectrum.take_mean()
        self.disable_buttons()

    @pyqtSlot()
    def on_bg_clicked(self):
        self.ui.status.setText('Taking Background Spectrum')
        self.spectrum.take_bg()
        self.disable_buttons()

    @pyqtSlot()
    def on_series_clicked(self):
        self.ui.status.setText('Taking Time Series')
        prefix = self.prefix_dialog.rundialog()
        if prefix is not None:
            try:
                # os.path.exists(prefix)
                os.mkdir(self.savedir + prefix)
            except:
                # print("Error creating directory ."+path.sep + prefix)
                print("Error creating directory ./" + prefix)
            # path = self.savedir + prefix + path.sep
            path = self.savedir + prefix + "/"
        else:
            self.ui.status.setText("Error")
        self.spectrum.take_series(path)
        self.disable_buttons()

    @pyqtSlot()
    def on_loaddark_clicked(self):
        buf = self._load_spectrum_from_file()
        if not buf is None:
            self.spectrum.dark = buf

    @pyqtSlot()
    def on_loadlamp_clicked(self):
        buf = self._load_spectrum_from_file()
        if not buf is None:
            self.spectrum.lamp = buf

    @pyqtSlot()
    def on_loadbg_clicked(self):
        buf = self._load_spectrum_from_file()
        if not buf is None:
            self.spectrum.bg = buf

# ----- END Slots for Buttons


# ----- Slots for Settings

    @pyqtSlot()
    def on_int_time_edited(self):
        print(self.ui.integration_time_spin.value())

    @pyqtSlot()
    def on_number_of_samples_edited(self):
        self.settings.number_of_samples = self.ui.number_of_samples_spin.value()
        print(self.ui.number_of_samples_spin.value())

    @pyqtSlot()
    def on_slit_width_edited(self):
        print(self.ui.slitwidth_spin.value())

    @pyqtSlot()
    def on_centre_wavelength_edited(self):
        print(self.ui.slitwidth_spin.value())

    @pyqtSlot(int)
    def on_grating_changed(self, index):
        print("grating: " + str(index))

    @pyqtSlot(int)
    def on_image_readout_changed(int, index):
        print("readout:" + str(index))

    @pyqtSlot()
    def on_exposure_time_edited(self):
        self.settings.cam_exposure_time = self.ui.exposure_time_spin.value()
        self.cam.set_exposure(self.settings.cam_exposure_time * 1000)
        print(self.ui.exposure_time_spin.value())

    @pyqtSlot()
    def on_search_int_time_edited(self):
        self.settings.search_integration_time = self.ui.search_int_time_spin.value()
        print(self.ui.search_int_time_spin.value())

    @pyqtSlot()
    def on_rasterdim_edited(self):
        self.settings.rasterdim = self.ui.rasterdim_spin.value()
        print(self.ui.rasterdim_spin.value())

    @pyqtSlot()
    def on_rasterwidth_edited(self):
        self.settings.rasterwidth = self.ui.rasterwidth_spin.value()
        print(self.ui.rasterwidth_spin.value())

    @pyqtSlot()
    def on_sigma_edited(self):
        self.settings.sigma = self.ui.sigma_spin.value()
        print(self.ui.sigma_spin.value())

    @pyqtSlot()
    def on_savesettings_clicked(self):
        #self.settings.save()
        pass

if __name__ == '__main__':
    import sys

    app = QApplication(sys.argv)
    main = SCNR()
    main.show()
    sys.exit(app.exec_())