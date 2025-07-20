# main_window.py
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QTextEdit,
    QPushButton, QCheckBox, QMessageBox, QSpinBox, QFormLayout, QSplitter, QListWidget, QListWidgetItem,
    QTableWidget, QTableWidgetItem, QHeaderView, QStackedWidget, QDialog, QSizePolicy, QProgressBar, QWidget, QHBoxLayout, QAbstractItemView
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from core.api import Pan123Api
from core.storage import TokenStorage
from core.user import UserManager
from gui.file_list import FileListPage
from gui.download_tasks import DownloadTaskWidget, DownloadTaskManager, OfflineTaskManager
from gui.folder_select_dialog import FolderSelectDialog
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon, QPixmap
import base64
import os
import sys
from PyQt5.QtWidgets import QGraphicsDropShadowEffect
from PyQt5.QtGui import QColor

class ProgressQueryThread(QThread):
    """异步查询离线任务进度的线程"""
    progress_updated = pyqtSignal(list)  # 发送更新后的任务列表
    error_occurred = pyqtSignal(str)     # 发送错误信息
    round_completed = pyqtSignal(int)    # 发送轮次完成信号
    
    def __init__(self, tasks, token, api):
        super().__init__()
        self.tasks = tasks
        self.token = token
        self.api = api
        self.is_running = True
        self.current_round = 1  # 当前轮次
        self.max_tasks_per_batch = 3  # 每批最多查询3个任务
        self.first_round_interval = 500  # 第一轮间隔0.5秒
        self.subsequent_round_interval = 1000  # 后续轮次间隔1秒
    
    def run(self):
        try:
            # 第一轮：查询所有任务
            self.query_round(self.tasks, is_first_round=True)
            self.round_completed.emit(self.current_round)
            
            # 后续轮次：只查询进行中的任务
            while self.is_running:
                self.current_round += 1
                self.msleep(self.subsequent_round_interval)
                
                if not self.is_running:
                    break
                
                # 筛选进行中的任务
                active_tasks = [task for task in self.tasks if task.status == "进行中"]
                
                if not active_tasks:
                    # 没有进行中的任务，查询所有任务（可能有新任务或状态变化）
                    active_tasks = [task for task in self.tasks if task.status not in ["成功", "失败"]]
                
                if not active_tasks:
                    # 所有任务都完成了，停止查询
                    break
                
                self.query_round(active_tasks, is_first_round=False)
                self.round_completed.emit(self.current_round)
                
        except Exception as e:
            self.error_occurred.emit(str(e))
    
    def query_round(self, tasks_to_query, is_first_round=False):
        """查询一轮任务进度"""
        interval = self.first_round_interval if is_first_round else 100  # 第一轮间隔0.5秒，后续轮次间隔0.1秒
        
        for i in range(0, len(tasks_to_query), self.max_tasks_per_batch):
            if not self.is_running:
                break
            
            # 获取当前批次的任务
            batch_tasks = tasks_to_query[i:i + self.max_tasks_per_batch]
            
            # 查询当前批次
            for task in batch_tasks:
                if not self.is_running:
                    break
                
                if self.token and task.task_id:
                    try:
                        resp = self.api.check_download_progress(self.token, task.task_id)
                        if resp.get('code') == 0 and 'data' in resp:
                            progress = int(resp['data'].get('process', 0))
                            st = resp['data'].get('status', 0)
                            status = {0: "进行中", 1: "失败", 2: "成功", 3: "重试中"}.get(st, str(st))
                            
                            # 更新任务状态
                            task.progress = progress
                            task.status = status
                    except Exception as e:
                        task.status = "查询失败"
            
            # 发送当前批次更新
            self.progress_updated.emit(self.tasks.copy())
            
            # 批次间延迟
            if i + self.max_tasks_per_batch < len(tasks_to_query):
                self.msleep(interval)
    
    def stop(self):
        self.is_running = False

class UserDialog(QDialog):
    def __init__(self, parent=None, user=None):
        super().__init__(parent)
        self.setWindowTitle("用户信息")
        self.setModal(True)
        self.resize(540, 320)  # 弹窗更大
        layout = QFormLayout(self)
        self.name_input = QLineEdit()
        self.client_id_input = QLineEdit()
        self.client_id_input.setEchoMode(QLineEdit.Normal)
        self.client_secret_input = QLineEdit()
        self.client_secret_input.setEchoMode(QLineEdit.Normal)
        self.token_input = QLineEdit()
        self.token_input.setEchoMode(QLineEdit.Password)
        self.token_input.setReadOnly(True)
        self.expired_label = QLabel("")
        # Token输入框和获取Token按钮同一行
        token_hbox = QHBoxLayout()
        token_hbox.addWidget(self.token_input)
        self.get_token_btn = QPushButton("获取Token")
        self.get_token_btn.setMinimumWidth(110)
        self.get_token_btn.setStyleSheet("QPushButton{font-weight:bold;background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #165DFF,stop:1 #0FC6C2);color:#fff;border:none;border-radius:8px;font-size:16px;} QPushButton:hover{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #0E4FE1,stop:1 #0FC6C2);}")
        token_hbox.addWidget(self.get_token_btn)
        token_hbox.setSpacing(8)
        token_hbox.setContentsMargins(0, 0, 0, 0)
        layout.addRow(QLabel("用户名:"), self.name_input)
        layout.addRow(QLabel("Client ID:"), self.client_id_input)
        layout.addRow(QLabel("Client Secret:"), self.client_secret_input)
        layout.addRow(QLabel("Token:"), token_hbox)
        layout.addRow(QLabel("有效期:"), self.expired_label)
        # 底部确认按钮
        self.confirm_btn = QPushButton("确认")
        self.confirm_btn.setMinimumHeight(38)
        self.confirm_btn.setStyleSheet("QPushButton{font-weight:bold;background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #13C2C2,stop:1 #165DFF);color:#fff;border:none;border-radius:8px;font-size:17px;} QPushButton:hover{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #08979C,stop:1 #0E4FE1);}")
        layout.addRow(self.confirm_btn)
        self.setLayout(layout)
        if user:
            self.name_input.setText(user.get('name', ''))
            self.client_id_input.setText(user.get('client_id', ''))
            self.client_secret_input.setText(user.get('client_secret', ''))
            self.token_input.setText(user.get('access_token', ''))
            self.expired_label.setText(user.get('expired_at', ''))
        self.get_token_btn.clicked.connect(self.get_token)
        self.confirm_btn.clicked.connect(self.accept)
        self.api = Pan123Api()
    def get_token(self):
        client_id = self.client_id_input.text().strip()
        client_secret = self.client_secret_input.text().strip()
        if not client_id or not client_secret:
            QMessageBox.warning(self, "提示", "请输入Client ID和Client Secret")
            return
        try:
            token, expired_at = self.api.get_token_by_credentials(client_id, client_secret)
            self.token_input.setText(token)
            self.expired_label.setText(str(expired_at))
        except Exception as e:
            QMessageBox.critical(self, "错误", f"获取Token失败: {e}")
    def get_user_data(self):
        return {
            'name': self.name_input.text().strip(),
            'client_id': self.client_id_input.text().strip(),
            'client_secret': self.client_secret_input.text().strip(),
            'access_token': self.token_input.text().strip(),
            'expired_at': self.expired_label.text().strip()
        }

class MainWindow(QMainWindow):
    def delete_user_from_table(self):
        row = self.user_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "提示", "请先选择要删除的用户")
            return
        name = self.user_table.item(row, 0).text()
        reply = QMessageBox.question(self, "确认删除", f"确定要删除用户 {name} 吗？", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.user_manager.delete_user(name)
            self.user_manager.save()  # 确保本地文件同步
            self.refresh_user_table()
            QMessageBox.information(self, "成功", f"用户 {name} 已删除")
    def edit_user_from_table(self):
        row = self.user_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "提示", "请先选择要编辑的用户")
            return
        name = self.user_table.item(row, 0).text()
        self.load_user(name)
        self.tabs.setCurrentIndex(1)
    def goto_token_tab(self):
        self.tabs.setCurrentIndex(1)
    def refresh_user_table(self):
        try:
            self.user_table.itemSelectionChanged.disconnect(self.check_token_expired_highlight)
        except Exception:
            pass
        users = self.user_manager.get_all_users()
        self.user_table.setRowCount(len(users))
        for row, (name, info) in enumerate(users.items()):
            self.user_table.setItem(row, 0, QTableWidgetItem(name))
            # Client列脱敏
            client_id = info.get('client_id', '')
            client_secret = info.get('client_secret', '')
            client_html = f"""
                <div style='line-height:1.6;'>
                    <span style='color:#165DFF;font-weight:bold;'>ID:</span> {'*' * len(client_id) if client_id else ''}<br>
                    <span style='color:#13C2C2;font-weight:bold;'>Secret:</span> {'*' * len(client_secret) if client_secret else ''}
                </div>
            """
            client_label = QLabel()
            client_label.setTextFormat(Qt.RichText)
            client_label.setText(client_html)
            client_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            client_label.setStyleSheet("font-size:15px;padding:2px 0;")
            self.user_table.setCellWidget(row, 1, client_label)
            # Token列脱敏，时间正常显示
            token_val = info.get('access_token', '')
            expired_at = info.get('expired_at', '')
            token_str = f"{'*' * len(token_val) if token_val else ''}\n{expired_at}"
            token_item = QTableWidgetItem(token_str)
            self.user_table.setItem(row, 2, token_item)
            # 操作栏按钮组优化，垂直居中
            op_widget = QWidget()
            op_layout = QHBoxLayout()
            op_layout.setContentsMargins(0, 10, 0, 10)  # 上下各留10像素
            outer_layout = QVBoxLayout()
            outer_layout.setContentsMargins(0, 10, 0, 10)  # 上下各留10像素
            outer_layout.addStretch()
            outer_layout.addLayout(op_layout)
            outer_layout.addStretch()
            op_widget.setLayout(outer_layout)
            op_widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
            op_widget.setMinimumHeight(60)
            self.user_table.setCellWidget(row, 3, op_widget)
            self.user_table.setRowHeight(row, 90)
            btn_edit = QPushButton("编辑")
            btn_edit.setFixedSize(56, 36)
            btn_edit.setStyleSheet("QPushButton{font-weight:bold;background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #165DFF,stop:1 #0FC6C2);color:#fff;border:none;border-radius:8px;font-size:16px;} QPushButton:hover{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #0E4FE1,stop:1 #0FC6C2);}")
            btn_del = QPushButton("删除")
            btn_del.setFixedSize(56, 36)
            btn_del.setStyleSheet("QPushButton{font-weight:bold;background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #FF4D4F,stop:1 #FF7A45);color:#fff;border:none;border-radius:8px;font-size:16px;} QPushButton:hover{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #D9363E,stop:1 #FF7A45);}")
            btn_update = QPushButton("更新")
            btn_update.setFixedSize(56, 36)
            btn_update.setStyleSheet("QPushButton{font-weight:bold;background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #13C2C2,stop:1 #165DFF);color:#fff;border:none;border-radius:8px;font-size:16px;} QPushButton:hover{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #08979C,stop:1 #0E4FE1);}")
            op_layout.addWidget(btn_edit)
            op_layout.addWidget(btn_del)
            op_layout.addWidget(btn_update)
            btn_edit.clicked.connect(lambda _, n=name: self.edit_user_dialog(n))
            btn_del.clicked.connect(lambda _, n=name: self.delete_user(n))
            btn_update.clicked.connect(lambda _, n=name: self.update_token(n))
        self.user_table.setColumnWidth(0, 120)
        self.user_table.setColumnWidth(3, 280)
        self.user_table.itemSelectionChanged.connect(self.check_token_expired_highlight)
    def check_token_expired_highlight(self):
        selected = self.user_table.selectedItems()
        if not selected:
            return
        row = self.user_table.currentRow()
        name = self.user_table.item(row, 0).text()
        if self.user_manager.is_token_expired(name):
            # token单元格变红
            token_item = self.user_table.item(row, 2)
            token_item.setBackground(Qt.red)
            ret = QMessageBox.question(self, "Token已过期", "Token已过期，是否立即更新？", QMessageBox.Yes | QMessageBox.No)
            if ret == QMessageBox.Yes:
                user = self.user_manager.get_user(name)
                if not user:
                    QMessageBox.warning(self, "提示", "用户不存在，无法刷新Token")
                    self.user_table.clearSelection()
                    return
                try:
                    token, expired_at = self.api.get_token_by_credentials(user['client_id'], user['client_secret'])
                    self.user_manager.update_token(name, token, expired_at)
                    QMessageBox.information(self, "成功", "Token已自动刷新")
                    self.refresh_user_table()
                except Exception as e:
                    QMessageBox.critical(self, "错误", f"Token刷新失败: {e}")
            else:
                self.user_table.clearSelection()
    def __init__(self):
        super().__init__()
        self.setWindowTitle("123网盘离线下载工具1.0.3-beta")
        self.resize(1400, 900)
        # 设置窗口图标，兼容打包和源码
        try:
            if getattr(sys, 'frozen', False):
                icon_path = os.path.join(sys._MEIPASS, 'icon_date.ico')
            else:
                icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'icon_date.ico')
            if os.path.exists(icon_path):
                icon = QIcon(icon_path)
                self.setWindowIcon(icon)
        except Exception as e:
            pass  # 图标设置失败时忽略
        self.setStyleSheet("""
            QMainWindow {
                background: #f6f8fa;
            }
            QTabWidget::pane {
                border: 1px solid #d0d7de;
                border-radius: 8px;
                background: #fff;
            }
            QTabBar::tab {
                background: #eaeef2;
                border: 1px solid #d0d7de;
                border-bottom: none;
                min-width: 120px;
                min-height: 32px;
                font-size: 18px;
                font-weight: bold;
                padding: 8px 20px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background: #fff;
                color: #165DFF;
                font-weight: bold;
            }
            QListWidget {
                background: #f0f4f8;
                border: none;
                font-size: 18px;
                font-weight: bold;
                padding: 10px 0;
            }
            QListWidget::item {
                padding: 16px 10px;
                border-radius: 6px;
                margin-bottom: 4px;
            }
            QListWidget::item:selected {
                background: #165DFF;
                color: #fff;
                outline: none;
                border: none;
            }
            QLabel {
                font-size: 18px;
                font-weight: bold;
            }
            QLineEdit, QTextEdit, QSpinBox {
                border: 1px solid #d0d7de;
                border-radius: 6px;
                padding: 8px 10px;
                font-size: 18px;
                font-weight: bold;
                background: #fafdff;
            }
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #165DFF, stop:1 #0FC6C2);
                color: #fff;
                border: none;
                border-radius: 8px;
                padding: 12px 28px;
                font-size: 19px;
                font-weight: bold;
                margin-top: 12px;
                margin-bottom: 12px;
                min-width: 130px;
                min-height: 40px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0E4FE1, stop:1 #0FC6C2);
            }
            QCheckBox {
                font-size: 18px;
                font-weight: bold;
                margin-top: 8px;
                margin-bottom: 8px;
            }
            QFormLayout > * {
                margin-bottom: 12px;
            }
            QTextEdit {
                min-height: 120px;
            }
        """)
        self.api = Pan123Api()
        self.token_storage = TokenStorage()
        self.user_manager = UserManager()
        self.current_user = None
        self.download_task_manager = DownloadTaskManager()
        self.offline_task_manager = OfflineTaskManager()
        self.progress_query_thread = None  # 进度查询线程
        self.init_ui()

    def init_ui(self):
        self.splitter = QSplitter(Qt.Horizontal)
        # 左侧导航
        self.nav_list = QListWidget()
        self.nav_list.setFixedWidth(150)
        self.nav_list.addItem(QListWidgetItem("用户管理"))
        self.nav_list.addItem(QListWidgetItem("离线下载"))
        self.nav_list.addItem(QListWidgetItem("离线进度"))
        self.nav_list.addItem(QListWidgetItem("文件管理"))
        self.nav_list.addItem(QListWidgetItem("下载任务"))
        self.nav_list.addItem(QListWidgetItem("上传任务"))
        self.splitter.addWidget(self.nav_list)

        # 右侧内容区（QStackedWidget）
        self.stack = QStackedWidget()
        self.splitter.addWidget(self.stack)

        # 用户管理页
        user_tab = QWidget()
        user_layout = QVBoxLayout()
        user_layout.setContentsMargins(8, 8, 8, 8)  # 缩小边距
        user_layout.setSpacing(6)
        self.user_table = QTableWidget()
        self.user_table.setColumnCount(4)
        self.user_table.setHorizontalHeaderLabels(["用户名", "Client", "Token", "操作"])
        self.user_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)  # 填满父容器
        self.user_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.user_table.horizontalHeader().setStretchLastSection(True)
        self.set_table_column_widths()
        self.user_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.user_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.user_table.setSelectionMode(QTableWidget.SingleSelection)
        self.refresh_user_table()
        user_layout.addWidget(self.user_table)
        # 先创建按钮
        self.add_user_btn = QPushButton("添加用户")
        self.add_user_btn.setMinimumWidth(140)
        self.add_user_btn.setMinimumHeight(44)
        self.add_user_btn.setStyleSheet("QPushButton{font-weight:bold;background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #165DFF,stop:1 #0FC6C2);color:#fff;border:none;border-radius:10px;font-size:18px;} QPushButton:hover{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #0E4FE1,stop:1 #0FC6C2);}")
        self.add_user_btn.clicked.connect(self.add_user_dialog)
        self.confirm_btn = QPushButton("确认使用")
        self.confirm_btn.setMinimumWidth(140)
        self.confirm_btn.setMinimumHeight(44)
        self.confirm_btn.setStyleSheet("QPushButton{font-weight:bold;background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #13C2C2,stop:1 #165DFF);color:#fff;border:none;border-radius:10px;font-size:18px;} QPushButton:hover{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #08979C,stop:1 #0E4FE1);}")
        self.confirm_btn.clicked.connect(self.confirm_use)
        # 底部按钮居中+导入导出
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.import_user_btn = QPushButton("导入用户")
        self.import_user_btn.setMinimumWidth(120)
        self.import_user_btn.setMinimumHeight(44)
        self.import_user_btn.setStyleSheet("QPushButton{font-weight:bold;background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #6DD5FA,stop:1 #2980B9);color:#fff;border:none;border-radius:10px;font-size:18px;} QPushButton:hover{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #2980B9,stop:1 #6DD5FA);}")
        self.import_user_btn.clicked.connect(self.import_users)
        btn_layout.addWidget(self.import_user_btn)
        btn_layout.addSpacing(18)
        self.export_user_btn = QPushButton("导出用户")
        self.export_user_btn.setMinimumWidth(120)
        self.export_user_btn.setMinimumHeight(44)
        self.export_user_btn.setStyleSheet("QPushButton{font-weight:bold;background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #F7971E,stop:1 #FFD200);color:#fff;border:none;border-radius:10px;font-size:18px;} QPushButton:hover{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #FFD200,stop:1 #F7971E);}")
        self.export_user_btn.clicked.connect(self.export_users)
        btn_layout.addWidget(self.export_user_btn)
        btn_layout.addSpacing(30)
        btn_layout.addWidget(self.add_user_btn)
        btn_layout.addSpacing(30)
        btn_layout.addWidget(self.confirm_btn)
        btn_layout.addStretch()
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(12)
        btn_widget = QWidget()
        btn_widget.setLayout(btn_layout)
        btn_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        user_layout.addWidget(btn_widget)
        user_tab.setLayout(user_layout)
        self.stack.addWidget(user_tab)

        # 离线下载页
        download_tab = QWidget()
        download_layout = QFormLayout()
        self.urls_edit = QTextEdit()
        self.urls_edit.setPlaceholderText("每行一个下载URL")
        self.clear_urls_btn = QPushButton("清空")
        self.clear_urls_btn.setStyleSheet('QPushButton{min-width:60px;max-width:90px;min-height:26px;max-height:32px;font-size:14px;}')
        self.clear_urls_btn.clicked.connect(lambda: self.urls_edit.clear())
        # 新增粘贴按钮
        self.paste_urls_btn = QPushButton("粘贴")
        self.paste_urls_btn.setStyleSheet('QPushButton{min-width:60px;max-width:90px;min-height:26px;max-height:32px;font-size:14px;}')
        self.paste_urls_btn.clicked.connect(self.on_paste_urls)
        urls_hbox = QHBoxLayout()
        urls_hbox.addWidget(self.urls_edit)
        urls_hbox.addWidget(self.clear_urls_btn)
        urls_hbox.addWidget(self.paste_urls_btn)
        self.offline_dir_input = QLineEdit()
        offline_hbox = QHBoxLayout()
        offline_hbox.addWidget(self.offline_dir_input)
        self.get_folder_id_btn = QPushButton("获取文件夹ID")
        self.get_folder_id_btn.setStyleSheet('QPushButton{min-width:90px;max-width:120px;min-height:28px;max-height:36px;font-size:15px;}')
        self.get_folder_id_btn.clicked.connect(self.on_get_folder_id)
        offline_hbox.addWidget(self.get_folder_id_btn)
        download_layout.addRow(QLabel("离线文件夹ID(可选):"), offline_hbox)
        download_layout.addRow(QLabel("文件URL列表:"), urls_hbox)
        # 移除刷新间隔和请求间隔
        self.submit_btn = QPushButton("开始离线下载")
        self.submit_btn.clicked.connect(self.submit_download)
        download_layout.addRow(self.submit_btn)
        download_tab.setLayout(download_layout)
        self.stack.addWidget(download_tab)

        # 任务结果页（改为离线进度页）
        self.progress_tab = QWidget()
        progress_layout = QVBoxLayout()
        
        # 顶部按钮和状态栏
        top_layout = QHBoxLayout()
        # 新增清空按钮
        clear_progress_btn = QPushButton("清空")
        clear_progress_btn.setStyleSheet('QPushButton{min-width:60px;max-width:90px;min-height:26px;max-height:32px;font-size:14px;background:#FF7875;color:#fff;border-radius:8px;} QPushButton:hover{background:#FF4D4F;}')
        clear_progress_btn.clicked.connect(self.on_clear_progress_tasks)
        top_layout.addWidget(clear_progress_btn)
        
        top_layout.addStretch()
        
        progress_layout.addLayout(top_layout)
        self.progress_table = QTableWidget()
        self.progress_table.setColumnCount(4)
        self.progress_table.setHorizontalHeaderLabels(["任务ID", "文件名", "进度", "状态"])
        self.progress_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.progress_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.progress_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.progress_table.setSelectionMode(QTableWidget.SingleSelection)
        self.progress_table.setStyleSheet("""
QTableWidget {
    border-radius: 12px;
    border: 1.5px solid #d0d7de;
    background: #fafdff;
    font-size: 18px;
    gridline-color: #e0e0e0;
}
QTableWidget::item {
    border-radius: 8px;
    padding: 8px 12px;
    margin: 2px;
}
QTableWidget::item:selected {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #e6f7ff, stop:1 #cce7ff);
    color: #165DFF;
    border: 1.5px solid #165DFF;
}
QTableWidget::item:hover {
    background: #f0faff;
}
QHeaderView::section {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #A3C8F7, stop:1 #e6f7ff);
    color: #222;
    font-weight: bold;
    font-size: 20px;
    border: none;
    height: 44px;
    border-radius: 10px;
}
""")
        self.progress_table.verticalHeader().setDefaultSectionSize(54)
        progress_layout.addWidget(self.progress_table)
        self.progress_tab.setLayout(progress_layout)
        self.stack.addWidget(self.progress_tab)

        # 文件管理页
        def get_token():
            if self.current_user:
                user = self.user_manager.get_user(self.current_user)
                if user:
                    return user.get('access_token', '')
            return ''
        self.file_list_page = FileListPage(get_token, self)
        self.stack.addWidget(self.file_list_page)
        # 下载任务页
        self.download_task_widget = DownloadTaskWidget(self.download_task_manager, self)
        self.stack.addWidget(self.download_task_widget)
        # 上传任务页
        from gui.upload_manager import UploadManager
        class UploadTaskWidget(QWidget):
            def __init__(self, manager, parent=None):
                super().__init__(parent)
                self.manager = manager
                self.init_ui()
            def init_ui(self):
                layout = QVBoxLayout(self)
                self.table = QTableWidget()
                self.table.setColumnCount(5)
                self.table.setHorizontalHeaderLabels(["文件名", "目录ID", "进度", "状态", "错误信息"])
                self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
                self.table.verticalHeader().setDefaultSectionSize(36)
                # 美化表头
                self.table.setStyleSheet('''
QTableWidget::item { font-size:15px; }
QHeaderView::section {
    background: qlineargradient(x1:0, y1:0,x2:1,y2:0,stop:0 #A3C8F7,stop:1 #e6f7ff);
    color: #222;
    font-weight: bold;
    font-size: 17px;
    border: none;
    height: 38px;
    border-radius: 8px;
}
''')
                # 上传任务美化外壳
                wrapper = QWidget()
                wrapper_layout = QVBoxLayout(wrapper)
                wrapper_layout.setContentsMargins(0, 0, 0, 0)
                wrapper_layout.setSpacing(0)
                wrapper.setStyleSheet('''
QWidget {
    background: #fafdff;
    border-radius: 18px;
    border: 1.5px solid #e6f0fa;
}
''')
                # 添加阴影效果
                shadow = QGraphicsDropShadowEffect()
                shadow.setBlurRadius(24)
                shadow.setOffset(0, 4)
                shadow.setColor(QColor(22, 93, 255, 40))  # 半透明蓝色
                wrapper.setGraphicsEffect(shadow)
                # 删除任务按钮
                self.delete_btn = QPushButton("删除任务")
                self.delete_btn.setFixedSize(44, 16)
                self.delete_btn.setStyleSheet('QPushButton{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #FF4D4F,stop:1 #FF7A45);color:#fff;border:none;border-radius:8px;font-size:15px;} QPushButton:hover{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #D9363E,stop:1 #FF7A45);} ')
                self.delete_btn.clicked.connect(self.delete_selected_task)
                # 新增清空按钮
                self.clear_btn = QPushButton("清空任务")
                self.clear_btn.setFixedSize(44, 16)
                self.clear_btn.setStyleSheet('QPushButton{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #FF7875,stop:1 #FF4D4F);color:#fff;border:none;border-radius:8px;font-size:13px;} QPushButton:hover{background:#FF4D4F;}')
                self.clear_btn.clicked.connect(self.clear_all_tasks)
                btn_layout = QHBoxLayout()
                btn_layout.addWidget(self.delete_btn)
                btn_layout.addSpacing(16)
                btn_layout.addWidget(self.clear_btn)
                btn_layout.addStretch()
                btn_layout.setContentsMargins(8, 12, 8, 18)  # 上下左右留白，按钮不贴表格
                wrapper_layout.addLayout(btn_layout)
                wrapper_layout.addSpacing(6)
                wrapper_layout.addWidget(self.table)
                layout.addWidget(wrapper)
                self.setLayout(layout)
                self.refresh_table()
            def clear_all_tasks(self):
                from PyQt5.QtWidgets import QMessageBox
                reply = QMessageBox.question(self, "确认清空", "确定要清空所有上传任务吗？", QMessageBox.Yes | QMessageBox.No)
                if reply == QMessageBox.Yes:
                    self.manager.tasks.clear()
                    self.refresh_table()
            def refresh_table(self):
                tasks = self.manager.tasks
                self.table.setRowCount(len(tasks))
                self.table.setStyleSheet('''
QTableWidget {
    border-radius: 14px;
    background: #fafdff;
    border: none;
    font-size: 15px;
    selection-background-color: #e6f7ff;
    selection-color: #222;
}
QTableWidget::item:selected {
    background: #e6f7ff;
    color: #165DFF;
}
QTableWidget::item:hover {
    background: #f0f4fa;
}
QHeaderView::section {
    background: qlineargradient(x1:0, y1:0,x2:1,y2:0,stop:0 #A3C8F7,stop:1 #e6f7ff);
    color: #222;
    font-weight: bold;
    font-size: 17px;
    border: none;
    height: 38px;
    border-radius: 8px;
}
''')
                for row, t in enumerate(tasks):
                    self.table.setItem(row, 0, QTableWidgetItem(os.path.basename(t.file_path)))
                    self.table.setItem(row, 1, QTableWidgetItem(str(t.parent_id)))
                    # 进度条美化
                    bar = QProgressBar()
                    bar.setValue(int(t.progress))
                    bar.setFormat(f"{t.progress:.1f}%")
                    bar.setAlignment(Qt.AlignCenter)
                    bar.setFixedHeight(32)
                    bar.setStyleSheet('''
QProgressBar {
    border: 2px solid #e0e6ed;
    border-radius: 16px;
    background: #fff;
    height: 32px;
    font-weight: bold;
    font-size: 18px;
    color: #222;
    text-align: center;
}
QProgressBar::chunk {
    border-radius: 16px;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #13C2C2, stop:1 #165DFF);
    margin: 2px;
    min-width: 24px;
}
''')
                    self.table.setCellWidget(row, 2, bar)
                    status_item = QTableWidgetItem(t.status)
                    if t.status == '已完成':
                        status_item.setForeground(Qt.green)
                    elif t.status == '失败':
                        status_item.setForeground(Qt.red)
                    else:
                        status_item.setForeground(Qt.darkBlue)
                    self.table.setItem(row, 3, status_item)
                    error_item = QTableWidgetItem(t.error or "")
                    if t.error:
                        error_item.setForeground(Qt.red)
                    self.table.setItem(row, 4, error_item)
                # 自动上传所有待上传任务
                self.auto_start_uploads()
            def update_progress(self, task):
                QTimer.singleShot(0, self.refresh_table)
            def update_status(self, task):
                QTimer.singleShot(0, self.refresh_table)
            def auto_start_uploads(self):
                # 只在有待上传任务时校验token
                has_pending = any(task.status == '待上传' for task in self.manager.tasks)
                if not has_pending:
                    return
                main_win = self.parent()
                while main_win and not hasattr(main_win, 'get_token_func'):
                    main_win = main_win.parent()
                token = main_win.get_token_func() if main_win else ""
                if not token:
                    from PyQt5.QtWidgets import QMessageBox
                    QMessageBox.warning(self, "提示", "请先登录/选择用户并获取有效Token！")
                    return
                for task in self.manager.tasks:
                    if task.status == '待上传':
                        self.manager.start_upload(task, token, self.update_progress, self.update_status)
            def delete_task(self, row):
                if 0 <= row < len(self.manager.tasks):
                    task = self.manager.tasks[row]
                    # 若正在上传可加终止逻辑
                    self.manager.tasks.pop(row)
                    self.refresh_table()
            def delete_selected_task(self):
                selected_rows = sorted(set([i.row() for i in self.table.selectedIndexes()]), reverse=True)
                for row in selected_rows:
                    if 0 <= row < len(self.manager.tasks):
                        self.manager.tasks.pop(row)
                self.refresh_table()
        self.upload_manager = UploadManager()
        self.upload_task_widget = UploadTaskWidget(self.upload_manager, self)
        self.stack.addWidget(self.upload_task_widget)

        # 侧边栏导航与内容联动
        self.nav_list.currentRowChanged.connect(self.on_nav_changed)
        self.nav_list.setCurrentRow(0)

        # 主窗口布局
        main_widget = QWidget()
        main_layout = QVBoxLayout()
        main_layout.addWidget(self.splitter)
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

        # 表格美化：减小圆角，增加间隔，显示网格线
        self.user_table.setStyleSheet("""
            QTableWidget {
                border-radius: 6px;
                border: 1.2px solid #d0d7de;
                background: #fff;
                font-size: 16px;
                gridline-color: #e0e0e0;
            }
            QTableWidget::item {
                border-radius: 4px;
                padding: 4px 6px;
                margin: 2px;
            }
            QTableWidget::item:selected {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #e6f7ff, stop:1 #cce7ff);
                color: #165DFF;
                border: 1.2px solid #165DFF;
            }
            QTableWidget::item:hover {
                background: #f0faff;
            }
            QHeaderView::section {
                background: #A3C8F7;
                color: #222;
                font-weight: bold;
                font-size: 17px;
                border: none;
                height: 40px;
                border-radius: 6px;
            }
        """)
        self.user_table.setShowGrid(True)
        # 阴影效果
        shadow = QGraphicsDropShadowEffect(self.user_table)
        shadow.setBlurRadius(18)
        shadow.setOffset(0, 4)
        shadow.setColor(Qt.gray)
        self.user_table.setGraphicsEffect(shadow)
        # 表格选中行可取消
        self.user_table.viewport().installEventFilter(self)
        self.user_table.setSelectionMode(QTableWidget.SingleSelection)

    def set_table_column_widths(self):
        # 前三列固定宽度，操作列自适应填满右侧
        header = self.user_table.horizontalHeader()
        self.user_table.setColumnWidth(0, 120)
        self.user_table.setColumnWidth(1, 220)
        self.user_table.setColumnWidth(2, 260)
        # 第3列（操作）不设置宽度，由setStretchLastSection控制

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.set_table_column_widths()

    def create_dir(self):
        token = self.token_input.text().strip()
        if not token:
            QMessageBox.warning(self, "提示", "请先获取Token")
            return
        archive_dir_id = self.archive_dir_input.text().strip()
        save_dir_name = self.save_dir_name_input.text().strip()
        if not archive_dir_id or not save_dir_name:
            QMessageBox.warning(self, "提示", "请填写归档文件夹ID和文件夹名称")
            return
        try:
            dir_id = self.api.create_directory(token, save_dir_name, archive_dir_id)
            self.save_dir_id_input.setText(dir_id)
            QMessageBox.information(self, "成功", f"文件夹 '{save_dir_name}' 创建成功")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"创建文件夹失败: {e}")

    def on_nav_changed(self, idx):
        self.stack.setCurrentIndex(idx)
        if idx == 2:
            # 切换到进度页面时，停止定时器，开始异步查询
            self.stop_progress_timer()
            self.refresh_progress_table()
        else:
            # 离开进度页面时，停止查询线程和定时器
            self.stop_progress_timer()
            if self.progress_query_thread and self.progress_query_thread.isRunning():
                self.progress_query_thread.stop()
                self.progress_query_thread.wait()
                self.progress_query_thread = None
        if idx == 3 and hasattr(self, 'file_list_page'):
            self.file_list_page.load_file_list()
        if idx == 4 and hasattr(self, 'download_task_widget'):
            self.download_task_widget.path_label.setText(f"下载路径: {self.download_task_manager.get_download_path() or '未设置'}")
        # 上传任务页（idx==5）
        if idx == 5 and hasattr(self, 'upload_task_widget'):
            self.upload_task_widget.refresh_table()

    def stop_progress_timer(self):
        if hasattr(self, '_progress_timer') and self._progress_timer:
            self._progress_timer.stop()
            self._progress_timer.deleteLater()
            self._progress_timer = None

    def refresh_progress_table(self):
        """异步刷新离线进度表格"""
        tasks = self.offline_task_manager.get_tasks()
        if not tasks:
            self.progress_table.setRowCount(0)
            return
        
        # 先显示任务列表，不查询进度
        self.progress_table.setRowCount(len(tasks))
        for row, task in enumerate(tasks):
            self.progress_table.setItem(row, 0, QTableWidgetItem(str(task.task_id)))
            self.progress_table.setItem(row, 1, QTableWidgetItem(task.file_name or '-'))
            from PyQt5.QtWidgets import QProgressBar
            bar = QProgressBar()
            bar.setValue(int(task.progress))
            bar.setFormat(f"{task.progress:.1f}%")
            bar.setAlignment(Qt.AlignCenter)
            bar.setStyleSheet("""
QProgressBar {
    border: 1.5px solid #d0d7de;
    border-radius: 14px;
    text-align: center;
    height: 28px;
    background: #fafdff;
    font-size: 18px;
    font-weight: bold;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #13C2C2, stop:1 #165DFF);
    border-radius: 14px;
}
""")
            self.progress_table.setCellWidget(row, 2, bar)
            # 状态列美化
            status_item = QTableWidgetItem(task.status)
            status_item.setTextAlignment(Qt.AlignCenter)
            if task.status == "成功":
                status_item.setForeground(Qt.green)
            elif task.status == "失败":
                status_item.setForeground(Qt.red)
            elif task.status == "进行中":
                status_item.setForeground(Qt.blue)
            else:
                status_item.setForeground(Qt.darkGray)
            font = status_item.font()
            font.setBold(True)
            status_item.setFont(font)
            self.progress_table.setItem(row, 3, status_item)
        
        # 获取token
        token = ""
        if self.current_user:
            user = self.user_manager.get_user(self.current_user)
            if user:
                token = user.get('access_token', '')
        
        if not token:
            return
            
        # 停止之前的查询线程
        if self.progress_query_thread and self.progress_query_thread.isRunning():
            self.progress_query_thread.stop()
            self.progress_query_thread.wait()
        
        # 创建新的查询线程，传递任务的副本
        tasks_copy = tasks.copy()
        self.progress_query_thread = ProgressQueryThread(tasks_copy, token, self.api)
        self.progress_query_thread.progress_updated.connect(self.on_progress_updated)
        self.progress_query_thread.error_occurred.connect(self.on_progress_error)
        self.progress_query_thread.round_completed.connect(self.on_round_completed) # 连接轮次完成信号
        self.progress_query_thread.start()
        
        # 不显示查询状态，保持界面简洁
        pass
    
    def on_progress_updated(self, updated_tasks):
        """进度查询线程返回更新结果"""
        try:
            # 更新原始任务列表
            original_tasks = self.offline_task_manager.get_tasks()
            for i, updated_task in enumerate(updated_tasks):
                if i < len(original_tasks):
                    # 更新原始任务对象
                    original_tasks[i].progress = updated_task.progress
                    original_tasks[i].status = updated_task.status
                                        
                    # 更新界面显示
                    if i < self.progress_table.rowCount():
                        # 更新进度条
                        bar = self.progress_table.cellWidget(i, 2)
                        if bar:
                            bar.setValue(int(updated_task.progress))
                            bar.setFormat(f"{updated_task.progress:.1f}%")
                        # 更新状态
                        self.progress_table.setItem(i, 3, QTableWidgetItem(updated_task.status))
            
            # 保存最新状态
            self.offline_task_manager.save_tasks()
        except Exception as e:
            pass  # 忽略更新错误，避免程序崩溃
    
    def on_progress_error(self, error_msg):
        """进度查询出错"""
        if hasattr(self, 'progress_status_label'):
            self.progress_status_label.setText(f"查询出错: {error_msg}")

    def on_round_completed(self, round_number):
        """进度查询线程完成一轮查询后触发"""
        # 不显示轮次信息，保持界面简洁
        pass

    def submit_download(self):
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QProgressBar, QTextEdit, QPushButton, QLabel
        token = ""
        if self.current_user:
            user = self.user_manager.get_user(self.current_user)
            if user:
                token = user.get('access_token', '')
        urls = [u.strip() for u in self.urls_edit.toPlainText().splitlines() if u.strip()]
        dir_id = self.offline_dir_input.text().strip()
        if not urls:
            QMessageBox.warning(self, "提示", "请输入要下载的文件URL")
            return
        if not token:
            QMessageBox.warning(self, "提示", "请先获取Token")
            return
        from core.api import Pan123Api
        api = Pan123Api()
        # 进度对话框
        class PushProgressDialog(QDialog):
            def __init__(self, total, parent=None):
                super().__init__(parent)
                self.setWindowTitle("离线任务推送进度")
                self.resize(480, 320)
                layout = QVBoxLayout(self)
                self.label = QLabel("正在推送离线任务...")
                layout.addWidget(self.label)
                self.bar = QProgressBar()
                self.bar.setRange(0, total)
                layout.addWidget(self.bar)
                self.text = QTextEdit()
                self.text.setReadOnly(True)
                layout.addWidget(self.text)
                btn_layout = QHBoxLayout()
                self.ok_btn = QPushButton("完成")
                self.ok_btn.setEnabled(False)
                self.ok_btn.clicked.connect(self.accept)
                btn_layout.addWidget(self.ok_btn)
                self.abort_btn = QPushButton("中止")
                self.abort_btn.setEnabled(True)
                self.abort_btn.clicked.connect(self.abort)
                btn_layout.addWidget(self.abort_btn)
                layout.addLayout(btn_layout)
                self._aborted = False
                self._auto_close_timer = None
            def update_progress(self, idx, total, msg):
                self.bar.setValue(idx)
                self.label.setText(f"正在推送第 {idx}/{total} 个...")
                self.text.append(msg)
            def finish(self):
                self.label.setText("推送完成！")
                self.ok_btn.setEnabled(True)
                self.abort_btn.setEnabled(False)
                # 2秒后自动关闭
                from PyQt5.QtCore import QTimer
                self._auto_close_timer = QTimer(self)
                self._auto_close_timer.setSingleShot(True)
                self._auto_close_timer.timeout.connect(self.accept)
                self._auto_close_timer.start(2000)
            def abort(self):
                self._aborted = True
                self.label.setText("已中止推送！")
                self.ok_btn.setEnabled(True)
                self.abort_btn.setEnabled(False)
                if self._auto_close_timer:
                    self._auto_close_timer.stop()
            def is_aborted(self):
                return self._aborted
        dlg = PushProgressDialog(len(urls), self)
        self.submit_btn.setEnabled(False)
        dlg.show()
        QApplication.processEvents()
        success_count = 0
        fail_count = 0
        new_tasks = []
        for idx, url in enumerate(urls, 1):
            QApplication.processEvents()
            if dlg.is_aborted():
                break
            try:
                dir_id_val = dir_id if dir_id and dir_id != '0' else None
                task_id = api.send_offline_download_request(token, url, dir_id=dir_id_val)
                success_count += 1
                # 获取文件名（如API无返回则用URL最后一段或占位）
                file_name = ''
                # 尝试从url获取文件名
                if '/' in url:
                    file_name = url.rstrip('/').split('/')[-1]
                if not file_name:
                    file_name = '未知文件'
                self.offline_task_manager.add_task(task_id, file_name, url)
                dlg.update_progress(idx, len(urls), f"✅ 成功: {url}")
            except Exception as e:
                err_msg = str(e)
                if '解析失败' in err_msg:
                    dlg.update_progress(idx, len(urls), f"❌ 链接解析失败")
                elif '服务内部错误' in err_msg:
                    dlg.update_progress(idx, len(urls), f"❌ 服务器内部错误")
                else:
                    dlg.update_progress(idx, len(urls), f"❌ 下载失败")
                fail_count += 1
        # 离线任务直接写入download_manager，无需再维护self.task_list
        dlg.finish()
        self.submit_btn.setEnabled(True)

    def add_user_dialog(self):
        dlg = UserDialog(self)
        if dlg.exec_() == QDialog.Accepted:
            data = dlg.get_user_data()
            if not data['name'] or not data['client_id'] or not data['client_secret']:
                QMessageBox.warning(self, "提示", "请填写完整信息")
                return
            self.user_manager.add_user(data['name'], data['client_id'], data['client_secret'])
            if data['access_token']:
                self.user_manager.update_token(data['name'], data['access_token'], data['expired_at'])
            self.refresh_user_table()

    def edit_user_dialog(self, name):
        user = self.user_manager.get_user(name)
        if not user:
            return
        dlg = UserDialog(self, {**user, 'name': name})
        if dlg.exec_() == QDialog.Accepted:
            data = dlg.get_user_data()
            if not data['name'] or not data['client_id'] or not data['client_secret']:
                QMessageBox.warning(self, "提示", "请填写完整信息")
                return
            self.user_manager.add_user(data['name'], data['client_id'], data['client_secret'])
            if data['access_token']:
                self.user_manager.update_token(data['name'], data['access_token'], data['expired_at'])
            self.refresh_user_table()

    def delete_user(self, name):
        reply = QMessageBox.question(self, "确认删除", f"确定要删除用户 {name} 吗？", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.user_manager.delete_user(name)
            # 删除该用户的下载任务和离线任务存储文件及下载路径配置文件
            from gui.download_tasks import get_download_tasks_file, get_offline_tasks_file, get_download_path_file
            import os
            for get_file in (get_download_tasks_file, get_offline_tasks_file, get_download_path_file):
                file_path = get_file(name)
                if os.path.exists(file_path):
                    os.remove(file_path)
            self.refresh_user_table()
            self.user_table.clearSelection()
            QMessageBox.information(self, "成功", f"用户 {name} 已删除")

    def update_token(self, name):
        user = self.user_manager.get_user(name)
        if not user:
            return
        try:
            token, expired_at = self.api.get_token_by_credentials(user['client_id'], user['client_secret'])
            self.user_manager.update_token(name, token, expired_at)
            QMessageBox.information(self, "成功", f"Token已更新")
            self.refresh_user_table()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"Token更新失败: {e}")

    def confirm_use(self):
        row = self.user_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "提示", "请先选择要使用的用户")
            return
        name = self.user_table.item(row, 0).text()
        user = self.user_manager.get_user(name)
        if not user:
            QMessageBox.warning(self, "提示", "用户不存在")
            return
        if self.user_manager.is_token_expired(name):
            try:
                token, expired_at = self.api.get_token_by_credentials(user['client_id'], user['client_secret'])
                self.user_manager.update_token(name, token, expired_at)
                QMessageBox.information(self, "成功", "Token已自动刷新")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"Token刷新失败: {e}")
                return
        self.current_user = name
        self.offline_task_manager.set_user(name)
        self.download_task_manager.set_user(name)
        QMessageBox.information(self, "成功", f"已确认使用用户 {name}")
        # 切换用户后，更新下载路径显示
        if hasattr(self, 'download_task_widget'):
            self.download_task_widget.path_label.setText(f"下载路径: {self.download_task_manager.get_download_path() or '未设置'}")

    def import_users(self):
        from .user_io import import_users_dialog
        import_users_dialog(self.user_manager, self)
        self.refresh_user_table()
    def export_users(self):
        from .user_io import export_users_dialog
        export_users_dialog(self.user_manager, self)

    def on_get_folder_id(self):
        token = ""
        if self.current_user:
            user = self.user_manager.get_user(self.current_user)
            if user:
                token = user.get('access_token', '')
        if not token:
            QMessageBox.warning(self, "提示", "请先登录/选择用户")
            return
        from core.file_api import FileApi
        dlg = FolderSelectDialog(FileApi(), token, self)
        if dlg.exec_() == QDialog.Accepted:
            folder_id = dlg.get_selected_folder_id()
            if folder_id:
                self.offline_dir_input.setText(str(folder_id))

    def on_clear_progress_tasks(self):
        reply = QMessageBox.question(self, "确认清空", "确定要清空所有离线任务记录吗？", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.offline_task_manager.clear_tasks()
            self.refresh_progress_table()

    def on_paste_urls(self):
        from PyQt5.QtWidgets import QApplication
        text = QApplication.clipboard().text()
        if text:
            self.urls_edit.insertPlainText(text)

    def eventFilter(self, obj, event):
        from PyQt5.QtCore import QEvent
        if obj == self.user_table.viewport() and event.type() == QEvent.MouseButtonPress:
            index = self.user_table.indexAt(event.pos())
            if not index.isValid():
                self.user_table.clearSelection()
        return super().eventFilter(obj, event)
    
    def closeEvent(self, event):
        """程序关闭时清理资源"""
        # 停止进度查询线程
        if self.progress_query_thread and self.progress_query_thread.isRunning():
            self.progress_query_thread.stop()
            self.progress_query_thread.wait()
        
        # 停止定时器
        self.stop_progress_timer()
        
        super().closeEvent(event)

    def get_token_func(self):
        if self.current_user:
            user = self.user_manager.get_user(self.current_user)
            if user:
                return user.get('access_token', '')
        return ''