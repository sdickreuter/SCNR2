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
        position = self._data.shape[0]
        count = data.shape[0]
        self.beginInsertRows(QModelIndex(), position, position + count - 1)
        #self._data = np.append(self._data,data,axis=0)
        if position > 0:
            self._data = np.vstack((self._data,data))
        else:
            self._data = data
        self.endInsertRows()

        return True


    def removeRows(self, rows):
        for row in rows:
            if row in np.arange(0,self._data.shape[0]):
                position = row
                count = 1
                self.beginRemoveRows(QModelIndex(), position, position + count - 1)
                self._data = np.delete(self._data, rows, axis=0)
                self.endRemoveRows()
        return True


    def clear(self):
        count = self._data.shape[0]
        self.beginRemoveRows(QModelIndex(), 0, count - 1)
        self._data = np.empty((0,2))
        self.endRemoveRows()
        return True

if __name__ == '__main__':

    position = np.matrix([[1,1],[2,2],[3,4],[5,6]])
    posModel = NumpyModel(position)
    print(posModel.getMatrix())
    posModel.clear()
    print(posModel.getMatrix())
    posModel.addData(position)
    posModel.addData(np.matrix([10,20]))
    print(posModel.getMatrix())
    posModel.removeRows([1,2,3,7])
    print(posModel.getMatrix())
