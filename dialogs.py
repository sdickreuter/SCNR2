__author__ = 'sei'

from qtpy import QtWidgets
from qtpy import QtCore

#from qtpy import uic
#Ui_SettingsDialog = uic.loadUiType("gui/settingsdialog.ui")[0]
#Ui_SpanGridDialog = uic.loadUiType("gui/griddialog.ui")[0]
#Ui_StartUpDialog = uic.loadUiType("gui/startup.ui")[0]

from gui.settingsdialog import Ui_SettingsDialog
from gui.griddialog import Ui_SpanGridDialog
from gui.startup import Ui_Startup_Dialog
from gui.offsetdialog import Ui_OffsetDialog

import numpy as np
import string
import pyqtgraph as pg
import itertools

class Settings_Dialog(QtWidgets.QDialog):
    updateSignal = QtCore.Signal()

    def __init__(self, settings, parent=None):
        super(Settings_Dialog, self).__init__(parent)
        self.settings = settings
        self.ui = Ui_SettingsDialog()
        self.ui.setupUi(self)
        self.reject()

    def accept(self):
        self.settings.number_of_samples = self.ui.number_of_samples_spin.value()
        self.settings.integration_time = self.ui.integration_time_spin.value()
        self.settings.search_integration_time = self.ui.search_int_time_spin.value()
        self.settings.rasterdim = self.ui.rasterdim_spin.value()
        self.settings.rasterwidth = self.ui.rasterwidth_spin.value()
        self.settings.sigma = self.ui.sigma_spin.value()
        self.settings.cam_exposure_time = self.ui.exposure_time_spin.value()
        self.settings.save()
        self.updateSignal.emit()
        self.hide()

    def reject(self):
        self.ui.number_of_samples_spin.setValue(self.settings.number_of_samples)
        self.ui.integration_time_spin.setValue(self.settings.integration_time)
        self.ui.search_int_time_spin.setValue(self.settings.search_integration_time)
        self.ui.rasterdim_spin.setValue(self.settings.rasterdim)
        self.ui.rasterwidth_spin.setValue(self.settings.rasterwidth)
        self.ui.sigma_spin.setValue(self.settings.sigma)

        self.ui.exposure_time_spin.setValue(self.settings.cam_exposure_time)
        self.hide()


# class SlitWidth_Dialog(QtWidgets.QDialog):
#     changeSlitSignal = QtCore.Signal(int)
#
#     def __init__(self, slitwidth, parent=None):
#         super(SlitWidth_Dialog, self).__init__(parent)
#         self.ui = Ui_SlitWidthDialog()
#         self.ui.setupUi(self)
#         self.ui.slitwidth_spin.setValue(slitwidth)
#
#     def accept(self):
#         self.changeSlitSignal.emit(self.ui.slitwidth_spin.value())
#         self.hide()
#
#     def reject(self):
#         self.hide()


class SpanGrid_Dialog(QtWidgets.QDialog):
    def __init__(self, vectors, parent=None):
        super(SpanGrid_Dialog, self).__init__(parent)
        self.vectors = vectors
        self.ui = Ui_SpanGridDialog()
        self.ui.setupUi(self)
        self.transpose = False
        self.flip_x = False
        self.flip_y = False

        self.pw = pg.PlotWidget()
        self.plot = self.pw.plot()
        l1 = QtWidgets.QVBoxLayout(self.ui.plotwidget)
        l1.addWidget(self.pw)
        self.pw.setLabel('left', 'Y')
        self.pw.setLabel('bottom', 'X')
        self.grid, self.labels = self.gen_grid(self.ui.x_spin.value(), self.ui.y_spin.value())
        self.update_plot()

    # static method to create the dialog and return (x steps, y steps, accepted)
    @staticmethod
    def getXY(vectors, parent=None):
        if (vectors.shape[0] >= 3):
            dialog = SpanGrid_Dialog(vectors, parent)
            result = dialog.exec_()
            return dialog.grid, dialog.labels, result == QtWidgets.QDialog.Accepted
        else:
            return None, None, None


    def get_letters(self,size):
        def iter_all_ascii():
            size = 1
            while True:
                for s in itertools.product(string.ascii_uppercase, repeat=size):
                    yield "".join(s)
                size += 1

        letters = np.array([])
        for s in itertools.islice(iter_all_ascii(), size):
            letters = np.append(letters,s)
        return letters

    def get_numbers(self,size):
        def iter_all_numbers():
            size = 1
            while True:
                for s in itertools.product(string.digits[0:10], repeat=size):
                    yield "".join(s)
                size += 1
        numbers = np.array([])
        for s in itertools.islice(iter_all_numbers(), size):
            numbers = np.append(numbers,s)
        return numbers


    @QtCore.Slot()
    def gen_grid(self, xl, yl):
        a = np.ravel(self.vectors[0, :])
        b = np.ravel(self.vectors[1, :])
        c = np.ravel(self.vectors[2, :])
        grid = np.zeros((xl * yl, 2))
        grid_vec_2 = [b[0] - a[0], b[1] - a[1]]
        grid_vec_1 = [c[0] - a[0], c[1] - a[1]]
        labels = []# np.empty((xl * yl),dtype=np.string_)
        # if not self.transpose:
        #     labelsx = np.array(list(string.ascii_uppercase))[:xl]
        #     labelsy = np.array(list(string.digits))[1:yl + 1]
        # else:
        #     labelsy = np.array(list(string.ascii_uppercase))[:yl]
        #     labelsx = np.array(list(string.digits))[1:xl + 1]
        if self.transpose:
            labelsx = self.get_letters(xl)
            labelsy = self.get_numbers(yl)
        else:
            labelsy = self.get_letters(yl)
            labelsx = self.get_numbers(xl)

        labelsy = labelsy[::-1]

        if not self.flip_x:
            labelsx = labelsx[::-1]
        if not self.flip_y:
            labelsy = labelsy[::-1]

        i = 0
        for x in range(xl):
            for y in range(yl):
                vec_x = a[0] + grid_vec_1[0] * x + grid_vec_2[0] * y
                vec_y = a[1] + grid_vec_1[1] * x + grid_vec_2[1] * y
                grid[i, 0] = vec_x
                grid[i, 1] = vec_y
                if self.transpose:
                    labels.append(labelsx[x]+labelsy[y])
                else:
                    labels.append(labelsy[y]+labelsx[x])
                i += 1

        labels = np.array(labels)
        return grid, labels

    @QtCore.Slot()
    def update_plot(self):
        self.pw.clear()
        self.plot = self.pw.plot()
        self.plot.setData(self.grid[:, 0], self.grid[:, 1], pen=None, symbol='o')
        if self.grid.shape[0] < 100:
            for i in range(self.grid.shape[0]):
                buf = pg.TextItem(text=self.labels[i])
                buf.setPos(self.grid[i,0], self.grid[i,1])
                self.pw.addItem(buf)


    @QtCore.Slot()
    def on_x_edited(self):
        self.grid, self.labels = self.gen_grid(self.ui.x_spin.value(), self.ui.y_spin.value())
        self.update_plot()

    @QtCore.Slot()
    def on_y_edited(self):
        self.grid, self.labels = self.gen_grid(self.ui.x_spin.value(), self.ui.y_spin.value())
        self.update_plot()

    @QtCore.Slot(bool)
    def flipx_toggled(self, state):
        self.flip_x = state
        self.grid, self.labels = self.gen_grid(self.ui.x_spin.value(), self.ui.y_spin.value())
        self.update_plot()

    @QtCore.Slot(bool)
    def flipy_toggled(self, state):
        self.flip_y = state
        self.grid, self.labels = self.gen_grid(self.ui.x_spin.value(), self.ui.y_spin.value())
        self.update_plot()

    @QtCore.Slot(bool)
    def transpose_toggled(self, state):
        self.transpose = state
        self.grid, self.labels = self.gen_grid(self.ui.x_spin.value(), self.ui.y_spin.value())
        self.update_plot()


class StartUp_Dialog(QtWidgets.QDialog):
    def __init__(self, settings, parent=None):
        super(StartUp_Dialog, self).__init__(parent)
        #self.ui = Ui_StartUpDialog()
        self.ui = Ui_Startup_Dialog()
        self.ui.setupUi(self)

    # static method to create the dialog and return (x steps, y steps, accepted)
    @staticmethod
    def getOptions(parent=None):
        dialog = StartUp_Dialog(parent)
        result = dialog.exec_()
        return dialog.ui.setup_combobox.currentText(), dialog.ui.stage_checkbox.isChecked(), dialog.ui.cam_checkbox.isChecked(), result == QtWidgets.QDialog.Accepted


class Offset_Dialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(Offset_Dialog, self).__init__(parent)
        self.ui = Ui_OffsetDialog()
        self.ui.setupUi(self)

    # static method to create the dialog and return (x steps, y steps, accepted)
    @staticmethod
    def get_Offsets(spectrometer,parent=None):
        dialog = Offset_Dialog(parent)
        dialog.ui.gratingoffset_label.setText("Grating Offset for Grating "+spectrometer.GetGrating())
        dialog.ui.detectoroffset_spinBox.setValue(spectrometer.GetDetectorOffset())
        dialog.ui.gratingoffset_spinBox.setValue(spectrometer.GetGratingOffset())

        result = dialog.exec_()
        return dialog.ui.detectoroffset_spinBox.value(), dialog.ui.gratingoffset_spinBox.value(), result == QtWidgets.QDialog.Accepted





if __name__ == '__main__':
    import sys
    import os
    #from PyQt5.QtWidgets import QApplication, QMainWindow
    os.environ["QT_API"] = "pyside"
    from qtpy import QtWidgets

    #app = QtWidgets.QApplication(sys.argv)
    #xl, yl, ok = SpanGrid_Dialog.getXY(np.array([[0, 0], [0, 1], [1, 0]]))
    #print(xl)
    #print(yl)
    #res = app.exec()

    app = QtWidgets.QApplication(sys.argv)
    opt = StartUp_Dialog.getOptions()
    print(opt)
    #res = app.exec()


    sys.exit(0)
