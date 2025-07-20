# 123网盘离线下载工具

## 项目简介

本项目是一个基于 PyQt5 的 123网盘离线下载管理工具，支持多用户管理、离线任务推送、进度实时查询、文件管理与本地下载等功能，界面美观，操作便捷，适合个人和小团队使用。

## 主要功能

- **多用户管理**：支持添加、编辑、删除多个123网盘账号。
- **离线下载任务**：批量推送离线下载任务，支持自定义文件夹ID。
- **离线进度监控**：实时异步查询离线任务进度，不卡死，进度条直观。
- **文件管理**：浏览网盘文件，支持文件夹选择、文件操作。
- **本地下载管理**：支持本地下载任务的管理与进度显示。
- **美观UI**：现代化界面，支持窗口图标自定义。

### 依赖环境

- Python 3.7+
- PyQt5
- requests

### 运行项目

```bash
python main.py
```
### 登录方式
- 秘钥登录
通过在123云盘的开发平台申请秘钥
<img width="1260" height="305" alt="image" src="https://github.com/user-attachments/assets/a18e59de-949a-4282-9be6-2f441386e64b" />
<img width="556" height="402" alt="image" src="https://github.com/user-attachments/assets/3c0f746f-0b10-4012-8b94-dab04dec7224" />

- token登录
首先在网页先退出登录，然后f12打开找这个
<img width="1820" height="945" alt="image" src="https://github.com/user-attachments/assets/6c1d26f7-0942-43c3-a4b2-27f320745f32" />
然后点击登录，之后就会更新，复制红款圈中的就是token，填入添加即可
<img width="1066" height="688" alt="image" src="https://github.com/user-attachments/assets/bfabb55d-2eb0-4613-a007-6652004fee89" />

## 目录结构

```
openapidown/
├── main.py                  # 程序入口
├── config/                  # 配置相关
├── core/                    # 核心逻辑（API、存储、用户等）
├── gui/                     # 前端界面（主窗口、弹窗、控件等）
├── resources/               # 资源文件
├── icon_date.ico            # 程序图标
├── requirements.txt         # 依赖包列表（如有）
```

## 常见问题

### 1. 图标不显示？
请确保 `icon_date.ico` 文件在项目根目录。
### 2. API Token/账号问题？
请在“用户管理”中正确填写 client_id、client_secret 并获取 token。
### 3. 运行报错？
请检查 Python 版本和依赖包是否安装齐全。
## 贡献与反馈
如有建议、Bug反馈或功能需求，欢迎提 Issue 或 PR！ 
