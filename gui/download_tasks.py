import os
import json
import threading
import requests
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget, QTableWidgetItem, QFileDialog, QProgressBar, QMessageBox
from PyQt5.QtWidgets import QHeaderView
from PyQt5.QtCore import Qt, QTimer

# 移除全局TASKS_FILE，改为按用户名动态生成

def get_download_tasks_file(username):
    if username is None:
        return os.path.join(os.path.expanduser('~'), '.oprnapidown_default_download_tasks.json')
    # 简单处理非法文件名字符
    safe_name = ''.join(c if c.isalnum() or c in '-_.' else '_' for c in username)
    return os.path.join(os.path.expanduser('~'), f'.oprnapidown_{safe_name}_download_tasks.json')

def get_download_path_file(username):
    if username is None:
        return os.path.join(os.path.expanduser('~'), '.oprnapidown_default_path.txt')
    safe_name = ''.join(c if c.isalnum() or c in '-_.' else '_' for c in username)
    return os.path.join(os.path.expanduser('~'), f'.oprnapidown_{safe_name}_path.txt')

PATH_FILE = os.path.join(os.path.expanduser('~'), '.oprnapidown_path.txt')

class DownloadTask:
    def __init__(self, file_id, file_name, url, save_path, status='等待中', progress=0):
        self.file_id = file_id
        self.file_name = file_name
        self.url = url
        self.save_path = save_path
        self.status = status
        self.progress = progress
        self.thread = None
        self._stop_flag = False  # 新增中断标志

    def stop(self):
        self._stop_flag = True

    def to_dict(self):
        return {
            'file_id': self.file_id,
            'file_name': self.file_name,
            'url': self.url,
            'save_path': self.save_path,
            'status': self.status,
            'progress': self.progress
        }
    @staticmethod
    def from_dict(d):
        return DownloadTask(d['file_id'], d['file_name'], d['url'], d['save_path'], d.get('status', '等待中'), d.get('progress', 0))

class DownloadTaskManager:
    def __init__(self, username=None):
        self.username = username or 'default'
        self.tasks = self.load_tasks()
        self.download_path = self.load_path()
        self.lock = threading.Lock()

    def set_user(self, username):
        self.username = username
        self.tasks = self.load_tasks()
        self.download_path = self.load_path()
        # 路径可选是否也按用户分，暂保留原逻辑

    def load_tasks(self):
        tasks_file = get_download_tasks_file(self.username)
        if os.path.exists(tasks_file):
            with open(tasks_file, 'r', encoding='utf-8') as f:
                return [DownloadTask.from_dict(t) for t in json.load(f)]
        return []
    def save_tasks(self):
        tasks_file = get_download_tasks_file(self.username)
        with open(tasks_file, 'w', encoding='utf-8') as f:
            json.dump([t.to_dict() for t in self.tasks], f, ensure_ascii=False, indent=2)
    def load_path(self):
        path_file = get_download_path_file(self.username)
        if os.path.exists(path_file):
            with open(path_file, 'r', encoding='utf-8') as f:
                path = f.read().strip()
                if os.path.exists(path):
                    return path
        return ''
    def save_path(self, path):
        path_file = get_download_path_file(self.username)
        with open(path_file, 'w', encoding='utf-8') as f:
            f.write(path)
        self.download_path = path
    def get_download_path(self):
        # 只返回保存的路径，不弹窗
        return self.download_path

    def set_download_path(self, path):
        self.save_path(path)

    def ensure_valid_download_path(self, parent_widget=None):
        # 校验路径是否存在，不存在则弹窗
        import os
        from PyQt5.QtWidgets import QFileDialog, QMessageBox
        if self.download_path and os.path.exists(self.download_path):
            return self.download_path
        path = QFileDialog.getExistingDirectory(parent_widget, "请选择新的下载保存路径", os.path.expanduser('~'))
        if not path:
            QMessageBox.warning(parent_widget, "提示", "未选择下载路径，无法继续操作")
            return ''
        self.set_download_path(path)
        QMessageBox.information(parent_widget, "提示", f"已更新下载路径: {path}")
        return path

    def add_task(self, file_id, file_name, url):
        # 新增任务前校验下载路径
        valid_path = self.ensure_valid_download_path()
        if not valid_path:
            return None
        task = DownloadTask(file_id, file_name, url, valid_path)
        with self.lock:
            self.tasks.append(task)
            self.save_tasks()
        return task
    def get_tasks(self):
        return self.tasks
    def update_task_status(self, file_id, status, progress=None):
        with self.lock:
            for t in self.tasks:
                if t.file_id == file_id:
                    t.status = status
                    if progress is not None:
                        t.progress = progress
            self.save_tasks()
    def start_download(self, task, callback=None):
        def run():
            try:
                local_path = os.path.join(task.save_path, task.file_name)
                with requests.get(task.url, stream=True) as r:
                    r.raise_for_status()
                    total = int(r.headers.get('content-length', 0))
                    with open(local_path, 'wb') as f:
                        downloaded = 0
                        for chunk in r.iter_content(chunk_size=8192):
                            if task._stop_flag:
                                break
                            if chunk:
                                f.write(chunk)
                                downloaded += len(chunk)
                                percent = int(downloaded * 100 / total) if total else 0
                                self.update_task_status(task.file_id, '下载中', percent)
                                if callback:
                                    callback()
                    if task._stop_flag:
                        # 被中断，删除未完成文件
                        if os.path.exists(local_path):
                            try:
                                os.remove(local_path)
                            except Exception:
                                pass
                        self.update_task_status(task.file_id, '已取消', 0)
                    else:
                        self.update_task_status(task.file_id, '已完成', 100)
            except Exception as e:
                self.update_task_status(task.file_id, f'失败: {e}')
                if callback:
                    callback()
        t = threading.Thread(target=run, daemon=True)
        task.thread = t
        t.start()

    def clear_tasks(self):
        with self.lock:
            self.tasks = []
            self.save_tasks()
            # 如果文件为空则物理删除
            tasks_file = get_download_tasks_file(self.username)
            if os.path.exists(tasks_file) and os.path.getsize(tasks_file) < 10:
                os.remove(tasks_file)

    def delete_tasks_file(self):
        tasks_file = get_download_tasks_file(self.username)
        if os.path.exists(tasks_file):
            os.remove(tasks_file)

class DownloadTaskWidget(QWidget):
    def __init__(self, manager: DownloadTaskManager, parent=None):
        super().__init__(parent)
        self.manager = manager
        self.init_ui()
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh_table)
        self.refresh_timer.start(1500)

    def init_ui(self):
        layout = QVBoxLayout()
        path_layout = QHBoxLayout()
        self.path_label = QLabel(f"下载路径: {self.manager.get_download_path() or '未设置'}")
        self.set_path_btn = QPushButton("设置下载路径")
        self.set_path_btn.setStyleSheet('QPushButton{min-width:80px;max-width:120px;min-height:28px;max-height:36px;font-size:15px;}')
        self.set_path_btn.clicked.connect(self.on_set_path)
        path_layout.addWidget(self.path_label)
        path_layout.addWidget(self.set_path_btn)
        # 新增“清空”按钮
        self.clear_btn = QPushButton("清空")
        self.clear_btn.setStyleSheet('QPushButton{min-width:60px;max-width:90px;min-height:26px;max-height:32px;font-size:14px;background:#FF7875;color:#fff;border-radius:8px;} QPushButton:hover{background:#FF4D4F;}')
        self.clear_btn.clicked.connect(self.on_clear_tasks)
        path_layout.addWidget(self.clear_btn)
        # 新增“删除任务”按钮
        self.delete_btn = QPushButton("删除任务")
        self.delete_btn.setStyleSheet('QPushButton{min-width:60px;max-width:90px;min-height:26px;max-height:32px;font-size:14px;background:#FF7875;color:#fff;border-radius:8px;} QPushButton:hover{background:#FF4D4F;}')
        self.delete_btn.clicked.connect(self.on_delete_task)
        path_layout.addWidget(self.delete_btn)
        path_layout.addStretch()
        layout.addLayout(path_layout)
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["文件名", "状态", "进度", "保存路径"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.verticalHeader().setDefaultSectionSize(36)
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
        layout.addWidget(self.table)
        # 新增“打开文件夹”按钮，放在设置下载路径右侧
        self.open_folder_btn = QPushButton("打开文件夹")
        self.open_folder_btn.setStyleSheet('''
QPushButton {
    min-width: 80px; max-width: 120px; min-height: 28px; max-height: 36px;
    font-size: 15px;
    border-radius: 8px;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #165DFF, stop:1 #0FC6C2);
    color: #fff;
    font-weight: bold;
}
QPushButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0E4FE1, stop:1 #0FC6C2);
}
''')
        self.open_folder_btn.clicked.connect(self.open_download_folder)
        path_layout.addWidget(self.open_folder_btn)
        self.setLayout(layout)
        self.refresh_table()

    def on_set_path(self):
        path = QFileDialog.getExistingDirectory(self, "选择下载保存路径", self.manager.get_download_path() or os.path.expanduser('~'))
        if path:
            self.manager.set_download_path(path)
            self.path_label.setText(f"下载路径: {path}")

    def refresh_table(self):
        tasks = self.manager.get_tasks()
        self.table.setRowCount(len(tasks))
        for row, t in enumerate(tasks):
            self.table.setItem(row, 0, QTableWidgetItem(t.file_name))
            self.table.setItem(row, 1, QTableWidgetItem(t.status))
            bar = QProgressBar()
            bar.setValue(t.progress)
            bar.setFormat(f"{t.progress}%")
            bar.setStyleSheet('''
QProgressBar {
    border: 1px solid #d0d7de;
    border-radius: 8px;
    text-align: center;
    height: 22px;
    background: #fafdff;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #13C2C2, stop:1 #165DFF);
    border-radius: 8px;
}
''')
            self.table.setCellWidget(row, 2, bar)
            self.table.setItem(row, 3, QTableWidgetItem(t.save_path))
    def open_folder(self, path):
        if os.path.exists(path):
            import subprocess
            if os.name == 'nt':
                os.startfile(path)
            elif os.name == 'posix':
                subprocess.Popen(['xdg-open', path])
        else:
            QMessageBox.warning(self, "提示", "文件夹不存在")
    def open_download_folder(self):
        path = self.manager.get_download_path()
        self.open_folder(path)

    def on_clear_tasks(self):
        from PyQt5.QtWidgets import QMessageBox
        reply = QMessageBox.question(self, "确认清空", "确定要清空所有下载任务吗？", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.manager.clear_tasks()
            self.refresh_table()

    def on_delete_task(self):
        from PyQt5.QtWidgets import QMessageBox
        selected = self.table.selectedItems()
        if not selected:
            QMessageBox.warning(self, "提示", "请先选择要删除的下载任务")
            return
        selected_rows = list(set([item.row() for item in selected]))
        if not selected_rows:
            QMessageBox.warning(self, "提示", "请先选择要删除的下载任务")
            return
        reply = QMessageBox.question(self, "确认删除", f"确定要删除选中的 {len(selected_rows)} 个下载任务吗？\n正在下载的任务将被终止，未完成的文件会被删除。", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            tasks = self.manager.get_tasks()
            for i in sorted(selected_rows, reverse=True):
                t = tasks[i]
                # 终止线程
                t.stop()
                # 等待线程结束（如果在下载中）
                if t.thread and t.thread.is_alive():
                    t.thread.join(timeout=2)
                # 删除未完成文件
                if t.status != '已完成':
                    local_path = os.path.join(t.save_path, t.file_name)
                    if os.path.exists(local_path):
                        try:
                            os.remove(local_path)
                        except Exception:
                            pass
                del tasks[i]
            self.manager.save_tasks()
            self.refresh_table()

def get_offline_tasks_file(username):
    if username is None:
        return os.path.join(os.path.expanduser('~'), '.oprnapidown_default_offline_tasks.json')
    safe_name = ''.join(c if c.isalnum() or c in '-_.' else '_' for c in username)
    return os.path.join(os.path.expanduser('~'), f'.oprnapidown_{safe_name}_offline_tasks.json')

class OfflineTask:
    def __init__(self, task_id, file_name, url, status='等待中', progress=0):
        self.task_id = task_id
        self.file_name = file_name
        self.url = url
        self.status = status
        self.progress = progress
    def to_dict(self):
        return {
            'task_id': self.task_id,
            'file_name': self.file_name,
            'url': self.url,
            'status': self.status,
            'progress': self.progress
        }
    @staticmethod
    def from_dict(d):
        return OfflineTask(d['task_id'], d.get('file_name', ''), d.get('url', ''), d.get('status', '等待中'), d.get('progress', 0))

class OfflineTaskManager:
    def __init__(self, username=None):
        self.username = username or 'default'
        self.tasks = self.load_tasks()
        self.lock = threading.Lock()
    def set_user(self, username):
        self.username = username
        self.tasks = self.load_tasks()
    def load_tasks(self):
        tasks_file = get_offline_tasks_file(self.username)
        if os.path.exists(tasks_file):
            with open(tasks_file, 'r', encoding='utf-8') as f:
                return [OfflineTask.from_dict(t) for t in json.load(f)]
        return []
    def save_tasks(self):
        tasks_file = get_offline_tasks_file(self.username)
        with open(tasks_file, 'w', encoding='utf-8') as f:
            json.dump([t.to_dict() for t in self.tasks], f, ensure_ascii=False, indent=2)
    def add_task(self, task_id, file_name, url):
        task = OfflineTask(task_id, file_name, url)
        with self.lock:
            self.tasks.append(task)
            self.save_tasks()
        return task
    def get_tasks(self):
        return self.tasks
    def clear_tasks(self):
        with self.lock:
            self.tasks = []
            self.save_tasks()
            tasks_file = get_offline_tasks_file(self.username)
            if os.path.exists(tasks_file) and os.path.getsize(tasks_file) < 10:
                os.remove(tasks_file)
    def delete_tasks_file(self):
        tasks_file = get_offline_tasks_file(self.username)
        if os.path.exists(tasks_file):
            os.remove(tasks_file) 