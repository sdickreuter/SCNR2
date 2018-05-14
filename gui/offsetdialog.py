# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'offsetdialog.ui'
#
# Created by: PyQt5 UI code generator 5.10.1
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_OffsetDialog(object):
    def setupUi(self, OffsetDialog):
        OffsetDialog.setObjectName("OffsetDialog")
        OffsetDialog.resize(249, 159)
        self.verticalLayout = QtWidgets.QVBoxLayout(OffsetDialog)
        self.verticalLayout.setObjectName("verticalLayout")
        self.detectoroffset_label = QtWidgets.QLabel(OffsetDialog)
        self.detectoroffset_label.setObjectName("detectoroffset_label")
        self.verticalLayout.addWidget(self.detectoroffset_label)
        self.detectoroffset_spinBox = QtWidgets.QSpinBox(OffsetDialog)
        self.detectoroffset_spinBox.setMinimum(-10000)
        self.detectoroffset_spinBox.setMaximum(10000)
        self.detectoroffset_spinBox.setObjectName("detectoroffset_spinBox")
        self.verticalLayout.addWidget(self.detectoroffset_spinBox)
        self.gratingoffset_label = QtWidgets.QLabel(OffsetDialog)
        self.gratingoffset_label.setObjectName("gratingoffset_label")
        self.verticalLayout.addWidget(self.gratingoffset_label)
        self.gratingoffset_spinBox = QtWidgets.QSpinBox(OffsetDialog)
        self.gratingoffset_spinBox.setMinimum(-10000)
        self.gratingoffset_spinBox.setMaximum(10000)
        self.gratingoffset_spinBox.setObjectName("gratingoffset_spinBox")
        self.verticalLayout.addWidget(self.gratingoffset_spinBox)
        spacerItem = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.verticalLayout.addItem(spacerItem)
        self.buttonBox = QtWidgets.QDialogButtonBox(OffsetDialog)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.verticalLayout.addWidget(self.buttonBox)

        self.retranslateUi(OffsetDialog)
        self.buttonBox.accepted.connect(OffsetDialog.accept)
        self.buttonBox.rejected.connect(OffsetDialog.reject)
        QtCore.QMetaObject.connectSlotsByName(OffsetDialog)

    def retranslateUi(self, OffsetDialog):
        _translate = QtCore.QCoreApplication.translate
        OffsetDialog.setWindowTitle(_translate("OffsetDialog", "Dialog"))
        self.detectoroffset_label.setText(_translate("OffsetDialog", "Detector Offset"))
        self.gratingoffset_label.setText(_translate("OffsetDialog", "Grating Offset"))

