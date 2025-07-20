# 上传任务管理器
from core.upload_api import UploadApi
import threading
import time

class UploadTask:
    def __init__(self, file_path, parent_id=0):
        self.file_path = file_path
        self.parent_id = parent_id
        self.file_name = None
        self.file_size = 0
        self.file_md5 = None
        self.slice_size = 0
        self.slices = []  # [(index, data, md5)]
        self.preupload_id = None
        self.servers = []
        self.progress = 0  # 0-100
        self.status = '待上传'  # 待上传/上传中/已完成/失败
        self.completed = False
        self.file_id = None
        self.error = ''
        self.thread = None

class UploadManager:
    def __init__(self):
        self.api = UploadApi()
        self.tasks = []

    def add_task(self, file_path, parent_id=0):
        task = UploadTask(file_path, parent_id)
        self.tasks.append(task)
        return task

    def start_upload(self, task, token, progress_callback=None, status_callback=None):
        """启动单个上传任务，支持进度和状态回调"""
        def run():
            import os
            try:
                task.status = '校验中...'
                task.error = ''
                task.progress = 0
                if status_callback:
                    status_callback(task)
                if progress_callback:
                    progress_callback(task)
                # 1. 计算MD5
                from core.utils import calc_file_md5, split_file, calc_bytes_md5
                task.file_name = os.path.basename(task.file_path)
                task.file_size = os.path.getsize(task.file_path)
                task.file_md5 = calc_file_md5(task.file_path)
                # 校验完成，进度设为5%
                task.progress = 5
                if status_callback:
                    status_callback(task)
                if progress_callback:
                    progress_callback(task)
                # 2. 创建文件
                resp = self.api.create_file(token, task.file_name, task.file_size, task.file_md5, parent_file_id=task.parent_id)
                if resp["code"] != 0:
                    task.status = '失败'
                    task.error = resp.get('message', '创建文件失败')
                    if status_callback:
                        status_callback(task)
                    return
                data = resp["data"]
                if data.get("reuse"):
                    task.status = '已完成'
                    task.progress = 100
                    task.completed = True
                    if progress_callback:
                        progress_callback(task)
                    if status_callback:
                        status_callback(task)
                    return
                task.slice_size = data["sliceSize"]
                task.preupload_id = data["preuploadID"]
                task.servers = data["servers"]
                # 校验通过，进入上传中
                task.status = '上传中...'
                task.error = ''
                if status_callback:
                    status_callback(task)
                # 3. 分片切割
                slices = split_file(task.file_path, task.slice_size)
                total = len(slices)
                # 4. 逐片上传
                last_reported = 5
                for idx, chunk in slices:
                    slice_md5 = calc_bytes_md5(chunk)
                    upload_resp = self.api.upload_slice(token, task.preupload_id, idx, chunk, slice_md5, task.servers[0])
                    if upload_resp["code"] != 0:
                        task.status = '失败'
                        task.error = upload_resp.get('message', '分片上传失败')
                        if status_callback:
                            status_callback(task)
                        return
                    # 进度从5%~100%
                    progress = 5 + (idx + 1) / total * 95
                    if int(progress) // 5 > last_reported // 5 or progress >= 100:
                        task.progress = round(progress, 1)
                        last_reported = int(progress)
                        if progress_callback:
                            progress_callback(task)
                # 5. 上传完毕，轮询直到completed为true
                max_retry = 60
                retry = 0
                fake_progress = 90
                while retry < max_retry:
                    complete_resp = self.api.complete_upload(token, task.preupload_id)
                    if complete_resp["code"] == 0:
                        completed = complete_resp["data"].get("completed")
                        file_id = complete_resp["data"].get("fileID", 0)
                        if completed and file_id:
                            task.status = '已完成'
                            task.progress = 100
                            task.completed = True
                            task.file_id = file_id
                            break
                        elif not completed:
                            task.status = '校验中...'
                            task.error = '文件正在校验中, 请间隔1秒后再试'
                            # 校验中进度条递增到99%
                            if fake_progress < 99:
                                fake_progress += 1
                            task.progress = fake_progress
                            if status_callback:
                                status_callback(task)
                            time.sleep(1)
                            retry += 1
                            continue
                    # 失败或超时
                    task.status = '失败'
                    task.error = complete_resp.get('message', '上传完毕未完成')
                    break
                if progress_callback:
                    progress_callback(task)
                if status_callback:
                    status_callback(task)
            except Exception as e:
                task.status = '失败'
                task.error = str(e)
                if status_callback:
                    status_callback(task)
        task.thread = threading.Thread(target=run)
        task.thread.start()

    def start_all_uploads(self, token, progress_callback=None, status_callback=None):
        for task in self.tasks:
            if task.status == '待上传':
                self.start_upload(task, token, progress_callback, status_callback)

    def pause_upload(self, task):
        pass

    def resume_upload(self, task):
        pass

    def cancel_upload(self, task):
        pass 