import os

import numpy as np
import time
from PyQt5.QtCore import pyqtSlot, QTimer, QEvent
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QFileDialog, QInputDialog, QWidget, QSizePolicy, \
    QMessageBox, QGridLayout
import pyqtgraph as pg
#from skimage import exposure

# from PyQt5 import uic
# Ui_MainWindow = uic.loadUiType("gui/main.ui")[0]

from gui.main import Ui_MainWindow

# Device Control imports
import PIStage
# import AndorSpectrometer
import spectrometer_client

# Helper Classes imports
import spectrum
import settings
import camerathread
import gamepadthread
import numpymodel
import settings
import spectrum
import dialogs
from custom_pyqtgraph_classes import movableCrosshair, xmovableCrosshair
from gui.main import Ui_MainWindow

# for debugging
init_pad = True
init_cam = True
init_stage = True
init_spectrometer = True


class SCNR(QMainWindow):
    _window_title = "SCNR2"
    _heartbeat = 100  # ms delay at which the plot/gui is refreshed, and the gamepad moves the stage
    stage = None
    cam = None
    padthread = None
    spectrometer = None
    labels = None

    savedir = "./Spectra/"
    path = "./"

    def __init__(self, parent=None):
        super(SCNR, self).__init__(parent)
        self.ui = Ui_MainWindow()

        setup, stage_ok, cam_ok, ok = dialogs.StartUp_Dialog.getOptions()
        #print(setup)

        if ok:
            init_cam = cam_ok
            init_stage = stage_ok
            if setup == 0: # Microscope Setup
                coord_mapping = {"x":"x","y":"y","z":"z"}
            elif setup == 1: #Freespace Setup
                coord_mapping = {"x":"z","y":"y","z":"x"}
            else:
                #raise RuntimeError("Setup not specified!")
                print("Setup not specified, quitting.")
                super(SCNR, self).close()
        else:
            super(SCNR, self).close()

        self.ui.setupUi(self)

        # init settings
        self.settings = settings.Settings()

        self.ui.slitwidth_spin.setValue(self.settings.slit_width)
        self.ui.centre_wavelength_spin.setValue(self.settings.centre_wavelength)

        self.ui.rasterdim_spin.setValue(self.settings.rasterdim)
        self.ui.rasterwidth_spin.setValue(self.settings.rasterwidth)
        self.ui.search_int_time_spin.setValue(self.settings.search_integration_time)
        self.ui.sigma_spin.setValue(self.settings.sigma)
        self.ui.exposure_time_spin.setValue(self.settings.cam_exposure_time)
        self.ui.label_stepsize.setText(str(self.settings.stepsize))

        self.pw = pg.PlotWidget()
        # vb = CustomViewBox()
        # self.pw = pg.PlotWidget(viewBox=vb, enableMenu=False)
        self.plot = self.pw.plot()
        l1 = QVBoxLayout(self.ui.specwidget)
        l1.addWidget(self.pw)
        self.pw.setLabel('left', 'Intensity [a.u.]')
        self.pw.setLabel('bottom', 'Wavelength [nm]')

        gv = pg.GraphicsView()
        vb = pg.ViewBox()
        self.detector_img = pg.ImageItem()
        vb.addItem(self.detector_img)
        self.slitmarker = xmovableCrosshair(pos=[self.settings.slitmarker_x, self.settings.slitmarker_y], size=15)
        vb.addItem(self.slitmarker)
        gv.setCentralWidget(vb)
        l = QGridLayout(self.ui.detectorwidget)
        l.setSpacing(0)
        l.addWidget(gv, 0, 0)

        w = pg.HistogramLUTWidget()
        l.addWidget(w, 0, 1)
        w.setImageItem(self.detector_img)


        # self.pw.setLabel('left', 'y', units='px')
        # self.pw.setLabel('bottom', 'x', units='px')

        # init Spectrometer
        if init_spectrometer:
            self.spectrometer = spectrometer_client.SpectrometerClient()
            # print('Initializing Spectrometer')
            # self.spectrometer = AndorSpectrometer.Spectrometer(start_cooler=start_cooler,init_shutter=True,verbosity=1)
            # self.spectrometer.SetExposureTime(self.settings.integration_time / 1000)
            self.setSpectrumMode()
            self.spectrometer.SetExposureTime(self.settings.integration_time)
            # print('Spectrometer initialized')

        # init detector mode combobox
        self.ui.mode_combobox.addItem("Spectrum")
        self.ui.mode_combobox.addItem("Image")

        # init camera stuff
        if init_cam:
            gv2 = pg.GraphicsView()
            vb2 = pg.ViewBox()
            self.img = pg.ImageItem()
            vb2.addItem(self.img)
            self.cammarker = movableCrosshair(pos=[self.settings.cammarker_x, self.settings.cammarker_y], size=25)
            vb2.addItem(self.cammarker)
            gv2.setCentralWidget(vb2)

            l2 = QGridLayout(self.ui.camwidget)
            l2.setSpacing(0)
            l2.addWidget(gv2, 0, 0)

            w = pg.HistogramLUTWidget()
            l2.addWidget(w, 0, 1)
            w.setImageItem(self.img)

            try:
                self.cam = camerathread.CameraThread(flip=True)
            except:
                print("Error initializing Camera")
            if self.cam.isinitialized:
                self.cam.set_exposure(self.settings.cam_exposure_time * 1000)
                self.cam.ImageReadySignal.connect(self.update_camera)
                self.cam.start()
                self.ui.cam_tab.setDisabled(False)
            else:
                self.cam = None
                # self.ui.left_tab.setEnabled(False)
                print("Could not initialize Camera")
                QMessageBox.critical(self, 'Error', "Could not initialize Camera.", QMessageBox.Ok)
                self.ui.left_tab.removeTab(1)
        else:
            self.ui.left_tab.removeTab(1)

        # init stage
        if init_stage:
            try:
                self.stage = PIStage.E545(self.settings.stage_ip, self.settings.stage_port, coordinate_mapping = coord_mapping)
                # self.stage = PIStage.E545('127.0.0.1', self.settings.stage_port)
            except Exception as e:
                print(e)
                self.stage = None
                # self.stage = PIStage.Dummy()
                # print("Could not initialize PIStage, using Dummy instead")
            if self.stage is not None:
                if self.stage.is_initialized:
                    self.ui.addpos_button.setEnabled(True)
                    self.ui.scanning_tab.setEnabled(True)
                    self.ui.searchmax_button.setEnabled(True)
                    self.ui.stage_frame.setEnabled(True)
                    self.ui.search_checkBox.setEnabled(True)
                    self.ui.lockin_button.setEnabled(True)
                    self.ui.lockin_checkBox.setEnabled(True)
                else:
                    self.stage = None
                    QMessageBox.critical(self, 'Error', "Could not initialize PI Stage.", QMessageBox.Ok)

        # for testing:
        else:
            self.ui.scanning_tab.setEnabled(True)

        # init Gamepad
        if not self.stage is None:
            if init_pad:
                try:
                    self.padthread = gamepadthread.GamepadThread()
                except:
                    print("Error initializing Gamepad")
                if self.padthread.isinitialized:
                    self.padthread.BSignal.connect(self.on_search_clicked)
                    self.padthread.XSignal.connect(self.on_addpos_clicked)
                    self.padthread.YSignal.connect(self.on_stepup_clicked)
                    self.padthread.ASignal.connect(self.on_stepdown_clicked)
                    self.padthread.xaxisSignal.connect(self.on_xaxis)
                    self.xaxis = 0.0
                    self.padthread.yaxisSignal.connect(self.on_yaxis)
                    self.yaxis = 0.0
                    self.padthread.start()
                    self.gamepad_timer = QTimer(self)
                    self.gamepad_timer.timeout.connect(self.check_pad_analog)
                    self.gamepad_timer.start(100)
                    self.pad_active = True
                else:
                    self.pad_active = False
                    self.padthread = None
                    print("Could not initialize Gamepad")
                    QMessageBox.critical(self, 'Error', "Could not initialize Gamepad.", QMessageBox.Ok)

        # init spectrum stuff
        self.spectrum = spectrum.Spectrum(self.spectrometer, self.stage, self.settings)
        self.spectrum.updateStatus.connect(self.on_updateStatus)
        self.spectrum.updateProgress.connect(self.on_updateProgress)
        self.spectrum.updatePositions.connect(self.on_updatePositions)
        self.spectrum.disableButtons.connect(self.on_disableButtons)
        self.spectrum.enableButtons.connect(self.on_enableButtons)
        self.spectrum.specSignal.connect(self.on_update_spectrum)

        # init setting tab values
        self.ui.integration_time_spin.setValue(self.settings.integration_time)
        self.ui.number_of_samples_spin.setValue(self.settings.number_of_samples)
        if init_spectrometer:
            # init grating combobox
            gratings = self.spectrometer.GetGratingInfo()
            for i in range(len(gratings)):
                self.ui.grating_combobox.addItem(str(round(gratings[i + 1])) + ' lines/mm')

            active_grating = self.spectrometer.GetGrating()
            self.ui.grating_combobox.setCurrentIndex(active_grating - 1)

        # init Position Table
        self.positions = np.matrix([[10.0, 10.0], [15.0, 15.0]])
        self.posModel = numpymodel.NumpyModel(self.positions)
        self.ui.posTable.setModel(self.posModel)
        self.vh = self.ui.posTable.verticalHeader()
        self.vh.setVisible(False)
        self.hh = self.ui.posTable.horizontalHeader()
        self.hh.setModel(self.posModel)
        self.hh.setVisible(True)

        self.show_pos()

    def closeEvent(self, event):
        self.on_savesettings_clicked()
        super(SCNR, self).closeEvent(event)

    def close(self):
        self.on_savesettings_clicked()
        super(SCNR, self).close()

    def show_pos(self):
        if not self.stage is None:
            pos = self.stage.last_pos()
            # print(pos)
            self.ui.label_x.setText("x: {0:+8.4f}".format(pos[0]))
            self.ui.label_y.setText("y: {0:+8.4f}".format(pos[1]))
            self.ui.label_z.setText("z: {0:+8.4f}".format(pos[2]))


        # ----- Slot for Detector Mode

    @pyqtSlot(int)
    def on_mode_changed(self, index):
        if init_spectrometer:
            self.spectrometer.AbortAcquisition()
            time.sleep(0.5)
            if index == 0:
                self.setSpectrumMode()
            elif index == 1:
                self.setImageMode()

    def setSpectrumMode(self):
        self.ui.dark_button.setEnabled(True)
        self.ui.bg_button.setEnabled(True)
        self.ui.ref_button.setEnabled(True)
        self.ui.mean_button.setEnabled(True)
        self.ui.series_button.setEnabled(True)
        self.ui.searchmax_button.setEnabled(True)
        self.ui.lockin_button.setEnabled(True)

        if self.settings.centre_wavelength > 0:
            self.spectrometer.SetCentreWavelength(self.settings.centre_wavelength)
        else:
            self.spectrometer.SetCentreWavelength(700)
        self.ui.centre_wavelength_spin.setValue(self.settings.centre_wavelength)
        self.spectrometer.SetSlitWidth(self.settings.slit_width)
        self.ui.slitwidth_spin.setValue(self.settings.slit_width)
        self.spectrometer.SetSingleTrack()

        #self.ui.left_tab.setCurrentIndex(0)

    def setImageMode(self):
        self.ui.dark_button.setDisabled(True)
        self.ui.bg_button.setDisabled(True)
        self.ui.ref_button.setDisabled(True)
        self.ui.mean_button.setDisabled(True)
        self.ui.series_button.setDisabled(True)
        self.ui.searchmax_button.setDisabled(True)
        self.ui.lockin_button.setDisabled(True)

        self.spectrometer.SetSlitWidth(2500)
        self.ui.slitwidth_spin.setValue(2500)
        self.spectrometer.SetImageofSlit()
        self.ui.centre_wavelength_spin.setValue(0)
        # if self.ui.image_combobox.currentIndex() == 0:
        #    self.spectrometer.SetImageofSlit()
        # elif self.ui.image_combobox.currentIndex() ==1:
        #    self.spectrometer.SetFullImage()
        #self.ui.left_tab.setCurrentIndex(2)

    # ----- END Slot for Detektor Mode


    # ----- Slots for Camera Stuff

    @pyqtSlot(np.ndarray)
    def update_camera(self, img):
        #plow, phigh = np.percentile(img, (2, 98))
        #img = exposure.rescale_intensity(img, in_range=(plow, phigh))

        self.img.setImage(img,autoLevels=False,autoDownsample = True)

    @pyqtSlot(int)
    def on_lefttab_changed(self, index):
        if init_cam:
            if index == 1:
                self.cam.enable()
            else:
                self.cam.disable()

            # ----- END Slots for Camera Stuff

            # ----- Slots for Spectrum Stuff

    def correct_spec(self, spec):
        if self.ui.correct_checkBox.isChecked():
            if not self.spectrum.dark is None:
                if not self.spectrum.bg is None:
                    if not self.spectrum.lamp is None:
                        return (spec - self.spectrum.bg) / (self.spectrum.lamp - self.spectrum.dark)
                    return self.spectrum._spec - self.spectrum.bg
                else:
                    if not self.spectrum.lamp is None:
                        return (spec - self.spectrum.dark) / (self.spectrum.lamp - self.spectrum.dark)
                    return spec - self.spectrum.dark
            else:
                if not self.spectrum.bg is None:
                    return spec - self.spectrum.bg
        return spec

    @pyqtSlot(np.ndarray)
    def on_update_spectrum(self, spec):
        if spec is not None:
            if self.spectrometer.mode == "Image":
                #plow, phigh = np.percentile(spec, (2, 98))
                #spec = exposure.rescale_intensity(spec, in_range=(plow, phigh))
                self.detector_img.setImage(spec,autoLevels=False)
            elif self.spectrometer.mode == 'SingleTrack':
                self.plot.setData(self.spectrometer.GetWavelength(), self.correct_spec(spec))
        else:
            QMessageBox.warning(self, 'Error', "Communication with Spectrometer out of sync, please try again.", QMessageBox.Ok)

    @pyqtSlot(str)
    def on_updateStatus(self, status):
        self.ui.status.setText(status)

    @pyqtSlot(float)
    def on_updateProgress(self, progress):
        self.ui.progressBar.setValue(int(progress))

    @pyqtSlot(np.ndarray)
    def on_updatePositions(self, pos):
        self.posModel.update(pos)

    @pyqtSlot()
    def on_disableButtons(self):
        self.ui.right_tab.setDisabled(True)
        self.ui.stage_frame.setDisabled(True)
        self.ui.searchmax_button.setDisabled(True)
        self.ui.stepup_button.setDisabled(True)
        self.ui.stepdown_button.setDisabled(True)
        self.ui.temp_button.setDisabled(True)
        self.ui.lockin_button.setDisabled(True)
        self.ui.lockin_checkBox.setDisabled(True)
        self.ui.stop_button.setDisabled(False)

    @pyqtSlot()
    def on_enableButtons(self):
        self.ui.right_tab.setDisabled(False)
        self.ui.temp_button.setDisabled(False)
        if not self.stage is None:
            self.ui.stage_frame.setDisabled(False)
            self.ui.searchmax_button.setDisabled(False)
            self.ui.stepup_button.setDisabled(False)
            self.ui.stepdown_button.setDisabled(False)
            self.ui.addpos_button.setDisabled(False)
            self.ui.lockin_button.setDisabled(False)
            self.ui.lockin_checkBox.setDisabled(False)
        self.ui.stop_button.setDisabled(True)
        self.pad_active = True

    # ----- END Slots for Spectrum Stuff

    # ----- Slots for Gamepad

    @pyqtSlot(float)
    def on_xaxis(self, x):
        self.xaxis = x

    @pyqtSlot(float)
    def on_yaxis(self, y):
        self.yaxis = -y

    @pyqtSlot()
    def check_pad_analog(self):
        if self.pad_active:
            x_step = self.xaxis
            if abs(x_step) > 0.001:
                x_step = x_step * self.settings.stepsize
            else:
                x_step = 0.0

            y_step = self.yaxis
            if abs(y_step) > 0.001:
                y_step = y_step * self.settings.stepsize
            else:
                y_step = 0.0

            if abs(x_step) > 0.0001:
                if abs(y_step) > 0.0001:
                    self.stage.moverel(dx=x_step, dy=y_step)
                else:
                    self.stage.moverel(dx=x_step)
            elif abs(y_step) > 0.001:
                self.stage.moverel(dy=y_step)
            self.show_pos()

        # ----- END Slots for Gamepad


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
                QMessageBox.warning(self, 'Error', "Error creating directory ./" + prefix + "", QMessageBox.Ok)

            # path = self.savedir + prefix + path.sep
            path = self.savedir + prefix + "/"
            self.ui.status.setText("Scanning ...")
            # self.spectrum.make_scan(self.scan_store, path, self.button_searchonoff.get_active(), self.button_lockinonoff.get_active())
            self.on_disableButtons()
            self.spectrum.take_scan(self.posModel.getMatrix(), self.labels, path, self.ui.lockin_checkBox.isChecked(),
                                    self.ui.search_checkBox.isChecked())

    @pyqtSlot()
    def on_stop_clicked(self):
        self.ui.status.setText('Stopped')
        self.spectrum.stop_process()

    @pyqtSlot()
    def on_reset_clicked(self):
        self.spectrum.reset()

    @pyqtSlot()
    def on_lockin_clicked(self):
        self.on_disableButtons()
        self.ui.status.setText('Acquiring ...')
        self.spectrum.take_lockin()

    # @pyqtSlot()
    # def on_direction_clicked(self):
    #     self.direction_dialog.rundialog()

    @pyqtSlot()
    def on_live_clicked(self):
        self.on_disableButtons()
        self.ui.status.setText('Liveview')
        if self.spectrometer.mode == 'SingleTrack':
            self.spectrum.take_live()
        elif self.spectrometer.mode == 'Image':
            self.spectrum.take_live_image()

    @pyqtSlot()
    def on_searchgrid_clicked(self):
        self.on_disableButtons()
        self.ui.status.setText("Searching Max.")
        self.spectrum.scan_search_max(self.posModel.getMatrix(), self.labels)

    @pyqtSlot()
    def on_search_clicked(self):
        self.on_disableButtons()
        self.ui.status.setText("Searching Max.")
        self.spectrum.search_max()

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
                QMessageBox.warning(self, 'Error', "Error creating directory ./" + prefix + "", QMessageBox.Ok)
            # path = self.savedir + prefix + path.sep
            path = self.savedir + prefix + "/"
            self.spectrum.save_data(path)

    @pyqtSlot()
    def on_saveas_clicked(self):
        self.ui.status.setText("Saving Data ...")
        save_as = QFileDialog.getSaveFileName(self, "Save currently shown Spectrum as", './spectra/',
                                              'CSV Files (*.csv)')
        print(save_as[0])
        # prefix, ok = QInputDialog.getText(self, 'Save Folder', 'Enter Folder to save spectra to:')
        if not self.spectrum.mean is None:
            try:
                self.spectrum.save_spectrum(self.spectrum.mean, save_as[0], None, False, True)
            except:
                print("Error Saving file " + save_as[0])
                QMessageBox.warning(self, 'Error', "Error Saving file " + save_as[0], QMessageBox.Ok)

    @pyqtSlot()
    def on_dark_clicked(self):
        self.on_disableButtons()
        self.ui.status.setText('Taking Dark Spectrum')
        self.spectrum.take_dark()

    @pyqtSlot()
    def on_lamp_clicked(self):
        self.on_disableButtons()
        self.ui.status.setText('Taking Lamp Spectrum')
        self.spectrum.take_lamp()

    @pyqtSlot()
    def on_mean_clicked(self):
        self.on_disableButtons()
        self.ui.status.setText('Taking Normal Spectrum')
        self.spectrum.take_mean()

    @pyqtSlot()
    def on_bg_clicked(self):
        self.on_disableButtons()
        self.ui.status.setText('Taking Background Spectrum')
        self.spectrum.take_bg()

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
                QMessageBox.warning(self, 'Error', "Error creating directory ./" + prefix + "", QMessageBox.Ok)
            # path = self.savedir + prefix + path.sep
            path = self.savedir + prefix + "/"
            self.spectrum.take_series(path)
        else:
            self.ui.status.setText("Error")
            # self.on_disableButtons()

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

    @pyqtSlot()
    def on_xup_clicked(self):
        self.stage.moverel(dx=self.settings.stepsize)
        self.show_pos()

    @pyqtSlot()
    def on_xdown_clicked(self):
        self.stage.moverel(dx=-self.settings.stepsize)
        self.show_pos()

    @pyqtSlot()
    def on_yup_clicked(self):
        self.stage.moverel(dy=self.settings.stepsize)
        self.show_pos()

    @pyqtSlot()
    def on_ydown_clicked(self):
        self.stage.moverel(dy=-self.settings.stepsize)
        self.show_pos()

    @pyqtSlot()
    def on_zup_clicked(self):
        self.stage.moverel(dz=self.settings.stepsize)
        self.show_pos()

    @pyqtSlot()
    def on_zdown_clicked(self):
        self.stage.moverel(dz=-self.settings.stepsize)
        self.show_pos()

    @pyqtSlot()
    def on_stepup_clicked(self):
        self.settings.stepsize *= 10
        if self.settings.stepsize > 10:
            self.settings.stepsize = 10.0
        self.ui.label_stepsize.setText(str(self.settings.stepsize))
        self.settings.save()

    @pyqtSlot()
    def on_stepdown_clicked(self):
        self.settings.stepsize /= 10
        if self.settings.stepsize < 0.001:
            self.settings.stepsize = 0.001
        self.ui.label_stepsize.setText(str(self.settings.stepsize))
        self.settings.save()

    @pyqtSlot()
    def on_temp_clicked(self):
        self.ui.label_temp.setText('Detector Temperature: ' + str(round(self.spectrometer.GetTemperature(), 1)) + ' °C')

    # ----- END Slots for Buttons

    # ----- Scanning Listview Slots

    @pyqtSlot()
    def on_addpos_clicked(self):
        self.stage.query_pos()
        x, y, z = self.stage.last_pos()
        positions = self.posModel.getMatrix()
        if positions.shape[1] == 2:
            positions = np.append(positions, np.matrix([x, y]), axis=0)
        else:
            positions = np.matrix([x, y])
        self.posModel.update(positions)

    @pyqtSlot()
    def on_spangrid_clicked(self):
        positions = self.posModel.getMatrix()
        grid, self.labels, ok = dialogs.SpanGrid_Dialog.getXY(positions)
        if ok:
            self.posModel.update(grid)

    @pyqtSlot()
    def on_scan_add(self):
        positions = self.posModel.getMatrix()
        if positions.shape[1] == 2:
            positions = np.append(positions, np.matrix([0.0, 0.0]), axis=0)
        else:
            positions = np.matrix([0.0, 0.0])
        self.posModel.update(positions)

    @pyqtSlot()
    def on_scan_remove(self):
        indices = self.ui.posTable.selectionModel().selectedIndexes()
        rows = np.array([], dtype=int)
        for index in indices:
            rows = np.append(rows, index.row())
        positions = self.posModel.getMatrix()
        positions = np.delete(positions, rows, axis=0)
        self.posModel.update(positions)

    @pyqtSlot()
    def on_scan_clear(self):
        self.posModel.update(np.matrix([[]]))

    @pyqtSlot(np.ndarray)
    def update_positions(self, pos):
        self.posModel.update(pos)

    # ----- END Scanning Listview Slots

    # ----- Slots for Settings

    @pyqtSlot()
    def on_int_time_edited(self):
        self.settings.integration_time = self.ui.integration_time_spin.value()
        self.spectrometer.SetExposureTime(self.ui.integration_time_spin.value())

    @pyqtSlot()
    def on_number_of_samples_edited(self):
        self.settings.number_of_samples = self.ui.number_of_samples_spin.value()

    @pyqtSlot()
    def on_slit_width_edited(self):
        self.settings.slit_width = self.ui.slitwidth_spin.value()
        self.spectrometer.SetSlitWidth(self.ui.slitwidth_spin.value())
        time.sleep(0.5)

    @pyqtSlot()
    def on_centre_wavelength_edited(self):
        self.settings.centre_wavelength = self.ui.centre_wavelength_spin.value()
        self.spectrometer.SetCentreWavelength(self.ui.centre_wavelength_spin.value())

    @pyqtSlot(int)
    def on_grating_changed(self, index):
        self.spectrometer.SetGrating(index + 1)

    @pyqtSlot()
    @pyqtSlot()
    def on_exposure_time_edited(self):
        self.settings.cam_exposure_time = self.ui.exposure_time_spin.value()
        self.cam.set_exposure(self.settings.cam_exposure_time * 1000)

    @pyqtSlot()
    def on_search_int_time_edited(self):
        self.settings.search_integration_time = self.ui.search_int_time_spin.value()

    @pyqtSlot()
    def on_rasterdim_edited(self):
        self.settings.rasterdim = self.ui.rasterdim_spin.value()

    @pyqtSlot()
    def on_rasterwidth_edited(self):
        self.settings.rasterwidth = self.ui.rasterwidth_spin.value()

    @pyqtSlot()
    def on_sigma_edited(self):
        self.settings.sigma = self.ui.sigma_spin.value()

    @pyqtSlot()
    def on_savesettings_clicked(self):
        if self.cam is not None:
            pos = self.cammarker.pos()
            self.settings.cammarker_x = pos.x()
            self.settings.cammarker_y = pos.y()
        if self.spectrometer is not None:
            pos = self.slitmarker.pos()
            self.settings.slitmarker_x = pos.x()
        self.settings.save()

    def _load_spectrum_from_file(self):
        save_dir = QFileDialog.getOpenFileName(self, "Load Spectrum from CSV", './spectra/', 'CSV Files (*.csv)')

        if len(save_dir[0]) > 1:
            save_dir = save_dir[0]
            # data = pandas.DataFrame(pandas.read_csv(save_dir,skiprows=8))
            # data = data['counts']
            #data = np.genfromtxt(save_dir, delimiter=',', skip_header=12)
            data = np.genfromtxt(save_dir, delimiter=',', skip_header=16)
            data = data[:, 1]
            return np.array(data)
        return None


def sigint_handler(*args):
    """Handler for the SIGINT signal."""
    # sys.stderr.write('\r')
    # if QMessageBox.question(None, '', "Are you sure you want to quit?",
    #                        QMessageBox.Yes | QMessageBox.No,
    #                        QMessageBox.No) == QMessageBox.Yes:
    #    QApplication.quit()
    QApplication.quit()


if __name__ == '__main__':
    import sys
    import signal

    signal.signal(signal.SIGINT, sigint_handler)

    try:
        app = QApplication(sys.argv)
        #timer = QTimer()
        #timer.start(500)  # You may change this if you wish.
        #timer.timeout.connect(lambda: None)  # Let the interpreter run each 500 ms.
        main = SCNR()
        main.show()
    except Exception as e:
        print(e)

    try:
        res = app.exec()
    except Exception as e:
        print(e)

    sys.exit(0)

    # try:
    #     app = QApplication(sys.argv)
    #     main = SCNR()
    #     main.show()
    # except Exception as e:
    #     print("Whaaaat ?")
    #     print(e)
    #     (type, value, traceback) = sys.exc_info()
    #     sys.excepthook(type, value, traceback)
    #     AndorSpectrometer.andor.Shutdown()
    #     AndorSpectrometer.shamrock.Shutdown()
    #     sys.exit(app.exec_())
    # #finally:
    # #    print("Finally")
    # #    spectrometer.Shutdown()
    # #    spectrometer = None
    #     sys.exit(app.exec_())
