from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget, QTableWidgetItem, QLineEdit, QLabel, QMessageBox, QInputDialog
from PyQt5.QtCore import Qt

class MoveFolderDialog(QDialog):
    def __init__(self, api, token, parent=None):
        super().__init__(parent)
        self.api = api
        self.token = token
        self.setWindowTitle("选择目标文件夹")
        self.resize(600, 500)  # 弹窗适中大小
        self.current_parent_id = 0
        self.selected_folder_id = None
        self.folder_path = [(0, '根目录')]
        self.init_ui()
        self.load_folders()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # 路径面包屑
        top_bar = QHBoxLayout()
        self.back_btn = QPushButton('返回上一层')
        self.back_btn.setStyleSheet('''
            QPushButton {
                min-width: 70px;
                max-width: 100px;
                min-height: 22px;
                max-height: 26px;
                font-size: 13px;
                border: 1.2px solid #d0d7de;
                border-radius: 6px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ffffff, stop:1 #f8f9fa);
                color: #222;
            }
            QPushButton:hover {
                border-color: #165DFF;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ffffff, stop:1 #f0f7ff);
            }
        ''')
        self.back_btn.clicked.connect(self.on_back)
        top_bar.addWidget(self.back_btn)
        
        self.path_bar = QHBoxLayout()
        top_bar.addLayout(self.path_bar)
        top_bar.addStretch()
        layout.addLayout(top_bar)
        
        # 文件夹表格 - 只显示文件夹名称列
        self.table = QTableWidget()
        self.table.setColumnCount(1)
        self.table.setHorizontalHeaderLabels(["文件夹名"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.cellDoubleClicked.connect(self.on_cell_double_clicked)
        self.table.setMinimumHeight(350)
        self.table.verticalHeader().setDefaultSectionSize(32)
        self.table.setStyleSheet('''
QTableWidget {
    border-radius: 10px;
    border: 1.2px solid #d0d7de;
    background: #fafdff;
    font-size: 14px;
    selection-background-color: #e6f7ff;
    selection-color: #165DFF;
    gridline-color: #e0e0e0;
    alternate-background-color: #f5faff;
}
QHeaderView::section {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #A3C8F7, stop:1 #e6f7ff);
    color: #222;
    font-weight: bold;
    font-size: 14px;
    border: none;
    border-radius: 8px;
    height: 32px;
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
        layout.addWidget(self.table)
        
        # 按钮区
        btn_layout = QHBoxLayout()
        self.create_btn = QPushButton("创建目录")
        self.create_btn.setStyleSheet('''
            QPushButton {
                min-width: 80px;
                max-width: 120px;
                min-height: 32px;
                max-height: 36px;
                font-size: 14px;
                border: 1.2px solid #d0d7de;
                border-radius: 6px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ffffff, stop:1 #f8f9fa);
                color: #222;
            }
            QPushButton:hover {
                border-color: #165DFF;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ffffff, stop:1 #f0f7ff);
            }
        ''')
        self.create_btn.clicked.connect(self.on_create_dir)
        
        self.ok_btn = QPushButton("确定目录")
        self.ok_btn.setToolTip("选择当前目录或选中的子文件夹")
        self.ok_btn.setStyleSheet('''
            QPushButton {
                min-width: 80px;
                max-width: 120px;
                min-height: 32px;
                max-height: 36px;
                font-size: 14px;
                border: 1.2px solid #165DFF;
                border-radius: 6px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #165DFF, stop:1 #13C2C2);
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #13C2C2, stop:1 #165DFF);
            }
        ''')
        self.ok_btn.clicked.connect(self.on_ok)
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.create_btn)
        btn_layout.addSpacing(20)
        btn_layout.addWidget(self.ok_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def update_path_bar(self):
        # 清空原有
        while self.path_bar.count():
            item = self.path_bar.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        
        # 生成面包屑
        for i, (fid, name) in enumerate(self.folder_path):
            btn = QPushButton(name)
            btn.setFlat(True)
            btn.setStyleSheet('''
                QPushButton {
                    color: #165DFF;
                    font-weight: bold;
                    background: transparent;
                    padding: 0 1px;
                    font-size: 13px;
                    border: none;
                }
                QPushButton:hover {
                    color: #13C2C2;
                }
            ''')
            btn.clicked.connect(lambda _, idx=i: self.on_path_clicked(idx))
            self.path_bar.addWidget(btn)
            
            if i < len(self.folder_path) - 1:
                sep = QLabel('>')
                sep.setStyleSheet('QLabel{padding:0;color:#888;font-size:12px;}')
                self.path_bar.addWidget(sep)

    def load_folders(self, parent_id=None):
        parent_id = parent_id if parent_id is not None else self.current_parent_id
        self.table.setRowCount(0)
        self.table.setDisabled(True)
        
        try:
            resp = self.api.get_file_list(self.token, parent_file_id=parent_id, limit=100)
            if resp.get('code') != 0:
                QMessageBox.warning(self, "错误", f"获取文件夹失败: {resp.get('message')}")
                return
            
            data = resp.get('data', {})
            folders = [f for f in data.get('fileList', []) if f.get('type') == 1 and f.get('trashed', 0) == 0]
            
            self.table.setRowCount(len(folders))
            for row, f in enumerate(folders):
                # 只显示文件夹名称，但内部保存文件夹ID
                folder_name = f.get('filename', '')
                item = QTableWidgetItem(folder_name)
                item.setData(Qt.UserRole, f.get('fileId'))  # 将文件夹ID存储在UserRole中
                self.table.setItem(row, 0, item)
            
            self.current_parent_id = parent_id
            
            # 路径追踪
            if not self.folder_path or self.folder_path[-1][0] != parent_id:
                if parent_id == 0:
                    self.folder_path = [(0, '根目录')]
                else:
                    folder_name = None
                    for f in folders:
                        if f.get('fileId') == parent_id:
                            folder_name = f.get('filename', str(parent_id))
                            break
                    if not folder_name:
                        folder_name = str(parent_id)
                    self.folder_path.append((parent_id, folder_name))
            
            self.update_path_bar()
            self.selected_folder_id = None
            self.table.clearSelection()
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载文件夹失败: {e}")
        finally:
            self.table.setDisabled(False)

    def on_cell_double_clicked(self, row, col):
        # 进入子文件夹
        item = self.table.item(row, 0)
        folder_id = item.data(Qt.UserRole)  # 从UserRole获取文件夹ID
        folder_name = item.text()
        self.folder_path.append((folder_id, folder_name))
        self.load_folders(parent_id=folder_id)

    def on_path_clicked(self, idx):
        fid, _ = self.folder_path[idx]
        self.folder_path = self.folder_path[:idx+1]
        self.load_folders(parent_id=fid)

    def on_create_dir(self):
        dir_name, ok = QInputDialog.getText(self, "创建目录", "请输入新目录名称：")
        if ok and dir_name.strip():
            try:
                dir_id = self.api.create_directory(self.token, dir_name.strip(), self.current_parent_id)
                QMessageBox.information(self, "成功", f"目录 '{dir_name}' 创建成功！")
                self.load_folders(parent_id=self.current_parent_id)
            except Exception as e:
                QMessageBox.critical(self, "错误", f"创建目录失败: {e}")

    def on_ok(self):
        selected = self.table.selectedItems()
        if not selected:
            # 如果没有选择子文件夹，则选择当前目录
            self.selected_folder_id = self.current_parent_id
            self.accept()
        else:
            # 如果选择了子文件夹，则选择该子文件夹
            row = selected[0].row()
            item = self.table.item(row, 0)
            self.selected_folder_id = item.data(Qt.UserRole)  # 从UserRole获取文件夹ID
            self.accept()

    def on_back(self):
        if len(self.folder_path) > 1:
            self.folder_path.pop()
            fid, _ = self.folder_path[-1]
            self.load_folders(parent_id=fid)

    def get_selected_folder_id(self):
        return self.selected_folder_id 