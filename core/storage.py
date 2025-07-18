"""
storage.py - 存储相关逻辑
"""

import os
import json
from .utils import get_user_data_dir

class TokenStorage:
    def __init__(self):
        self.FILE = os.path.join(get_user_data_dir(), "token.json")

    def save_token(self, token):
        data = {"token": token}
        with open(self.FILE, "w", encoding="utf-8") as f:
            json.dump(data, f)

    def get_token(self):
        if not os.path.exists(self.FILE):
            return None
        with open(self.FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("token")

    def delete_token(self):
        if os.path.exists(self.FILE):
            os.remove(self.FILE)