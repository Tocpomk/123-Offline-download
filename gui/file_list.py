from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, QPushButton, QLineEdit, QLabel, QHeaderView, QComboBox, QDialog, QProgressBar, QApplication, QScrollArea, QMenu, QAction, QToolButton, QAbstractItemView
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from core.file_api import FileApi
from gui.pagination import PaginationWidget
import os

class BatchRenameWorker(QThread):
    progress = pyqtSignal(int, int)  # 已完成，总数
    finished = pyqtSignal(int, int)  # 成功，失败
    def __init__(self, api, token, rename_list, batch_size=3, parent=None):
        super().__init__(parent)
        self.api = api
        self.token = token
        self.rename_list = rename_list
        self.batch_size = batch_size
        self._is_running = True
    def run(self):
        import time
        total = len(self.rename_list)
        success, fail = 0, 0
        for i in range(0, total, self.batch_size):
            if not self._is_running:
                break
            batch = self.rename_list[i:i+self.batch_size]
            for item in batch:
                if item['old_name'] == item['new_name']:
                    continue
                try:
                    self.api.rename_file(self.token, item['file_id'], item['new_name'])
                    success += 1
                except Exception as e:
                    fail += 1
                self.progress.emit(success+fail, total)
            time.sleep(0.6)
        self.finished.emit(success, fail)
    def stop(self):
        self._is_running = False

class AutoLoadWorker(QThread):
    progress = pyqtSignal(int)  # 已加载文件数量
    finished = pyqtSignal(list)  # 完整的文件列表
    error = pyqtSignal(str)  # 错误信息
    
    def __init__(self, api, token, parent_id, page_size, parent=None):
        super().__init__(parent)
        self.api = api
        self.token = token
        self.parent_id = parent_id
        self.page_size = page_size
        self._is_running = True
    
    def run(self):
        all_files = []
        last_file_id = None
        
        while self._is_running:
            try:
                resp = self.api.get_file_list(self.token, parent_file_id=self.parent_id, limit=self.page_size, last_file_id=last_file_id)
            except Exception as e:
                self.error.emit(str(e))
                return
            
            data = resp.get("data", {})
            file_list = [f for f in data.get("fileList", []) if f.get('trashed', 0) == 0]
            
            if not file_list:
                break
                
            all_files.extend(file_list)
            self.progress.emit(len(all_files))
            
            if len(file_list) < self.page_size:
                break
                
            last_file_id = file_list[-1].get('fileId')
        
        # 验证文件数据完整性
        valid_files = []
        for file_info in all_files:
            if isinstance(file_info, dict) and 'fileId' in file_info and 'filename' in file_info:
                file_info.setdefault('type', 0)
                file_info.setdefault('size', 0)
                file_info.setdefault('status', 0)
                file_info.setdefault('createAt', '')
                valid_files.append(file_info)
        
        self.finished.emit(valid_files)
    
    def stop(self):
        self._is_running = False

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

class FileListPage(QWidget):
    def __init__(self, get_token_func, parent=None):
        super().__init__(parent)
        self.get_token_func = get_token_func  # 获取token的方法
        self.api = FileApi()
        self.current_parent_id = 0
        self.file_list = []
        self.file_list_cache = {}  # 新增缓存
        self.folder_path = [(0, '根目录')]
        self.page_size = 100  # 直接最大100
        self.total = 0
        # 排序相关
        self.sort_column = 1  # 默认按文件名排序
        self.sort_order = Qt.AscendingOrder  # 默认升序
        # 自动加载工作线程
        self.auto_load_worker = None
        # 信息标签隐藏定时器
        self.info_hide_timer = QTimer()
        self.info_hide_timer.setSingleShot(True)
        self.info_hide_timer.timeout.connect(self.hide_info_label)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        # 路径面包屑和返回按钮
        path_layout = QHBoxLayout()
        self.back_btn = QPushButton('返回上一层')
        self.back_btn.setStyleSheet('QPushButton{min-width:90px;max-width:110px;min-height:28px;max-height:32px;font-size:14px;}')
        self.back_btn.clicked.connect(self.on_back)
        self.path_bar = QHBoxLayout()
        path_layout.addWidget(self.back_btn)
        path_layout.addSpacing(24)
        path_layout.addLayout(self.path_bar)
        path_layout.addStretch()
        layout.addLayout(path_layout)
        # 顶部功能按钮区
        func_layout = QHBoxLayout()
        # 主操作按钮全部用QToolButton
        self.create_dir_btn = self.make_flat_btn('创建目录', '#13C2C2', '#165DFF')
        self.create_dir_btn.clicked.connect(self.on_create_dir)
        func_layout.addWidget(self.create_dir_btn)
        self.upload_btn = self.make_flat_btn('上传文件', '#13C2C2', '#165DFF')
        self.upload_btn.clicked.connect(self.on_upload_file)
        func_layout.addWidget(self.upload_btn)
        self.rename_btn = self.make_flat_btn('重命名', '#13C2C2', '#165DFF')
        self.rename_btn.clicked.connect(self.on_rename)
        func_layout.addWidget(self.rename_btn)
        self.batch_rename_btn = self.make_flat_btn('批量重命名', '#13C2C2', '#165DFF')
        self.batch_rename_btn.clicked.connect(self.on_batch_rename)
        func_layout.addWidget(self.batch_rename_btn)
        # 删除按钮带下拉菜单
        menu = QMenu()
        menu.setStyleSheet('''
        QMenu {
            background: #fff;
            border: 1.5px solid #FF7A45;
            border-radius: 8px;
            font-size: 15px;
            min-width: 110px;
        }
        QMenu::item {
            padding: 8px 18px;
            border-radius: 6px;
        }
        QMenu::item:selected {
            background: #FFF1F0;
            color: #FF4D4F;
        }
        ''')
        act_del = QAction('删除', self)
        act_del.triggered.connect(self.on_delete)
        menu.addAction(act_del)
        act_del_harmony = QAction('删除和谐', self)
        act_del_harmony.triggered.connect(self.on_delete_harmony)
        menu.addAction(act_del_harmony)
        self.delete_btn = self.make_flat_btn('删除', '#FF4D4F', '#FF7A45', menu)
        self.delete_btn.clicked.connect(self.on_delete)
        func_layout.addWidget(self.delete_btn)
        self.move_btn = self.make_flat_btn('移动', '#13C2C2', '#165DFF')
        self.move_btn.clicked.connect(self.on_move)
        func_layout.addWidget(self.move_btn)
        self.download_btn = self.make_flat_btn('下载', '#13C2C2', '#165DFF')
        self.download_btn.clicked.connect(self.on_download)
        func_layout.addWidget(self.download_btn)
        func_layout.addStretch()
        layout.addLayout(func_layout)
        # 顶部搜索栏
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索文件名/关键字")
        self.search_btn = QPushButton("搜索")
        self.search_btn.setStyleSheet('QPushButton{min-width:70px;max-width:80px;min-height:26px;max-height:30px;font-size:13px;}')
        self.search_btn.clicked.connect(self.on_search)
        self.clear_btn = QPushButton("清空")
        self.clear_btn.setStyleSheet('QPushButton{min-width:70px;max-width:80px;min-height:26px;max-height:30px;font-size:13px;}')
        self.clear_btn.clicked.connect(self.on_clear_search)
        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.setStyleSheet('QPushButton{min-width:70px;max-width:80px;min-height:26px;max-height:30px;font-size:13px;}')
        self.refresh_btn.clicked.connect(self.on_refresh)
        search_layout.addWidget(QLabel("文件列表"))
        search_layout.addStretch()
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.search_btn)
        search_layout.addWidget(self.clear_btn)
        search_layout.addWidget(self.refresh_btn)
        # 新增全选按钮
        self.select_all_btn = QPushButton("全选")
        self.select_all_btn.setStyleSheet('QPushButton{min-width:70px;max-width:80px;min-height:26px;max-height:30px;font-size:13px;}')
        self.select_all_btn.clicked.connect(self.on_select_all)
        search_layout.addWidget(self.select_all_btn)
        layout.addLayout(search_layout)
        # 文件表格
        layout.addSpacing(18)
        from PyQt5.QtWidgets import QTableWidget
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["文件ID", "文件名", "类型", "大小", "状态", "创建时间"])
        
        # 设置列宽模式
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        # 设置各列的固定宽度
        self.table.setColumnWidth(0, 110)   # 文件ID
        self.table.setColumnWidth(2, 110)   # 类型（稍微宽一点）
        self.table.setColumnWidth(3, 120)  # 大小（稍微宽一点）
        self.table.setColumnWidth(4, 110)   # 状态（稍微宽一点）
        self.table.setColumnWidth(5, 180)  # 创建时间（稍微宽一点）
        # 文件名列设置为拉伸模式，占用剩余空间
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setColumnWidth(1, 400)  # 设置文件名列最小宽度为400像素
        
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        from PyQt5.QtWidgets import QAbstractItemView
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.setAlternatingRowColors(True)
        
        # 启用排序功能
        self.table.setSortingEnabled(False)
        self.table.horizontalHeader().setSectionsClickable(True)
        self.table.horizontalHeader().sectionClicked.connect(self.on_header_clicked)
        
        # 设置表头鼠标指针样式
        from PyQt5.QtGui import QCursor
        self.table.horizontalHeader().setCursor(QCursor(Qt.PointingHandCursor))
        
        # 保存原始表头文本
        self.original_headers = ["文件ID", "文件名", "类型", "大小", "状态", "创建时间"]
        
        self.table.setStyleSheet("""
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
    padding-left: 12px;
    text-align: left;
}
QHeaderView::section:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #8BB8F5, stop:1 #D4E8FF);
}
QHeaderView::section:checked {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #165DFF, stop:1 #0FC6C2);
    color: white;
}
QHeaderView::up-arrow {
    image: none;
    border: none;
    width: 0px;
    height: 0px;
}
QHeaderView::down-arrow {
    image: none;
    border: none;
    width: 0px;
    height: 0px;
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
QScrollBar:horizontal {
    height: 10px;
    background: #f0f4f8;
    margin: 0px 0px 0px 0px;
    border-radius: 5px;
}
QScrollBar::handle:horizontal {
    background: #A3C8F7;
    min-width: 20px;
    border-radius: 5px;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}
""")
        self.table.cellDoubleClicked.connect(self.on_cell_double_clicked)
        self.table.setMinimumHeight(int(self.table.sizeHint().height() * 1.3))
        from PyQt5.QtWidgets import QGraphicsDropShadowEffect
        shadow = QGraphicsDropShadowEffect(self.table)
        shadow.setBlurRadius(16)
        shadow.setOffset(0, 3)
        shadow.setColor(Qt.gray)
        self.table.setGraphicsEffect(shadow)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.on_table_context_menu)
        layout.addWidget(self.table)
        # 移除分页控件
        # self.pagination = PaginationWidget()
        # layout.addWidget(self.pagination)
        self.info_label = QLabel("")
        self.info_label.setVisible(False)
        self.info_label.setWordWrap(True)
        self.info_label.setMaximumHeight(40)
        self.info_label.setStyleSheet("color:#d9363e;font-size:14px;")
        layout.addWidget(self.info_label)
        self.setLayout(layout)
        self.load_file_list()

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
            btn.setStyleSheet('QPushButton{color:#165DFF;font-weight:bold;background:transparent;padding:0 2px;font-size:15px;} QPushButton:hover{color:#13C2C2;}')
            btn.clicked.connect(lambda _, idx=i: self.on_path_clicked(idx))
            self.path_bar.addWidget(btn)
            if i < len(self.folder_path) - 1:
                sep = QLabel('>')
                sep.setStyleSheet('QLabel{padding:0;color:#888;font-size:14px;}')
                self.path_bar.addWidget(sep)

    def on_path_clicked(self, idx):
        # 跳转到指定层级
        fid, _ = self.folder_path[idx]
        self.folder_path = self.folder_path[:idx+1]
        self.load_file_list(parent_id=fid)

    def on_back(self):
        if len(self.folder_path) > 1:
            self.folder_path.pop()
            fid, _ = self.folder_path[-1]
            self.load_file_list(parent_id=fid)

    def load_file_list(self, parent_id=None, search_data=None, reset_cursor=False):
        token = self.get_token_func()
        if not token:
            self.info_label.setText("请先登录/选择用户")
            self.info_label.setToolTip("")
            self.info_label.setVisible(True)
            return
        parent_id = parent_id if parent_id is not None else self.current_parent_id
        # 优先用缓存
        if search_data is None and parent_id in self.file_list_cache:
            self.file_list = self.file_list_cache[parent_id].copy()
            self.total = len(self.file_list)
            self.current_parent_id = parent_id
            self.sort_column = 1
            self.sort_order = Qt.AscendingOrder
            self.update_path_bar()
            self.refresh_table()
            self.info_label.setText(f"已加载全部文件（缓存），共{self.total}个")
            self.info_label.setVisible(True)
            # 1秒后自动隐藏信息标签
            self.info_hide_timer.start(1000)
            return
        page_size = self.page_size
        self.table.setRowCount(0)
        self.table.setDisabled(True)
        self.info_label.setText("加载中...")
        self.info_label.setToolTip("")
        self.info_label.setVisible(True)
        
        def fetch():
            try:
                resp = self.api.get_file_list(token, parent_file_id=parent_id, limit=page_size, search_data=search_data)
                return resp
            except Exception as e:
                short_msg = "获取失败：网络异常或服务器无响应"
                self.info_label.setText(short_msg)
                self.info_label.setToolTip(str(e))
                self.info_label.setVisible(True)
                return {"code": -1, "message": short_msg}
        
        class Loader(QThread):
            finished = pyqtSignal(dict)
            def run(self):
                try:
                    result = fetch()
                    self.finished.emit(result)
                except Exception as e:
                    self.finished.emit({"code": -1, "message": f"线程异常: {e}"})
        
        self.loader = Loader()
        self.loader.finished.connect(lambda resp: self.on_file_list_loaded_safe(resp, parent_id, page_size, search_data))
        self.loader.start()

    def on_file_list_loaded_safe(self, resp, parent_id, page_size, search_data):
        try:
            self.on_file_list_loaded(resp, parent_id, page_size, search_data)
        except Exception as e:
            self.table.setDisabled(False)
            self.info_label.setVisible(True)
            self.info_label.setText(f"加载失败: {e}")

    def on_file_list_loaded(self, resp, parent_id, page_size, search_data):
        self.table.setDisabled(False)
        if resp.get("code") != 0:
            self.info_label.setVisible(True)
            self.info_label.setText(f"获取失败: {resp.get('message')}")
            self.table.setRowCount(0)
            return
        
        data = resp.get("data", {})
        all_files = [f for f in data.get("fileList", []) if f.get('trashed', 0) == 0]
        
        # 验证文件数据完整性
        valid_files = []
        for file_info in all_files:
            if isinstance(file_info, dict) and 'fileId' in file_info and 'filename' in file_info:
                # 确保关键字段存在且有默认值
                file_info.setdefault('type', 0)
                file_info.setdefault('size', 0)
                file_info.setdefault('status', 0)
                file_info.setdefault('createAt', '')
                valid_files.append(file_info)
            else:
                print(f"警告：跳过无效文件数据：{file_info}")
        
        if len(valid_files) != len(all_files):
            print(f"警告：{len(all_files) - len(valid_files)} 个文件数据无效，已过滤")
        
        self.total = len(valid_files)
        self.file_list = valid_files.copy()  # 使用copy确保数据独立
        self.current_parent_id = parent_id
        # 每次加载新数据都重置排序状态，不自动排序
        self.sort_column = 1  # 默认按文件名
        self.sort_order = Qt.AscendingOrder
        
        # 路径追踪
        if not self.folder_path or self.folder_path[-1][0] != parent_id:
            if parent_id == 0:
                self.folder_path = [(0, '根目录')]
            else:
                folder_name = None
                for f in self.file_list:
                    if f.get('fileId') == parent_id and f.get('type') == 1:
                        folder_name = f.get('filename', str(parent_id))
                        break
                if not folder_name:
                    folder_name = str(parent_id)
                self.folder_path.append((parent_id, folder_name))
        
        self.update_path_bar()
        self.refresh_table()
        
        # 检查是否需要自动加载更多文件
        if self.total >= 100 and not search_data:
            # 自动加载所有文件
            self.auto_load_all_files(parent_id)
        else:
            # 文件夹内文件少于100个，隐藏加载提示
            self.info_label.setVisible(False)

    def auto_load_all_files(self, parent_id):
        """自动分批加载所有文件"""
        token = self.get_token_func()
        if not token:
            return
        
        # 如果已有工作线程在运行，先停止它
        if self.auto_load_worker and self.auto_load_worker.isRunning():
            self.auto_load_worker.stop()
            self.auto_load_worker.wait()
        
        # 创建新的工作线程
        self.auto_load_worker = AutoLoadWorker(self.api, token, parent_id, self.page_size, self)
        self.auto_load_worker.progress.connect(self.on_auto_load_progress)
        self.auto_load_worker.finished.connect(self.on_auto_load_finished)
        self.auto_load_worker.error.connect(self.on_auto_load_error)
        
        # 更新UI状态
        self.info_label.setText("正在自动加载全部文件...")
        self.info_label.setVisible(True)
        
        # 启动工作线程
        self.auto_load_worker.start()
    
    def on_auto_load_progress(self, count):
        """自动加载进度更新"""
        self.info_label.setText(f"已加载{count}个文件...")
    
    def on_auto_load_finished(self, file_list):
        """自动加载完成"""
        self.file_list = file_list.copy()
        self.file_list_cache[self.current_parent_id] = file_list.copy()  # 写入缓存
        self.total = len(file_list)
        self.info_label.setText(f"已加载全部文件，共{self.total}个")
        self.info_label.setVisible(True)
        self.refresh_table()
        
        # 1秒后自动隐藏信息标签
        self.info_hide_timer.start(1000)
        
        # 清理工作线程
        if self.auto_load_worker:
            self.auto_load_worker.deleteLater()
            self.auto_load_worker = None
    
    def on_auto_load_error(self, error_msg):
        """自动加载出错"""
        self.info_label.setText(f"获取失败：{error_msg}")
        self.info_label.setVisible(True)
        
        # 清理工作线程
        if self.auto_load_worker:
            self.auto_load_worker.deleteLater()
            self.auto_load_worker = None

    def hide_info_label(self):
        """隐藏信息标签"""
        self.info_label.setVisible(False)

    def refresh_table(self):
        """刷新表格显示"""
        if not self.file_list:
            self.table.setRowCount(0)
            return
            
        # 验证数据完整性
        valid_files = []
        for i, file_info in enumerate(self.file_list):
            if isinstance(file_info, dict) and 'fileId' in file_info and 'filename' in file_info:
                # 确保所有必要字段都有默认值
                file_info.setdefault('type', 0)
                file_info.setdefault('size', 0)
                file_info.setdefault('status', 0)
                file_info.setdefault('createAt', '')
                valid_files.append(file_info)
            else:
                print(f"警告：发现无效文件数据（第{i}个）：{file_info}")
        
        if len(valid_files) != len(self.file_list):
            print(f"警告：{len(self.file_list) - len(valid_files)} 个文件数据无效，已过滤")
            self.file_list = valid_files.copy()  # 使用copy确保数据独立
        
        self.table.setRowCount(len(self.file_list))
        for row, file_info in enumerate(self.file_list):
            try:
                # 文件ID
                file_id = str(file_info.get('fileId', ''))
                id_item = QTableWidgetItem(file_id)
                id_item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, 0, id_item)
                
                # 文件名
                filename = file_info.get('filename', '')
                filename_item = QTableWidgetItem(filename)
                filename_item.setToolTip(filename)  # 设置tooltip，显示完整文件名
                # 为排序设置数据
                filename_item.setData(Qt.UserRole, filename.lower())
                self.table.setItem(row, 1, filename_item)
                
                # 类型
                file_type = "文件夹" if file_info.get('type') == 1 else "文件"
                type_item = QTableWidgetItem(file_type)
                type_item.setData(Qt.UserRole, file_info.get('type', 0))
                type_item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, 2, type_item)
                
                # 大小
                size = file_info.get('size', 0)
                size_str = self.format_size(size)
                size_item = QTableWidgetItem(size_str)
                size_item.setData(Qt.UserRole, size)  # 用于排序的原始大小
                size_item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, 3, size_item)
                
                # 状态
                status = file_info.get('status', 0)
                status_text = '正常' if status < 100 else '审核驳回'
                status_item = QTableWidgetItem(status_text)
                status_item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, 4, status_item)
                
                # 创建时间
                create_time = file_info.get('createAt', '')
                create_time_item = QTableWidgetItem(create_time)
                create_time_item.setData(Qt.UserRole, create_time)  # 用于排序的时间
                self.table.setItem(row, 5, create_time_item)
                
            except Exception as e:
                print(f"警告：处理第 {row} 行数据时出错：{e}")
                print(f"问题数据：{file_info}")
                # 填充空数据
                for col in range(6):
                    self.table.setItem(row, col, QTableWidgetItem(""))
        
        # 应用当前排序（如果有排序状态）
        if hasattr(self, 'sort_column') and hasattr(self, 'sort_order'):
            self.apply_current_sort()
            # 更新排序状态指示器
            self.update_sort_indicator()

    def on_header_clicked(self, logical_index):
        """处理表格头部点击事件"""
        self.restore_header_texts()
        if logical_index == self.sort_column:
            self.sort_order = Qt.DescendingOrder if self.sort_order == Qt.AscendingOrder else Qt.AscendingOrder
        else:
            self.sort_column = logical_index
            self.sort_order = Qt.AscendingOrder
        # 只对当前file_list排序
        self.sort_file_list()
        self.refresh_table()

    def restore_header_texts(self):
        """恢复所有表头文本为原始状态"""
        for i, header_text in enumerate(self.original_headers):
            if i < self.table.columnCount():
                self.table.horizontalHeaderItem(i).setText(header_text)

    def sort_file_list(self):
        """对文件列表进行排序，文件夹始终排在前面"""
        if not self.file_list:
            return
        original_files = self.file_list.copy()
        reverse = (self.sort_order == Qt.DescendingOrder)
        try:
            if not all(isinstance(f, dict) and 'fileId' in f and 'filename' in f for f in self.file_list):
                print("警告：排序前数据验证失败，跳过排序")
                return
            # 文件夹优先，再按选中列排序
            if self.sort_column == 1:  # 文件名
                self.file_list.sort(key=lambda x: (x.get('type', 0) != 1, x.get('filename', '').lower()), reverse=reverse)
            elif self.sort_column == 2:  # 类型
                self.file_list.sort(key=lambda x: (x.get('type', 0) != 1, x.get('type', 0)), reverse=reverse)
            elif self.sort_column == 3:  # 大小
                self.file_list.sort(key=lambda x: (x.get('type', 0) != 1, x.get('size', 0)), reverse=reverse)
            elif self.sort_column == 5:  # 创建时间
                self.file_list.sort(key=lambda x: (x.get('type', 0) != 1, x.get('createAt', '')), reverse=reverse)
            # 其他列保持原有顺序
            if len(self.file_list) != len(original_files):
                self.file_list = original_files
                print("警告：排序过程中数据丢失，已恢复原始数据")
                return
            for i, file_info in enumerate(self.file_list):
                if not isinstance(file_info, dict) or 'fileId' not in file_info:
                    print(f"警告：排序后第 {i} 个文件数据无效，恢复原始数据")
                    self.file_list = original_files
                    return
        except Exception as e:
            self.file_list = original_files
            print(f"排序出错：{e}，已恢复原始数据")

    def apply_current_sort(self):
        # 禁用QTableWidget的sortItems，保持表格和file_list顺序一致
        pass

    def get_file_by_row(self, row):
        # 通过表格行号获取fileId，再反查file_list
        file_id = self.table.item(row, 0).text()
        for f in self.file_list:
            if str(f.get('fileId')) == file_id:
                return f
        return None

    def on_cell_double_clicked(self, row, col):
        f = self.get_file_by_row(row)
        if f and f.get('type') == 1:  # 文件夹
            self.folder_path.append((f.get('fileId'), f.get('filename', str(f.get('fileId')))))
            self.load_file_list(parent_id=f.get('fileId'))

    def on_create_dir(self):
        from PyQt5.QtWidgets import QInputDialog, QMessageBox
        dir_name, ok = QInputDialog.getText(self, "创建目录", "请输入新目录名称：")
        if ok and dir_name.strip():
            token = self.get_token_func()
            if not token:
                QMessageBox.warning(self, "提示", "请先登录/选择用户")
                return
            parent_id = self.current_parent_id
            try:
                resp = self.api.create_directory(token, dir_name.strip(), parent_id)
                if resp:
                    QMessageBox.information(self, "成功", f"目录 '{dir_name}' 创建成功！")
                    self.load_file_list()
                else:
                    QMessageBox.warning(self, "失败", "目录创建失败")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"创建目录失败: {e}") 

    def on_rename(self):
        from PyQt5.QtWidgets import QInputDialog, QMessageBox
        selected = self.table.selectedItems()
        if not selected:
            QMessageBox.warning(self, "提示", "请先选择要重命名的文件/文件夹")
            return
        selected_rows = list(set([item.row() for item in selected]))
        if len(selected_rows) == 1:
            row = selected_rows[0]
            f = self.get_file_by_row(row)
            if not f:
                QMessageBox.warning(self, "提示", "未找到对应文件")
                return
            file_id = f.get('fileId')
            old_name = f.get('filename', '')
            new_name, ok = QInputDialog.getText(self, "重命名", f"请输入新名称：", text=old_name)
            if ok and new_name.strip() and new_name.strip() != old_name:
                token = self.get_token_func()
                if not token:
                    QMessageBox.warning(self, "提示", "请先登录/选择用户")
                    return
                try:
                    self.api.rename_file(token, file_id, new_name.strip())
                    QMessageBox.information(self, "成功", f"重命名成功！")
                    self.load_file_list()
                except Exception as e:
                    QMessageBox.critical(self, "错误", f"重命名失败: {e}")
        elif len(selected_rows) > 1:
            if len(selected_rows) > 30:
                QMessageBox.warning(self, "提示", "批量重命名一次最多支持30个文件！")
                return
            # 批量重命名对话框
            class BatchRenameDialog(QDialog):
                def __init__(self, file_infos, parent=None):
                    super().__init__(parent)
                    self.setWindowTitle("批量重命名")
                    self.resize(480, 480)
                    layout = QVBoxLayout(self)
                    scroll = QScrollArea(self)
                    scroll.setWidgetResizable(True)
                    content = QWidget()
                    form_layout = QVBoxLayout(content)
                    self.line_edits = []
                    for file_id, old_name in file_infos:
                        row_layout = QHBoxLayout()
                        row_layout.addWidget(QLabel(f"ID:{file_id}"))
                        old_label = QLabel(old_name)
                        old_label.setMinimumWidth(120)
                        row_layout.addWidget(old_label)
                        edit = QLineEdit(old_name)
                        row_layout.addWidget(edit)
                        self.line_edits.append((file_id, edit, old_name))
                        form_layout.addLayout(row_layout)
                    content.setLayout(form_layout)
                    scroll.setWidget(content)
                    layout.addWidget(scroll)
                    btn_layout = QHBoxLayout()
                    ok_btn = QPushButton("确定")
                    cancel_btn = QPushButton("取消")
                    btn_layout.addStretch()
                    btn_layout.addWidget(ok_btn)
                    btn_layout.addWidget(cancel_btn)
                    layout.addLayout(btn_layout)
                    ok_btn.clicked.connect(self.accept)
                    cancel_btn.clicked.connect(self.reject)
                def get_rename_list(self):
                    result = []
                    for file_id, edit, old_name in self.line_edits:
                        new_name = edit.text().strip()
                        if new_name and new_name != old_name:
                            result.append(f"{file_id}|{new_name}")
                    return result
            file_infos = [(int(self.table.item(row, 0).text()), self.table.item(row, 1).text()) for row in selected_rows]
            dlg = BatchRenameDialog(file_infos, self)
            if dlg.exec_() == QDialog.Accepted:
                rename_list = dlg.get_rename_list()
                token = self.get_token_func()
                api = FileApi()
                progress_dlg = ProgressDialog("批量重命名进度", len(rename_list), self)
                worker = BatchRenameWorker(api, token, rename_list, batch_size=5)  # 并发数改为5
                def on_progress(done, total):
                    progress_dlg.setValue(done)
                def on_finished(success, fail):
                    progress_dlg.setValue(len(rename_list))
                    progress_dlg.setLabelText(f"完成，成功{success}个，失败{fail}个。")
                    QApplication.processEvents()
                    import time
                    time.sleep(1.2)
                    progress_dlg.accept()
                    QMessageBox.information(self, "批量重命名", f"重命名完成，成功{success}个，失败{fail}个。")
                    self.on_refresh()
                worker.progress.connect(on_progress)
                worker.finished.connect(on_finished)
                progress_dlg.cancel_btn.clicked.connect(worker.stop)
                worker.start()
                progress_dlg.exec_()

    def on_delete(self):
        from PyQt5.QtWidgets import QMessageBox
        selected = self.table.selectedItems()
        if not selected:
            QMessageBox.warning(self, "提示", "请先选择要删除的文件/文件夹")
            return
        selected_rows = list(set([item.row() for item in selected]))
        file_ids = []
        for row in selected_rows:
            f = self.get_file_by_row(row)
            if f:
                file_ids.append(f.get('fileId'))
        if not file_ids:
            QMessageBox.warning(self, "提示", "未找到要删除的文件")
            return
        reply = QMessageBox.question(self, "确认删除", f"确定要删除选中的 {len(file_ids)} 个文件/文件夹吗？\n删除后可在回收站找回。", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            token = self.get_token_func()
            if not token:
                QMessageBox.warning(self, "提示", "请先登录/选择用户")
                return
            try:
                self.api.move_to_trash(token, file_ids)
                QMessageBox.information(self, "成功", f"删除成功，已移入回收站！")
                self.load_file_list()
            except Exception as e:
                QMessageBox.critical(self, "错误", f"删除失败: {e}") 

    def on_move(self):
        from PyQt5.QtWidgets import QInputDialog, QMessageBox, QLineEdit, QMenu, QAction
        selected = self.table.selectedItems()
        if not selected:
            QMessageBox.warning(self, "提示", "请先选择要移动的文件/文件夹")
            return
        selected_rows = list(set([item.row() for item in selected]))
        file_ids = []
        for row in selected_rows:
            f = self.get_file_by_row(row)
            if f:
                file_ids.append(f.get('fileId'))
        if not file_ids:
            QMessageBox.warning(self, "提示", "未找到要移动的文件")
            return
        # 自定义QInputDialog，设置QLineEdit右键菜单为中文
        class ChineseInputDialog(QInputDialog):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
            def showEvent(self, event):
                super().showEvent(event)
                edits = self.findChildren(QLineEdit)
                for edit in edits:
                    edit.setContextMenuPolicy(Qt.CustomContextMenu)
                    edit.customContextMenuRequested.connect(lambda pos, e=edit: self.show_chinese_menu(e, pos))
            def show_chinese_menu(self, edit, pos):
                menu = QMenu(edit)
                menu.addAction(QAction("撤销", edit, triggered=edit.undo))
                menu.addAction(QAction("重做", edit, triggered=edit.redo))
                menu.addSeparator()
                menu.addAction(QAction("剪切", edit, triggered=edit.cut))
                menu.addAction(QAction("复制", edit, triggered=edit.copy))
                menu.addAction(QAction("粘贴", edit, triggered=edit.paste))
                menu.addAction(QAction("删除", edit, triggered=lambda: edit.del_()))
                menu.addSeparator()
                menu.addAction(QAction("全选", edit, triggered=edit.selectAll))
                menu.exec_(edit.mapToGlobal(pos))
        # 给QLineEdit补充del_方法
        def del_(self):
            cursor = self.cursorPosition()
            if self.hasSelectedText():
                self.insert('')
            else:
                text = self.text()
                if cursor < len(text):
                    self.setText(text[:cursor] + text[cursor+1:])
                    self.setCursorPosition(cursor)
        QLineEdit.del_ = del_
        dlg = ChineseInputDialog(self)
        dlg.setInputMode(QInputDialog.IntInput)
        dlg.setWindowTitle("移动到...")
        dlg.setLabelText("请输入目标文件夹ID（根目录填0）：")
        dlg.setIntRange(0, 2**31-1)
        dlg.setIntValue(0)
        if dlg.exec_() == QInputDialog.Accepted:
            to_parent_id = dlg.intValue()
            token = self.get_token_func()
            if not token:
                QMessageBox.warning(self, "提示", "请先登录/选择用户")
                return
            try:
                self.api.move_files(token, file_ids, to_parent_id)
                QMessageBox.information(self, "成功", f"移动成功！")
                self.load_file_list()
            except Exception as e:
                QMessageBox.critical(self, "错误", f"移动失败: {e}") 

    def on_download(self):
        from PyQt5.QtWidgets import QMessageBox, QFileDialog
        from gui.main_window import MainWindow
        selected = self.table.selectedItems()
        if not selected:
            QMessageBox.warning(self, "提示", "请先选择要下载的文件（仅支持单选）")
            return
        selected_rows = list(set([item.row() for item in selected]))
        if len(selected_rows) != 1:
            QMessageBox.warning(self, "提示", "请只选择一个文件进行下载")
            return
        row = selected_rows[0]
        f = self.get_file_by_row(row)
        if not f:
            QMessageBox.warning(self, "提示", "未找到对应文件")
            return
        file_id = f.get('fileId')
        file_name = f.get('filename', '')
        token = self.get_token_func()
        if not token:
            QMessageBox.warning(self, "提示", "请先登录/选择用户")
            return
        # 获取主窗口的 download_task_manager
        main_win = self.parent()
        while main_win and not hasattr(main_win, 'download_task_manager'):
            main_win = main_win.parent()
        if not main_win or not hasattr(main_win, 'download_task_manager'):
            QMessageBox.warning(self, "提示", "未找到下载管理器")
            return
        download_manager = main_win.download_task_manager
        # 检查下载路径
        download_path = download_manager.get_download_path()
        if not download_path:
            path = QFileDialog.getExistingDirectory(self, "请选择下载保存路径", os.path.expanduser('~'))
            if not path:
                QMessageBox.warning(self, "提示", "未选择下载路径，已取消下载")
                return
            download_manager.set_download_path(path)
        try:
            url = self.api.get_download_url(token, file_id)
            # 推送任务到下载队列并启动
            task = download_manager.add_task(file_id, file_name, url)
            download_manager.start_download(task)
            QMessageBox.information(self, "下载任务", f"下载任务已创建，进度可在‘下载任务’页面查看！")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"获取下载链接失败: {e}") 

    def on_table_context_menu(self, pos):
        from PyQt5.QtWidgets import QMenu, QAction, QApplication, QMessageBox
        index = self.table.indexAt(pos)
        if not index.isValid():
            return
        row = index.row()
        # 判断是否单选且为文件夹
        selected = self.table.selectedItems()
        selected_rows = list(set([item.row() for item in selected]))
        if len(selected_rows) == 1 and row == selected_rows[0]:
            file_type = self.table.item(row, 2).text()
            if file_type == '文件夹':
                menu = QMenu(self.table)
                copy_id_action = QAction('复制文件夹ID', self.table)
                def do_copy():
                    file_id = self.table.item(row, 0).text()
                    QApplication.clipboard().setText(file_id)
                    QMessageBox.information(self, '提示', f'文件夹ID已复制：{file_id}')
                copy_id_action.triggered.connect(do_copy)
                menu.addAction(copy_id_action)
                menu.exec_(self.table.viewport().mapToGlobal(pos)) 

    def on_batch_rename(self):
        from gui.batch_rename import BatchRenameDialog
        from core.file_api import FileApi
        from PyQt5.QtWidgets import QMessageBox, QApplication
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "提示", "请先选择要批量重命名的文件/文件夹")
            return
        file_infos = []
        for idx in selected_rows:
            row = idx.row()
            file_id = self.table.item(row, 0).text()
            file_name = self.table.item(row, 1).text()
            file_infos.append({'file_id': file_id, 'file_name': file_name})
        dlg = BatchRenameDialog(file_infos, self)
        if dlg.exec_() == dlg.Accepted:
            rename_list = dlg.get_rename_list()
            token = self.get_token_func()
            api = FileApi()
            progress_dlg = ProgressDialog("批量重命名进度", len(rename_list), self)
            worker = BatchRenameWorker(api, token, rename_list, batch_size=5)  # 并发数改为5
            def on_progress(done, total):
                progress_dlg.setValue(done)
            def on_finished(success, fail):
                progress_dlg.setValue(len(rename_list))
                progress_dlg.setLabelText(f"完成，成功{success}个，失败{fail}个。")
                QApplication.processEvents()
                import time
                time.sleep(1.2)
                progress_dlg.accept()
                QMessageBox.information(self, "批量重命名", f"重命名完成，成功{success}个，失败{fail}个。")
                self.on_refresh()
            worker.progress.connect(on_progress)
            worker.finished.connect(on_finished)
            progress_dlg.cancel_btn.clicked.connect(worker.stop)
            worker.start()
            progress_dlg.exec_()

    def on_select_all(self):
        self.table.selectAll() 

    def update_sort_indicator(self):
        """更新排序状态指示器"""
        # 清除所有列的排序指示器
        for i in range(self.table.columnCount()):
            self.table.horizontalHeader().setSortIndicatorShown(False)
        
        # 自定义排序指示器：在表头文本右边添加箭头
        if self.file_list:
            # 获取当前排序列的原始标题
            header_text = self.original_headers[self.sort_column]
            
            # 根据排序方向选择箭头符号
            if self.sort_order == Qt.AscendingOrder:
                arrow = " ▲"  # 升序箭头，前面加空格
            else:
                arrow = " ▼"  # 降序箭头，前面加空格
            
            # 更新表头文本，在右边添加箭头
            new_header_text = header_text + arrow
            self.table.horizontalHeaderItem(self.sort_column).setText(new_header_text)
            
            # 设置排序列的背景色
            self.table.horizontalHeader().setStyleSheet("""
                QHeaderView::section {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #A3C8F7, stop:1 #e6f7ff);
                    color: #222;
                    font-weight: bold;
                    font-size: 16px;
                    border: none;
                    border-radius: 8px;
                    height: 38px;
                    padding: 4px 0;
                    padding-left: 12px;
                    text-align: left;
                }
                QHeaderView::section:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #8BB8F5, stop:1 #D4E8FF);
                }
                QHeaderView::section:nth-child(%d) {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #165DFF, stop:1 #0FC6C2);
                    color: white;
                }
                QHeaderView::up-arrow {
                    image: none;
                    border: none;
                    width: 0px;
                    height: 0px;
                }
                QHeaderView::down-arrow {
                    image: none;
                    border: none;
                    width: 0px;
                    height: 0px;
                }
            """ % (self.sort_column + 1)) 

    def on_search(self):
        search_text = self.search_input.text().strip()
        self.load_file_list(search_data=search_text)

    def on_clear_search(self):
        self.search_input.clear()
        self.load_file_list() 

    def on_refresh(self):
        self.load_file_list() 

    def format_size(self, size):
        if not size:
            return '-'
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024:
                return f"{size:.2f} {unit}"
            size /= 1024
        return f"{size:.2f} PB" 

    def on_upload_file(self):
        from gui.upload_dialog import UploadDialog
        # 找到主窗口
        main_win = self.parent()
        while main_win and not hasattr(main_win, 'upload_manager'):
            main_win = main_win.parent()
        upload_manager = main_win.upload_manager if main_win else None
        dlg = UploadDialog(self, upload_manager)
        dlg.exec_() 

 

    def make_flat_btn(self, text, color1, color2, menu=None):
        btn = QToolButton()
        btn.setText(text)
        btn.setPopupMode(QToolButton.MenuButtonPopup if menu else QToolButton.InstantPopup)
        btn.setStyleSheet(f'''
        QToolButton {{
            min-width: 110px; max-width: 140px; min-height: 44px; max-height: 44px;
            font-size: 18px; font-weight: bold;
            color: #fff;
            background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 {color1},stop:1 {color2});
            border: none;
            border-radius: 10px;
            padding-right: 18px;
        }}
        QToolButton::menu-indicator {{
            subcontrol-origin: padding;
            subcontrol-position: right center;
            right: 8px;
            width: 16px;
            height: 16px;
        }}
        QToolButton:hover, QToolButton:pressed {{
            background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 {color2},stop:1 {color1});
        }}
        ''')
        if menu:
            btn.setMenu(menu)
        return btn

    def on_delete_harmony(self):
        from PyQt5.QtWidgets import QMessageBox
        harmony_file_ids = [f.get('fileId') for f in self.file_list if f.get('status', 0) >= 100]
        if not harmony_file_ids:
            QMessageBox.information(self, "提示", "没有需要删除的审核驳回文件")
            return
        reply = QMessageBox.question(self, "确认删除", f"确定要删除所有审核驳回的 {len(harmony_file_ids)} 个文件/文件夹吗？\n删除后可在回收站找回。", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            token = self.get_token_func()
            if not token:
                QMessageBox.warning(self, "提示", "请先登录/选择用户")
                return
            try:
                self.api.move_to_trash(token, harmony_file_ids)
                QMessageBox.information(self, "成功", f"删除成功，已移入回收站！")
                self.load_file_list()
            except Exception as e:
                QMessageBox.critical(self, "错误", f"删除失败: {e}")
    
    def closeEvent(self, event):
        """窗口关闭时清理工作线程"""
        if self.auto_load_worker and self.auto_load_worker.isRunning():
            self.auto_load_worker.stop()
            self.auto_load_worker.wait()
        # 停止定时器
        if self.info_hide_timer.isActive():
            self.info_hide_timer.stop()
        super().closeEvent(event) 