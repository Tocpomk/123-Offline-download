from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, QPushButton, QLineEdit, QLabel, QHeaderView, QAbstractItemView, QMessageBox, QMenu, QAction
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QIcon
from core.file_api import FileApi
import os

class RecycleBinWorker(QThread):
    """回收站文件加载工作线程"""
    progress = pyqtSignal(int)  # 已加载文件数量
    finished = pyqtSignal(list)  # 完整的文件列表
    error = pyqtSignal(str)  # 错误信息
    
    def __init__(self, api, token, page_size, parent=None):
        super().__init__(parent)
        self.api = api
        self.token = token
        self.page_size = page_size
        self._is_running = True
    
    def run(self):
        """使用v1 API获取回收站文件"""
        all_files = []
        page = 1
        has_more = True
        while self._is_running and has_more:
            try:
                resp = self.api.get_trash_files(
                    self.token,
                    page=page,
                    limit=self.page_size
                )
                if resp is None:
                    self.error.emit("API响应为空")
                    return
                if resp.get("code") != 0:
                    error_msg = resp.get("message", "未知错误")
                    self.error.emit(f"API错误: {error_msg}")
                    return
            except Exception as e:
                self.error.emit(str(e))
                return
            data = resp.get("data", {})
            file_list = data.get("fileList", [])
            if not file_list:
                break
            for file_info in file_list:
                if 'fileID' in file_info and 'fileId' not in file_info:
                    file_info['fileId'] = file_info['fileID']
            all_files.extend(file_list)
            self.progress.emit(len(all_files))
            total_page = data.get("totalPage", 0)
            total = data.get("total", 0)
            if total_page > 0 and page >= total_page:
                has_more = False
            elif total > 0 and len(all_files) >= total:
                has_more = False
            elif len(file_list) < self.page_size:
                has_more = False
            else:
                page += 1
        # 加上 finished 信号发射，通知主线程加载完成
        self.finished.emit(all_files)

    
    def stop(self):
        self._is_running = False

class RecycleBinPage(QWidget):
    def __init__(self, get_token_func, parent=None):
        super().__init__(parent)
        self.get_token_func = get_token_func
        self.api = FileApi()
        self.file_list = []
        self.page_size = 100
        self.total = 0
        # 自动加载工作线程
        self.auto_load_worker = None
        # 信息标签隐藏定时器
        self.info_hide_timer = QTimer()
        self.info_hide_timer.setSingleShot(True)
        self.info_hide_timer.timeout.connect(self.hide_info_label)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)
        
        # 顶部工具栏
        toolbar_layout = QHBoxLayout()
        
        # 刷新按钮
        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.setMinimumWidth(80)
        self.refresh_btn.setMinimumHeight(36)
        self.refresh_btn.setStyleSheet("""
            QPushButton {
                font-weight: bold;
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #165DFF,stop:1 #0FC6C2);
                color: #fff;
                border: none;
                border-radius: 8px;
                font-size: 14px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #0E4FE1,stop:1 #0FC6C2);
            }
        """)
        self.refresh_btn.clicked.connect(self.load_recycle_bin)
        toolbar_layout.addWidget(self.refresh_btn)
        

        
        # 搜索框
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("搜索文件...")
        self.search_edit.setMinimumHeight(36)
        self.search_edit.setStyleSheet("""
            QLineEdit {
                border: 2px solid #e1e5e9;
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 14px;
                background: #fff;
            }
            QLineEdit:focus {
                border-color: #165DFF;
            }
        """)
        self.search_edit.textChanged.connect(self.on_search_changed)
        toolbar_layout.addWidget(self.search_edit)
        
        # 恢复按钮
        self.recover_btn = QPushButton("恢复选中")
        self.recover_btn.setMinimumWidth(100)
        self.recover_btn.setMinimumHeight(36)
        self.recover_btn.setStyleSheet("""
            QPushButton {
                font-weight: bold;
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #52C41A,stop:1 #73D13D);
                color: #fff;
                border: none;
                border-radius: 8px;
                font-size: 14px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #389E0D,stop:1 #52C41A);
            }
            QPushButton:disabled {
                background: #d9d9d9;
                color: #999;
            }
        """)
        self.recover_btn.clicked.connect(self.recover_selected_files)
        self.recover_btn.setEnabled(False)
        toolbar_layout.addWidget(self.recover_btn)
        
        # 永久删除按钮
        self.delete_btn = QPushButton("永久删除")
        self.delete_btn.setMinimumWidth(100)
        self.delete_btn.setMinimumHeight(36)
        self.delete_btn.setStyleSheet("""
            QPushButton {
                font-weight: bold;
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #FF4D4F,stop:1 #FF7875);
                color: #fff;
                border: none;
                border-radius: 8px;
                font-size: 14px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #D9363E,stop:1 #FF4D4F);
            }
            QPushButton:disabled {
                background: #d9d9d9;
                color: #999;
            }
        """)
        self.delete_btn.clicked.connect(self.delete_selected_files)
        self.delete_btn.setEnabled(False)
        toolbar_layout.addWidget(self.delete_btn)
        
        # 全选按钮
        self.select_all_btn = QPushButton("全选")
        self.select_all_btn.setMinimumWidth(80)
        self.select_all_btn.setMinimumHeight(36)
        self.select_all_btn.setStyleSheet("""
            QPushButton {
                font-weight: bold;
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #722ED1,stop:1 #9254DE);
                color: #fff;
                border: none;
                border-radius: 8px;
                font-size: 14px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #531DAB,stop:1 #722ED1);
            }
        """)
        self.select_all_btn.clicked.connect(self.select_all_files)
        toolbar_layout.addWidget(self.select_all_btn)
        
        toolbar_layout.addStretch()
        layout.addLayout(toolbar_layout)

        # 文件表格
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["文件名", "大小", "类型", "删除时间"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.verticalHeader().setDefaultSectionSize(40)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.MultiSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        # 美化表格：斑马纹、圆角、悬浮高亮、表头加深、边框阴影
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet("""
            QTableWidget {
                border: 2px solid #e1e5e9;
                border-radius: 12px;
                background: #fff;
                gridline-color: #f0f0f0;
                font-size: 15px;
                alternate-background-color: #f6f8fa;
                selection-background-color: #e6f7ff;
                selection-color: #165DFF;
            }
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid #f0f0f0;
                border-radius: 6px;
            }
            QTableWidget::item:hover {
                background: #f0f5ff;
            }
            QTableWidget::item:selected {
                background: #e6f7ff;
                color: #165DFF;
            }
            QHeaderView::section {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #e9ecef, stop:1 #d6e4ff);
                color: #222;
                font-weight: bold;
                padding: 14px 8px;
                border: none;
                border-bottom: 2px solid #b7c5e0;
                font-size: 16px;
                border-radius: 8px 8px 0 0;
            }
            QTableCornerButton::section {
                background: #e9ecef;
                border-radius: 8px 0 0 0;
            }
        """)
        self.table.itemSelectionChanged.connect(self.on_selection_changed)
        layout.addWidget(self.table)

        # 信息标签（移动到表格下方）
        self.info_label = QLabel()
        self.info_label.setWordWrap(False)  # 禁用自动换行，保持一行显示
        self.info_label.setMaximumHeight(40)  # 限制最大高度
        self.info_label.setMinimumWidth(400)  # 设置最小宽度，确保有足够空间显示
        self.info_label.setStyleSheet("""
            QLabel {
                color: #165DFF;
                font-size: 14px;
                padding: 8px 12px;
                background: #e6f7ff;
                border-radius: 6px;
                border: 1px solid #91d5ff;
                max-width: none;
            }
        """)
        self.info_label.setVisible(False)
        layout.addWidget(self.info_label)

        # 加载回收站文件
        self.load_recycle_bin()
    
    def load_recycle_bin(self):
        """加载回收站文件"""
        token = self.get_token_func()
        if not token:
            self.info_label.setText("请先选择用户")
            self.info_label.setVisible(True)
            return
        
        # 如果已有工作线程在运行，先停止它
        if self.auto_load_worker and self.auto_load_worker.isRunning():
            self.auto_load_worker.stop()
            self.auto_load_worker.wait()
        
        # 创建新的工作线程
        self.auto_load_worker = RecycleBinWorker(self.api, token, self.page_size, self)
        self.auto_load_worker.progress.connect(self.on_auto_load_progress)
        self.auto_load_worker.finished.connect(self.on_auto_load_finished)
        self.auto_load_worker.error.connect(self.on_auto_load_error)
        
        # 更新UI状态
        self.info_label.setText("正在加载回收站文件...")
        self.info_label.setVisible(True)
        
        # 启动工作线程
        self.auto_load_worker.start()
    
    def on_auto_load_progress(self, count):
        """自动加载进度更新"""
        self.info_label.setText(f"已加载{count}个文件...")
    
    def on_auto_load_finished(self, file_list):
        """自动加载完成"""
        self.file_list = file_list
        self.total = len(file_list)
        self.refresh_table()
        self.info_label.setText(f"已加载全部文件，共{self.total}个")
        self.info_label.setVisible(True)
        
        # 1秒后自动隐藏信息标签
        self.info_hide_timer.start(1000)
        
        # 清理工作线程
        if self.auto_load_worker:
            self.auto_load_worker.deleteLater()
            self.auto_load_worker = None
    
    def on_auto_load_error(self, error_msg):
        """自动加载出错"""
        # 简化错误信息，确保在一行内显示
        if "HTTPSConnectionPool" in error_msg:
            simplified_error = "网络连接失败，请检查网络连接后重试"
        elif "Max retries exceeded" in error_msg:
            simplified_error = "请求超时，请稍后重试"
        elif "API错误" in error_msg:
            # 截断API错误信息
            api_msg = error_msg.replace("API错误: ", "")
            if len(api_msg) > 40:
                simplified_error = f"API错误: {api_msg[:40]}..."
            else:
                simplified_error = error_msg
        else:
            # 截断过长的错误信息
            if len(error_msg) > 60:
                simplified_error = error_msg[:60] + "..."
            else:
                simplified_error = error_msg
        
        self.info_label.setText(f"获取失败：{simplified_error}")
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
        self.table.setRowCount(len(self.file_list))
        
        for row, file_info in enumerate(self.file_list):
            # 文件名
            filename_item = QTableWidgetItem(file_info.get('filename', ''))
            self.table.setItem(row, 0, filename_item)
            
            # 文件大小
            size = file_info.get('size', 0)
            if file_info.get('type') == 1:  # 文件夹
                size_text = "文件夹"
            else:
                size_text = self.format_size(size)
            size_item = QTableWidgetItem(size_text)
            self.table.setItem(row, 1, size_item)
            
            # 文件类型
            file_type = "文件夹" if file_info.get('type') == 1 else "文件"
            type_item = QTableWidgetItem(file_type)
            self.table.setItem(row, 2, type_item)
            
            # 删除时间
            create_time = file_info.get('createAt', '')
            # 处理时间格式，去掉后面的时区信息
            if ' +' in create_time:
                create_time = create_time.split(' +')[0]
            time_item = QTableWidgetItem(create_time)
            self.table.setItem(row, 3, time_item)
            
        # ...不再输出调试信息...
    
    def format_size(self, size_bytes):
        """格式化文件大小"""
        if size_bytes == 0:
            return "0 B"
        size_names = ["B", "KB", "MB", "GB", "TB"]
        i = 0
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024.0
            i += 1
        return f"{size_bytes:.1f} {size_names[i]}"
    
    def on_selection_changed(self):
        """选择变化时更新按钮状态"""
        selected_rows = set(item.row() for item in self.table.selectedItems())
        has_selection = len(selected_rows) > 0
        self.recover_btn.setEnabled(has_selection)
        self.delete_btn.setEnabled(has_selection)
    
    def select_all_files(self):
        """全选所有文件"""
        self.table.selectAll()
    
    def on_search_changed(self):
        """搜索文本变化时过滤文件"""
        search_text = self.search_edit.text().lower()
        if not search_text:
            self.refresh_table()
            return
        
        # 从原始文件列表中过滤
        filtered_files = [f for f in self.file_list if search_text in f.get('filename', '').lower()]
        
        self.table.setRowCount(len(filtered_files))
        for row, file_info in enumerate(filtered_files):
            # 文件名
            filename_item = QTableWidgetItem(file_info.get('filename', ''))
            self.table.setItem(row, 0, filename_item)
            
            # 文件大小
            size = file_info.get('size', 0)
            if file_info.get('type') == 1:  # 文件夹
                size_text = "文件夹"
            else:
                size_text = self.format_size(size)
            size_item = QTableWidgetItem(size_text)
            self.table.setItem(row, 1, size_item)
            
            # 文件类型
            file_type = "文件夹" if file_info.get('type') == 1 else "文件"
            type_item = QTableWidgetItem(file_type)
            self.table.setItem(row, 2, type_item)
            
            # 删除时间
            create_time = file_info.get('createAt', '')
            time_item = QTableWidgetItem(create_time)
            self.table.setItem(row, 3, time_item)
    
    def get_selected_file_ids(self):
        """获取选中的文件ID列表"""
        selected_rows = set(item.row() for item in self.table.selectedItems())
        file_ids = []
        for row in selected_rows:
            if row < len(self.file_list):
                # 检查 fileID 或 fileId 字段
                file_id = self.file_list[row].get('fileId') or self.file_list[row].get('fileID')
                if file_id:
                    file_ids.append(file_id)
                # else: 缺少ID字段时不做任何处理
        return file_ids
    
    def recover_selected_files(self):
        """恢复选中的文件"""
        file_ids = self.get_selected_file_ids()
        if not file_ids:
            QMessageBox.warning(self, "提示", "请先选择要恢复的文件")
            return
        
        reply = QMessageBox.question(self, "确认恢复", f"确定要恢复选中的{len(file_ids)}个文件吗？", 
                                   QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.recover_files(file_ids)
    
    def delete_selected_files(self):
        """永久删除选中的文件"""
        file_ids = self.get_selected_file_ids()
        if not file_ids:
            QMessageBox.warning(self, "提示", "请先选择要删除的文件")
            return
        
        reply = QMessageBox.question(self, "确认删除", f"确定要永久删除选中的{len(file_ids)}个文件吗？\n此操作不可撤销！", 
                                   QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.delete_files(file_ids)
    
    def recover_single_file(self, file_id):
        """恢复单个文件"""
        reply = QMessageBox.question(self, "确认恢复", "确定要恢复这个文件吗？", 
                                   QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.recover_files([file_id])
    
    def delete_single_file(self, file_id):
        """删除单个文件"""
        reply = QMessageBox.question(self, "确认删除", "确定要永久删除这个文件吗？\n此操作不可撤销！", 
                                   QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.delete_files([file_id])
    
    def recover_files(self, file_ids):
        """恢复文件"""
        token = self.get_token_func()
        if not token:
            QMessageBox.warning(self, "错误", "请先选择用户")
            return
        
        try:
            # 分批处理，每批最多100个
            batch_size = 100
            for i in range(0, len(file_ids), batch_size):
                batch = file_ids[i:i + batch_size]
                self.api.recover_file(token, batch)
            
            QMessageBox.information(self, "成功", f"已成功恢复{len(file_ids)}个文件")
            self.load_recycle_bin()  # 重新加载列表
        except Exception as e:
            # 简化错误信息
            error_msg = str(e)
            if len(error_msg) > 100:
                error_msg = error_msg[:100] + "..."
            QMessageBox.critical(self, "错误", f"恢复文件失败：{error_msg}")
    
    def delete_files(self, file_ids):
        """永久删除文件"""
        token = self.get_token_func()
        if not token:
            QMessageBox.warning(self, "错误", "请先选择用户")
            return
        
        try:
            # 分批处理，每批最多100个
            batch_size = 100
            for i in range(0, len(file_ids), batch_size):
                batch = file_ids[i:i + batch_size]
                self.api.delete_file_permanently(token, batch)
            
            QMessageBox.information(self, "成功", f"已成功删除{len(file_ids)}个文件")
            self.load_recycle_bin()  # 重新加载列表
        except Exception as e:
            # 简化错误信息
            error_msg = str(e)
            if len(error_msg) > 100:
                error_msg = error_msg[:100] + "..."
            QMessageBox.critical(self, "错误", f"删除文件失败：{error_msg}")
    
    def closeEvent(self, event):
        """关闭事件"""
        # 停止工作线程
        if self.auto_load_worker and self.auto_load_worker.isRunning():
            self.auto_load_worker.stop()
            self.auto_load_worker.wait()
        # 停止定时器
        if self.info_hide_timer.isActive():
            self.info_hide_timer.stop()
        super().closeEvent(event)
    
    def clear_data(self):
        """清除数据（用户退出时调用）"""
        # 停止工作线程
        if self.auto_load_worker and self.auto_load_worker.isRunning():
            self.auto_load_worker.stop()
            self.auto_load_worker.wait()
        # 停止定时器
        if self.info_hide_timer.isActive():
            self.info_hide_timer.stop()
        # 清除数据
        self.file_list = []
        self.total = 0
        self.table.setRowCount(0)
        self.info_label.setVisible(False) 