from PyQt5.QtCore import QThread, pyqtSignal
from core.file_api import FileApi
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
                # 跳过新文件名与原文件名相同的情况
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

class FolderDownloadWorker(QThread):
    progress = pyqtSignal(int, int)  # 当前文件索引，总文件数
    finished = pyqtSignal(int, int)  # 成功，失败
    error = pyqtSignal(str)  # 错误信息
    
    def __init__(self, api, token, folder_id, folder_name, download_path, download_manager, parent=None):
        super().__init__(parent)
        self.api = api
        self.token = token
        self.folder_id = folder_id
        self.folder_name = folder_name
        self.download_path = download_path
        self.download_manager = download_manager
        self._is_running = True
    
    def run(self):
        try:
            # 创建目标文件夹
            target_folder = self.create_target_folder()
            if not target_folder:
                self.error.emit("无法创建目标文件夹")
                return
            
            # 获取文件夹中的所有文件
            all_files = self.get_all_files_in_folder()
            if not all_files:
                self.finished.emit(0, 0)
                return
            
            # 为每个文件创建下载任务
            success_count = 0
            fail_count = 0
            
            for i, file_info in enumerate(all_files):
                if not self._is_running:
                    break
                
                try:
                    # 获取下载链接
                    url = self.api.get_download_url(self.token, file_info['fileId'])
                    
                    # 创建下载任务，使用原始文件名
                    task = self.download_manager.add_task(file_info['fileId'], file_info['filename'], url)
                    
                    if task:
                        # 修改任务的保存路径，指向我们创建的文件夹
                        task.save_path = target_folder
                        # 启动下载任务
                        self.download_manager.start_download(task)
                        success_count += 1
                    else:
                        fail_count += 1
                    
                except Exception as e:
                    fail_count += 1
                    print(f"创建下载任务失败 {file_info['filename']}: {e}")
                
                self.progress.emit(i + 1, len(all_files))
            
            self.finished.emit(success_count, fail_count)
            
        except Exception as e:
            self.error.emit(str(e))
    
    def create_target_folder(self):
        """创建目标文件夹，如果存在则添加序号"""
        base_name = self.folder_name
        counter = 1
        target_path = os.path.join(self.download_path, base_name)
        
        while os.path.exists(target_path):
            target_path = os.path.join(self.download_path, f"{base_name}_{counter}")
            counter += 1
        
        try:
            os.makedirs(target_path, exist_ok=True)
            return target_path
        except Exception as e:
            print(f"创建文件夹失败: {e}")
            return None
    
    def get_all_files_in_folder(self):
        """递归获取文件夹中的所有文件"""
        all_files = []
        self._collect_files_recursive(self.folder_id, all_files)
        return all_files
    
    def _collect_files_recursive(self, folder_id, file_list):
        """递归收集文件"""
        if not self._is_running:
            return
        
        try:
            resp = self.api.get_file_list(self.token, parent_file_id=folder_id, limit=100)
            data = resp.get("data", {})
            file_list_data = [f for f in data.get("fileList", []) if f.get('trashed', 0) == 0]
            
            for file_info in file_list_data:
                if not self._is_running:
                    return
                
                if file_info.get('type') == 0:  # 文件
                    file_list.append(file_info)
                elif file_info.get('type') == 1:  # 文件夹
                    # 递归处理子文件夹
                    self._collect_files_recursive(file_info['fileId'], file_list)
                    
        except Exception as e:
            print(f"获取文件夹内容失败: {e}")
    
    def stop(self):
        self._is_running = False 