"""
utils.py - 通用工具函数
"""

import os
import sys

def get_user_data_dir():
    """
    获取用户数据目录，确保目录存在
    
    Returns:
        str: 用户数据目录的路径
    """
    # 在Windows上使用AppData/Local目录
    app_name = "openapidown"
    if os.name == 'nt':  # Windows
        app_data = os.path.join(os.environ['LOCALAPPDATA'], app_name)
    else:  # macOS和Linux
        app_data = os.path.expanduser(f"~/.{app_name}")
    
    # 确保目录存在
    if not os.path.exists(app_data):
        os.makedirs(app_data)
    
    return app_data

def get_base_path():
    """
    获取应用程序的基础路径
    
    Returns:
        str: 应用程序的基础路径
    """
    # 检查是否在PyInstaller环境中运行
    if getattr(sys, 'frozen', False):
        # 如果是PyInstaller打包的应用，使用_MEIPASS
        base_path = sys._MEIPASS
    else:
        # 否则使用脚本所在目录
        base_path = os.path.dirname(os.path.abspath(__file__))
    return base_path