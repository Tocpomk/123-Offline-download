from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem, QMessageBox, QComboBox, QSizePolicy, QSpacerItem, QFormLayout, QWidget, QTextEdit
from PyQt5.QtCore import Qt
import re

class BatchRenameDialog(QDialog):
    def __init__(self, file_infos, parent=None):
        super().__init__(parent)
        self.setWindowTitle("批量重命名")
        self.resize(1000, 540)  # 更宽
        self.file_infos = file_infos  # [{'file_id':..., 'file_name':...}, ...]
        self.rename_list = []  # [{'file_id':..., 'old_name':..., 'new_name':...}, ...]
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        # 模式选择区
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("重命名模式:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["正则模式", "剧集模式"])
        self.mode_combo.setFixedWidth(120)
        self.mode_combo.setCurrentIndex(1)  # 默认剧集模式
        self.mode_combo.currentIndexChanged.connect(self.on_mode_changed)
        mode_layout.addWidget(self.mode_combo)
        mode_layout.addStretch()
        layout.addLayout(mode_layout)
        # 规则输入区（两个widget，切换时show/hide）
        self.rule_layout = QHBoxLayout()
        self.rule_layout.setSpacing(8)
        self.rule_layout.setContentsMargins(0, 0, 0, 0)
        # 正则模式控件
        self.regex_widget = QWidget()
        regex_hbox = QHBoxLayout()
        regex_hbox.setSpacing(8)
        self.find_input = QLineEdit()
        self.find_input.setPlaceholderText("查找(正则)")
        self.find_input.setFixedWidth(220)
        self.replace_input = QLineEdit()
        self.replace_input.setPlaceholderText("替换为")
        self.replace_input.setFixedWidth(220)
        regex_hbox.addWidget(self.find_input)
        regex_hbox.addWidget(self.replace_input)
        self.regex_widget.setLayout(regex_hbox)
        # 剧集模式控件
        self.episode_widget = QWidget()
        episode_form = QFormLayout()
        episode_form.setHorizontalSpacing(8)
        episode_form.setVerticalSpacing(0)
        episode_form.setContentsMargins(0, 0, 0, 0)
        self.prefix_input = QLineEdit()
        self.prefix_input.setPlaceholderText("前缀，如 灵笼.")
        self.prefix_input.setFixedWidth(220)
        self.season_input = QLineEdit()
        self.season_input.setPlaceholderText("季数，如 1")
        self.season_input.setFixedWidth(120)
        episode_form.addRow(QLabel("前缀："), self.prefix_input)
        episode_form.addRow(QLabel("季数："), self.season_input)
        episode_hbox = QHBoxLayout()
        episode_hbox.setSpacing(8)
        episode_hbox.addLayout(episode_form)
        self.episode_widget.setLayout(episode_hbox)
        self.rule_layout.addWidget(self.regex_widget)
        self.rule_layout.addWidget(self.episode_widget)
        # 统一的预览按钮
        self.preview_btn = QPushButton("预览")
        self.preview_btn.setFixedHeight(32)
        self.preview_btn.setFixedWidth(110)
        self.preview_btn.clicked.connect(self.on_preview)
        self.rule_layout.addWidget(self.preview_btn)
        layout.addLayout(self.rule_layout)
        layout.addSpacing(16)
        # 预览表格
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["文件ID", "原文件名", "新文件名"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.NoSelection)
        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.table.setMinimumHeight(340)
        self.table.setStyleSheet('''
QTableWidget {
    border-radius: 10px;
    border: 1.2px solid #d0d7de;
    background: #fafdff;
    font-size: 15px;
    selection-background-color: #e6f7ff;
    selection-color: #165DFF;
    gridline-color: #e0e0e0;
    alternate-background-color: #f5faff;
}
QHeaderView::section {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #A3C8F7, stop:1 #e6f7ff);
    color: #222;
    font-weight: bold;
    font-size: 16px;
    border: none;
    border-radius: 8px;
    height: 38px;
    padding: 4px 0;
}
QTableWidget::item {
    border-radius: 6px;
    padding: 6px 8px;
}
QTableWidget::item:selected {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #e6f7ff, stop:1 #cce7ff);
    color: #165DFF;
    border: 1.2px solid #165DFF;
}
QTableWidget::item:hover {
    background: #f0faff;
}
QCornerButton::section {
    background: #A3C8F7;
    border-radius: 8px;
}
QScrollBar:vertical {
    width: 10px;
    background: #f0f4f8;
    margin: 0px 0px 0px 0px;
    border-radius: 5px;
}
QScrollBar::handle:vertical {
    background: #A3C8F7;
    min-height: 20px;
    border-radius: 5px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
''')
        self.table.verticalHeader().setDefaultSectionSize(36)
        self.table.setColumnWidth(0, 120)
        self.table.setColumnWidth(1, 400)
        self.table.setColumnWidth(2, 400)
        self.table.cellDoubleClicked.connect(self.on_table_double_clicked)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.on_table_context_menu)
        layout.addWidget(self.table)
        # 按钮区
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.ok_btn = QPushButton("应用重命名")
        self.ok_btn.setFixedHeight(36)
        self.ok_btn.setFixedWidth(160)
        self.ok_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self.ok_btn)
        btn_layout.addSpacing(60)
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setFixedHeight(36)
        self.cancel_btn.setFixedWidth(120)
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        self.setLayout(layout)
        self.on_mode_changed()

    def on_mode_changed(self):
        mode = self.mode_combo.currentText()
        self.regex_widget.hide()
        self.episode_widget.hide()
        if mode == "正则模式":
            self.regex_widget.show()
        else:
            self.episode_widget.show()
        self.on_preview()

    def on_preview(self):
        mode = self.mode_combo.currentText()
        self.rename_list = []
        self.table.setRowCount(len(self.file_infos))
        if mode == "正则模式":
            find = self.find_input.text().strip()
            replace = self.replace_input.text().strip()
            for i, info in enumerate(self.file_infos):
                old_name = info['file_name']
                new_name = old_name
                if find:
                    try:
                        new_name = re.sub(find, replace, old_name)
                    except Exception as e:
                        new_name = old_name
                self.rename_list.append({'file_id': info['file_id'], 'old_name': old_name, 'new_name': new_name})
                self.table.setItem(i, 0, QTableWidgetItem(info['file_id']))
                old_item = QTableWidgetItem(old_name)
                old_item.setToolTip(old_name)
                self.table.setItem(i, 1, old_item)
                new_item = QTableWidgetItem(new_name)
                new_item.setToolTip(new_name)
                self.table.setItem(i, 2, new_item)
        else:
            prefix = self.prefix_input.text().strip()
            season = self.season_input.text().strip() or '1'
            for i, info in enumerate(self.file_infos):
                old_name = info['file_name']
                ep = self.extract_episode_number(old_name)
                ext = self.get_ext(old_name)
                if ep:
                    new_name = f'{prefix} S{int(season):02d}E{int(ep):02d}{ext}'
                else:
                    new_name = old_name
                self.rename_list.append({'file_id': info['file_id'], 'old_name': old_name, 'new_name': new_name})
                self.table.setItem(i, 0, QTableWidgetItem(info['file_id']))
                old_item = QTableWidgetItem(old_name)
                old_item.setToolTip(old_name)
                self.table.setItem(i, 1, old_item)
                new_item = QTableWidgetItem(new_name)
                new_item.setToolTip(new_name)
                self.table.setItem(i, 2, new_item)

    def extract_episode_number(self, name):
        # 支持 SxxExx、EPxx、E01、01、1 等多种剧集格式
        m = re.search(r'[Ss](\d{1,2})[Ee](\d{1,3})', name)
        if m:
            return m.group(2)
        m = re.search(r'[Ee][Pp]?(\d{1,3})', name)
        if m:
            return m.group(1)
        m = re.search(r'(\d{2,3})', name)
        if m:
            return m.group(1)
        return None

    def get_ext(self, name):
        idx = name.rfind('.')
        return name[idx:] if idx != -1 else ''

    def get_rename_list(self):
        return self.rename_list

    def on_table_double_clicked(self, row, col):
        # 1=原文件名，2=新文件名，双击直接复制
        if col in (1, 2):
            item = self.table.item(row, col)
            if item:
                text = item.text()
                from PyQt5.QtWidgets import QApplication, QToolTip
                QApplication.clipboard().setText(text)
                QToolTip.showText(self.table.viewport().mapToGlobal(self.table.visualItemRect(item).center()), "已复制")

    def on_table_context_menu(self, pos):
        index = self.table.indexAt(pos)
        row, col = index.row(), index.column()
        if col in (1, 2) and row >= 0:
            from PyQt5.QtWidgets import QMenu
            menu = QMenu(self)
            action = menu.addAction("查看完整文件名")
            action.triggered.connect(lambda: self.show_full_name_dialog(row, col))
            menu.exec_(self.table.viewport().mapToGlobal(pos))

    def show_full_name_dialog(self, row, col):
        item = self.table.item(row, col)
        if item:
            text = item.text()
            title = "原文件名" if col == 1 else "新文件名"
            dlg = FileNameDialog(title, text, self)
            dlg.exec_()

class FileNameDialog(QDialog):
    def __init__(self, title, text, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(600, 180)
        layout = QVBoxLayout(self)
        self.text_edit = QTextEdit()
        self.text_edit.setPlainText(text)
        self.text_edit.setReadOnly(True)
        self.text_edit.setMinimumHeight(60)
        self.text_edit.setMaximumHeight(80)
        self.text_edit.setLineWrapMode(QTextEdit.NoWrap)
        layout.addWidget(self.text_edit)
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.copy_btn = QPushButton("复制")
        self.copy_btn.setFixedWidth(120)
        self.copy_btn.clicked.connect(self.copy_text)
        btn_layout.addWidget(self.copy_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
    def copy_text(self):
        from PyQt5.QtWidgets import QApplication, QToolTip
        text = self.text_edit.toPlainText()
        QApplication.clipboard().setText(text)
        QToolTip.showText(self.copy_btn.mapToGlobal(self.copy_btn.rect().center()), "已复制") 