# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'griddialog.ui'
#
# Created by: PyQt5 UI code generator 5.8.2
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_SpanGridDialog(object):
    def setupUi(self, SpanGridDialog):
        SpanGridDialog.setObjectName("SpanGridDialog")
        SpanGridDialog.setEnabled(True)
        SpanGridDialog.resize(500, 580)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(SpanGridDialog.sizePolicy().hasHeightForWidth())
        SpanGridDialog.setSizePolicy(sizePolicy)
        SpanGridDialog.setMinimumSize(QtCore.QSize(500, 580))
        SpanGridDialog.setMaximumSize(QtCore.QSize(500, 580))
        SpanGridDialog.setBaseSize(QtCore.QSize(280, 115))
        SpanGridDialog.setSizeGripEnabled(False)
        self.buttonBox = QtWidgets.QDialogButtonBox(SpanGridDialog)
        self.buttonBox.setEnabled(True)
        self.buttonBox.setGeometry(QtCore.QRect(150, 540, 340, 32))
        self.buttonBox.setMaximumSize(QtCore.QSize(340, 16777215))
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.gridLayoutWidget = QtWidgets.QWidget(SpanGridDialog)
        self.gridLayoutWidget.setGeometry(QtCore.QRect(10, 0, 221, 91))
        self.gridLayoutWidget.setObjectName("gridLayoutWidget")
        self.gridLayout = QtWidgets.QGridLayout(self.gridLayoutWidget)
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.gridLayout.setObjectName("gridLayout")
        self.label = QtWidgets.QLabel(self.gridLayoutWidget)
        self.label.setObjectName("label")
        self.gridLayout.addWidget(self.label, 0, 0, 1, 1)
        self.x_spin = QtWidgets.QSpinBox(self.gridLayoutWidget)
        self.x_spin.setMinimumSize(QtCore.QSize(0, 25))
        self.x_spin.setMinimum(1)
        self.x_spin.setMaximum(9999)
        self.x_spin.setProperty("value", 5)
        self.x_spin.setObjectName("x_spin")
        self.gridLayout.addWidget(self.x_spin, 0, 1, 1, 1)
        self.label_2 = QtWidgets.QLabel(self.gridLayoutWidget)
        self.label_2.setObjectName("label_2")
        self.gridLayout.addWidget(self.label_2, 1, 0, 1, 1)
        self.y_spin = QtWidgets.QSpinBox(self.gridLayoutWidget)
        self.y_spin.setMinimumSize(QtCore.QSize(0, 25))
        self.y_spin.setMinimum(1)
        self.y_spin.setMaximum(9999)
        self.y_spin.setProperty("value", 5)
        self.y_spin.setObjectName("y_spin")
        self.gridLayout.addWidget(self.y_spin, 1, 1, 1, 1)
        self.plotwidget = QtWidgets.QWidget(SpanGridDialog)
        self.plotwidget.setGeometry(QtCore.QRect(10, 100, 481, 391))
        self.plotwidget.setObjectName("plotwidget")
        self.verticalLayoutWidget = QtWidgets.QWidget(SpanGridDialog)
        self.verticalLayoutWidget.setGeometry(QtCore.QRect(240, 0, 251, 91))
        self.verticalLayoutWidget.setObjectName("verticalLayoutWidget")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.verticalLayoutWidget)
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout.setObjectName("verticalLayout")
        self.flipxlabels = QtWidgets.QCheckBox(self.verticalLayoutWidget)
        self.flipxlabels.setObjectName("flipxlabels")
        self.verticalLayout.addWidget(self.flipxlabels)
        self.flipylabels = QtWidgets.QCheckBox(self.verticalLayoutWidget)
        self.flipylabels.setObjectName("flipylabels")
        self.verticalLayout.addWidget(self.flipylabels)
        self.transposelabels = QtWidgets.QCheckBox(self.verticalLayoutWidget)
        self.transposelabels.setObjectName("transposelabels")
        self.verticalLayout.addWidget(self.transposelabels)
        self.label_3 = QtWidgets.QLabel(SpanGridDialog)
        self.label_3.setGeometry(QtCore.QRect(10, 500, 471, 51))
        self.label_3.setTextFormat(QtCore.Qt.PlainText)
        self.label_3.setWordWrap(True)
        self.label_3.setObjectName("label_3")

        self.retranslateUi(SpanGridDialog)
        self.buttonBox.accepted.connect(SpanGridDialog.accept)
        self.buttonBox.rejected.connect(SpanGridDialog.reject)
        self.x_spin.editingFinished.connect(SpanGridDialog.on_x_edited)
        self.y_spin.editingFinished.connect(SpanGridDialog.on_y_edited)
        self.transposelabels.toggled['bool'].connect(SpanGridDialog.transpose_toggled)
        self.flipxlabels.toggled['bool'].connect(SpanGridDialog.flipx_toggled)
        self.flipylabels.toggled['bool'].connect(SpanGridDialog.flipy_toggled)
        QtCore.QMetaObject.connectSlotsByName(SpanGridDialog)

    def retranslateUi(self, SpanGridDialog):
        _translate = QtCore.QCoreApplication.translate
        SpanGridDialog.setWindowTitle(_translate("SpanGridDialog", "Span Grid"))
        self.label.setText(_translate("SpanGridDialog", "X Steps"))
        self.label_2.setText(_translate("SpanGridDialog", "Y Steps"))
        self.flipxlabels.setText(_translate("SpanGridDialog", "Flip x labels"))
        self.flipylabels.setText(_translate("SpanGridDialog", "Flip y labels"))
        self.transposelabels.setText(_translate("SpanGridDialog", "Transpose labels"))
        self.label_3.setText(_translate("SpanGridDialog", "Important: The Figure above is in the coordinate System of the  Piezo-Stage. If you want to compare it to the camera, please make sure that both coordinate systems are aligned. "))

