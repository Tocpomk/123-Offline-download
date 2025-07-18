import requests

class FileApi:
    BASE_URL = "https://open-api.123pan.com"

    def get_file_list(self, token, parent_file_id=0, limit=100, search_data=None, search_mode=None, last_file_id=None):
        url = f"{self.BASE_URL}/api/v2/file/list"
        headers = {
            "Content-Type": "application/json",
            "Platform": "open_platform",
            "Authorization": f"Bearer {token}"
        }
        params = {
            "parentFileId": parent_file_id,
            "limit": limit
        }
        if search_data:
            params["searchData"] = search_data
        if search_mode is not None:
            params["searchMode"] = search_mode
        if last_file_id is not None:
            params["lastFileId"] = last_file_id
        resp = requests.get(url, headers=headers, params=params)
        return resp.json()

    def create_directory(self, token, name, parent_id):
        url = f"{self.BASE_URL}/upload/v1/file/mkdir"
        headers = {
            "Content-Type": "application/json",
            "Platform": "open_platform",
            "Authorization": f"Bearer {token}"
        }
        payload = {
            "name": name,
            "parentID": parent_id
        }
        resp = requests.post(url, json=payload, headers=headers)
        data = resp.json()
        if data.get("code") == 0 and data.get("data", {}).get("dirID"):
            return data["data"]["dirID"]
        raise Exception(data.get("message", "创建目录失败"))

    def rename_file(self, token, file_id, file_name):
        url = f"{self.BASE_URL}/api/v1/file/name"
        headers = {
            "Content-Type": "application/json",
            "Platform": "open_platform",
            "Authorization": f"Bearer {token}"
        }
        payload = {
            "fileId": file_id,
            "fileName": file_name
        }
        resp = requests.put(url, json=payload, headers=headers)
        data = resp.json()
        if data.get("code") == 0:
            return True
        raise Exception(data.get("message", "重命名失败"))

    def batch_rename_files(self, token, rename_list):
        url = f"{self.BASE_URL}/api/v1/file/rename"
        headers = {
            "Content-Type": "application/json",
            "Platform": "open_platform",
            "Authorization": f"Bearer {token}"
        }
        payload = {
            "renameList": rename_list
        }
        resp = requests.post(url, json=payload, headers=headers)
        data = resp.json()
        if data.get("code") == 0:
            return True
        raise Exception(data.get("message", "批量重命名失败"))

    def move_to_trash(self, token, file_ids):
        url = f"{self.BASE_URL}/api/v1/file/trash"
        headers = {
            "Content-Type": "application/json",
            "Platform": "open_platform",
            "Authorization": f"Bearer {token}"
        }
        payload = {
            "fileIDs": file_ids
        }
        resp = requests.post(url, json=payload, headers=headers)
        data = resp.json()
        if data.get("code") == 0:
            return True
        raise Exception(data.get("message", "删除失败"))

    def move_files(self, token, file_ids, to_parent_file_id):
        url = f"{self.BASE_URL}/api/v1/file/move"
        headers = {
            "Content-Type": "application/json",
            "Platform": "open_platform",
            "Authorization": f"Bearer {token}"
        }
        payload = {
            "fileIDs": file_ids,
            "toParentFileID": to_parent_file_id
        }
        resp = requests.post(url, json=payload, headers=headers)
        data = resp.json()
        if data.get("code") == 0:
            return True
        raise Exception(data.get("message", "移动失败"))

    def get_download_url(self, token, file_id):
        url = f"{self.BASE_URL}/api/v1/file/download_info"
        headers = {
            "Content-Type": "application/json",
            "Platform": "open_platform",
            "Authorization": f"Bearer {token}"
        }
        params = {"fileId": file_id}
        resp = requests.get(url, headers=headers, params=params)
        data = resp.json()
        if data.get("code") == 0 and data.get("data", {}).get("downloadUrl"):
            return data["data"]["downloadUrl"]
        raise Exception(data.get("message", "获取下载地址失败")) 