import os

import numpy as np
import time
#os.environ["QT_API"] = "pyside"
from qtpy import QtCore,QtWidgets,QtGui

import pyqtgraph as pg
from skimage import exposure

# from PyQt5 import uic
# Ui_MainWindow = uic.loadUiType("gui/main.ui")[0]
# from qtpy import uic
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
import dialogs
from custom_pyqtgraph_classes import movableCrosshair, xmovableCrosshair
from gui.main import Ui_MainWindow

# for debugging
init_pad = True
init_cam = True
init_stage = True
init_spectrometer = True


class SCNR(QtWidgets.QMainWindow):
    _window_title = "SCNR2"
    _heartbeat = 100  # ms delay at which the plot/gui is refreshed, and the gamepad moves the stage
    stage = None
    cam = None
    padthread = None
    spectrometer = None
    labels = None
    cam_reference_image = None
    background_image = None
    last_image = None

    savedir = "./Spectra/"
    path = "./"

    def __init__(self, options,parent=None):
        super(SCNR, self).__init__(parent)
        self.ui = Ui_MainWindow()

        #setup, stage_ok, cam_ok, ok = dialogs.StartUp_Dialog.getOptions()
        setup, stage_ok, cam_ok = options
        #print(setup)

        if ok:
            init_cam = cam_ok
            init_stage = stage_ok
            if setup == 'Nikon' :
                self.settings = settings.Settings('config_nikon.ini')
            elif setup == 'Zeiss':
                self.settings = settings.Settings('config_zeiss.ini')
            elif setup == 'Freespace': #Freespace Setup
                self.settings = settings.Settings('config_freespace.ini')
            else:
                raise RuntimeError("Setup not specified!")
                #print("Setup not specified, quitting.")
                super(SCNR, self).close()
        else:
            super(SCNR, self).close()

        self.ui.setupUi(self)

        # init settings
        self.ui.search_correct_checkBox.setChecked(False)

        self.ui.slitwidth_spin.setValue(self.settings.slit_width)
        self.ui.centre_wavelength_spin.setValue(self.settings.centre_wavelength)

        self.ui.rasterdim_spin.setValue(self.settings.rasterdim)
        self.ui.rasterwidth_spin.setValue(self.settings.rasterwidth)
        self.ui.search_int_time_spin.setValue(self.settings.search_integration_time)
        self.ui.sigma_spin.setValue(self.settings.sigma)
        self.ui.search_zmult_spin.setValue(self.settings.zmult)
        self.ui.exposure_time_spin.setValue(self.settings.cam_exposure_time)
        self.ui.label_stepsize.setText(str(self.settings.stepsize))
        self.ui.zscan_centre_spinbox.setValue(self.settings.zscan_centre)
        self.ui.zscan_width_spinbox.setValue(self.settings.zscan_width)
        if self.settings.autofocus_mode == 'gauss':
            self.ui.autofocus_combobox.setCurrentIndex(0)
        elif self.settings.autofocus_mode == 'gaussexport':
            self.ui.autofocus_combobox.setCurrentIndex(1)
        elif self.settings.autofocus_mode == 'maximum':
            self.ui.autofocus_combobox.setCurrentIndex(2)
        elif self.settings.autofocus_mode == 'brightfield':
            self.ui.autofocus_combobox.setCurrentIndex(3)
        elif self.settings.autofocus_mode == 'zscan':
            self.ui.autofocus_combobox.setCurrentIndex(4)

        self.pw = pg.PlotWidget()
        # vb = CustomViewBox()
        # self.pw = pg.PlotWidget(viewBox=vb, enableMenu=False)
        self.plot = self.pw.plot()
        l1 = QtWidgets.QVBoxLayout(self.ui.specwidget)
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
        l = QtWidgets.QGridLayout(self.ui.detectorwidget)
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
            self.spectrometer.SetMinVertReadout(1)

        # init detector mode combobox
        self.ui.mode_combobox.addItem("Spectrum")
        self.ui.mode_combobox.addItem("Image of Slit")
        self.ui.mode_combobox.addItem("Full Image")


        # init camera stuff
        if init_cam:
            gv2 = pg.GraphicsView()
            vb2 = pg.ViewBox()
            self.img = pg.ImageItem()
            vb2.addItem(self.img)
            self.cammarker = movableCrosshair(pos=[self.settings.cammarker_x, self.settings.cammarker_y], size=25)
            vb2.addItem(self.cammarker)
            gv2.setCentralWidget(vb2)

            l2 = QtWidgets.QGridLayout(self.ui.camwidget)
            l2.setSpacing(0)
            l2.addWidget(gv2, 0, 0)

            w = pg.HistogramLUTWidget()
            l2.addWidget(w, 0, 1)
            w.setImageItem(self.img)

            try:
                if setup == 'Nikon':
                    self.cam = camerathread.CameraThread(xflip=False,yflip=False)
                elif setup == 'Zeiss':  # Microscope Setup
                    self.cam = camerathread.CameraThread(xflip=False,yflip=False)
                elif setup == 'Freespace':  # Freespace Setup
                    self.cam = camerathread.CameraThread(xflip=False,yflip=True)

                img = self.cam.get_image()
                print(img.shape)
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
                QtWidgets.QMessageBox.critical(self, 'Error', "Could not initialize Camera.", QtWidgets.QMessageBox.Ok)
                #self.ui.left_tab.removeTab(1)
                self.ui.cam_tab.setDisabled(True)
        else:
            #self.ui.left_tab.removeTab(1)
            self.cam = None
            self.ui.cam_tab.setDisabled(True)

        # init stage
        if init_stage:
            try:
                self.stage = PIStage.E545(self.settings.stage_ip, self.settings.stage_port, coordinate_mapping = self.settings.coord_mapping)
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
                    self.ui.autofocus_button.setEnabled(True)
                    self.ui.stage_frame.setEnabled(True)
                    self.ui.search_checkBox.setEnabled(True)
                    self.ui.lockin_button.setEnabled(True)
                    self.ui.lockin_checkBox.setEnabled(True)
                else:
                    self.stage = None
                    QtWidgets.QMessageBox.critical(self, 'Error', "Could not initialize PI Stage.", QtWidgets.QMessageBox.Ok)

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

                    self.padthread.rxaxisSignal.connect(self.on_rxaxis)
                    self.rxaxis = 0.0
                    self.padthread.ryaxisSignal.connect(self.on_ryaxis)
                    self.ryaxis = 0.0

                    self.padthread.start()
                    self.gamepad_timer = QtCore.QTimer(self)
                    self.gamepad_timer.timeout.connect(self.check_pad_analog)
                    self.gamepad_timer.start(100)
                    self.pad_active = True
                else:
                    self.pad_active = False
                    self.padthread = None
                    print("Could not initialize Gamepad")
                    QtWidgets.QMessageBox.critical(self, 'Error', "Could not initialize Gamepad.", QtWidgets.QMessageBox.Ok)

        # init spectrum stuff
        self.spectrum = spectrum.Spectrum(self.spectrometer, self.stage, self.settings)
        self.spectrum.updateStatus.connect(self.on_updateStatus)
        self.spectrum.updateProgress.connect(self.on_updateProgress)
        self.spectrum.updatePositions.connect(self.on_updatePositions)
        self.spectrum.disableButtons.connect(self.on_disableButtons)
        self.spectrum.enableButtons.connect(self.on_enableButtons)
        self.spectrum.specSignal.connect(self.on_update_spectrum)
        self.spectrum.set_searchmax_ontarget.connect(self.set_searchmax_ontarget)
        self.spectrum.set_autofocus_ontarget.connect(self.set_autofocus_ontarget)

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
        self.hh.setVisible(True)

        self.on_temp_clicked()
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
            self.ui.label_x.setText("x: {0:+6.3f}".format(pos[0]))
            self.ui.label_y.setText("y: {0:+6.3f}".format(pos[1]))
            self.ui.label_z.setText("z: {0:+6.3f}".format(pos[2]))


        # ----- Slot for Detector Mode

    @QtCore.Slot(int)
    def on_mode_changed(self, index):
        if init_spectrometer:
            self.spectrometer.AbortAcquisition()
            time.sleep(0.5)
            if index == 0:
                self.setSpectrumMode()
            elif index == 1:
                self.setImageMode()
            elif index == 2:
                self.setFullImageMode()

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

    def setFullImageMode(self):
        self.ui.dark_button.setDisabled(True)
        self.ui.bg_button.setDisabled(True)
        self.ui.ref_button.setDisabled(True)
        self.ui.mean_button.setDisabled(True)
        self.ui.series_button.setDisabled(True)
        self.ui.searchmax_button.setDisabled(True)
        self.ui.lockin_button.setDisabled(True)
        self.spectrometer.SetFullImage()


    # ----- END Slot for Detektor Mode


    # ----- Slots for Camera Stuff

    @QtCore.Slot(np.ndarray)
    def update_camera(self, img):
        self.cam.disable()
        autolevels = False
        if self.cam_reference_image is not None:
            img -= self.cam_reference_image
            #img = img / self.cam_reference_image
            img -= np.min(img)
            #img *= 1000

        if self.ui.autocontrast_checkBox.isChecked():
            plow, phigh = np.percentile(img, (1, 99))
            img = exposure.rescale_intensity(img, in_range=(plow, phigh))
            #img = exposure.equalize_adapthist(img, clip_limit=0.03)
            autolevels = True

        self.img.setImage(img,autoLevels=autolevels,autoDownsample = True)
        self.cam.enable()

    @QtCore.Slot()
    def on_camreference_clicked(self):
        self.cam_reference_image = self.cam.get_image()

    @QtCore.Slot()
    def on_clear_reference_clicked(self):
        self.cam_reference_image = None

    @QtCore.Slot(int)
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
            return self.spectrum.correct_spectrum(spec)
        return spec

    def correct_image(self, image):
        if self.ui.correct_image_checkBox.isChecked():
            if self.background_image is not None:
                image = np.subtract(image,self.background_image)
            if not self.spectrum.dark is None and not self.spectrum.lamp is None:
                image = np.array(image,dtype=np.float32)
                print('correct_image '+ str(image.shape))
                for i in range(image.shape[1]):
                    image[:,i] = image[:,i] / (self.spectrum.lamp - self.spectrum.dark)
                image = image - image.min()
                image = image / image.max()
                image = image * 10000
                image = np.array(image,dtype=np.int)
                print('correct_image finished')

        return image

    @QtCore.Slot(np.ndarray)
    def on_update_spectrum(self, spec):
        if spec is not None:
            if self.spectrometer.mode == "imageofslit" or self.spectrometer.mode == "fullimage":
                self.last_image = spec
                print('on_update_spectrum '+str(spec.shape))
                # img = self.correct_image(self.last_image)
                # self.detector_img.setImage(img,autoLevels=False)
                self.detector_img.setImage(self.correct_image(self.last_image), autoLevels=False)

            elif self.spectrometer.mode == 'singletrack':
                self.plot.setData(self.spectrometer.GetWavelength(), self.correct_spec(spec))
        else:
            QtWidgets.QMessageBox.warning(self, 'Error', "Communication with Spectrometer out of sync, please try again.", QtWidgets.QMessageBox.Ok)

    @QtCore.Slot(str)
    def on_updateStatus(self, status):
        self.ui.status.setText(status)

    @QtCore.Slot(float)
    def on_updateProgress(self, progress):
        self.ui.progressBar.setValue(int(progress))

    @QtCore.Slot(np.ndarray)
    def on_updatePositions(self, pos):
        self.posModel.addData(pos)

    @QtCore.Slot()
    def on_disableButtons(self):
        self.ui.right_tab.setDisabled(True)
        self.ui.stage_frame.setDisabled(True)
        self.ui.searchmax_button.setDisabled(True)
        self.ui.autofocus_button.setDisabled(True)
        self.ui.stepup_button.setDisabled(True)
        self.ui.stepdown_button.setDisabled(True)
        self.ui.temp_button.setDisabled(True)
        self.ui.lockin_button.setDisabled(True)
        self.ui.lockin_checkBox.setDisabled(True)
        self.ui.stop_button.setDisabled(False)

    @QtCore.Slot()
    def on_enableButtons(self):
        self.ui.right_tab.setDisabled(False)
        self.ui.temp_button.setDisabled(False)
        if not self.stage is None:
            self.ui.stage_frame.setDisabled(False)
            self.ui.searchmax_button.setDisabled(False)
            self.ui.autofocus_button.setDisabled(False)
            self.ui.stepup_button.setDisabled(False)
            self.ui.stepdown_button.setDisabled(False)
            self.ui.addpos_button.setDisabled(False)
            self.ui.lockin_button.setDisabled(False)
            self.ui.lockin_checkBox.setDisabled(False)
        self.ui.stop_button.setDisabled(True)
        #self.pad_active = True

    # ----- END Slots for Spectrum Stuff

    # ----- Slots for Gamepad

    @QtCore.Slot(float)
    def on_xaxis(self, x):
        self.xaxis = x

    @QtCore.Slot(float)
    def on_yaxis(self, y):
        self.yaxis = -y

    @QtCore.Slot(float)
    def on_rxaxis(self, x):
        print(x)
        self.rxaxis = x

    @QtCore.Slot(float)
    def on_ryaxis(self, y):
        print(y)
        self.ryaxis = -y

    @QtCore.Slot()
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

            z_step = self.ryaxis
            if abs(z_step) > 0.001:
                z_step = z_step * self.settings.stepsize
            else:
                z_step = 0.0

            if abs(x_step) > 0.001:
                if abs(y_step) > 0.001:
                    self.set_searchmax_ontarget(False)
                    self.stage.moverel(dx=x_step, dy=y_step)
                else:
                    self.set_searchmax_ontarget(False)
                    self.stage.moverel(dx=x_step)
            elif abs(y_step) > 0.001:
                self.set_searchmax_ontarget(False)
                self.stage.moverel(dy=y_step)

            if abs(z_step) > 0.0001:
                self.stage.moverel(dz=z_step)
                self.set_autofocus_ontarget(False)

            self.show_pos()


    # ----- END Slots for Gamepad


    # ----- Slots for Buttons

    @QtCore.Slot()
    def on_start_scan_clicked(self):
        prefix, ok = QtWidgets.QInputDialog.getText(self, 'Save Folder',
                                          'Enter Folder to save spectra to:')
        if ok:
            try:
                # os.path.exists(prefix)
                os.mkdir(self.savedir + prefix)
            except:
                # print("Error creating directory ."+path.sep + prefix)
                print("Error creating directory ./" + prefix)
                QtWidgets.QMessageBox.warning(self, 'Error', "Error creating directory ./" + prefix + "", QtWidgets.QMessageBox.Ok)

            # path = self.savedir + prefix + path.sep
            path = self.savedir + prefix + "/"
            self.ui.status.setText("Scanning ...")
            # self.spectrum.make_scan(self.scan_store, path, self.button_searchonoff.get_active(), self.button_lockinonoff.get_active())
            self.on_disableButtons()
            self.spectrum.take_scan(self.posModel.getMatrix(), self.labels, path, self.ui.lockin_checkBox.isChecked(),
                                    self.ui.search_checkBox.isChecked())


    @QtCore.Slot()
    def on_scan3d_clicked(self):
        prefix, ok = QtWidgets.QInputDialog.getText(self, 'Save Folder',
                                          'Enter Folder to save spectra to:')
        if ok:
            try:
                os.mkdir(self.savedir + prefix)
            except:
                print("Error creating directory ./" + prefix)
                QtWidgets.QMessageBox.warning(self, 'Error', "Error creating directory ./" + prefix + "", QtWidgets.QMessageBox.Ok)

            path = self.savedir + prefix + "/"
            file = path + "cube.csv"
            self.stage.query_pos()
            x,y,z = self.stage.last_pos()

            x = np.linspace(x - self.ui.cube_width_spin.value() / 2, x + self.ui.cube_width_spin.value() / 2,
                            self.ui.cube_steps_spin.value())
            y = np.linspace(y - self.ui.cube_width_spin.value() / 2, y + self.ui.cube_width_spin.value() / 2,
                            self.ui.cube_steps_spin.value())
            z = np.linspace(z - self.ui.cube_width_spin.value()*self.settings.zmult / 2, z + self.ui.cube_width_spin.value()*self.settings.zmult / 2,
                            self.ui.cube_steps_spin.value()*self.settings.zmult)

            xx,yy,zz = np.meshgrid(x,y,z)
            xx = xx.ravel()
            yy = yy.ravel()
            zz = zz.ravel()

            pos = np.vstack((xx,yy,zz))
            pos = pos.transpose()

            self.ui.status.setText("Scanning ...")
            self.on_disableButtons()
            self.spectrum.take_scan3d(pos, file)


    @QtCore.Slot()
    def on_stop_clicked(self):
        self.ui.status.setText('Stopped')
        self.spectrum.stop_process()

    @QtCore.Slot()
    def on_reset_clicked(self):
        self.spectrum.reset()

    @QtCore.Slot()
    def on_lockin_clicked(self):
        self.on_disableButtons()
        self.ui.status.setText('Acquiring ...')
        self.spectrum.take_lockin()

    # @QtCore.Slot()
    # def on_direction_clicked(self):
    #     self.direction_dialog.rundialog()

    @QtCore.Slot()
    def on_live_clicked(self):
        self.on_disableButtons()
        self.ui.status.setText('Liveview')
        if self.spectrometer.mode == 'singletrack':
            self.spectrum.take_live()
        elif self.spectrometer.mode == 'imageofslit':
            self.spectrum.take_live_image()
        elif self.spectrometer.mode == 'fullimage':
            self.spectrum.take_live_fullimage()

    @QtCore.Slot()
    def on_single_clicked(self):
        self.on_disableButtons()
        self.ui.status.setText('Single')
        if self.spectrometer.mode == 'singletrack':
            self.spectrum.take_live(single=True)
        elif self.spectrometer.mode == 'imageofslit':
            self.spectrum.take_live_image(single=True)
        elif self.spectrometer.mode == 'fullimage':
            self.spectrum.take_live_fullimage(single=True)


    @QtCore.Slot()
    def on_searchgrid_clicked(self):
        self.set_searchmax_ontarget(False)
        self.on_disableButtons()
        self.ui.status.setText("Searching Max.")
        self.spectrum.scan_search_max(self.posModel.getMatrix(), self.labels)

    @QtCore.Slot()
    def on_search_clicked(self):
        if self.spectrometer.mode == 'singletrack':
            self.set_searchmax_ontarget(False)

            self.on_disableButtons()

            # self.spectrometer.SetCentreWavelength(0.0)
            # self.spectrometer.SetSlitWidth(500)
            # self.spectrum.start_autofocus()

            self.ui.status.setText("Searching Max ...")
            self.spectrum.search_max()
        else:
            QtWidgets.QMessageBox.warning(self, 'Error', 'Search only possible in Spectrum Mode' ,QtWidgets.QMessageBox.Ok)

    @QtCore.Slot()
    def on_autofocus_clicked(self):
        if self.spectrometer.mode == 'singletrack':
            self.set_autofocus_ontarget(False)
            self.on_disableButtons()
            self.ui.status.setText("Focussing ...")
            self.spectrum.start_autofocus()
        else:
            QtWidgets.QMessageBox.warning(self, 'Error', 'Autofocus only possible in Spectrum Mode' ,QtWidgets.QMessageBox.Ok)


    @QtCore.Slot()
    def on_save_clicked(self):
        self.ui.status.setText("Saving Data ...")
        prefix, ok = QtWidgets.QInputDialog.getText(self, 'Save Folder',
                                          'Enter Folder to save spectra to:')
        if ok:
            try:
                # os.path.exists(prefix)
                os.mkdir(self.savedir + prefix)
            except:
                # print("Error creating directory ."+path.sep + prefix)
                print("Error creating directory ./" + prefix)
                QtWidgets.QMessageBox.warning(self, 'Error', "Error creating directory ./" + prefix + "", QtWidgets.QMessageBox.Ok)
            # path = self.savedir + prefix + path.sep
            path = self.savedir + prefix + "/"
            self.spectrum.save_data(path)

    @QtCore.Slot()
    def on_saveas_clicked(self):
        self.ui.status.setText("Saving Data ...")
        save_as = QtWidgets.QFileDialog.getSaveFileName(self, "Save currently shown Spectrum as", './spectra/',
                                              'CSV Files (*.csv)')

        #print(save_as[0])
        save_as = save_as[0]
        if not save_as[-4:] == '.csv':
            save_as += ".csv"
        # prefix, ok = QtWidgets.QInputDialog.getText(self, 'Save Folder', 'Enter Folder to save spectra to:')
        if not self.spectrum.mean is None:
            try:
                self.spectrum.save_spectrum(self.spectrum.mean, save_as, None, False, True)
            except:
                print("Error Saving file " + save_as)
                QtWidgets.QMessageBox.warning(self, 'Error', "Error Saving file " + save_as, QtWidgets.QMessageBox.Ok)

    @QtCore.Slot()
    def on_dark_clicked(self):
        self.on_disableButtons()
        self.ui.status.setText('Taking Dark Spectrum')
        self.spectrum.take_dark()

    @QtCore.Slot()
    def on_lamp_clicked(self):
        self.on_disableButtons()
        self.ui.status.setText('Taking Lamp Spectrum')
        self.spectrum.take_lamp()

    @QtCore.Slot()
    def on_mean_clicked(self):
        self.on_disableButtons()
        self.ui.status.setText('Taking Normal Spectrum')
        self.spectrum.take_mean()

    @QtCore.Slot()
    def on_bg_clicked(self):
        self.on_disableButtons()
        self.ui.status.setText('Taking Background Spectrum')
        self.spectrum.take_bg()

    @QtCore.Slot()
    def on_series_clicked(self):
        prefix, ok = QtWidgets.QInputDialog.getText(self, 'Save Folder',
                                          'Enter Folder to save spectra to:')
        if ok:
            try:
                # os.path.exists(prefix)
                os.mkdir(self.savedir + prefix)
            except:
                # print("Error creating directory ."+path.sep + prefix)
                print("Error creating directory ./" + prefix)
                QtWidgets.QMessageBox.warning(self, 'Error', "Error creating directory ./" + prefix + "", QtWidgets.QMessageBox.Ok)

            # path = self.savedir + prefix + path.sep
            path = self.savedir + prefix + "/"
            self.ui.status.setText("Time Series ...")
            # self.spectrum.make_scan(self.scan_store, path, self.button_searchonoff.get_active(), self.button_lockinonoff.get_active())
            self.on_disableButtons()
            self.spectrum.take_series(path)


    @QtCore.Slot()
    def on_loaddark_clicked(self):
        buf = self._load_spectrum_from_file()
        if not buf is None:
            self.spectrum.dark = buf

    @QtCore.Slot()
    def on_loadlamp_clicked(self):
        buf = self._load_spectrum_from_file()
        if not buf is None:
            self.spectrum.lamp = buf

    @QtCore.Slot()
    def on_loadbg_clicked(self):
        buf = self._load_spectrum_from_file()
        if not buf is None:
            self.spectrum.bg = buf

    @QtCore.Slot()
    def on_xup_clicked(self):
        self.stage.moverel(dx=self.settings.stepsize)
        self.show_pos()
        self.set_searchmax_ontarget(False)

    @QtCore.Slot()
    def on_xdown_clicked(self):
        self.stage.moverel(dx=-self.settings.stepsize)
        self.show_pos()
        self.set_searchmax_ontarget(False)

    @QtCore.Slot()
    def on_yup_clicked(self):
        self.stage.moverel(dy=self.settings.stepsize)
        self.show_pos()
        self.set_searchmax_ontarget(False)

    @QtCore.Slot()
    def on_ydown_clicked(self):
        self.stage.moverel(dy=-self.settings.stepsize)
        self.show_pos()
        self.set_searchmax_ontarget(False)

    @QtCore.Slot()
    def on_zup_clicked(self):
        self.stage.moverel(dz=self.settings.stepsize)
        self.show_pos()
        self.set_autofocus_ontarget(False)

    @QtCore.Slot()
    def on_zdown_clicked(self):
        self.stage.moverel(dz=-self.settings.stepsize)
        self.show_pos()
        self.set_autofocus_ontarget(False)

    @QtCore.Slot()
    def on_stepup_clicked(self):
        self.settings.stepsize *= 10
        if self.settings.stepsize > 10:
            self.settings.stepsize = 10.0
        self.ui.label_stepsize.setText(str(self.settings.stepsize))
        self.settings.save()

    @QtCore.Slot()
    def on_stepdown_clicked(self):
        self.settings.stepsize /= 10
        if self.settings.stepsize < 0.001:
            self.settings.stepsize = 0.001
        self.ui.label_stepsize.setText(str(self.settings.stepsize))
        self.settings.save()

    @QtCore.Slot()
    def on_temp_clicked(self):
        self.ui.label_temp.setText('Detector Temperature: ' + str(round(self.spectrometer.GetTemperature(), 1)) + ' °C')

    @QtCore.Slot()
    def on_use_image_background_clicked(self):
        self.background_image = self.last_image

    @QtCore.Slot()
    def on_save_detectorimage_clicked(self):
        img = self.correct_image(self.last_image)
        save_as = QtWidgets.QFileDialog.getSaveFileName(self, "Save currently shown Spectrum as", './spectra/',
                                              'CSV Files (*.csv)')
        save_as = save_as[0]
        if not save_as[-4:] == '.csv':
            save_as += ".csv"

        try:
            img = np.vstack((img.T,self.spectrometer.GetWavelength()))
            np.savetxt(save_as,img)
        except:
            print("Error Saving file " + save_as)
            QtWidgets.QMessageBox.warning(self, 'Error', "Error Saving file " + save_as, QtWidgets.QMessageBox.Ok)

    @QtCore.Slot()
    def on_offset_clicked(self):
        detector_offset, grating_offset, ok = dialogs.Offset_Dialog.get_Offsets(self.spectrometer)

        if ok:
            print("1 ")
            self.spectrometer.SetGratingOffset(grating_offset)
            print("2 ")
            self.spectrometer.SetDetectorOffset(detector_offset)
            print("3 ")

    # ----- END Slots for Buttons

    # ----- Scanning Listview Slots

    @QtCore.Slot()
    def on_addpos_clicked(self):
        self.stage.query_pos()
        x, y, z = self.stage.last_pos()
        positions = np.matrix([x, y])
        self.posModel.addData(positions)

    @QtCore.Slot()
    def on_spangrid_clicked(self):
        positions = self.posModel.getMatrix()
        grid, self.labels, ok = dialogs.SpanGrid_Dialog.getXY(positions)
        if ok:
            self.posModel.clear()
            self.posModel.addData(grid)

    @QtCore.Slot()
    def on_scan_add(self):
        positions = np.matrix([0.0, 0.0])
        self.posModel.addData(positions)

    @QtCore.Slot()
    def on_scan_remove(self):
        indices = self.ui.posTable.selectionModel().selectedIndexes()
        rows = np.array([], dtype=int)
        for index in indices:
            rows = np.append(rows, index.row())
        self.posModel.removeRows(rows)

    @QtCore.Slot()
    def on_scan_clear(self):
        self.posModel.clear()

    # ----- END Scanning Listview Slots

    # ----- Slots for Settings

    @QtCore.Slot()
    def on_int_time_edited(self):
        self.settings.integration_time = self.ui.integration_time_spin.value()
        self.spectrometer.SetExposureTime(self.ui.integration_time_spin.value())

    @QtCore.Slot()
    def on_number_of_samples_edited(self):
        self.settings.number_of_samples = self.ui.number_of_samples_spin.value()

    @QtCore.Slot()
    def on_slit_width_edited(self):
        self.settings.slit_width = self.ui.slitwidth_spin.value()
        self.spectrometer.SetSlitWidth(self.ui.slitwidth_spin.value())
        time.sleep(0.5)

    @QtCore.Slot()
    def on_centre_wavelength_edited(self):
        self.settings.centre_wavelength = self.ui.centre_wavelength_spin.value()
        self.spectrometer.SetCentreWavelength(self.ui.centre_wavelength_spin.value())

    @QtCore.Slot(int)
    def on_grating_changed(self, index):
        self.spectrometer.SetGrating(index + 1)

    @QtCore.Slot()
    @QtCore.Slot()
    def on_exposure_time_edited(self):
        self.settings.cam_exposure_time = self.ui.exposure_time_spin.value()
        self.cam.set_exposure(self.settings.cam_exposure_time * 1000)

    @QtCore.Slot()
    def on_search_int_time_edited(self):
        self.settings.search_integration_time = self.ui.search_int_time_spin.value()

    @QtCore.Slot()
    def on_rasterdim_edited(self):
        self.settings.rasterdim = self.ui.rasterdim_spin.value()

    @QtCore.Slot()
    def on_rasterwidth_edited(self):
        self.settings.rasterwidth = self.ui.rasterwidth_spin.value()

    @QtCore.Slot()
    def on_sigma_edited(self):
        self.settings.sigma = self.ui.sigma_spin.value()

    @QtCore.Slot()
    def on_search_zmult_edited(self):
        self.settings.zmult = self.ui.search_zmult_spin.value()

    @QtCore.Slot(bool)
    def on_search_corrected_toggled(self,state):
        self.settings.correct_search = self.ui.search_correct_checkBox.isChecked()

    @QtCore.Slot(bool)
    def on_increase_minimum_readout_toggled(self,state):
        if state:
            self.spectrometer.SetMinVertReadout(7)
        else:
            self.spectrometer.SetMinVertReadout(1)

    @QtCore.Slot()
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
        save_dir = QtWidgets.QFileDialog.getOpenFileName(self, "Load Spectrum from CSV", './spectra/', 'CSV Files (*.csv)')

        if len(save_dir[0]) > 1:
            save_dir = save_dir[0]
            # data = pandas.DataFrame(pandas.read_csv(save_dir,skiprows=8))
            # data = data['counts']
            #data = np.genfromtxt(save_dir, delimiter=',', skip_header=12)
            data = np.genfromtxt(save_dir, delimiter=',', skip_header=16)
            data = data[:, 1]
            return np.array(data)
        return None

    @QtCore.Slot()
    def on_z_correction_angle_edited(self):
        if self.stage is not None:
            if self.ui.zcorrection_checkbox.isChecked():
                self.stage.set_z_correction_angle(self.ui.zcorrection_spinbox.value())
            else:
                self.stage.set_z_correction_angle(0)

    @QtCore.Slot(bool)
    def set_searchmax_ontarget(self, ontarget):
        if ontarget:
            self.ui.searchmax_button.setIcon(QtGui.QIcon('./gui/ontarget.png'))
        else:
            self.ui.searchmax_button.setIcon(QtGui.QIcon())

    @QtCore.Slot(bool)
    def set_autofocus_ontarget(self, ontarget):
        if ontarget:
            self.ui.autofocus_button.setIcon(QtGui.QIcon('./gui/ontarget.png'))
        else:
            self.ui.autofocus_button.setIcon(QtGui.QIcon())


    @QtCore.Slot(int)
    def on_af_mode_changed(self, index):
        if index == 0:
            self.settings.autofocus_mode = 'gauss'
        elif index == 1:
            self.settings.autofocus_mode = 'gaussexport'
        elif index == 2:
            self.settings.autofocus_mode = 'maximum'
        elif index == 3:
            self.settings.autofocus_mode = 'brightfield'
        elif index == 4:
            self.settings.autofocus_mode = 'zscan'
        elif index == 5:
            self.settings.autofocus_mode = 'gausswidth'

    @QtCore.Slot()
    def on_zscan_centre_edited(self):
        self.settings.zscan_centre = self.ui.zscan_centre_spinbox.value()

    @QtCore.Slot()
    def on_zscan_width_edited(self):
        self.settings.zscan_width = self.ui.zscan_width_spinbox.value()


def sigint_handler(*args):
    """Handler for the SIGINT signal."""
    # sys.stderr.write('\r')
    if QtWidgets.QMessageBox.question(None, '', "Are you sure you want to quit?",
                          QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                           QtWidgets.QMessageBox.No) == QtWidgets.QMessageBox.Yes:
        QtWidgets.QApplication.quit()
    #QtWidgets.QApplication.quit()


if __name__ == '__main__':
    import sys
    import signal

    signal.signal(signal.SIGINT, sigint_handler)

    app = QtWidgets.QApplication(sys.argv)
    setup, stage_ok, cam_ok, ok = dialogs.StartUp_Dialog.getOptions()
    #app.quit()


    #try:
    #app = QtWidgets.QApplication(sys.argv)
    #timer = QtCore.QTimer()
    #timer.start(500)  # You may change this if you wish.
    #timer.timeout.connect(lambda: None)  # Let the interpreter run each 500 ms.
    if ok:
        main = SCNR([setup,stage_ok,cam_ok])
        main.show()
    #except Exception as e:
    #    print(e)
        try:
            res = app.exec()
        except Exception as e:
            print(e)

    sys.exit(0)

    # try:
    #     app = QtWidgets.QApplication(sys.argv)
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
