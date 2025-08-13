from PyQt5.QtWidgets import QMessageBox, QDialog, QFileDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QScrollArea, QWidget, QApplication
from PyQt5.QtCore import QTimer
from gui.file_list_workers import BatchRenameWorker, FolderDownloadWorker
from gui.file_list_dialogs import ProgressDialog, RenameDialog, MultiRenameDialog
# from gui.batch_rename import BatchRenameDialog as AdvancedBatchRenameDialog
from gui.move_folder_dialog import MoveFolderDialog
from core.file_api import FileApi
import os

class FileOperations:
    """文件操作相关方法"""
    
    def __init__(self, file_list_page):
        self.file_list_page = file_list_page
        self.api = file_list_page.api
        self.get_token_func = file_list_page.get_token_func
    
    def on_create_dir(self):
        """创建目录"""
        from PyQt5.QtWidgets import QInputDialog
        dir_name, ok = QInputDialog.getText(self.file_list_page, "创建目录", "请输入新目录名称：")
        if ok and dir_name.strip():
            token = self.get_token_func()
            if not token:
                QMessageBox.warning(self.file_list_page, "提示", "请先登录/选择用户")
                return
            parent_id = self.file_list_page.current_parent_id
            try:
                resp = self.api.create_directory(token, dir_name.strip(), parent_id)
                if resp:
                    QMessageBox.information(self.file_list_page, "成功", f"目录 '{dir_name}' 创建成功！")
                    self.file_list_page.clear_cache()  # 清除缓存
                    self.file_list_page.load_file_list(parent_id=self.file_list_page.current_parent_id)
                else:
                    QMessageBox.warning(self.file_list_page, "失败", "目录创建失败")
            except Exception as e:
                QMessageBox.critical(self.file_list_page, "错误", f"创建目录失败: {e}")
    
    def on_rename(self):
        """重命名操作"""
        selected = self.file_list_page.table.selectedItems()
        if not selected:
            QMessageBox.warning(self.file_list_page, "提示", "请先选择要重命名的文件/文件夹")
            return
        selected_rows = list(set([item.row() for item in selected]))
        if len(selected_rows) == 1:
            row = selected_rows[0]
            f = self.file_list_page.get_file_by_row(row)
            if not f:
                QMessageBox.warning(self.file_list_page, "提示", "未找到对应文件")
                return
            file_id = f.get('fileId')
            old_name = f.get('filename', '')
            
            # 使用自定义重命名对话框
            rename_dlg = RenameDialog([{'file_id': file_id, 'file_name': old_name}], self.file_list_page)
            if rename_dlg.exec_() == QDialog.Accepted:
                new_name = rename_dlg.get_new_name()
                if new_name and new_name != old_name:
                    token = self.get_token_func()
                    if not token:
                        QMessageBox.warning(self.file_list_page, "提示", "请先登录/选择用户")
                        return
                    try:
                        self.api.rename_file(token, file_id, new_name)
                        QMessageBox.information(self.file_list_page, "成功", f"重命名成功！")
                        self.file_list_page.clear_cache()  # 清除缓存
                        self.file_list_page.load_file_list(parent_id=self.file_list_page.current_parent_id)
                    except Exception as e:
                        QMessageBox.critical(self.file_list_page, "错误", f"重命名失败: {e}")
        elif len(selected_rows) > 1:
            if len(selected_rows) > 30:
                QMessageBox.warning(self.file_list_page, "提示", "批量重命名一次最多支持30个文件！")
                return
            # 批量重命名对话框
            class BatchRenameDialog(QDialog):
                def __init__(self, file_infos, parent=None):
                    super().__init__(parent)
                    self.file_infos = file_infos  # 存储文件信息列表
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
            file_infos = [(int(self.file_list_page.table.item(row, 0).text()), self.file_list_page.table.item(row, 1).text()) for row in selected_rows]
            dlg = BatchRenameDialog(file_infos, self.file_list_page)
            if dlg.exec_() == QDialog.Accepted:
                rename_list = dlg.get_rename_list()
                token = self.get_token_func()
                api = FileApi()
                progress_dlg = ProgressDialog("批量重命名进度", len(rename_list), self.file_list_page)
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
                    QMessageBox.information(self.file_list_page, "批量重命名", f"重命名完成，成功{success}个，失败{fail}个。")
                    self.file_list_page.clear_cache()  # 清除缓存
                    self.file_list_page.load_file_list(parent_id=self.file_list_page.current_parent_id)
                worker.progress.connect(on_progress)
                worker.finished.connect(on_finished)
                progress_dlg.cancel_btn.clicked.connect(worker.stop)
                worker.start()
                progress_dlg.exec_()
    
    def on_delete(self):
        """删除操作"""
        selected = self.file_list_page.table.selectedItems()
        if not selected:
            QMessageBox.warning(self.file_list_page, "提示", "请先选择要删除的文件/文件夹")
            return
        selected_rows = list(set([item.row() for item in selected]))
        file_ids = []
        for row in selected_rows:
            f = self.file_list_page.get_file_by_row(row)
            if f:
                file_ids.append(f.get('fileId'))
        if not file_ids:
            QMessageBox.warning(self.file_list_page, "提示", "未找到要删除的文件")
            return
        reply = QMessageBox.question(self.file_list_page, "确认删除", f"确定要删除选中的 {len(file_ids)} 个文件/文件夹吗？\n删除后可在回收站找回。", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            token = self.get_token_func()
            if not token:
                QMessageBox.warning(self.file_list_page, "提示", "请先登录/选择用户")
                return
            try:
                self.api.move_to_trash(token, file_ids)
                QMessageBox.information(self.file_list_page, "成功", f"删除成功，已移入回收站！")
                self.file_list_page.clear_cache()  # 清除缓存
                self.file_list_page.load_file_list(parent_id=self.file_list_page.current_parent_id)
            except Exception as e:
                QMessageBox.critical(self.file_list_page, "错误", f"删除失败: {e}")
    
    def on_move(self):
        """移动操作"""
        selected = self.file_list_page.table.selectedItems()
        if not selected:
            QMessageBox.warning(self.file_list_page, "提示", "请先选择要移动的文件/文件夹")
            return
        
        selected_rows = list(set([item.row() for item in selected]))
        file_ids = []
        for row in selected_rows:
            f = self.file_list_page.get_file_by_row(row)
            if f:
                file_ids.append(f.get('fileId'))
        
        if not file_ids:
            QMessageBox.warning(self.file_list_page, "提示", "未找到要移动的文件")
            return
        
        # 获取token和API
        token = self.get_token_func()
        if not token:
            QMessageBox.warning(self.file_list_page, "提示", "请先登录/选择用户")
            return
        
        # 显示文件夹选择对话框
        dlg = MoveFolderDialog(self.api, token, self.file_list_page)
        if dlg.exec_() == MoveFolderDialog.Accepted:
            to_parent_id = dlg.get_selected_folder_id()
            if to_parent_id is not None:
                try:
                    self.api.move_files(token, file_ids, to_parent_id)
                    QMessageBox.information(self.file_list_page, "成功", f"移动成功！")
                    self.file_list_page.clear_cache()  # 清除缓存
                    self.file_list_page.load_file_list(parent_id=self.file_list_page.current_parent_id)
                except Exception as e:
                    QMessageBox.critical(self.file_list_page, "错误", f"移动失败: {e}")
    
    def on_download(self):
        """下载操作"""
        selected = self.file_list_page.table.selectedItems()
        if not selected:
            QMessageBox.warning(self.file_list_page, "提示", "请先选择要下载的文件或文件夹（仅支持单选）")
            return
        selected_rows = list(set([item.row() for item in selected]))
        if len(selected_rows) != 1:
            QMessageBox.warning(self.file_list_page, "提示", "请只选择一个文件或文件夹进行下载")
            return
        row = selected_rows[0]
        f = self.file_list_page.get_file_by_row(row)
        if not f:
            QMessageBox.warning(self.file_list_page, "提示", "未找到对应文件")
            return
        
        file_id = f.get('fileId')
        file_name = f.get('filename', '')
        file_type = f.get('type', 0)  # 0=文件, 1=文件夹
        
        token = self.get_token_func()
        if not token:
            QMessageBox.warning(self.file_list_page, "提示", "请先登录/选择用户")
            return
        
        # 获取主窗口的 download_task_manager
        main_win = self.file_list_page.parent()
        while main_win and not hasattr(main_win, 'download_task_manager'):
            main_win = main_win.parent()
        if not main_win or not hasattr(main_win, 'download_task_manager'):
            QMessageBox.warning(self.file_list_page, "提示", "未找到下载管理器")
            return
        
        download_manager = main_win.download_task_manager
        
        # 检查下载路径
        download_path = download_manager.get_download_path()
        if not download_path:
            path = QFileDialog.getExistingDirectory(self.file_list_page, "请选择下载保存路径", os.path.expanduser('~'))
            if not path:
                QMessageBox.warning(self.file_list_page, "提示", "未选择下载路径，已取消下载")
                return
            download_manager.set_download_path(path)
        
        if file_type == 1:  # 文件夹
            self.download_folder(file_id, file_name, download_path, download_manager, token, show_message=True)
        else:  # 文件
            self.download_file(file_id, file_name, download_manager, token, show_message=True)
    
    def download_file(self, file_id, file_name, download_manager, token, show_message=True):
        """下载单个文件"""
        try:
            url = self.api.get_download_url(token, file_id)
            # 推送任务到下载队列并启动
            task = download_manager.add_task(file_id, file_name, url)
            download_manager.start_download(task)
            if show_message:
                QMessageBox.information(self.file_list_page, "下载任务", f"文件下载任务已创建，进度可在'下载任务'页面查看！")
        except Exception as e:
            if show_message:
                QMessageBox.critical(self.file_list_page, "错误", f"获取下载链接失败: {e}")
            else:
                raise e
    
    def download_folder(self, folder_id, folder_name, download_path, download_manager, token, show_message=True):
        """下载文件夹"""
        # 创建文件夹下载工作线程
        self.file_list_page.folder_download_worker = FolderDownloadWorker(
            self.api, token, folder_id, folder_name, download_path, download_manager, self.file_list_page
        )
        
        def on_finished(success, fail):
            if show_message:
                if success > 0:
                    QMessageBox.information(self.file_list_page, "下载任务创建完成", 
                        f"文件夹下载任务已创建！\n成功创建: {success} 个下载任务\n失败: {fail} 个任务\n\n请在'下载任务'页面查看下载进度")
                else:
                    QMessageBox.warning(self.file_list_page, "下载任务创建失败", f"文件夹下载任务创建失败！\n失败: {fail} 个任务")
        
        def on_error(error_msg):
            if show_message:
                QMessageBox.critical(self.file_list_page, "下载错误", f"创建文件夹下载任务时发生错误: {error_msg}")
        
        # 连接信号
        self.file_list_page.folder_download_worker.finished.connect(on_finished)
        self.file_list_page.folder_download_worker.error.connect(on_error)
        
        # 开始创建下载任务
        self.file_list_page.folder_download_worker.start()
    
    def on_batch_rename(self):
        """批量重命名操作"""
        selected_rows = self.file_list_page.table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self.file_list_page, "提示", "请先选择要批量重命名的文件/文件夹")
            return
        
        # 检查选择数量 - 批量重命名用于2个及以上的文件
        if len(selected_rows) < 2:
            QMessageBox.information(self.file_list_page, "提示", "批量重命名功能需要选择2个及以上的文件。")
            return
        
        file_infos = []
        for idx in selected_rows:
            row = idx.row()
            f = self.file_list_page.get_file_by_row(row)
            if f:
                file_infos.append({
                    'file_id': f.get('fileId'),
                    'file_name': f.get('filename', '')
                })
        
        if not file_infos:
            QMessageBox.warning(self.file_list_page, "提示", "未找到有效的文件信息")
            return
        
        from gui.batch_rename import BatchRenameDialog as AdvancedBatchRenameDialog
        dlg = AdvancedBatchRenameDialog(file_infos, self.file_list_page)
        if dlg.exec_() == dlg.Accepted:
            rename_list = dlg.get_rename_list()
            if not rename_list:
                QMessageBox.information(self.file_list_page, "提示", "没有需要重命名的文件")
                return
            
            token = self.get_token_func()
            if not token:
                QMessageBox.warning(self.file_list_page, "提示", "请先登录/选择用户")
                return
            
            api = FileApi()
            progress_dlg = ProgressDialog("批量重命名进度", len(rename_list), self.file_list_page)
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
                QMessageBox.information(self.file_list_page, "批量重命名", f"重命名完成，成功{success}个，失败{fail}个。")
                self.file_list_page.clear_cache()  # 清除缓存
                self.file_list_page.load_file_list(parent_id=self.file_list_page.current_parent_id)
            worker.progress.connect(on_progress)
            worker.finished.connect(on_finished)
            progress_dlg.cancel_btn.clicked.connect(worker.stop)
            worker.start()
            progress_dlg.exec_()
    
    def on_delete_harmony(self):
        """删除和谐文件操作"""
        harmony_file_ids = [f.get('fileId') for f in self.file_list_page.file_list if f.get('status', 0) >= 100]
        if not harmony_file_ids:
            QMessageBox.information(self.file_list_page, "提示", "没有需要删除的审核驳回文件")
            return
        reply = QMessageBox.question(self.file_list_page, "确认删除", f"确定要删除所有审核驳回的 {len(harmony_file_ids)} 个文件/文件夹吗？\n删除后可在回收站找回。", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            token = self.get_token_func()
            if not token:
                QMessageBox.warning(self.file_list_page, "提示", "请先登录/选择用户")
                return
            try:
                self.api.move_to_trash(token, harmony_file_ids)
                QMessageBox.information(self.file_list_page, "成功", f"删除成功，已移入回收站！")
                self.file_list_page.clear_cache()  # 清除缓存
                self.file_list_page.load_file_list(parent_id=self.file_list_page.current_parent_id)
            except Exception as e:
                QMessageBox.critical(self.file_list_page, "错误", f"删除失败: {e}") 