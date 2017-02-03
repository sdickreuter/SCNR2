from PyQt5.QtCore import QAbstractTableModel, QVariant, Qt, QModelIndex
import numpy as np

class NumpyModel(QAbstractTableModel):
    def __init__(self, data, parent=None):
        QAbstractTableModel.__init__(self, parent)
        self._data = np.array(data)
        self._cols = data.shape[1]
        self.r, self.c = self._data.shape

    def getMatrix(self):
        return self._data.copy()

    def rowCount(self, parent=None):
        return self._data.shape[0]

    def columnCount(self, parent=None):
        return self._data.shape[1]

    def data(self, index, role=Qt.DisplayRole):
        if index.isValid():
            if role == Qt.DisplayRole or role == Qt.EditRole :
                row = index.row()
                col = index.column()
                return QVariant("%.5f"%self._data[row, col])
        return QVariant()

    def setData(self, index, value, role = Qt.EditRole):
        if role == Qt.EditRole:
            try:
                val = float(value)
            except:
                return False
            self._data[index.row(),index.column()] = val
            self.dataChanged.emit(index, index, ())
            return True
        return False

    def flags(self, index):
        #if (index.column() == 0):
        return Qt.ItemIsEditable | Qt.ItemIsEnabled | Qt.ItemIsSelectable
        #else:
        #    return Qt.ItemIsEnabled

    def headerData(self, col, orientation, role):
        if role != Qt.DisplayRole:
            return QVariant()

        if orientation == Qt.Horizontal:
            if col == 0:
                return 'x'
            if col == 1:
                return 'y'
        return QVariant()

    def addData(self, data):
        position = self.rowCount()
        count = data.shape[0]

        self.beginInsertRows(QModelIndex(), position, position + count - 1)
        self._data = np.append(self._data,data,axis=0)
        self.endInsertRows()
        return True


    def removeRows(self, rows):
        position = min(rows)
        count = len(rows)
        self.beginRemoveRows(QModelIndex(), position, position + count - 1)
        indices = np.arange(0,self._data.shape[0])
        for row in rows:
            indices = indices[np.where(indices != row)]
        self._data = self._data[indices,:]
        self.endRemoveRows()
        return True
