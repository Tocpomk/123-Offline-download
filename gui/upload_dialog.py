# 上传文件对话框
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QPushButton, QLabel, QFileDialog, QListWidget, QListWidgetItem, QMessageBox
from gui.upload_manager import UploadManager
import os

class UploadDialog(QDialog):
    def __init__(self, parent=None, upload_manager=None):
        super().__init__(parent)
        self.setWindowTitle("文件上传")
        self.resize(320, 200)
        self.manager = upload_manager if upload_manager else UploadManager()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        self.select_files_btn = QPushButton("选择文件")
        self.select_files_btn.clicked.connect(self.select_files)
        layout.addWidget(self.select_files_btn)
        self.select_folder_btn = QPushButton("选择文件夹")
        self.select_folder_btn.clicked.connect(self.select_folder)
        layout.addWidget(self.select_folder_btn)
        self.file_list = QListWidget()
        layout.addWidget(self.file_list)
        self.setLayout(layout)
        self.selected_files = []

    def select_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "选择上传文件")
        if files:
            self.selected_files = files
            self.update_file_list()
            self.finish_and_add_tasks()

    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "选择上传文件夹")
        if folder:
            # 记录顶层文件夹名
            top_folder_name = os.path.basename(folder.rstrip(os.sep))
            all_files = []
            for root, _, filenames in os.walk(folder):
                for fname in filenames:
                    abs_path = os.path.join(root, fname)
                    rel_path = os.path.relpath(abs_path, folder)
                    all_files.append((abs_path, rel_path, top_folder_name))
            self.selected_files = all_files
            self.selected_folder = folder
            self.top_folder_name = top_folder_name
            self.update_file_list()
            self.finish_and_add_tasks()

    def update_file_list(self):
        self.file_list.clear()
        for f in self.selected_files:
            if isinstance(f, tuple):
                # 显示顶层目录/相对路径
                item = QListWidgetItem(os.path.join(f[2], f[1]))
            else:
                item = QListWidgetItem(f)
            self.file_list.addItem(item)

    def finish_and_add_tasks(self):
        parent_id = 0
        if self.parent() and hasattr(self.parent(), 'current_parent_id'):
            parent_id = getattr(self.parent(), 'current_parent_id', 0)
        if self.selected_files and isinstance(self.selected_files[0], tuple):
            from core.file_api import FileApi
            token = None
            if self.parent() and hasattr(self.parent(), 'get_token_func'):
                token = self.parent().get_token_func() if callable(self.parent().get_token_func) else self.parent().get_token_func
            if not token:
                QMessageBox.warning(self, "错误", "未获取到token，无法上传")
                return
            file_api = FileApi()
            # 先在网盘端创建顶层目录
            try:
                top_dir_id = file_api.create_directory(token, self.top_folder_name, parent_id)
            except Exception as e:
                QMessageBox.warning(self, "创建顶层目录失败", f"{self.top_folder_name}: {e}")
                return
            dir_cache = {"": top_dir_id}  # 相对路径->网盘目录ID
            for abs_path, rel_path, _ in self.selected_files:
                rel_dir = os.path.dirname(rel_path)
                # 递归创建目录（即使是第一级目录也要创建）
                if rel_dir not in dir_cache:
                    parts = rel_dir.split(os.sep) if rel_dir else []
                    cur_path = ""
                    cur_id = top_dir_id
                    for part in parts:
                        if not part:
                            continue
                        cur_path = os.path.join(cur_path, part) if cur_path else part
                        if cur_path not in dir_cache:
                            try:
                                new_id = file_api.create_directory(token, part, cur_id)
                            except Exception as e:
                                QMessageBox.warning(self, "创建目录失败", f"{cur_path}: {e}")
                                return
                            dir_cache[cur_path] = new_id
                            cur_id = new_id
                        else:
                            cur_id = dir_cache[cur_path]
                    dir_cache[rel_dir] = cur_id
                self.manager.add_task(abs_path, dir_cache[rel_dir])
        else:
            for file_path in self.selected_files:
                self.manager.add_task(file_path, parent_id)
        self.accept() 