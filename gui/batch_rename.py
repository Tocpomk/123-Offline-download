from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem, QMessageBox, QComboBox, QSizePolicy, QSpacerItem, QFormLayout, QWidget, QTextEdit
from PyQt5.QtCore import Qt
import re
from collections import Counter

def number_to_chinese(num):
    """将数字转换为中文数字表示"""
    if not isinstance(num, int) or num < 0:
        return str(num)
    
    # 简单实现，直接返回数字字符串，不转换为中文汉字
    # 这样可以保持"第1集"而不是"第一集"的格式
    return str(num)

class BatchRenameDialog(QDialog):
    def __init__(self, file_infos, parent=None):
        super().__init__(parent)
        self.setWindowTitle("批量重命名")
        self.resize(1000, 540)  # 更宽
        self.file_infos = file_infos  # [{'file_id':..., 'file_name':...}, ...]
        self.rename_list = []  # [{'file_id':..., 'old_name':..., 'new_name':...}, ...]
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        # 模式选择区
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("重命名模式:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["正则模式", "剧集模式", "自动模式"])
        self.mode_combo.setFixedWidth(120)
        self.mode_combo.setCurrentIndex(1)  # 默认剧集模式
        self.mode_combo.currentIndexChanged.connect(self.on_mode_changed)
        self.mode_combo.setStyleSheet('''
            QComboBox {
                border: 1.2px solid #d0d7de;
                border-radius: 6px;
                padding: 5px 10px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ffffff, stop:1 #f8f9fa);
                min-height: 25px;
                font-size: 14px;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: url(resources/down-arrow.png);
                width: 12px;
                height: 12px;
            }
            QComboBox:hover {
                border-color: #165DFF;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ffffff, stop:1 #f0f7ff);
            }
            QComboBox:focus {
                border-color: #165DFF;
                outline: none;
            }
            QComboBox::item {
                padding: 5px 10px;
                min-height: 25px;
            }
            QComboBox::item:selected {
                background-color: #e6f7ff;
                color: #165DFF;
            }
            QComboBox::item:hover {
                background-color: #f0f7ff;
            }
        ''')
        mode_layout.addWidget(self.mode_combo)
        
        # 自动模式下的二级选项
        self.auto_submode_combo = QComboBox()
        self.auto_submode_combo.addItems(["按最多模板", "序列最低模板"])
        self.auto_submode_combo.setFixedWidth(180)  # 加宽二级菜单
        self.auto_submode_combo.setVisible(False)
        self.auto_submode_combo.currentIndexChanged.connect(self.on_preview)
        self.auto_submode_combo.setStyleSheet('''
            QComboBox {
                border: 1.2px solid #d0d7de;
                border-radius: 6px;
                padding: 5px 10px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #f0f7ff, stop:1 #e6f7ff);
                min-height: 25px;
                font-size: 14px;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: url(resources/down-arrow.png);
                width: 12px;
                height: 12px;
            }
            QComboBox:hover {
                border-color: #165DFF;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #e6f7ff, stop:1 #cce7ff);
            }
            QComboBox:focus {
                border-color: #165DFF;
                outline: none;
            }
            QComboBox::item {
                padding: 5px 10px;
                min-height: 25px;
            }
            QComboBox::item:selected {
                background-color: #e6f7ff;
                color: #165DFF;
            }
            QComboBox::item:hover {
                background-color: #f0f7ff;
            }
        ''')
        mode_layout.addWidget(self.auto_submode_combo)
        mode_layout.addStretch()
        layout.addLayout(mode_layout)
        # 规则输入区（两个widget，切换时show/hide）
        self.rule_layout = QHBoxLayout()
        self.rule_layout.setSpacing(8)
        self.rule_layout.setContentsMargins(0, 0, 0, 0)
        # 正则模式控件
        self.regex_widget = QWidget()
        regex_hbox = QHBoxLayout()
        regex_hbox.setSpacing(8)
        self.find_input = QLineEdit()
        self.find_input.setPlaceholderText("查找(正则)")
        self.find_input.setFixedWidth(220)
        self.replace_input = QLineEdit()
        self.replace_input.setPlaceholderText("替换为")
        self.replace_input.setFixedWidth(220)
        regex_hbox.addWidget(self.find_input)
        regex_hbox.addWidget(self.replace_input)
        self.regex_widget.setLayout(regex_hbox)
        # 剧集模式控件
        self.episode_widget = QWidget()
        episode_form = QFormLayout()
        episode_form.setHorizontalSpacing(8)
        episode_form.setVerticalSpacing(0)
        episode_form.setContentsMargins(0, 0, 0, 0)
        self.prefix_input = QLineEdit()
        self.prefix_input.setPlaceholderText("前缀，如 灵笼.")
        self.prefix_input.setFixedWidth(220)
        self.season_input = QLineEdit()
        self.season_input.setPlaceholderText("季数，如 1")
        self.season_input.setFixedWidth(120)
        episode_form.addRow(QLabel("前缀："), self.prefix_input)
        episode_form.addRow(QLabel("季数："), self.season_input)
        episode_hbox = QHBoxLayout()
        episode_hbox.setSpacing(8)
        episode_hbox.addLayout(episode_form)
        self.episode_widget.setLayout(episode_hbox)
        self.rule_layout.addWidget(self.regex_widget)
        self.rule_layout.addWidget(self.episode_widget)
        # 统一的预览按钮
        self.preview_btn = QPushButton("预览")
        self.preview_btn.setFixedHeight(32)
        self.preview_btn.setFixedWidth(110)
        self.preview_btn.clicked.connect(self.on_preview)
        self.rule_layout.addWidget(self.preview_btn)
        layout.addLayout(self.rule_layout)
        layout.addSpacing(16)
        # 预览表格
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["文件ID", "原文件名", "新文件名"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.NoSelection)
        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.table.setMinimumHeight(340)
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
        self.table.verticalHeader().setDefaultSectionSize(36)
        self.table.setColumnWidth(0, 120)
        self.table.setColumnWidth(1, 400)
        self.table.setColumnWidth(2, 400)
        self.table.cellDoubleClicked.connect(self.on_table_double_clicked)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.on_table_context_menu)
        layout.addWidget(self.table)
        # 按钮区
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.ok_btn = QPushButton("应用重命名")
        self.ok_btn.setFixedHeight(36)
        self.ok_btn.setFixedWidth(160)
        self.ok_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self.ok_btn)
        btn_layout.addSpacing(60)
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setFixedHeight(36)
        self.cancel_btn.setFixedWidth(120)
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        self.setLayout(layout)
        self.on_mode_changed()

    def on_mode_changed(self):
        mode = self.mode_combo.currentText()
        self.regex_widget.hide()
        self.episode_widget.hide()
        self.auto_submode_combo.setVisible(False)
        self.preview_btn.setVisible(True)  # 默认显示预览按钮
        
        if mode == "正则模式":
            self.regex_widget.show()
        elif mode == "剧集模式":
            self.episode_widget.show()
        elif mode == "自动模式":
            self.auto_submode_combo.setVisible(True)
            self.preview_btn.setVisible(False)  # 自动模式下隐藏预览按钮
        self.on_preview()

    def on_preview(self):
        mode = self.mode_combo.currentText()
        self.rename_list = []
        self.table.setRowCount(len(self.file_infos))
        if mode == "正则模式":
            find = self.find_input.text().strip()
            replace = self.replace_input.text().strip()
            for i, info in enumerate(self.file_infos):
                old_name = info['file_name']
                new_name = old_name
                if find:
                    try:
                        new_name = re.sub(find, replace, old_name)
                    except Exception as e:
                        new_name = old_name
                self.rename_list.append({'file_id': info['file_id'], 'old_name': old_name, 'new_name': new_name})
                self.table.setItem(i, 0, QTableWidgetItem(info['file_id']))
                old_item = QTableWidgetItem(old_name)
                old_item.setToolTip(old_name)
                self.table.setItem(i, 1, old_item)
                new_item = QTableWidgetItem(new_name)
                new_item.setToolTip(new_name)
                self.table.setItem(i, 2, new_item)
        elif mode == "剧集模式":
            prefix = self.prefix_input.text().strip()
            season = self.season_input.text().strip() or '1'
            for i, info in enumerate(self.file_infos):
                old_name = info['file_name']
                ep = self.extract_episode_number(old_name)
                ext = self.get_ext(old_name)
                if ep:
                    m_epnum = re.search(r'\d+', str(ep))
                    if m_epnum:
                        ep_num = int(m_epnum.group())
                        new_name = f'{prefix} S{int(season):02d}E{ep_num:02d}{ext}'
                    else:
                        new_name = old_name
                else:
                    new_name = old_name
                self.rename_list.append({'file_id': info['file_id'], 'old_name': old_name, 'new_name': new_name})
                self.table.setItem(i, 0, QTableWidgetItem(info['file_id']))
                old_item = QTableWidgetItem(old_name)
                old_item.setToolTip(old_name)
                self.table.setItem(i, 1, old_item)
                new_item = QTableWidgetItem(new_name)
                new_item.setToolTip(new_name)
                self.table.setItem(i, 2, new_item)
        elif mode == "自动模式":
            submode = self.auto_submode_combo.currentText()
            
            if submode == "序列最低模板":
                # 使用和"按最多模板"相同的机制，但选择主模板的方式不同
                import difflib
                
                # 改进剧集信息提取函数
                def extract_episode_info(name):
                    # 提取英文集数(SxxExx)
                    en_ep_match = re.search(r'(S\d{1,2}E\d{1,3})', name, re.I)
                    en_episode = en_ep_match.group(0) if en_ep_match else None
                    
                    # 提取中文集数(第x集)
                    ch_ep_match = re.search(r'(第[零一二三四五六七八九十百千万\d]+[集话話])', name)
                    ch_episode = ch_ep_match.group(0) if ch_ep_match else None
                    
                    # 如果只有英文集数没有中文集数，尝试从英文集数提取集号并生成中文集数
                    episode_num = None
                    if en_episode and not ch_episode:
                        num_match = re.search(r'E(\d{1,3})', en_episode, re.I)
                        if num_match:
                            episode_num = int(num_match.group(1))
                    
                    return {
                        'en_episode': en_episode,
                        'ch_episode': ch_episode,
                        'episode_num': episode_num,
                        'ch_match': ch_ep_match,
                        'en_match': en_ep_match
                    }
                
                # 分析所有文件结构
                pattern_counter = Counter()
                file_infos_enhanced = []
                for info in self.file_infos:
                    name = info['file_name']
                    ep_info = extract_episode_info(name)
                    
                    # 确定集数部分的位置
                    matches = []
                    if ep_info['en_match']:
                        matches.append(ep_info['en_match'])
                    if ep_info['ch_match']:
                        matches.append(ep_info['ch_match'])
                    
                    # 如果没有找到任何集数，保持原名
                    if not matches:
                        pattern_counter[name] += 1
                        file_infos_enhanced.append({
                            'template': name,
                            'ep_info': ep_info,
                            'original': name
                        })
                        continue
                    
                    # 按出现顺序排序
                    matches.sort(key=lambda m: m.start())
                    
                    # 构建分段列表
                    parts = []
                    last_end = 0
                    for i, match in enumerate(matches):
                        # 添加匹配前的部分
                        if match.start() > last_end:
                            parts.append(name[last_end:match.start()])
                        
                        # 添加占位符
                        if 'S' in match.group(0):
                            parts.append("{en_episode}")
                        else:
                            parts.append("{ch_episode}")
                        
                        last_end = match.end()
                    
                    # 添加最后部分
                    if last_end < len(name):
                        parts.append(name[last_end:])
                    
                    # 构建完整模板
                    template = "".join(parts)
                    pattern_counter[template] += 1
                    file_infos_enhanced.append({
                        'template': template,
                        'ep_info': ep_info,
                        'original': name
                    })
                
                # 选择序号最低的文件作为主模板（而不是使用最多的模板）
                min_episode_num = float('inf')
                main_template = None
                
                for info, templ_info in zip(self.file_infos, file_infos_enhanced):
                    ep_info = templ_info['ep_info']
                    if ep_info['episode_num'] is not None and ep_info['episode_num'] < min_episode_num:
                        min_episode_num = ep_info['episode_num']
                        main_template = templ_info['template']
                
                # 如果没有找到有效的序号，使用第一个模板
                if main_template is None and file_infos_enhanced:
                    main_template = file_infos_enhanced[0]['template']
                
                # 生成新文件名
                for i, (info, templ_info) in enumerate(zip(self.file_infos, file_infos_enhanced)):
                    old_name = info['file_name']
                    if not main_template:
                        new_name = old_name
                    else:
                        ep_info = templ_info['ep_info']
                        
                        # 保持原有的集数
                        en_episode = ep_info['en_episode']
                        ch_episode = ep_info['ch_episode']
                        
                        # 如果缺少英文集数但有数字
                        if not en_episode and ep_info['episode_num']:
                            # 从已有的其他文件中推断季数
                            season_num = "01"  # 默认第一季
                            for other_info in file_infos_enhanced:
                                if other_info['ep_info']['en_episode']:
                                    season_match = re.search(r'S(\d{2})', other_info['ep_info']['en_episode'], re.I)
                                    if season_match:
                                        season_num = season_match.group(1)
                                        break
                            en_episode = f"S{season_num}E{ep_info['episode_num']:02d}"
                        
                        # 如果缺少中文集数但有数字
                        if not ch_episode and ep_info['episode_num']:
                            ch_episode = f"第{number_to_chinese(ep_info['episode_num'])}集"
                        
                        # 应用主模板
                        new_name = main_template
                        # 确保替换值不为None
                        if "{en_episode}" in new_name:
                            new_name = new_name.replace("{en_episode}", en_episode or "")
                        if "{ch_episode}" in new_name:
                            new_name = new_name.replace("{ch_episode}", ch_episode or "")
                        
                        # 移除可能的双重点号和连续的空格
                        new_name = re.sub(r'\.\.+', '.', new_name)
                        new_name = re.sub(r'\s+', ' ', new_name).strip()
                    
                    # 只有当新文件名与原文件名不同时才添加到重命名列表
                    if new_name != old_name:
                        self.rename_list.append({
                            'file_id': info['file_id'],
                            'old_name': old_name,
                            'new_name': new_name
                        })
                    
                    # 更新表格显示
                    self.table.setItem(i, 0, QTableWidgetItem(info['file_id']))
                    old_item = QTableWidgetItem(old_name)
                    old_item.setToolTip(old_name)
                    self.table.setItem(i, 1, old_item)
                    new_item = QTableWidgetItem(new_name)
                    new_item.setToolTip(new_name)
                    self.table.setItem(i, 2, new_item)
                
                # 直接返回，不执行后面的模板匹配逻辑
                return
                
            # 按最多模板模式的处理
            import difflib
            
            # 改进剧集信息提取函数
            def extract_episode_info(name):
                # 提取英文集数(SxxExx)
                en_ep_match = re.search(r'(S\d{1,2}E\d{1,3})', name, re.I)
                en_episode = en_ep_match.group(0) if en_ep_match else None
                
                # 提取中文集数(第x集)
                ch_ep_match = re.search(r'(第[零一二三四五六七八九十百千万\d]+[集话話])', name)
                ch_episode = ch_ep_match.group(0) if ch_ep_match else None
                
                # 如果只有英文集数没有中文集数，尝试从英文集数提取集号并生成中文集数
                episode_num = None
                if en_episode and not ch_episode:
                    num_match = re.search(r'E(\d{1,3})', en_episode, re.I)
                    if num_match:
                        episode_num = int(num_match.group(1))
                
                return {
                    'en_episode': en_episode,
                    'ch_episode': ch_episode,
                    'episode_num': episode_num,
                    'ch_match': ch_ep_match,
                    'en_match': en_ep_match
                }
            
            # 分析所有文件结构
            pattern_counter = Counter()
            file_infos_enhanced = []
            for info in self.file_infos:
                name = info['file_name']
                ep_info = extract_episode_info(name)
                
                # 确定集数部分的位置
                matches = []
                if ep_info['en_match']:
                    matches.append(ep_info['en_match'])
                if ep_info['ch_match']:
                    matches.append(ep_info['ch_match'])
                
                # 如果没有找到任何集数，保持原名
                if not matches:
                    pattern_counter[name] += 1
                    file_infos_enhanced.append({
                        'template': name,
                        'ep_info': ep_info,
                        'original': name
                    })
                    continue
                
                # 按出现顺序排序
                matches.sort(key=lambda m: m.start())
                
                # 构建分段列表
                parts = []
                last_end = 0
                for i, match in enumerate(matches):
                    # 添加匹配前的部分
                    if match.start() > last_end:
                        parts.append(name[last_end:match.start()])
                    
                    # 添加占位符
                    if 'S' in match.group(0):
                        parts.append("{en_episode}")
                    else:
                        parts.append("{ch_episode}")
                    
                    last_end = match.end()
                
                # 添加最后部分
                if last_end < len(name):
                    parts.append(name[last_end:])
                
                # 构建完整模板
                template = "".join(parts)
                pattern_counter[template] += 1
                file_infos_enhanced.append({
                    'template': template,
                    'ep_info': ep_info,
                    'original': name
                })
            
            # 选择最常用的模板
            if pattern_counter:
                main_template = pattern_counter.most_common(1)[0][0]
            else:
                main_template = None
            
            # 生成新文件名
            for i, (info, templ_info) in enumerate(zip(self.file_infos, file_infos_enhanced)):
                old_name = info['file_name']
                if not main_template:
                    new_name = old_name
                else:
                    ep_info = templ_info['ep_info']
                    
                    # 保持原有的集数
                    en_episode = ep_info['en_episode']
                    ch_episode = ep_info['ch_episode']
                    
                    # 如果缺少英文集数但有数字
                    if not en_episode and ep_info['episode_num']:
                        # 从已有的其他文件中推断季数
                        season_num = "01"  # 默认第一季
                        for other_info in file_infos_enhanced:
                            if other_info['ep_info']['en_episode']:
                                season_match = re.search(r'S(\d{2})', other_info['ep_info']['en_episode'], re.I)
                                if season_match:
                                    season_num = season_match.group(1)
                                    break
                        en_episode = f"S{season_num}E{ep_info['episode_num']:02d}"
                    
                    # 如果缺少中文集数但有数字
                    if not ch_episode and ep_info['episode_num']:
                        ch_episode = f"第{number_to_chinese(ep_info['episode_num'])}集"
                    
                    # 应用主模板
                    new_name = main_template
                    # 确保替换值不为None
                    if "{en_episode}" in new_name:
                        new_name = new_name.replace("{en_episode}", en_episode or "")
                    if "{ch_episode}" in new_name:
                        new_name = new_name.replace("{ch_episode}", ch_episode or "")
                    
                    # 移除可能的双重点号和连续的空格
                    new_name = re.sub(r'\.\.+', '.', new_name)
                    new_name = re.sub(r'\s+', ' ', new_name).strip()
                
                # 只有当新文件名与原文件名不同时才添加到重命名列表
                if new_name != old_name:
                    self.rename_list.append({
                        'file_id': info['file_id'],
                        'old_name': old_name,
                        'new_name': new_name
                    })
                
                # 更新表格显示
                self.table.setItem(i, 0, QTableWidgetItem(info['file_id']))
                old_item = QTableWidgetItem(old_name)
                old_item.setToolTip(old_name)
                self.table.setItem(i, 1, old_item)
                new_item = QTableWidgetItem(new_name)
                new_item.setToolTip(new_name)
                self.table.setItem(i, 2, new_item)

    def extract_episode_number(self, name):
        # 改进后的正则表达式，支持中文前缀和多种剧集格式
        patterns = [
            r'[Ss](\d{1,2})[Ee](\d{1,3})',  # SxxExx
            r'[Ee][Pp]?(\d{1,3})',           # EPxx/Exx
            r'第(\d{1,3})[集话話]',           # 第xx集
            r'(\d{2,4})'                     # 纯数字
        ]
        for pattern in patterns:
            m = re.search(pattern, name)
            if m:
                return m.group(1) if pattern == r'第(\d{1,3})[集话話]' else m.group()
        return None

    def get_ext(self, name):
        idx = name.rfind('.')
        return name[idx:] if idx != -1 else ''

    def get_rename_list(self):
        return self.rename_list

    def on_table_double_clicked(self, row, col):
        # 1=原文件名，2=新文件名，双击直接复制
        if col in (1, 2):
            item = self.table.item(row, col)
            if item:
                text = item.text()
                from PyQt5.QtWidgets import QApplication, QToolTip
                QApplication.clipboard().setText(text)
                QToolTip.showText(self.table.viewport().mapToGlobal(self.table.visualItemRect(item).center()), "已复制")

    def on_table_context_menu(self, pos):
        index = self.table.indexAt(pos)
        row, col = index.row(), index.column()
        if col in (1, 2) and row >= 0:
            from PyQt5.QtWidgets import QMenu
            menu = QMenu(self)
            action = menu.addAction("查看完整文件名")
            action.triggered.connect(lambda: self.show_full_name_dialog(row, col))
            menu.exec_(self.table.viewport().mapToGlobal(pos))

    def show_full_name_dialog(self, row, col):
        item = self.table.item(row, col)
        if item:
            text = item.text()
            title = "原文件名" if col == 1 else "新文件名"
            dlg = FileNameDialog(title, text, self)
            dlg.exec_()

class FileNameDialog(QDialog):
    def __init__(self, title, text, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(600, 180)
        layout = QVBoxLayout(self)
        self.text_edit = QTextEdit()
        self.text_edit.setPlainText(text)
        self.text_edit.setReadOnly(True)
        self.text_edit.setMinimumHeight(60)
        self.text_edit.setMaximumHeight(80)
        self.text_edit.setLineWrapMode(QTextEdit.NoWrap)
        layout.addWidget(self.text_edit)
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.copy_btn = QPushButton("复制")
        self.copy_btn.setFixedWidth(120)
        self.copy_btn.clicked.connect(self.copy_text)
        btn_layout.addWidget(self.copy_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
    def copy_text(self):
        from PyQt5.QtWidgets import QApplication, QToolTip
        text = self.text_edit.toPlainText()
        QApplication.clipboard().setText(text)
        QToolTip.showText(self.copy_btn.mapToGlobal(self.copy_btn.rect().center()), "已复制") 