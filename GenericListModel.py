from PyQt5 import QtCore
from PyQt5.QtCore import pyqtSlot, QModelIndex, QVariant


class GenericListModel(QtCore.QAbstractListModel):
    def __init__(self, schema, parent=None):
        super(GenericListModel, self).__init__(parent)

        self.items = list()

        self.schema = schema

    @pyqtSlot(QVariant)
    def append(self, item):
        self.beginInsertRows(QtCore.QModelIndex(), self.rowCount(), self.rowCount())
        if not isinstance(item, dict):
            item = item.toVariant()
        self.items.append(item)
        self.endInsertRows()

    @pyqtSlot(int)
    def remove(self, ind):
        self.beginRemoveRows(QModelIndex(), ind, ind)
        self.items.pop(ind)
        self.endRemoveRows()

    @pyqtSlot()
    def clear(self):
        self.beginRemoveRows(QModelIndex(), 0, len(self.items) - 1)
        self.items.clear()
        self.endRemoveRows()

    def data(self, index, role):
        key = self.schema[role]
        return self.items[index.row()].get(key)

    def setData(self, index, value, role):
        key = self.schema[role]
        self.items[index.row()][key] = value
        self.dataChanged.emit(index, index)
        return True

    def rowCount(self, parent=QtCore.QModelIndex()):
        return len(self.items)

    def roleNames(self):
        return {key: value.encode('utf-8') for key, value in enumerate(self.schema)}

    @pyqtSlot(str, str, result="bool")
    def contains(self, key, value):
        for item in self.items:
            if item[key] == value:
                return True
        return False
