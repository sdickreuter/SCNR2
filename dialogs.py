__author__ = 'sei'

#from SCNR_settingsdialog import Ui_SettingsDialog
#from SCNR_griddialog import Ui_SpanGridDialog
from PyQt5.QtWidgets import QDialog
from PyQt5 import uic
from PyQt5.QtCore import pyqtSignal

Ui_SettingsDialog = uic.loadUiType("gui/settingsdialog.ui")[0]
Ui_SpanGridDialog = uic.loadUiType("gui/griddialog.ui")[0]
Ui_SlitWidthDialog = uic.loadUiType("gui/slitwidthdialog.ui")[0]


class Settings_Dialog(QDialog):
    updateSignal = pyqtSignal()

    def __init__(self,settings, parent = None):
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


class SlitWidth_Dialog(QDialog):
    changeSlitSignal = pyqtSignal(int)

    def __init__(self, slitwidth, parent = None):
        super(SlitWidth_Dialog, self).__init__(parent)
        self.ui = Ui_SlitWidthDialog()
        self.ui.setupUi(self)
        self.ui.slitwidth_spin.setValue(slitwidth)

    def accept(self):
        self.changeSlitSignal.emit(self.ui.slitwidth_spin.value())
        self.hide()

    def reject(self):
        self.hide()




class SpanGrid_Dialog(QDialog):
    def __init__(self,settings, parent = None):
        super(SpanGrid_Dialog, self).__init__(parent)
        self.settings = settings
        self.ui = Ui_SpanGridDialog()
        self.ui.setupUi(self)

    # static method to create the dialog and return (x steps, y steps, accepted)
    @staticmethod
    def getXY(parent = None):
        dialog = SpanGrid_Dialog(parent)
        result = dialog.exec_()
        return (dialog.ui.x_spin.value(), dialog.ui.y_spin.value(), result == QDialog.Accepted)


#
# class DirectionDialog(Gtk.Dialog):
#     def __init__(self, parent, settings):
#         self.settings = settings
#         # super(Settings_Dialog, self).__init__(self, "Settings", parent, 0, (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,Gtk.STOCK_OK, Gtk.ResponseType.OK))
#         Gtk.Dialog.__init__(self, "Direction of Stage Movement", parent, 0,
#                             (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OK, Gtk.ResponseType.OK))
#         # self.set_default_size(150, 100)
#
#         self.box = self.get_content_area()
#         self.box.set_spacing(6)
#
#         # buttons
#
#         # Spinbuttons
#         self.x_adj = Gtk.Adjustment(value=1, lower=-1, upper=1, step_incr=0.1, page_incr=0.1, page_size=0)
#         self.y_adj = Gtk.Adjustment(value=0, lower=-1, upper=1, step_incr=0.1, page_incr=0.1, page_size=0)
#         self.z_adj = Gtk.Adjustment(value=0, lower=-1, upper=1, step_incr=0.1, page_incr=0.1, page_size=0)
#         self.amp_adj = Gtk.Adjustment(value=5, lower=0.1, upper=20, step_incr=0.1, page_incr=1, page_size=0)
#         self.f_adj = Gtk.Adjustment(value=0.01, lower=0.00001, upper=10, step_incr=0.001, page_incr=0.01, page_size=0)
#
#         self.x_spin = Gtk.SpinButton(adjustment=self.x_adj, climb_rate=0.1, digits=2)
#         self.y_spin = Gtk.SpinButton(adjustment=self.y_adj, climb_rate=0.1, digits=2)
#         self.z_spin = Gtk.SpinButton(adjustment=self.z_adj, climb_rate=0.1, digits=2)
#         self.amp_spin = Gtk.SpinButton(adjustment=self.amp_adj, climb_rate=0.1, digits=2)
#         self.f_spin = Gtk.SpinButton(adjustment=self.f_adj, climb_rate=0.0001, digits=6)
#
#         # self.number_of_samples_spin.set_value(self.settings.number_of_samples)
#         # self.integration_time_spin.set_value(self.settings.integration_time)
#         self.box.add(Gtk.Label(label="x"))
#         self.box.add(self.x_spin)
#         self.box.add(Gtk.Label(label="y"))
#         self.box.add(self.y_spin)
#         self.box.add(Gtk.Label(label="z"))
#         self.box.add(self.z_spin)
#         self.box.add(Gtk.Label(label="Amplitude of Movement [um]"))
#         self.box.add(self.amp_spin)
#         self.box.add(Gtk.Label(label="Modulation Frequency"))
#         self.box.add(self.f_spin)
#
#         self.x_spin.set_value(self.settings.direction_x)
#         self.y_spin.set_value(self.settings.direction_y)
#         self.z_spin.set_value(self.settings.direction_z)
#         self.amp_spin.set_value(self.settings.amplitude)
#         self.f_spin.set_value(self.settings.f)
#
#         self.x_spin.connect("value-changed", self.on_change)
#         self.y_spin.connect("value-changed", self.on_change)
#         self.z_spin.connect("value-changed", self.on_change)
#
#         self.hide()
#
#     @staticmethod
#     def _normalize(x, y, z):
#         l = math.sqrt(math.pow(x, 2) + math.pow(y, 2) + math.pow(z, 2))
#         x /= l
#         y /= l
#         z /= l
#         return x, y, z
#
#     def on_change(self, widget):
#         x = self.x_spin.get_value()
#         y = self.y_spin.get_value()
#         z = self.z_spin.get_value()
#         x, y, z = self._normalize(x, y, z)
#         self.x_spin.set_value(x)
#         self.y_spin.set_value(y)
#         self.z_spin.set_value(z)
#
#
#     def rundialog(self):
#         self.show_all()
#         result = self.run()
#         if result == Gtk.ResponseType.OK:
#             self.settings.direction_x = self.x_spin.get_value()
#             self.settings.direction_y = self.y_spin.get_value()
#             self.settings.direction_z = self.z_spin.get_value()
#             self.settings.amplitude = self.amp_spin.get_value()
#             self.settings.f = self.f_spin.get_value()
#             self.settings.save()
#         else:
#             self.x_spin.set_value(self.settings.direction_x)
#             self.y_spin.set_value(self.settings.direction_y)
#             self.z_spin.set_value(self.settings.direction_z)
#             self.amp_spin.set_value(self.settings.amplitude)
#             self.f_spin.set_value(self.settings.f)
#         self.hide()
#
#
# class MoveAbsDialog(Gtk.Dialog):
#     def __init__(self, parent, stage):
#         # super(Settings_Dialog, self).__init__(self, "Settings", parent, 0, (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,Gtk.STOCK_OK, Gtk.ResponseType.OK))
#         Gtk.Dialog.__init__(self, "Move Stage to Absolute Position", parent, 0,
#                             (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OK, Gtk.ResponseType.OK))
#         # self.set_default_size(150, 100)
#
#         self.box = self.get_content_area()
#         self.box.set_spacing(6)
#
#         # buttons
#
#         self.stage = stage
#         self.stage.query_pos()
#         pos = self.stage.last_pos()
#         self.x = float(pos[0])
#         self.y = float(pos[1])
#         self.z = float(pos[2])
#
#         self.entry_x = Gtk.Entry()
#         self.entry_x.set_text(str(self.x))
#         self.entry_x.set_alignment(1)
#         self.entry_x.set_max_length(7)
#
#         self.entry_y = Gtk.Entry()
#         self.entry_y.set_text(str(self.y))
#         self.entry_y.set_alignment(1)
#         self.entry_y.set_max_length(7)
#
#         self.entry_z = Gtk.Entry()
#         self.entry_z.set_text(str(self.z))
#         self.entry_z.set_alignment(1)
#         self.entry_z.set_max_length(7)
#
#         # Stage Control Button Table
#         self.table = Gtk.Table(3, 3, True)
#         self.table.attach(Gtk.Label(label="x [um]"), 0, 1, 0, 1)
#         self.table.attach(Gtk.Label(label="y [um]"), 0, 1, 1, 2)
#         self.table.attach(Gtk.Label(label="z [um]"), 0, 1, 2, 3)
#         self.table.attach(self.entry_x, 1, 3, 0, 1)
#         self.table.attach(self.entry_y, 1, 3, 1, 2)
#         self.table.attach(self.entry_z, 1, 3, 2, 3)
#
#         # self.number_of_samples_spin.set_value(self.settings.number_of_samples)
#         # self.integration_time_spin.set_value(self.settings.integration_time)
#         self.box.add(self.table)
#
#         # self.entry_x.connect("changed", self.on_change)
#         # self.entry_y.connect("changed", self.on_change)
#         # self.entry_z.connect("changed", self.on_change)
#
#         self.hide()
#
#     def on_change(self, widget):
#         x = self.entry_x.get_text()
#         y = self.entry_y.get_text()
#         z = self.entry_z.get_text()
#         try:
#             self.x = float(x)
#         except ValueError:
#             pass  # x = self.x
#         try:
#             self.y = float(y)
#         except ValueError:
#             pass  # y = self.y
#         try:
#             self.z = float(z)
#         except ValueError:
#             pass  # z = self.z
#         if self.x > 200:
#             self.x = 200.0
#         if self.x < 0:
#             self.x = 0.0
#
#         if self.y > 200:
#             self.y = 200.0
#         if self.y < 0:
#             self.y = 0.0
#
#         if self.z > 200:
#             self.z = 200.0
#         if self.z < 0:
#             self.z = 0.0
#
#         self.entry_x.set_text(str(self.x))
#         self.entry_y.set_text(str(self.y))
#         self.entry_z.set_text(str(self.z))
#
#     def rundialog(self):
#         pos = self.stage.query_pos()
#         self.x = pos[0]
#         self.y = pos[1]
#         self.z = pos[2]
#         # print "rundialog {0:+8.4f} {1:+8.4f} {2:+8.4f}".format(self.x, self.y, self.z)
#         self.entry_x.set_text(str(self.x))
#         self.entry_y.set_text(str(self.y))
#         self.entry_z.set_text(str(self.z))
#         self.show_all()
#         result = self.run()
#         if result == Gtk.ResponseType.OK:
#             self.stage.moveabs(self.x, self.y, self.z)
#         self.hide()
#
#
# class MoveRelDialog(Gtk.Dialog):
#     def __init__(self, parent, stage):
#         # super(Settings_Dialog, self).__init__(self, "Settings", parent, 0, (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,Gtk.STOCK_OK, Gtk.ResponseType.OK))
#         Gtk.Dialog.__init__(self, "Move Stage Relative to Position", parent, 0,
#                             (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OK, Gtk.ResponseType.OK))
#         # self.set_default_size(150, 100)
#
#         self.box = self.get_content_area()
#         self.box.set_spacing(6)
#
#         # buttons
#
#         self.stage = stage
#         self.x = .0
#         self.y = .0
#         self.z = .0
#         self.dx = .0
#         self.dy = .0
#         self.dz = .0
#
#         self.entry_x = Gtk.Entry()
#         self.entry_x.set_text(str(self.x))
#         self.entry_x.set_alignment(1)
#         self.entry_x.set_max_length(7)
#         self.entry_y = Gtk.Entry()
#         self.entry_y.set_text(str(self.y))
#         self.entry_y.set_alignment(1)
#         self.entry_y.set_max_length(7)
#         self.entry_z = Gtk.Entry()
#         self.entry_z.set_text(str(self.z))
#         self.entry_z.set_alignment(1)
#         self.entry_z.set_max_length(7)
#
#         # Stage Control Button Table
#         self.table = Gtk.Table(3, 3, True)
#         self.table.attach(Gtk.Label(label="dx [um]"), 0, 1, 0, 1)
#         self.table.attach(Gtk.Label(label="dy [um]"), 0, 1, 1, 2)
#         self.table.attach(Gtk.Label(label="dz [um]"), 0, 1, 2, 3)
#         self.table.attach(self.entry_x, 1, 3, 0, 1)
#         self.table.attach(self.entry_y, 1, 3, 1, 2)
#         self.table.attach(self.entry_z, 1, 3, 2, 3)
#
#         # self.number_of_samples_spin.set_value(self.settings.number_of_samples)
#         # self.integration_time_spin.set_value(self.settings.integration_time)
#         self.box.add(self.table)
#
#         self.entry_x.connect("changed", self.on_change)
#         self.entry_y.connect("changed", self.on_change)
#         self.entry_z.connect("changed", self.on_change)
#
#         self.hide()
#
#     def on_change(self, widget):
#         dx = self.entry_x.get_text()
#         dy = self.entry_y.get_text()
#         dz = self.entry_z.get_text()
#         try:
#             dx = float(dx)
#         except ValueError:
#             dx = 0
#         try:
#             dy = float(dy)
#         except ValueError:
#             dy = 0
#         try:
#             dz = float(dz)
#         except ValueError:
#             dz = 0
#         if (self.x + dx) > 200:
#             dx = 0
#         if (self.x + dx) < 0:
#             dx = 0
#         if (self.y + dy) > 200:
#             dy = 0
#         if (self.y + dy) < 0:
#             dy = 0
#         if (self.z + dz) > 200:
#             dz = 0.0
#         if (self.z + dz) < 0:
#             dz = 0.0
#         self.entry_x.set_text(str(dx))
#         self.entry_y.set_text(str(dy))
#         self.entry_z.set_text(str(dz))
#         self.dx = dx
#         self.dy = dy
#         self.dz = dz
#
#     def rundialog(self):
#         pos = self.stage.pos()
#         self.x = pos[0]
#         self.y = pos[1]
#         self.z = pos[2]
#         self.show_all()
#         result = self.run()
#         if result == Gtk.ResponseType.OK:
#             self.stage.moverel(self.dx, self.dy, self.dz)
#         self.hide()
#
#
# class SpanGridDialog(Gtk.Dialog):
#     def __init__(self, parent):
#         # super(Settings_Dialog, self).__init__(self, "Settings", parent, 0, (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,Gtk.STOCK_OK, Gtk.ResponseType.OK))
#         Gtk.Dialog.__init__(self, "Direction of Stage Movement", parent, 0,
#                             (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OK, Gtk.ResponseType.OK))
#         # self.set_default_size(150, 100)
#
#         self.box = self.get_content_area()
#         self.box.set_spacing(6)
#
#         # Spinbuttons
#         self.x_adj = Gtk.Adjustment(value=5, lower=2, upper=1000, step_incr=1, page_incr=1, page_size=0)
#         self.y_adj = Gtk.Adjustment(value=5, lower=2, upper=1000, step_incr=1, page_incr=1, page_size=0)
#
#         self.x_spin = Gtk.SpinButton(adjustment=self.x_adj, climb_rate=1, digits=0)
#         self.y_spin = Gtk.SpinButton(adjustment=self.y_adj, climb_rate=1, digits=0)
#
#         # self.number_of_samples_spin.set_value(self.settings.number_of_samples)
#         # self.integration_time_spin.set_value(self.settings.integration_time)
#         self.box.add(Gtk.Label(label="X Steps"))
#         self.box.add(self.x_spin)
#         self.box.add(Gtk.Label(label="Y Steps"))
#         self.box.add(self.y_spin)
#
#         self.hide()
#
#     def rundialog(self):
#         self.show_all()
#         result = self.run()
#         self.hide()
#         if result == Gtk.ResponseType.OK:
#             return self.x_spin.get_value(), self.y_spin.get_value()
#         else:
#             return 0, 0
#
#
# class PrefixDialog(Gtk.Dialog):
#     def __init__(self, parent):
#         # super(Settings_Dialog, self).__init__(self, "Settings", parent, 0, (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,Gtk.STOCK_OK, Gtk.ResponseType.OK))
#         Gtk.Dialog.__init__(self, "Direction of Stage Movement", parent, 0,
#                             (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OK, Gtk.ResponseType.OK))
#         # self.set_default_size(150, 100)
#
#         self.box = self.get_content_area()
#         self.box.set_spacing(6)
#
#         # Spinbuttons
#         self.entry = Gtk.Entry()
#         self.entry.set_text('')
#
#         # self.number_of_samples_spin.set_value(self.settings.number_of_samples)
#         # self.integration_time_spin.set_value(self.settings.integration_time)
#         self.box.add(Gtk.Label(label="Prefix for Saving Spectra"))
#         self.box.add(self.entry)
#
#         self.hide()
#
#     def rundialog(self):
#         self.entry.set_text('')
#         self.show_all()
#         result = self.run()
#         self.hide()
#         if result == Gtk.ResponseType.OK:
#             return self.entry.get_text()
#         else:
#             return None