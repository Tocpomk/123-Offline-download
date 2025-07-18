"""
api.py - API相关逻辑
"""

# 这里实现API相关的函数和类 
import requests

class Pan123Api:
    BASE_URL = "https://open-api.123pan.com"

    def get_token_by_credentials(self, client_id, client_secret):
        url = f"{self.BASE_URL}/api/v1/access_token"
        resp = requests.post(url, json={
            "clientID": client_id,
            "clientSecret": client_secret
        }, headers={"Platform": "open_platform"})
        data = resp.json()
        if data.get("code") == 0 and data.get("data", {}).get("accessToken"):
            token = data["data"]["accessToken"]
            expired_at = data["data"].get("expiredAt")
            return token, expired_at
        raise Exception(data.get("message", "获取Token失败"))

    def send_offline_download_request(self, token, file_url, dir_id=None, file_name=None):
        url = f"{self.BASE_URL}/api/v1/offline/download"
        payload = {"url": file_url}
        if file_name:
            payload["fileName"] = file_name
        if dir_id and str(dir_id) != "0":
            payload["dirID"] = dir_id
        headers = {
            "Content-Type": "application/json",
            "Platform": "open_platform",
            "Authorization": f"Bearer {token}"
        }
        resp = requests.post(url, json=payload, headers=headers)
        data = resp.json()
        if data.get("code") == 0 and data.get("data", {}).get("taskID"):
            return data["data"]["taskID"]
        raise Exception(data.get("message", "离线下载任务创建失败"))

    def check_download_progress(self, token, task_id):
        url = f"{self.BASE_URL}/api/v1/offline/download/process?taskID={task_id}"
        headers = {
            "Content-Type": "application/json",
            "Platform": "open_platform",
            "Authorization": f"Bearer {token}"
        }
        resp = requests.get(url, headers=headers)
        return resp.json()

    def create_directory(self, token, name, parent_id):
        url = f"{self.BASE_URL}/upload/v1/file/mkdir"
        payload = {"name": name, "parentID": parent_id}
        headers = {
            "Content-Type": "application/json",
            "Platform": "open_platform",
            "Authorization": f"Bearer {token}"
        }
        resp = requests.post(url, json=payload, headers=headers)
        data = resp.json()
        if data.get("code") == 0 and data.get("data", {}).get("dirID"):
            return data["data"]["dirID"]
        raise Exception(data.get("message", "创建文件夹失败"))

    def get_actual_download_url(self, url):
        try:
            resp = requests.head(url, allow_redirects=True)
            return resp.url
        except Exception:
            return url