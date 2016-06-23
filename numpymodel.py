from PyQt5.QtCore import QAbstractTableModel, QVariant, Qt

class NumpyModel(QAbstractTableModel):
    def __init__(self, nmatrix, parent=None):
        QAbstractTableModel.__init__(self, parent)
        self._matrix = nmatrix

    def update(self, narray):
        self._matrix = narray.copy()
        self.layoutChanged.emit()

    def getMatrix(self):
        return self._matrix.copy()

    def rowCount(self, parent=None):
        return self._matrix.shape[0]

    def columnCount(self, parent=None):
        return self._matrix.shape[1]

    def data(self, index, role=Qt.DisplayRole):
        if index.isValid():
            if role == Qt.DisplayRole or role == Qt.EditRole :
                row = index.row()
                col = index.column()
                return QVariant("%.5f"%self._matrix[row, col])
        return QVariant()

    def setData(self, index, value, role = Qt.EditRole):
        if role == Qt.EditRole:
            try:
                val = float(value)
            except:
                return False
            self._matrix[index.row(),index.column()] = val
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
