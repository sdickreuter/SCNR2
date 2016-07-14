# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'launcher_main.ui'
#
# Created by: PyQt5 UI code generator 5.6
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.setEnabled(True)
        MainWindow.resize(270, 120)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(MainWindow.sizePolicy().hasHeightForWidth())
        MainWindow.setSizePolicy(sizePolicy)
        MainWindow.setMinimumSize(QtCore.QSize(270, 120))
        MainWindow.setMaximumSize(QtCore.QSize(270, 120))
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.centralwidget)
        self.verticalLayout.setObjectName("verticalLayout")
        self.spectrometerButton = QtWidgets.QPushButton(self.centralwidget)
        self.spectrometerButton.setObjectName("spectrometerButton")
        self.verticalLayout.addWidget(self.spectrometerButton)
        self.startButton = QtWidgets.QPushButton(self.centralwidget)
        self.startButton.setEnabled(False)
        self.startButton.setObjectName("startButton")
        self.verticalLayout.addWidget(self.startButton)
        self.quitButton = QtWidgets.QPushButton(self.centralwidget)
        self.quitButton.setObjectName("quitButton")
        self.verticalLayout.addWidget(self.quitButton)
        MainWindow.setCentralWidget(self.centralwidget)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "SCNR2 Launcher"))
        self.spectrometerButton.setText(_translate("MainWindow", "Initialize Spectrometer"))
        self.startButton.setText(_translate("MainWindow", "Start Graphical User Interface"))
        self.quitButton.setText(_translate("MainWindow", "Quit"))

