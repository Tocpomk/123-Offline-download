from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, 
                             QPushButton, QLineEdit, QLabel, QHeaderView, QComboBox, QMenu, 
                             QAction, QToolButton, QAbstractItemView, QGraphicsDropShadowEffect, QDialog, QMessageBox, QFileDialog)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QDialog
from PyQt5.QtGui import QCursor, QPixmap, QPainter, QPen, QBrush, QColor
from gui.file_list_workers import AutoLoadWorker
from gui.file_list_dialogs import RenameDialog, MultiRenameDialog, ProgressDialog
from gui.file_list_operations import FileOperations
from gui.batch_rename import BatchRenameDialog as AdvancedBatchRenameDialog
from gui.move_folder_dialog import MoveFolderDialog
from gui.upload_dialog import UploadDialog
from core.file_api import FileApi
from collections import Counter
import re
import os

class FileListUI:
    """文件列表UI相关方法"""
    
    def __init__(self, file_list_page):
        self.file_list_page = file_list_page
        self.operations = FileOperations(file_list_page)
    
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout()
        
        # 顶部按钮和搜索栏（一行）
        top_layout = QHBoxLayout()
        
        # 返回上一层按钮放在最左边
        self.file_list_page.back_btn = QPushButton('返回上一层')
        self.file_list_page.back_btn.setStyleSheet('QPushButton{min-width:90px;max-width:110px;min-height:28px;max-height:32px;font-size:14px;}')
        self.file_list_page.back_btn.clicked.connect(self.file_list_page.on_back)
        top_layout.addWidget(self.file_list_page.back_btn)
        top_layout.addSpacing(16)
        
        # 主操作按钮
        self.file_list_page.create_dir_btn = self.make_flat_btn('创建目录', '#13C2C2', '#165DFF')
        self.file_list_page.create_dir_btn.clicked.connect(self.operations.on_create_dir)
        top_layout.addWidget(self.file_list_page.create_dir_btn)
        
        self.file_list_page.upload_btn = self.make_flat_btn('上传文件', '#13C2C2', '#165DFF')
        self.file_list_page.upload_btn.clicked.connect(self.file_list_page.on_upload_file)
        top_layout.addWidget(self.file_list_page.upload_btn)
        
        # 更多操作按钮（下拉菜单）
        more_menu = QMenu()
        more_menu.setStyleSheet('''
        QMenu {
            background: #fff;
            border: 1.5px solid #e1e5e9;
            border-radius: 8px;
            font-size: 15px;
            min-width: 120px;
        }
        QMenu::item {
            padding: 8px 18px;
            border-radius: 6px;
        }
        QMenu::item:selected {
            background: #e6f7ff;
            color: #165DFF;
        }
        ''')
        
        # 重命名
        act_rename = QAction('重命名', self.file_list_page)
        act_rename.triggered.connect(self.operations.on_rename)
        more_menu.addAction(act_rename)
        
        # 批量重命名
        act_batch_rename = QAction('批量重命名', self.file_list_page)
        act_batch_rename.triggered.connect(self.operations.on_batch_rename)
        more_menu.addAction(act_batch_rename)
        
        # 添加分隔线
        more_menu.addSeparator()
        
        # 删除
        act_delete = QAction('删除', self.file_list_page)
        act_delete.triggered.connect(self.operations.on_delete)
        more_menu.addAction(act_delete)
        
        # 删除和谐
        act_delete_harmony = QAction('删除和谐', self.file_list_page)
        act_delete_harmony.triggered.connect(self.operations.on_delete_harmony)
        more_menu.addAction(act_delete_harmony)
        
        # 添加分隔线
        more_menu.addSeparator()
        
        # 移动
        act_move = QAction('移动', self.file_list_page)
        act_move.triggered.connect(self.operations.on_move)
        more_menu.addAction(act_move)
        
        # 下载
        act_download = QAction('下载', self.file_list_page)
        act_download.triggered.connect(self.operations.on_download)
        more_menu.addAction(act_download)
        
        self.file_list_page.more_btn = self.make_flat_btn('更多', '#13C2C2', '#165DFF', more_menu)
        top_layout.addWidget(self.file_list_page.more_btn)
        
        # 添加一些间距
        top_layout.addSpacing(20)
        
        # 搜索相关组件
        self.file_list_page.search_input = QLineEdit()
        self.file_list_page.search_input.setPlaceholderText("搜索文件名/关键字")
        self.file_list_page.search_input.setStyleSheet('QLineEdit{min-width:200px;max-width:300px;min-height:26px;max-height:30px;font-size:13px;}')
        # 设置回车键触发搜索
        self.file_list_page.search_input.returnPressed.connect(self.file_list_page.on_search)
        top_layout.addWidget(self.file_list_page.search_input)
        
        self.file_list_page.search_btn = QPushButton("搜索")
        self.file_list_page.search_btn.setStyleSheet('QPushButton{min-width:60px;max-width:70px;min-height:26px;max-height:30px;font-size:13px;}')
        self.file_list_page.search_btn.clicked.connect(self.file_list_page.on_search)
        top_layout.addWidget(self.file_list_page.search_btn)
        
        self.file_list_page.clear_btn = QPushButton("清空")
        self.file_list_page.clear_btn.setStyleSheet('QPushButton{min-width:60px;max-width:70px;min-height:26px;max-height:30px;font-size:13px;}')
        self.file_list_page.clear_btn.clicked.connect(self.file_list_page.on_clear_search)
        top_layout.addWidget(self.file_list_page.clear_btn)
        
        self.file_list_page.refresh_btn = QPushButton("刷新")
        self.file_list_page.refresh_btn.setStyleSheet('QPushButton{min-width:60px;max-width:70px;min-height:26px;max-height:30px;font-size:13px;}')
        self.file_list_page.refresh_btn.clicked.connect(self.file_list_page.on_refresh)
        top_layout.addWidget(self.file_list_page.refresh_btn)
        
        top_layout.addStretch()
        layout.addLayout(top_layout)
        
        # 面包屑路径 - 放在搜索栏下面，靠左对齐
        path_layout = QHBoxLayout()
        # 文件列表标签放在面包屑路径的左边
        file_list_label = QLabel("文件列表")
        file_list_label.setStyleSheet('QLabel{font-size:15px;font-weight:bold;color:#333333;padding-right:10px;}')
        path_layout.addWidget(file_list_label)
        
        self.file_list_page.path_bar = QHBoxLayout()
        path_layout.addLayout(self.file_list_page.path_bar)
        path_layout.addStretch()
        layout.addLayout(path_layout)
        
        # 文件表格
        layout.addSpacing(18)
        self.file_list_page.table = QTableWidget()
        self.file_list_page.table.setColumnCount(7)
        self.file_list_page.table.setHorizontalHeaderLabels(["文件ID", "文件名", "扩展名", "类型", "大小", "状态", "创建时间"])
        
        # 设置列宽模式
        self.file_list_page.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        # 设置各列的固定宽度
        self.file_list_page.table.setColumnWidth(0, 110)   # 文件ID
        self.file_list_page.table.setColumnWidth(2, 110)   # 扩展名（与类型列宽度相同）
        self.file_list_page.table.setColumnWidth(3, 110)   # 类型
        self.file_list_page.table.setColumnWidth(4, 120)  # 大小（稍微宽一点）
        self.file_list_page.table.setColumnWidth(5, 110)   # 状态（稍微宽一点）
        self.file_list_page.table.setColumnWidth(6, 180)  # 创建时间（稍微宽一点）
        # 文件名列设置为拉伸模式，占用剩余空间
        self.file_list_page.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.file_list_page.table.setColumnWidth(1, 400)  # 设置文件名列最小宽度为400像素
        
        self.file_list_page.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.file_list_page.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.file_list_page.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.file_list_page.table.setAlternatingRowColors(True)
        
        # 启用排序功能
        self.file_list_page.table.setSortingEnabled(False)
        self.file_list_page.table.horizontalHeader().setSectionsClickable(True)
        self.file_list_page.table.horizontalHeader().sectionClicked.connect(self.file_list_page.on_header_clicked)
        
        # 设置表头鼠标指针样式
        self.file_list_page.table.horizontalHeader().setCursor(QCursor(Qt.PointingHandCursor))
        
        # 保存原始表头文本
        self.file_list_page.original_headers = ["文件ID", "文件名", "扩展名", "类型", "大小", "状态", "创建时间"]
        
        # 添加全选图标到表格左上角
        self.setup_select_all_corner()
        
        self.file_list_page.table.setStyleSheet("""
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
        self.file_list_page.table.cellDoubleClicked.connect(self.file_list_page.on_cell_double_clicked)
        self.file_list_page.table.setMinimumHeight(int(self.file_list_page.table.sizeHint().height() * 1.3))
        shadow = QGraphicsDropShadowEffect(self.file_list_page.table)
        shadow.setBlurRadius(16)
        shadow.setOffset(0, 3)
        shadow.setColor(Qt.gray)
        self.file_list_page.table.setGraphicsEffect(shadow)
        self.file_list_page.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.file_list_page.table.customContextMenuRequested.connect(self.on_table_context_menu)
        layout.addWidget(self.file_list_page.table)
        
        self.file_list_page.info_label = QLabel("")
        self.file_list_page.info_label.setVisible(False)
        self.file_list_page.info_label.setWordWrap(True)
        self.file_list_page.info_label.setMaximumHeight(40)
        self.file_list_page.info_label.setStyleSheet("color:#d9363e;font-size:14px;")
        layout.addWidget(self.file_list_page.info_label)
        self.file_list_page.setLayout(layout)
    
    def make_flat_btn(self, text, color1, color2, menu=None):
        """创建扁平化按钮"""
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
    
    def setup_select_all_corner(self):
        """设置表格左上角的全选图标"""
        # 创建全选图标
        def create_select_all_icon():
            # 创建一个16x16的图标
            pixmap = QPixmap(16, 16)
            pixmap.fill(Qt.transparent)
            
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.Antialiasing)
            
            # 绘制复选框边框
            pen = QPen(QColor("#165DFF"), 1.5)
            painter.setPen(pen)
            painter.setBrush(QBrush(QColor("#FFFFFF")))
            painter.drawRect(2, 2, 12, 12)
            
            # 绘制勾选标记
            pen = QPen(QColor("#165DFF"), 2)
            painter.setPen(pen)
            painter.drawLine(4, 8, 7, 11)
            painter.drawLine(7, 11, 12, 4)
            
            painter.end()
            return pixmap
        
        # 创建corner widget
        corner_widget = QWidget()
        corner_layout = QHBoxLayout(corner_widget)
        corner_layout.setContentsMargins(8, 8, 8, 8)
        corner_layout.setSpacing(0)
        
        # 创建图标标签
        icon_label = QLabel()
        icon_label.setPixmap(create_select_all_icon())
        icon_label.setToolTip("全选")
        icon_label.setCursor(Qt.PointingHandCursor)
        
        # 设置点击事件
        def on_corner_clicked():
            self.file_list_page.on_select_all()
        
        icon_label.mousePressEvent = lambda event: on_corner_clicked()
        
        corner_layout.addWidget(icon_label)
        corner_layout.addStretch()
        
        # 设置corner widget
        self.file_list_page.table.setCornerWidget(corner_widget)
    
    def update_path_bar(self):
        """更新路径栏"""
        # 清空原有
        while self.file_list_page.path_bar.count():
            item = self.file_list_page.path_bar.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        
        # 生成面包屑 - 更紧凑的样式
        for i, (fid, name) in enumerate(self.file_list_page.folder_path):
            # 路径按钮
            btn = QPushButton(name)
            btn.setFlat(True)
            
            # 根据是否是最后一个元素设置不同的样式
            if i == len(self.file_list_page.folder_path) - 1:
                # 最后一个元素（当前目录）- 深色显示
                btn.setStyleSheet('''
                    QPushButton {
                        color: #333333;
                        font-weight: bold;
                        background: transparent;
                        padding: 0 1px;
                        font-size: 15px;
                        border: none;
                        min-height: 20px;
                    }
                    QPushButton:hover {
                        color: #165DFF;
                        background: #f0f7ff;
                        border-radius: 4px;
                    }
                ''')
            else:
                # 其他元素 - 浅色显示
                btn.setStyleSheet('''
                    QPushButton {
                        color: #666666;
                        font-weight: bold;
                        background: transparent;
                        padding: 0 1px;
                        font-size: 15px;
                        border: none;
                        min-height: 20px;
                    }
                    QPushButton:hover {
                        color: #165DFF;
                        background: #f0f7ff;
                        border-radius: 4px;
                    }
                ''')
            
            btn.clicked.connect(lambda _, idx=i: self.file_list_page.on_path_clicked(idx))
            self.file_list_page.path_bar.addWidget(btn)
            
            # 添加分隔符 - 使用紧凑的箭头
            if i < len(self.file_list_page.folder_path) - 1:
                sep = QLabel('▶')
                sep.setStyleSheet('''
                    QLabel {
                        padding: 0 1px;
                        color: #CCCCCC;
                        font-size: 12px;
                        background: transparent;
                        margin: 0 2px;
                    }
                ''')
                self.file_list_page.path_bar.addWidget(sep)
    
    def on_table_context_menu(self, pos):
        """表格右键菜单"""
        from PyQt5.QtWidgets import QApplication
        from PyQt5.QtCore import QTimer
        index = self.file_list_page.table.indexAt(pos)
        if not index.isValid():
            return
        row = index.row()
        # 获取选中的行
        selected = self.file_list_page.table.selectedItems()
        selected_rows = list(set([item.row() for item in selected]))
        
        # 如果右击的行不在选中行中，则只选中该行
        if row not in selected_rows:
            self.file_list_page.table.clearSelection()
            self.file_list_page.table.selectRow(row)
            selected_rows = [row]
        
        # 支持单选和多选
        if len(selected_rows) >= 1:
            # 获取第一个选中项的类型作为参考
            file_type = self.file_list_page.table.item(selected_rows[0], 3).text()
            menu = QMenu(self.file_list_page.table)
            
            # 设置菜单样式，与文件列表UI协调
            menu.setStyleSheet("""
                QMenu {
                    background: #ffffff;
                    border: 2px solid #e1e5e9;
                    border-radius: 12px;
                    padding: 8px 0px;
                    font-size: 15px;
                    min-width: 160px;
                }
                QMenu::item {
                    padding: 10px 20px;
                    border-radius: 8px;
                    margin: 2px 8px;
                    color: #333333;
                }
                QMenu::item:selected {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #e6f7ff, stop:1 #cce7ff);
                    color: #165DFF;
                    border: 1px solid #165DFF;
                }
                QMenu::item:hover {
                    background: #f0f5ff;
                }
                QMenu::separator {
                    height: 1px;
                    background: #e1e5e9;
                    margin: 4px 12px;
                    border-radius: 1px;
                }
            """)
            
            # 复制ID功能（只有文件夹才显示，单选时）
            if file_type == '文件夹' and len(selected_rows) == 1:
                copy_id_action = QAction('复制文件夹ID', self.file_list_page.table)
                
                def do_copy():
                    file_id = self.file_list_page.table.item(selected_rows[0], 0).text()
                    QApplication.clipboard().setText(file_id)
                    QMessageBox.information(self.file_list_page, '提示', f'文件夹ID已复制：{file_id}')
                copy_id_action.triggered.connect(do_copy)
                menu.addAction(copy_id_action)
            
            # 添加分隔线
            menu.addSeparator()
            
            # 重命名功能（文件和文件夹都支持）
            rename_action = QAction('重命名', self.file_list_page.table)
            def do_rename():
                if len(selected_rows) == 1:
                    # 单选：执行重命名
                    f = self.file_list_page.get_file_by_row(selected_rows[0])
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
                            token = self.file_list_page.get_token_func()
                            if not token:
                                QMessageBox.warning(self.file_list_page, "提示", "请先登录/选择用户")
                                return
                            try:
                                self.file_list_page.api.rename_file(token, file_id, new_name)
                                QMessageBox.information(self.file_list_page, "成功", f"重命名成功！")
                                self.file_list_page.clear_cache()  # 清除缓存
                                self.file_list_page.load_file_list(parent_id=self.file_list_page.current_parent_id)
                            except Exception as e:
                                QMessageBox.critical(self.file_list_page, "错误", f"重命名失败: {e}")
                else:
                    # 多选：显示多文件重命名对话框
                    file_infos = []
                    for row_idx in selected_rows:
                        f = self.file_list_page.get_file_by_row(row_idx)
                        if f:
                            file_infos.append({
                                'file_id': f.get('fileId'),
                                'file_name': f.get('filename', '')
                            })
                    
                    if not file_infos:
                        QMessageBox.warning(self.file_list_page, "提示", "未找到有效的文件信息")
                        return
                    
                    # 使用自定义多文件重命名对话框
                    rename_dlg = MultiRenameDialog(file_infos, self.file_list_page)
                    if rename_dlg.exec_() == QDialog.Accepted:
                        rename_list = rename_dlg.get_rename_list()
                        if rename_list:
                            token = self.file_list_page.get_token_func()
                            if not token:
                                QMessageBox.warning(self.file_list_page, "提示", "请先登录/选择用户")
                                return
                            
                            api = FileApi()
                            progress_dlg = ProgressDialog("重命名进度", len(rename_list), self.file_list_page)
                            from gui.file_list_workers import BatchRenameWorker
                            worker = BatchRenameWorker(api, token, rename_list, batch_size=5)
                            
                            def on_progress(done, total):
                                progress_dlg.setValue(done)
                            
                            def on_finished(success, fail):
                                progress_dlg.setValue(len(rename_list))
                                progress_dlg.setLabelText(f"完成，成功{success}个，失败{fail}个。")
                                QApplication.processEvents()
                                QTimer.singleShot(1500, progress_dlg.close)
                                self.file_list_page.clear_cache()  # 清除缓存
                                self.file_list_page.load_file_list(parent_id=self.file_list_page.current_parent_id)
                            
                            worker.progress.connect(on_progress)
                            worker.finished.connect(on_finished)
                            worker.start()
                            progress_dlg.exec_()
            rename_action.triggered.connect(do_rename)
            menu.addAction(rename_action)
            
            # 批量重命名功能（只在多选且全部为文件时显示）
            if len(selected_rows) > 1:
                # 检查是否都是文件（type=0表示文件，type=1表示文件夹）
                all_files = True
                for row_idx in selected_rows:
                    f = self.file_list_page.get_file_by_row(row_idx)
                    if f and f.get('type', 0) == 1:  # 如果有文件夹
                        all_files = False
                        break
                
                if all_files:  # 只有当选中的都是文件时才显示批量重命名
                    batch_rename_action = QAction('批量重命名', self.file_list_page.table)
                    def do_batch_rename():
                        file_infos = []
                        for row_idx in selected_rows:
                            f = self.file_list_page.get_file_by_row(row_idx)
                            if f:
                                file_infos.append({
                                    'file_id': f.get('fileId'),
                                    'file_name': f.get('filename', '')
                                })
                        
                        if not file_infos:
                            QMessageBox.warning(self.file_list_page, "提示", "未找到有效的文件信息")
                            return
                        
                        # 打开批量重命名对话框
                        dlg = AdvancedBatchRenameDialog(file_infos, self.file_list_page)
                        if dlg.exec_() == dlg.Accepted:
                            rename_list = dlg.get_rename_list()
                            if rename_list:
                                token = self.file_list_page.get_token_func()
                                if not token:
                                    QMessageBox.warning(self.file_list_page, "提示", "请先登录/选择用户")
                                    return
                                
                                api = FileApi()
                                progress_dlg = ProgressDialog("批量重命名进度", len(rename_list), self.file_list_page)
                                from gui.file_list_workers import BatchRenameWorker
                                worker = BatchRenameWorker(api, token, rename_list, batch_size=5)
                                
                                def on_progress(done, total):
                                    progress_dlg.setValue(done)
                                
                                def on_finished(success, fail):
                                    progress_dlg.setValue(len(rename_list))
                                    progress_dlg.setLabelText(f"完成，成功{success}个，失败{fail}个。")
                                    QApplication.processEvents()
                                    QTimer.singleShot(1500, progress_dlg.close)
                                    self.file_list_page.clear_cache()  # 清除缓存
                                    self.file_list_page.load_file_list(parent_id=self.file_list_page.current_parent_id)
                                
                                worker.progress.connect(on_progress)
                                worker.finished.connect(on_finished)
                                worker.start()
                                progress_dlg.exec_()
                    batch_rename_action.triggered.connect(do_batch_rename)
                    menu.addAction(batch_rename_action)
            
            # 删除功能（文件和文件夹都支持）
            delete_action = QAction('删除', self.file_list_page.table)
            def do_delete():
                file_ids = []
                file_names = []
                for row_idx in selected_rows:
                    f = self.file_list_page.get_file_by_row(row_idx)
                    if f:
                        file_ids.append(f.get('fileId'))
                        file_names.append(f.get('filename', ''))
                
                if not file_ids:
                    QMessageBox.warning(self.file_list_page, "提示", "未找到要删除的文件")
                    return
                
                if len(file_ids) == 1:
                    confirm_text = f"确定要删除 '{file_names[0]}' 吗？\n删除后可在回收站找回。"
                else:
                    confirm_text = f"确定要删除选中的 {len(file_ids)} 个文件/文件夹吗？\n删除后可在回收站找回。"
                
                reply = QMessageBox.question(self.file_list_page, "确认删除", confirm_text, QMessageBox.Yes | QMessageBox.No)
                if reply == QMessageBox.Yes:
                    token = self.file_list_page.get_token_func()
                    if not token:
                        QMessageBox.warning(self.file_list_page, "提示", "请先登录/选择用户")
                        return
                    try:
                        self.file_list_page.api.move_to_trash(token, file_ids)
                        QMessageBox.information(self.file_list_page, "成功", f"删除成功，已移入回收站！")
                        self.file_list_page.clear_cache()  # 清除缓存
                        self.file_list_page.load_file_list(parent_id=self.file_list_page.current_parent_id)
                    except Exception as e:
                        QMessageBox.critical(self.file_list_page, "错误", f"删除失败: {e}")
            delete_action.triggered.connect(do_delete)
            menu.addAction(delete_action)
            
            # 移动功能（文件和文件夹都支持）
            move_action = QAction('移动', self.file_list_page.table)
            def do_move():
                file_ids = []
                for row_idx in selected_rows:
                    f = self.file_list_page.get_file_by_row(row_idx)
                    if f:
                        file_ids.append(f.get('fileId'))
                
                if not file_ids:
                    QMessageBox.warning(self.file_list_page, "提示", "未找到要移动的文件")
                    return
                
                # 获取token和API
                token = self.file_list_page.get_token_func()
                if not token:
                    QMessageBox.warning(self.file_list_page, "提示", "请先登录/选择用户")
                    return
                
                # 显示文件夹选择对话框
                dlg = MoveFolderDialog(self.file_list_page.api, token, self.file_list_page)
                if dlg.exec_() == MoveFolderDialog.Accepted:
                    to_parent_id = dlg.get_selected_folder_id()
                    if to_parent_id is not None:
                        try:
                            self.file_list_page.api.move_files(token, file_ids, to_parent_id)
                            QMessageBox.information(self.file_list_page, "成功", f"移动成功！")
                            self.file_list_page.clear_cache()  # 清除缓存
                            self.file_list_page.load_file_list(parent_id=self.file_list_page.current_parent_id)
                        except Exception as e:
                            QMessageBox.critical(self.file_list_page, "错误", f"移动失败: {e}")
            move_action.triggered.connect(do_move)
            menu.addAction(move_action)
            
            # 添加分隔线
            menu.addSeparator()
            
            # 下载功能（文件和文件夹都支持）
            download_action = QAction('下载', self.file_list_page.table)
            def do_download():
                token = self.file_list_page.get_token_func()
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
                
                # 处理选中的文件/文件夹
                success_count = 0
                fail_count = 0
                
                for row_idx in selected_rows:
                    f = self.file_list_page.get_file_by_row(row_idx)
                    if not f:
                        fail_count += 1
                        continue
                    
                    file_id = f.get('fileId')
                    file_name = f.get('filename', '')
                    file_type = f.get('type', 0)  # 0=文件, 1=文件夹
                    
                    try:
                        if file_type == 1:  # 文件夹
                            self.operations.download_folder(file_id, file_name, download_path, download_manager, token, show_message=False)
                            success_count += 1
                        else:  # 文件
                            self.operations.download_file(file_id, file_name, download_manager, token, show_message=False)
                            success_count += 1
                    except Exception as e:
                        fail_count += 1
                        print(f"下载失败 {file_name}: {e}")
                
                # 显示下载结果
                if success_count > 0:
                    if len(selected_rows) == 1:
                        QMessageBox.information(self.file_list_page, "下载任务", f"文件下载任务已创建，进度可在'下载任务'页面查看！")
                    else:
                        QMessageBox.information(self.file_list_page, "下载任务", 
                            f"批量下载任务已创建！\n成功创建: {success_count} 个下载任务\n失败: {fail_count} 个任务\n\n请在'下载任务'页面查看下载进度")
                else:
                    QMessageBox.warning(self.file_list_page, "下载失败", f"所有下载任务创建失败！\n失败: {fail_count} 个任务")
            
            download_action.triggered.connect(do_download)
            menu.addAction(download_action)
            
            menu.exec_(self.file_list_page.table.viewport().mapToGlobal(pos)) 