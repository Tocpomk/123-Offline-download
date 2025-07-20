import requests

# 上传相关API接口
class UploadApi:
    def __init__(self, base_url="https://open-api.123pan.com"):
        self.base_url = base_url

    def create_file(self, token, file_name, file_size, file_md5, parent_file_id=0, duplicate=None, contain_dir=False):
        """
        创建文件，返回是否秒传、预上传ID、分片大小、上传域名等
        :param token: access_token
        :param file_name: 文件名
        :param file_size: 文件大小（字节）
        :param file_md5: 文件MD5
        :param parent_file_id: 父目录id，默认0
        :param duplicate: 1保留两者，2覆盖原文件
        :param contain_dir: 是否包含路径
        :return: dict，接口返回json
        """
        # 参数校验
        if not file_name or len(file_name.strip()) == 0:
            raise ValueError("文件名不能为空或全空格")
        if any(c in file_name for c in '\\/:*?|"<>'):
            raise ValueError("文件名包含非法字符")
        if len(file_name) > 255:
            raise ValueError("文件名长度不能超过255字符")
        if not file_md5 or len(file_md5) != 32:
            raise ValueError("MD5格式不正确")
        if not isinstance(file_size, int) or file_size <= 0:
            raise ValueError("文件大小必须为正整数")
        url = self.base_url + "/upload/v2/file/create"
        headers = {
            "Authorization": f"Bearer {token}",
            "Platform": "open_platform",
            "Content-Type": "application/json"
        }
        body = {
            "parentFileID": parent_file_id,
            "filename": file_name,
            "etag": file_md5,
            "size": file_size
        }
        if duplicate is not None:
            body["duplicate"] = duplicate
        if contain_dir:
            body["containDir"] = True
        resp = requests.post(url, headers=headers, json=body, timeout=15)
        resp.raise_for_status()
        return resp.json()

    def upload_slice(self, token, preupload_id, slice_index, slice_data, slice_md5, server):
        """
        上传单个分片
        :param token: access_token
        :param preupload_id: 预上传ID
        :param slice_index: 分片序号（从1开始）
        :param slice_data: 分片二进制内容
        :param slice_md5: 分片MD5
        :param server: 上传域名（如 http://openapi-upload.123242.com）
        :return: dict，接口返回json
        """
        if not preupload_id:
            raise ValueError("preuploadID不能为空")
        if not isinstance(slice_index, int) or slice_index < 1:
            raise ValueError("slice_index必须为正整数且从1开始")
        if not slice_md5 or len(slice_md5) != 32:
            raise ValueError("sliceMD5格式不正确")
        if not slice_data or not isinstance(slice_data, (bytes, bytearray)):
            raise ValueError("slice_data必须为二进制内容")
        url = server.rstrip('/') + "/upload/v2/file/slice"
        headers = {
            "Authorization": f"Bearer {token}",
            "Platform": "open_platform"
        }
        data = {
            "preuploadID": preupload_id,
            "sliceNo": str(slice_index),
            "sliceMD5": slice_md5
        }
        files = {
            "slice": (f"part{slice_index}.bin", slice_data, "application/octet-stream")
        }
        resp = requests.post(url, headers=headers, data=data, files=files, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def complete_upload(self, token, preupload_id):
        """
        通知服务器上传完毕，返回completed和fileID
        :param token: access_token
        :param preupload_id: 预上传ID
        :return: dict，接口返回json
        """
        if not preupload_id:
            raise ValueError("preuploadID不能为空")
        url = self.base_url + "/upload/v2/file/upload_complete"
        headers = {
            "Authorization": f"Bearer {token}",
            "Platform": "open_platform",
            "Content-Type": "application/json"
        }
        body = {
            "preuploadID": preupload_id
        }
        resp = requests.post(url, headers=headers, json=body, timeout=15)
        resp.raise_for_status()
        return resp.json()

    def poll_upload_result(self, token, preupload_id):
        """轮询上传结果，直到completed为True"""
        pass

    def get_upload_domains(self, token):
        """
        获取上传域名列表
        :param token: access_token
        :return: list，域名字符串列表
        """
        url = self.base_url + "/upload/v2/file/domain"
        headers = {
            "Authorization": f"Bearer {token}",
            "Platform": "open_platform"
        }
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") == 0 and isinstance(data.get("data"), list):
            return data["data"]
        else:
            raise RuntimeError(f"获取上传域名失败: {data}")

    def single_upload(self, token, server, file_path, parent_file_id, file_md5, file_size, filename=None, duplicate=None, contain_dir=False):
        """
        单步上传小文件（1GB以内）
        :param token: access_token
        :param server: 上传域名
        :param file_path: 文件路径
        :param parent_file_id: 父目录id
        :param file_md5: 文件MD5
        :param file_size: 文件大小（字节）
        :param filename: 文件名（可选，默认取file_path）
        :param duplicate: 1保留两者，2覆盖原文件
        :param contain_dir: 是否包含路径
        :return: dict，接口返回json
        """
        import os
        if not filename:
            filename = os.path.basename(file_path)
        if not file_md5 or len(file_md5) != 32:
            raise ValueError("MD5格式不正确")
        if not isinstance(file_size, int) or file_size <= 0:
            raise ValueError("文件大小必须为正整数")
        url = server.rstrip('/') + "/upload/v2/file/single/create"
        headers = {
            "Authorization": f"Bearer {token}",
            "Platform": "open_platform"
        }
        data = {
            "parentFileID": parent_file_id,
            "filename": filename,
            "etag": file_md5,
            "size": str(file_size)
        }
        if duplicate is not None:
            data["duplicate"] = str(duplicate)
        if contain_dir:
            data["containDir"] = "true"
        with open(file_path, "rb") as f:
            files = {
                "file": (filename, f, "application/octet-stream")
            }
            resp = requests.post(url, headers=headers, data=data, files=files, timeout=60)
            resp.raise_for_status()
            return resp.json() 