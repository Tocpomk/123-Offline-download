from PyQt5.QtWidgets import QWidget, QHBoxLayout, QPushButton, QLabel, QComboBox, QLineEdit, QSizePolicy
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtCore import Qt

class PaginationWidget(QWidget):
    page_changed = pyqtSignal(int, int)  # (page, page_size)

    def __init__(self, total=0, page_size=20, parent=None):
        super().__init__(parent)
        self.total = total
        self.page_size = page_size
        self.page = 1
        self.page_count = 1
        self.init_ui()
        self.update_info()

    def init_ui(self):
        layout = QHBoxLayout()
        layout.addStretch()  # 左侧留白
        self.prev_btn = QPushButton("〈")
        self.prev_btn.setMinimumWidth(60)
        self.prev_btn.setMinimumHeight(32)
        self.prev_btn.clicked.connect(self.go_prev)
        layout.addWidget(self.prev_btn)
        self.next_btn = QPushButton("〉")
        self.next_btn.setMinimumWidth(60)
        self.next_btn.setMinimumHeight(32)
        self.next_btn.clicked.connect(self.go_next)
        layout.addWidget(self.next_btn)
        layout.addStretch()  # 右侧留白
        self.total_label = QLabel("共0条")
        layout.addWidget(self.total_label)
        self.setLayout(layout)

    def update_info(self):
        # 只更新按钮状态和总数
        self.prev_btn.setEnabled(self.page > 1)
        self.next_btn.setEnabled(self.page < self.page_count)
        self.total_label.setText(f"共{self.total}条")

    def set_total(self, total):
        self.total = total
        self.page_count = max(1, (self.total + self.page_size - 1) // self.page_size)
        self.update_info()

    def set_page(self, page):
        self.page = max(1, min(page, self.page_count))
        self.update_info()

    def set_page_size(self, size):
        self.page_size = size
        self.update_info()

    def on_size_changed(self, idx):
        size = int(self.size_combo.currentText().split('/')[0])
        self.page_size = size
        self.page = 1
        self.update_info()
        self.page_changed.emit(self.page, self.page_size)

    # 移除 on_page_edit

    def go_first(self):
        pass  # 移除首页功能

    def go_prev(self):
        if self.page > 1:
            self.set_page(self.page - 1)
            self.page_changed.emit(self.page, self.page_size)

    def go_next(self):
        if self.page < self.page_count:
            self.set_page(self.page + 1)
            self.page_changed.emit(self.page, self.page_size)

    def go_last(self):
        pass  # 移除末页功能 