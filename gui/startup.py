# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'startup.ui'
#
# Created by: PyQt5 UI code generator 5.9
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_Startup_Dialog(object):
    def setupUi(self, Startup_Dialog):
        Startup_Dialog.setObjectName("Startup_Dialog")
        Startup_Dialog.resize(282, 141)
        self.verticalLayoutWidget = QtWidgets.QWidget(Startup_Dialog)
        self.verticalLayoutWidget.setGeometry(QtCore.QRect(0, 0, 281, 141))
        self.verticalLayoutWidget.setObjectName("verticalLayoutWidget")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.verticalLayoutWidget)
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout.setObjectName("verticalLayout")
        self.label = QtWidgets.QLabel(self.verticalLayoutWidget)
        self.label.setObjectName("label")
        self.verticalLayout.addWidget(self.label)
        self.setup_combobox = QtWidgets.QComboBox(self.verticalLayoutWidget)
        self.setup_combobox.setEditable(False)
        self.setup_combobox.setCurrentText("Freespace")
        self.setup_combobox.setObjectName("setup_combobox")
        self.setup_combobox.addItem("")
        self.setup_combobox.addItem("")
        self.setup_combobox.addItem("")
        self.verticalLayout.addWidget(self.setup_combobox)
        self.stage_checkbox = QtWidgets.QCheckBox(self.verticalLayoutWidget)
        self.stage_checkbox.setChecked(True)
        self.stage_checkbox.setObjectName("stage_checkbox")
        self.verticalLayout.addWidget(self.stage_checkbox)
        self.cam_checkbox = QtWidgets.QCheckBox(self.verticalLayoutWidget)
        self.cam_checkbox.setChecked(True)
        self.cam_checkbox.setObjectName("cam_checkbox")
        self.verticalLayout.addWidget(self.cam_checkbox)
        self.buttonBox = QtWidgets.QDialogButtonBox(self.verticalLayoutWidget)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.verticalLayout.addWidget(self.buttonBox)

        self.retranslateUi(Startup_Dialog)
        self.setup_combobox.setCurrentIndex(0)
        self.buttonBox.accepted.connect(Startup_Dialog.accept)
        self.buttonBox.rejected.connect(Startup_Dialog.reject)
        QtCore.QMetaObject.connectSlotsByName(Startup_Dialog)

    def retranslateUi(self, Startup_Dialog):
        _translate = QtCore.QCoreApplication.translate
        Startup_Dialog.setWindowTitle(_translate("Startup_Dialog", "Choose start up options"))
        self.label.setText(_translate("Startup_Dialog", "Choose the Setup you want to use:"))
        self.setup_combobox.setItemText(0, _translate("Startup_Dialog", "Freespace"))
        self.setup_combobox.setItemText(1, _translate("Startup_Dialog", "Nikon"))
        self.setup_combobox.setItemText(2, _translate("Startup_Dialog", "Zeiss"))
        self.stage_checkbox.setText(_translate("Startup_Dialog", "Use Piezo-Stage"))
        self.cam_checkbox.setText(_translate("Startup_Dialog", "Use Camera"))

