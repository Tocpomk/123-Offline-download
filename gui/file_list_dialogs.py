from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QTextEdit, QScrollArea, QWidget, QProgressBar
from PyQt5.QtCore import Qt

class ProgressDialog(QDialog):
    def __init__(self, title, total, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(420, 180)
        layout = QVBoxLayout(self)
        self.label = QLabel("正在批量重命名...")
        self.label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.label)
        self.progress = QProgressBar()
        self.progress.setRange(0, total)
        self.progress.setValue(0)
        self.progress.setFixedHeight(32)
        layout.addWidget(self.progress)
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setFixedWidth(120)
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        self.cancel_btn.clicked.connect(self.reject)
    
    def setValue(self, val):
        self.progress.setValue(val)
    
    def setLabelText(self, text):
        self.label.setText(text)
    
    def exec_(self):
        return super().exec_()

class RenameDialog(QDialog):
    def __init__(self, file_infos, parent=None):
        super().__init__(parent)
        self.file_infos = file_infos  # 存储文件信息列表
        self.setWindowTitle("重命名")
        self.setFixedSize(500, 180)
        self.setStyleSheet("""
            QDialog {
                background: #ffffff;
                border: 2px solid #e1e5e9;
                border-radius: 12px;
            }
            QLabel {
                font-size: 15px;
                color: #333333;
                padding: 8px 0px;
            }
            QLineEdit {
                border: 2px solid #e1e5e9;
                border-radius: 8px;
                padding: 12px 16px;
                font-size: 15px;
                background: #fafdff;
                min-height: 20px;
            }
            QLineEdit:focus {
                border-color: #165DFF;
                background: #ffffff;
            }
            QPushButton {
                font-weight: bold;
                border: none;
                border-radius: 8px;
                padding: 10px 24px;
                font-size: 15px;
                min-width: 100px;
                min-height: 36px;
            }
            QPushButton#confirmBtn {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #165DFF, stop:1 #0FC6C2);
                color: #ffffff;
            }
            QPushButton#confirmBtn:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0E4FE1, stop:1 #0FC6C2);
            }
            QPushButton#confirmBtn:disabled {
                background: #cccccc;
                color: #999999;
            }
            QPushButton#cancelBtn {
                background: #f5f5f5;
                color: #666666;
                border: 1px solid #d9d9d9;
            }
            QPushButton#cancelBtn:hover {
                background: #e6e6e6;
                color: #333333;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # 显示选中的文件信息
        if len(file_infos) == 1:
            # 单选：显示文件名输入框
            self.name_edit = QLineEdit(file_infos[0]['file_name'])
            self.name_edit.selectAll()  # 自动选中所有文本
            layout.addWidget(self.name_edit)
        else:
            # 多选：显示文件列表
            info_label = QLabel(f"已选择 {len(file_infos)} 个文件/文件夹：")
            layout.addWidget(info_label)
            
            self.file_list_edit = QTextEdit()
            self.file_list_edit.setMaximumHeight(80)
            self.file_list_edit.setReadOnly(True)
            file_names = [info['file_name'] for info in file_infos]
            self.file_list_edit.setPlainText('\n'.join(file_names))
            layout.addWidget(self.file_list_edit)
            
            # 多选时不允许重命名，只显示文件列表
            info_label2 = QLabel("多选时请使用批量重命名功能")
            info_label2.setStyleSheet("color: #666666; font-size: 13px;")
            layout.addWidget(info_label2)
        
        # 添加弹性空间，让按钮不贴着底边
        layout.addStretch()
        
        # 按钮布局
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        # 确认按钮
        self.confirm_btn = QPushButton("确认")
        self.confirm_btn.setObjectName("confirmBtn")
        self.confirm_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self.confirm_btn)
        
        btn_layout.addSpacing(16)
        
        # 取消按钮
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setObjectName("cancelBtn")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        # 设置回车键确认
        if len(file_infos) == 1:
            self.name_edit.returnPressed.connect(self.accept)
            # 设置焦点到输入框
            self.name_edit.setFocus()
        else:
            # 多选时禁用确认按钮并修改文本
            self.confirm_btn.setEnabled(False)
            self.confirm_btn.setText("仅查看")
            # 设置焦点到取消按钮
            self.cancel_btn.setFocus()
    
    def get_new_name(self):
        if len(self.file_infos) == 1:
            return self.name_edit.text().strip()
        return None
    
    def get_file_infos(self):
        return self.file_infos

class MultiRenameDialog(QDialog):
    def __init__(self, file_infos, parent=None):
        super().__init__(parent)
        self.file_infos = file_infos
        self.setWindowTitle("重命名")
        self.resize(700, 500)  # 更大更宽
        self.setStyleSheet("""
            QDialog {
                background: #ffffff;
                border: 2px solid #e1e5e9;
                border-radius: 12px;
            }
            QLabel {
                font-size: 15px;
                color: #333333;
                padding: 8px 0px;
            }
            QLineEdit {
                border: 2px solid #e1e5e9;
                border-radius: 8px;
                padding: 12px 16px;
                font-size: 15px;
                background: #fafdff;
                min-height: 20px;
            }
            QLineEdit:focus {
                border-color: #165DFF;
                background: #ffffff;
            }
            QPushButton {
                font-weight: bold;
                border: none;
                border-radius: 8px;
                padding: 10px 24px;
                font-size: 15px;
                min-width: 100px;
                min-height: 36px;
            }
            QPushButton#confirmBtn {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #165DFF, stop:1 #0FC6C2);
                color: #ffffff;
            }
            QPushButton#confirmBtn:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0E4FE1, stop:1 #0FC6C2);
            }
            QPushButton#cancelBtn {
                background: #f5f5f5;
                color: #666666;
                border: 1px solid #d9d9d9;
            }
            QPushButton#cancelBtn:hover {
                background: #e6e6e6;
                color: #333333;
            }
            QScrollArea {
                border: none;
                background: transparent;
            }
            QWidget#scrollContent {
                background: transparent;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # 标题
        title_label = QLabel(f"重命名 {len(file_infos)} 个文件/文件夹")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #333333;")
        layout.addWidget(title_label)
        
        # 滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setMaximumHeight(350)  # 增加高度
        
        # 滚动内容
        scroll_content = QWidget()
        scroll_content.setObjectName("scrollContent")
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(12)  # 增加间距
        
        # 创建输入框
        self.line_edits = []
        for i, file_info in enumerate(file_infos):
            row_layout = QHBoxLayout()
            
            # 序号标签
            index_label = QLabel(f"{i+1}.")
            index_label.setFixedWidth(40)
            index_label.setStyleSheet("color: #666666; font-size: 14px; font-weight: bold;")
            row_layout.addWidget(index_label)
            
            # 输入框
            edit = QLineEdit(file_info['file_name'])
            edit.selectAll()  # 自动选中所有文本
            row_layout.addWidget(edit)
            self.line_edits.append((file_info['file_id'], edit, file_info['file_name']))
            
            scroll_layout.addLayout(row_layout)
        
        scroll_area.setWidget(scroll_content)
        layout.addWidget(scroll_area)
        
        # 按钮布局
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        # 确认按钮
        self.confirm_btn = QPushButton("确认")
        self.confirm_btn.setObjectName("confirmBtn")
        self.confirm_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self.confirm_btn)
        
        btn_layout.addSpacing(16)
        
        # 取消按钮
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setObjectName("cancelBtn")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        # 设置焦点到第一个输入框
        if self.line_edits:
            self.line_edits[0][1].setFocus()
    
    def get_rename_list(self):
        """获取重命名列表"""
        result = []
        for file_id, edit, old_name in self.line_edits:
            new_name = edit.text().strip()
            if new_name and new_name != old_name:
                result.append({
                    'file_id': file_id,
                    'old_name': old_name,
                    'new_name': new_name
                })
        return result 