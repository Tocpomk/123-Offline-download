"""
用户信息存储与管理模块
"""
import json
import os
from datetime import datetime, timedelta
from .utils import get_user_data_dir, get_base_path

# 用户数据文件路径
USER_FILE = os.path.join(get_user_data_dir(), 'users.json')
# 记忆登录配置文件路径
REMEMBER_LOGIN_FILE = os.path.join(get_user_data_dir(), 'remember_login.json')

# 如果用户数据文件不存在，但开发环境中的默认文件存在，则复制它
def init_user_file():
    """初始化用户数据文件"""
    if not os.path.exists(USER_FILE):
        # 尝试从开发环境中复制默认用户文件
        default_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'users.json')
        if os.path.exists(default_file):
            try:
                with open(default_file, 'r', encoding='utf-8') as src:
                    default_data = json.load(src)
                with open(USER_FILE, 'w', encoding='utf-8') as dst:
                    json.dump(default_data, dst, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"初始化用户数据文件失败: {e}")

# 初始化用户数据文件
init_user_file()

def load_users():
    if not os.path.exists(USER_FILE):
        return {}
    with open(USER_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_users(users):
    with open(USER_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

def load_remember_login():
    """加载记忆登录配置"""
    if not os.path.exists(REMEMBER_LOGIN_FILE):
        return {'enabled': False, 'last_user': None}
    try:
        with open(REMEMBER_LOGIN_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {'enabled': False, 'last_user': None}

def save_remember_login(config):
    """保存记忆登录配置"""
    with open(REMEMBER_LOGIN_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

class UserManager:
    def __init__(self):
        self.users = load_users()
        # 为现有用户添加创建时间字段
        self._add_created_at_to_existing_users()
    
    def _add_created_at_to_existing_users(self):
        """为现有用户添加创建时间字段"""
        modified = False
        for name, user_info in self.users.items():
            if 'created_at' not in user_info:
                user_info['created_at'] = '2024-01-01 00:00:00'  # 默认创建时间
                modified = True
        
        if modified:
            save_users(self.users)

    def add_user(self, name, client_id, client_secret):
        self.users[name] = {
            'client_id': client_id,
            'client_secret': client_secret,
            'access_token': '',
            'expired_at': '',
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        save_users(self.users)

    def update_token(self, name, access_token, expired_at):
        if name in self.users:
            self.users[name]['access_token'] = access_token
            self.users[name]['expired_at'] = expired_at
            save_users(self.users)

    def get_user(self, name):
        return self.users.get(name)

    def get_all_users(self):
        return self.users

    def is_token_expired(self, name):
        user = self.get_user(name)
        if not user or not user.get('expired_at'):
            return True
        try:
            expired_at = user['expired_at']
            # 兼容带时区的ISO格式
            dt = datetime.fromisoformat(expired_at.replace('Z', '+00:00'))
            return dt <= datetime.now(dt.tzinfo)
        except Exception:
            return True

    def delete_user(self, name):
        if name in self.users:
            del self.users[name]
            save_users(self.users)
    
    def save(self):
        """保存用户数据"""
        save_users(self.users)
    
    def save_remember_login_config(self, enabled, username=None):
        """保存记忆登录配置"""
        config = {
            'enabled': enabled,
            'last_user': username if enabled else None
        }
        save_remember_login(config)
    
    def get_remember_login_config(self):
        """获取记忆登录配置"""
        return load_remember_login()
    
    def get_last_login_user(self):
        """获取最后登录的用户名"""
        config = self.get_remember_login_config()
        if config.get('enabled') and config.get('last_user'):
            # 检查用户是否还存在
            if config['last_user'] in self.users:
                return config['last_user']
        return None
    
    def is_remember_login_user(self, username):
        """检查指定用户是否为记忆登录用户"""
        config = self.get_remember_login_config()
        return config.get('enabled') and config.get('last_user') == username