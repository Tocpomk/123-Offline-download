from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, QPushButton, QLineEdit, QLabel, QHeaderView, QComboBox, QDialog, QProgressBar, QApplication, QScrollArea, QMenu, QAction, QToolButton, QAbstractItemView, QMessageBox
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from core.file_api import FileApi
from gui.pagination import PaginationWidget
from gui.file_list_workers import AutoLoadWorker
from gui.file_list_ui import FileListUI
from gui.file_list_operations import FileOperations
from gui.upload_dialog import UploadDialog
import os

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
        
        # 初始化UI和操作
        self.ui = FileListUI(self)
        self.operations = FileOperations(self)
        
        self.init_ui()

    def init_ui(self):
        """初始化UI"""
        self.ui.init_ui()
        self.load_file_list()

    def load_file_list(self, parent_id=None, search_data=None, reset_cursor=False):
        """加载文件列表"""
        token = self.get_token_func()
        if not token:
            self.info_label.setText("请先登录/选择用户")
            self.info_label.setToolTip("")
            self.info_label.setVisible(True)
            return
        # 如果parent_id为None，表示根目录（ID为0）
        if parent_id is None:
            parent_id = 0
        else:
            parent_id = parent_id if parent_id is not None else self.current_parent_id
        # 优先用缓存
        if search_data is None and parent_id in self.file_list_cache:
            self.file_list = self.file_list_cache[parent_id].copy()
            self.total = len(self.file_list)
            self.current_parent_id = parent_id
            self.sort_column = 1
            self.sort_order = Qt.AscendingOrder
            self.ui.update_path_bar()
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
        """安全加载文件列表回调"""
        try:
            self.on_file_list_loaded(resp, parent_id, page_size, search_data)
        except Exception as e:
            self.table.setDisabled(False)
            self.info_label.setVisible(True)
            self.info_label.setText(f"加载失败: {e}")

    def on_file_list_loaded(self, resp, parent_id, page_size, search_data):
        """文件列表加载完成回调"""
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
        # 每次加载新数据都重置排序状态，默认按文件名升序，文件夹优先
        self.sort_column = 1  # 默认按文件名
        self.sort_order = Qt.AscendingOrder
        
        # 应用默认排序：文件夹优先，然后按文件名排序
        self.sort_file_list()
        
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
        
        self.ui.update_path_bar()
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
        
        # 应用排序：文件夹优先，然后按当前排序规则排序
        self.sort_file_list()
        
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

    def clear_cache(self):
        """清除当前目录的缓存"""
        if self.current_parent_id in self.file_list_cache:
            del self.file_list_cache[self.current_parent_id]
    
    def clear_file_list(self):
        """清除文件列表显示"""
        self.table.setRowCount(0)
        self.current_parent_id = None

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
                
                # 扩展名
                filename = file_info.get('filename', '')
                if file_info.get('type') == 1:  # 文件夹
                    extension = "文件夹"
                else:
                    # 提取文件扩展名
                    import os
                    _, ext = os.path.splitext(filename)
                    extension = ext[1:].upper() if ext else "无扩展名"
                extension_item = QTableWidgetItem(extension)
                extension_item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, 2, extension_item)
                
                # 类型
                file_type = "文件夹" if file_info.get('type') == 1 else "文件"
                type_item = QTableWidgetItem(file_type)
                type_item.setData(Qt.UserRole, file_info.get('type', 0))
                type_item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, 3, type_item)
                
                # 大小
                size = file_info.get('size', 0)
                size_str = self.format_size(size)
                size_item = QTableWidgetItem(size_str)
                size_item.setData(Qt.UserRole, size)  # 用于排序的原始大小
                size_item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, 4, size_item)
                
                # 状态
                status = file_info.get('status', 0)
                status_text = '正常' if status < 100 else '审核驳回'
                status_item = QTableWidgetItem(status_text)
                status_item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, 5, status_item)
                
                # 创建时间
                create_time = file_info.get('createAt', '')
                create_time_item = QTableWidgetItem(create_time)
                create_time_item.setData(Qt.UserRole, create_time)  # 用于排序的时间
                self.table.setItem(row, 6, create_time_item)
                
            except Exception as e:
                print(f"警告：处理第 {row} 行数据时出错：{e}")
                print(f"问题数据：{file_info}")
                # 填充空数据
                for col in range(7):
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
            # 数据验证
            if not all(isinstance(f, dict) and 'fileId' in f and 'filename' in f for f in self.file_list):
                print("警告：排序前数据验证失败，跳过排序")
                return
            
            # 定义排序键函数：文件夹优先，然后按指定列排序
            def get_sort_key(item):
                # 文件夹类型为1，文件类型为0，所以 type != 1 会让文件夹排在前面
                is_folder = item.get('type', 0) == 1
                
                if self.sort_column == 0:  # 文件ID
                    return (not is_folder, str(item.get('fileId', '')).lower())
                elif self.sort_column == 1:  # 文件名
                    return (not is_folder, item.get('filename', '').lower())
                elif self.sort_column == 2:  # 扩展名
                    # 提取扩展名用于排序
                    filename = item.get('filename', '')
                    if item.get('type') == 1:  # 文件夹
                        ext = "文件夹"
                    else:
                        import os
                        _, ext = os.path.splitext(filename)
                        ext = ext[1:].upper() if ext else "无扩展名"
                    return (not is_folder, ext)
                elif self.sort_column == 3:  # 类型
                    return (not is_folder, item.get('type', 0))
                elif self.sort_column == 4:  # 大小
                    return (not is_folder, item.get('size', 0))
                elif self.sort_column == 5:  # 状态
                    return (not is_folder, item.get('status', 0))
                elif self.sort_column == 6:  # 创建时间
                    return (not is_folder, item.get('createAt', ''))
                else:
                    # 默认按文件名排序
                    return (not is_folder, item.get('filename', '').lower())
            
            # 执行排序
            self.file_list.sort(key=get_sort_key, reverse=reverse)
            
            # 验证排序结果
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
        """应用当前排序"""
        # 禁用QTableWidget的sortItems，保持表格和file_list顺序一致
        pass

    def get_file_by_row(self, row):
        """通过表格行号获取文件信息"""
        # 通过表格行号获取fileId，再反查file_list
        file_id = self.table.item(row, 0).text()
        for f in self.file_list:
            if str(f.get('fileId')) == file_id:
                return f
        return None

    def on_cell_double_clicked(self, row, col):
        """单元格双击事件"""
        f = self.get_file_by_row(row)
        if f and f.get('type') == 1:  # 文件夹
            self.folder_path.append((f.get('fileId'), f.get('filename', str(f.get('fileId')))))
            self.load_file_list(parent_id=f.get('fileId'))

    def on_path_clicked(self, idx):
        """路径点击事件"""
        # 跳转到指定层级
        fid, _ = self.folder_path[idx]
        self.folder_path = self.folder_path[:idx+1]
        self.load_file_list(parent_id=fid)

    def on_back(self):
        """返回上一层"""
        if len(self.folder_path) > 1:
            self.folder_path.pop()
            fid, _ = self.folder_path[-1]
            self.load_file_list(parent_id=fid)

    def on_search(self):
        """搜索"""
        search_text = self.search_input.text().strip()
        self.load_file_list(search_data=search_text)

    def on_clear_search(self):
        """清空搜索"""
        self.search_input.clear()
        self.load_file_list(parent_id=self.current_parent_id)

    def on_refresh(self):
        """刷新"""
        self.load_file_list(parent_id=self.current_parent_id)

    def on_select_all(self):
        """全选"""
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

    def format_size(self, size):
        """格式化文件大小"""
        if not size:
            return '-'
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024:
                return f"{size:.2f} {unit}"
            size /= 1024
        return f"{size:.2f} PB"

    def on_upload_file(self):
        """上传文件"""
        # 找到主窗口
        main_win = self.parent()
        while main_win and not hasattr(main_win, 'upload_manager'):
            main_win = main_win.parent()
        upload_manager = main_win.upload_manager if main_win else None
        dlg = UploadDialog(self, upload_manager)
        dlg.exec_()

    def closeEvent(self, event):
        """窗口关闭时清理工作线程"""
        if self.auto_load_worker and self.auto_load_worker.isRunning():
            self.auto_load_worker.stop()
            self.auto_load_worker.wait()
        # 停止定时器
        if self.info_hide_timer.isActive():
            self.info_hide_timer.stop()
        super().closeEvent(event) 