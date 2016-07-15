import os
import signal
import time

import AndorSpectrometer
import PIStage
import numpy as np
from PyQt5.QtCore import pyqtSlot, QTimer
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QFileDialog, QInputDialog, QMessageBox
import pyqtgraph as pg

import camerathread
import dialogs
import gamepadthread
import numpymodel
import settings
import spectrum
from gui.main import Ui_MainWindow

# for debugging
init_pad = False
init_cam = False
init_stage = False
init_spectrometer = True
start_cooler = False


class SCNR(QMainWindow):
    _window_title = "SCNR2"
    _heartbeat = 100  # ms delay at which the plot/gui is refreshed, and the gamepad moves the stage
    stage = None
    cam = None
    padthread = None
    spectrometer = None

    def __init__(self, parent=None):
        super(SCNR, self).__init__(parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        # init settings
        self.settings = settings.Settings()

        self.ui.slitwidth_spin.setValue(self.settings.slit_width)
        self.ui.centre_wavelength_spin.setValue(650)

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
        gv.setCentralWidget(vb)
        l = QVBoxLayout(self.ui.detectorwidget)
        l.setSpacing(0)
        l.addWidget(gv)
        # self.pw.setLabel('left', 'y', units='px')
        # self.pw.setLabel('bottom', 'x', units='px')

        # init Spectrometer
        #self.spectrometer = spectrometer
        if init_spectrometer:
            # self.spectrometer = spectrometer_client.SpectrometerClient()
            print('Initializing Spectrometer')
            time.sleep(0.5)
            self.spectrometer = AndorSpectrometer.Spectrometer(start_cooler=start_cooler, init_shutter=True, verbosity=1)
            #self.spectrometer.SetExposureTime(self.settings.integration_time)
            time.sleep(1)
            print('Spectrometer initialized')
            self.setSpectrumMode()
            self.spectrometer.SetExposureTime(1.0)

        # init detector mode combobox
        self.ui.mode_combobox.addItem("Spectrum")
        self.ui.mode_combobox.addItem("Image")

        # init camera stuff
        if init_cam:
            gv2 = pg.GraphicsView()
            vb2 = pg.ViewBox()
            self.img = pg.ImageItem()
            vb2.addItem(self.img)
            roi = pg.ROI([50, 50], [10, 10])
            vb2.addItem(roi)
            gv2.setCentralWidget(vb2)
            l2 = QVBoxLayout(self.ui.camwidget)
            l2.setSpacing(0)
            l2.addWidget(gv2)
            try:
                self.cam = camerathread.CameraThread()
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

        # init stage
        if init_stage:
            try:
                # self.stage = PIStage.E545(self.settings.stage_ip, self.settings.stage_port)
                self.stage = PIStage.E545('127.0.0.1', self.settings.stage_port)
            except:
                self.stage = None
                # self.stage = PIStage.Dummy()
                # print("Could not initialize PIStage, using Dummy instead")
            if self.stage is not None:
                if self.stage.is_initialized:
                    self.ui.addpos_button.setEnabled(True)
                    self.ui.scanning_tab.setEnabled(True)
                    self.ui.searchmax_button.setEnabled(True)
                    self.ui.stage_frame.setEnabled(True)
                else:
                    self.stage = None
                    QMessageBox.critical(self, 'Error', "Could not initialize PI Stage.", QMessageBox.Ok)

        # for testing:
        else:
            self.ui.scanning_tab.setEnabled(True)

        # init Gamepad
        if self.stage is not None:
            if init_pad:
                try:
                    self.padthread = gamepadthread.GamepadThread()
                except:
                    print("Error initializing Gamepad")
                if self.padthread.isinitialized:
                    self.padthread.BSignal.connect(self.on_search_clicked)
                    self.padthread.XSignal.connect(self.on_addpos_clicked)
                    # self.padthread.YSignal.connect(self.on_stepup_clicked)
                    # self.padthread.ASignal.connect(self.on_stepdown_clicked)
                    self.padthread.xaxisSignal.connect(self.on_xaxis)
                    self.xaxis = 0.0
                    self.padthread.yaxisSignal.connect(self.on_yaxis)
                    self.yaxis = 0.0
                    self.padthread.start()
                    self.gamepad_timer = QTimer(self)
                    self.gamepad_timer.timeout.connect(self.check_pad_analog)
                    self.gamepad_timer.start(100)
                    self.pad_active = False
                else:
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

        # init image readout combobox
        self.ui.image_combobox.addItem("Only Slit")
        self.ui.image_combobox.addItem("Full Image")

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

        # Temperature  Display
        if start_cooler:
            self.temperature_timer = QTimer(self)
            self.temperature_timer.timeout.connect(self.check_temperature)
            self.temperature_timer.start(1000)

        # init Position Table
        self.positions = np.matrix([[0.0, 0.0], [0.0, 10.0], [10.0, 0.0]])
        self.posModel = numpymodel.NumpyModel(self.positions)
        self.ui.posTable.setModel(self.posModel)
        self.vh = self.ui.posTable.verticalHeader()
        self.vh.setVisible(False)
        self.hh = self.ui.posTable.horizontalHeader()
        self.hh.setModel(self.posModel)
        self.hh.setVisible(True)

    def close(self):
        if init_spectrometer:
            self.spectrometer.Shutdown()
        super(SCNR, self).close()

    # ----- Slot for Temperature Display

    @pyqtSlot()
    def check_temperature(self):
        self.ui.label_temp.setText('Detector Temperature: ' + str(round(self.spectrometer.GetTemperature(), 1)) + ' °C')

    # ----- END Slot for Temperature Display


    # ----- Slot for Detector Mode

    @pyqtSlot(int)
    def on_mode_changed(self, index):
        if init_spectrometer:
            if index == 0:
                self.setSpectrumMode()
            elif index == 1:
                self.setImageMode()

    def setSpectrumMode(self):
        self.spectrometer.SetCentreWavelength(self.ui.centre_wavelength_spin.value())
        self.spectrometer.SetSlitWidth(self.settings.slit_width)
        self.spectrometer.SetSingleTrack()

        self.ui.dark_button.setEnabled(True)
        self.ui.bg_button.setEnabled(True)
        self.ui.ref_button.setEnabled(True)
        self.ui.mean_button.setEnabled(True)
        self.ui.series_button.setEnabled(True)
        self.ui.left_tab.setCurrentIndex(0)

    def setImageMode(self):
        self.ui.dark_button.setEnabled(False)
        self.ui.bg_button.setEnabled(False)
        self.ui.ref_button.setEnabled(False)
        self.ui.mean_button.setEnabled(False)
        self.ui.series_button.setEnabled(False)

        self.spectrometer.SetSlitWidth(2500)
        self.spectrometer.SetImageofSlit()
        # if self.ui.image_combobox.currentIndex() == 0:
        #    self.spectrometer.SetImageofSlit()
        # elif self.ui.image_combobox.currentIndex() ==1:
        #    self.spectrometer.SetFullImage()
        self.ui.left_tab.setCurrentIndex(2)

    # ----- END Slot for Detektor Mode


    # ----- Slots for Camera Stuff

    @pyqtSlot(np.ndarray)
    def update_camera(self, img):
        self.img.setImage(img)

    @pyqtSlot(int)
    def on_lefttab_changed(self, index):
        if init_cam:
            if index == 1:
                self.cam.enable()
            else:
                self.cam.disable()

                # ----- END Slots for Camera Stuff

                # ----- Slots for Spectrum Stuff

    @pyqtSlot(np.ndarray)
    def on_update_spectrum(self, spec):
        if self.spectrometer.mode == "Image":
            self.detector_img.setImage(spec)
        elif self.spectrometer.mode == 'SingleTrack':
            self.plot.setData(self.spectrometer.GetWavelength(), spec)

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
        self.ui.stop_button.setDisabled(False)

    @pyqtSlot()
    def on_enableButtons(self):
        self.ui.right_tab.setDisabled(False)
        if self.stage is not None:
            self.ui.stage_frame.setDisabled(False)
            self.ui.searchmax_button.setDisabled(False)
            self.ui.stepup_button.setDisabled(False)
            self.ui.stepdown_button.setDisabled(False)
            self.ui.addpos_button.setDisabled(False)
        self.ui.stop_button.setDisabled(True)
        self.pad_active = True

    # ----- END Slots for Spectrum Stuff

    # ----- Slots for Gamepad

    @pyqtSlot(float)
    def on_xaxis(self, x):
        self.xaxis = x

    @pyqtSlot(float)
    def on_yaxis(self, y):
        self.yaxis = y

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
            self.spectrum.make_scan(self.posModel.getMatrix(), path, self.ui.lockin_checkBox.isChecked(),
                                    self.ui.search_checkBox.isChecked())
            self.disable_buttons()

    @pyqtSlot()
    def on_stop_clicked(self):
        self.ui.status.setText('Stopped')
        self.spectrum.stop_process()

    @pyqtSlot()
    def on_reset_clicked(self):
        self.spectrum.reset()

    # @pyqtSlot()
    # def on_acquirelockin_clicked(self):
    #     self.ui.status.setText('Acquiring ...')
    #     self.spectrum.take_lockin()
    #     self.disable_buttons()
    #
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
        self.spectrum.scan_search_max(self.posModel.getMatrix())

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
        if self.spectrum.mean is not None:
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
        else:
            self.ui.status.setText("Error")
        self.spectrum.take_series(path)
        # self.on_disableButtons()

    @pyqtSlot()
    def on_loaddark_clicked(self):
        buf = self._load_spectrum_from_file()
        if buf is not None:
            self.spectrum.dark = buf

    @pyqtSlot()
    def on_loadlamp_clicked(self):
        buf = self._load_spectrum_from_file()
        if buf is not None:
            self.spectrum.lamp = buf

    @pyqtSlot()
    def on_loadbg_clicked(self):
        buf = self._load_spectrum_from_file()
        if buf is not None:
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
        xl, yl, ok = dialogs.SpanGrid_Dialog.getXY()
        positions = self.posModel.getMatrix()
        if (positions.shape[0] >= 3) & ((xl is not 0) | (yl is not 0)):
            a = np.ravel(positions[0, :])
            b = np.ravel(positions[1, :])
            c = np.ravel(positions[2, :])
            grid = np.zeros((xl * yl, 2))
            if abs(b[0]) > abs(c[0]):
                grid_vec_1 = [b[0] - a[0], b[1] - a[1]]
                grid_vec_2 = [c[0] - a[0], c[1] - a[1]]
            else:
                grid_vec_2 = [b[0] - a[0], b[1] - a[1]]
                grid_vec_1 = [c[0] - a[0], c[1] - a[1]]

            i = 0
            for x in range(xl):
                for y in range(yl):
                    vec_x = a[0] + grid_vec_1[0] * x + grid_vec_2[0] * y
                    vec_y = a[1] + grid_vec_1[1] * x + grid_vec_2[1] * y
                    grid[i, 0] = vec_x
                    grid[i, 1] = vec_y
                    i += 1

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
        seconds = float(round(self.ui.integration_time_spin.value(),2))
        print(seconds)
        #self.spectrometer.SetExposureTime(seconds)
        self.spectrometer.SetExposureTime(0.5)

    @pyqtSlot()
    def on_number_of_samples_edited(self):
        self.settings.number_of_samples = self.ui.number_of_samples_spin.value()

    @pyqtSlot()
    def on_slit_width_edited(self):
        self.settings.slit_width = self.ui.slitwidth_spin.value()
        self.spectrometer.SetSlitWidth(self.ui.slitwidth_spin.value())

    @pyqtSlot()
    def on_centre_wavelength_edited(self):
        self.spectrometer.SetCentreWavelength(self.ui.centre_wavelength_spin.value())

    @pyqtSlot(int)
    def on_grating_changed(self, index):
        self.spectrometer.SetGrating(index + 1)

    @pyqtSlot(int)
    def on_image_readout_changed(self, index):
        print("readout:" + str(index))

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
        self.settings.save()


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

    # print('Initializing Spectrometer')
    # try:
    #     spectrometer = AndorSpectrometer.Spectrometer(start_cooler=start_cooler, init_shutter=True,
    #                                                    verbosity=1)
    # except Exception as e:
    #     print(e)
    #     sys.exit(1)
    # time.sleep(1)
    # print('Spectrometer initialized')

    try:
        signal.signal(signal.SIGINT, sigint_handler)
        app = QApplication(sys.argv)
        timer = QTimer()
        timer.start(500)  # You may change this if you wish.
        timer.timeout.connect(lambda: None)  # Let the interpreter run each 500 ms.
        main = SCNR()
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
