# MultiSelectComboBox.py
from PySide6.QtGui import QStandardItemModel, QStandardItem
from PySide6.QtWidgets import QComboBox
from PySide6.QtCore import Qt
from db import get_all_tags


class MultiSelectComboBox(QComboBox):
    def __init__(self, parent=None, book_name="总单词册", book_color="#FF0000"):
        super(MultiSelectComboBox, self).__init__(parent)
        self.book_name = book_name
        self.book_color = book_color
        self.setModel(QStandardItemModel(self))
        self.add_all_tags_item()
        self.all_tags_item_changed = False
        self.model().itemChanged.connect(self.handle_item_changed)

    def add_all_tags_item(self):
        self.all_tags_item = QStandardItem("全部标签")
        self.all_tags_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
        self.all_tags_item.setData(Qt.Unchecked, Qt.CheckStateRole)
        self.model().appendRow(self.all_tags_item)

    def addItem(self, text, checked=False):
        if text == "全部标签":
            return
        item = QStandardItem(text)
        item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
        item.setData(Qt.Checked if checked else Qt.Unchecked, Qt.CheckStateRole)
        self.model().appendRow(item)

    def selectedItems(self):
        selected = []
        for index in range(1, self.model().rowCount()):  # Skip "全部标签" at index 0
            item = self.model().item(index)
            if item.checkState() == Qt.Checked:
                selected.append(item.text())
        return selected

    def clear(self):
        self.model().clear()
        self.add_all_tags_item()

    def allItems(self):
        return get_all_tags(self.book_name, self.book_color)

    def handle_item_changed(self, item):
        if self.all_tags_item_changed:
            return
        self.all_tags_item_changed = True
        try:
            if item == self.all_tags_item:
                state = item.checkState()
                for i in range(1, self.model().rowCount()):
                    self.model().item(i).setCheckState(state)
            elif item != self.all_tags_item:
                if item.checkState() == Qt.Unchecked and self.all_tags_item.checkState() == Qt.Checked:
                    self.all_tags_item.setCheckState(Qt.Unchecked)
                elif all(self.model().item(i).checkState() == Qt.Checked for i in range(1, self.model().rowCount())):
                    self.all_tags_item.setCheckState(Qt.Checked)
        finally:
            self.all_tags_item_changed = False