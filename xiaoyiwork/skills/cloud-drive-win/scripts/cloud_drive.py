import argparse
import json
import os
import uuid
import logging
import sys
import tempfile

from claw_pipe_http import PipeHttpError, pipe_path_from_url, post_json

# ========== 接入方式 ==========
# 云盘操作一律经小艺Work主进程的云盘代理（命名管道 \\.\pipe\claw-cloud-drive）执行：
#   - 请求发到本机管道，由主进程注入云盘 AT 后访问云端；本 skill 不持有、也拿不到任何凭据
#   - 管道地址可用环境变量 CLOUD_DRIVE_PIPE_URL 覆盖（缺省 np://claw-cloud-drive）
#   - 本机防借用令牌由主进程注入（CLAW_SKILL_TOKEN，孙进程继承）
# 因此这里没有 token / 刷新 / 扫码逻辑；票据不可用只会表现为
# DRIVE_NOT_READY（稍后重试）或 DRIVE_NEED_LOGIN（提示重新登录小艺Work）。
CLOUD_DRIVE_PIPE_URL = os.environ.get("CLOUD_DRIVE_PIPE_URL", "np://claw-cloud-drive")

PARENT_FOLDER_NAME = "小艺Work"
FOLDER_MIME_TYPE = "application/vnd.huawei-apps.folder"
FILE_MIME_TYPE = "application/octet-stream"

QUERY_ERROR = "查询异常"
QUERY_FAIL = "查询失败"
FOLDER_NOT_EXIST = "小艺Work目录不存在"
FILE_NOT_EXIST = "文件不存在"

# 票据/上游不可用 → 两类可直接展示的失败（不提示扫码：扫码由小艺Work自己弹）
DRIVE_NOT_READY_MESSAGE = {
    "status": "error",
    "error_code": "DRIVE_NOT_READY",
    "message": "云空间暂时不可用，请稍后重试",
}
DRIVE_NEED_LOGIN_MESSAGE = {
    "status": "error",
    "error_code": "DRIVE_NEED_LOGIN",
    "message": "登录已失效，请重新登录小艺Work",
}

# 日志文件路径
LOG_DIR = os.path.join(tempfile.gettempdir(), "logs")
print("log:", LOG_DIR)
LOG_FILE = os.path.join(LOG_DIR, f"{os.path.basename(__file__).replace('.py', '')}.log")


# 创建日志目录并设置权限
os.makedirs(LOG_DIR, mode=0o700, exist_ok=True)

# 创建日志文件并设置权限（如果不存在）
if not os.path.exists(LOG_FILE):
    with open(LOG_FILE, 'w') as f1:
        pass
    os.chmod(LOG_FILE, 0o600)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)


def create_error_result(error_code, message):
    """标准错误结果"""
    return {"status": "error", "error_code": error_code, "message": message}


def create_success_result(**kwargs):
    """标准成功结果"""
    return {"status": "success", **kwargs}


def print_drive_unavailable(error_code=None):
    """票据不可用时打印统一结果（旧调用点沿用这个入口；扫码由小艺Work自行处理）。"""
    payload = dict(DRIVE_NEED_LOGIN_MESSAGE if error_code == "DRIVE_NEED_LOGIN" else DRIVE_NOT_READY_MESSAGE)
    print(json.dumps(payload, ensure_ascii=False))
    return payload


class DriveCallError(RuntimeError):
    """管道调用失败：code 为管道错误码（DRIVE_NOT_READY / DRIVE_NEED_LOGIN / ...）。"""

    def __init__(self, code, message):
        super().__init__(message)
        self.code = code
        self.message = message


def _is_auth_failure(code):
    """票据类失败：无票 / 票被拒 / 代理未就绪 —— 上层据此走「稍后重试」而不是「操作失败」。"""
    return code in ("DRIVE_NOT_READY", "DRIVE_NEED_LOGIN", "SKILL_TOKEN_INVALID", "PROXY_NOT_READY")


def _auth_failure_result(code):
    return dict(DRIVE_NEED_LOGIN_MESSAGE if code == "DRIVE_NEED_LOGIN" else DRIVE_NOT_READY_MESSAGE)


def _legacy_entry(entry):
    """管道条目（id/name/isFolder/size/modifiedAt）→ 本脚本其余部分沿用的字段形态。"""
    return {
        "id": entry.get("id"),
        "fileName": entry.get("name"),
        "mimeType": FOLDER_MIME_TYPE if entry.get("isFolder") else FILE_MIME_TYPE,
        "size": entry.get("size"),
        "editedTime": entry.get("modifiedAt"),
    }


class UploadFileHwDrive(object):
    """
    云盘操作客户端：所有请求经小艺Work主进程的云盘代理执行，本类不持有任何凭据。

    auth 参数只为兼容旧调用方保留（鉴权在主进程里注入）。
    """

    def __init__(self, auth=None):
        self.trace_id = str(uuid.uuid4())[:16]
        self.auth = auth

    # ========== 管道调用 ==========

    def _call(self, path, payload=None):
        """调管道端点：成功返回响应 dict；失败抛 DriveCallError（带 code / message）。"""
        try:
            status, data = post_json(
                path,
                payload or {},
                pipe_path=pipe_path_from_url(CLOUD_DRIVE_PIPE_URL),
                token=os.environ.get("CLAW_SKILL_TOKEN", ""),
            )
        except PipeHttpError as e:
            logger.error(f"云盘代理不可用: {e}")
            raise DriveCallError("PROXY_NOT_READY", "云空间暂时不可用，请稍后重试")
        if status == 200:
            return data
        error = data.get("error") or {}
        code = error.get("code") or f"HTTP_{status}"
        message = error.get("message") or "云空间暂时不可用，请稍后重试"
        logger.error(f"云盘调用失败 {path}: {code} {message}")
        raise DriveCallError(code, message)

    def _paginated_list(self, folder_id, fields=None):
        """
        取指定目录下的全部子项（内部按游标翻页）。

        :param folder_id: 目录 id（根目录用 "root"）
        :param fields: 兼容旧签名保留；管道返回固定字段集，由 _legacy_entry 映射
        :return: (all_files, error_result) —— 成功 (files, None)，失败 (None, error_dict)
        """
        all_files = []
        cursor = None
        page_count = 0
        while True:
            page_count += 1
            payload = {"folderId": folder_id}
            if cursor:
                payload["cursor"] = cursor
            try:
                data = self._call("/drive/list", payload)
            except DriveCallError as e:
                if _is_auth_failure(e.code):
                    return None, _auth_failure_result(e.code)
                return None, create_error_result("QUERY_FAILED", f"查询失败: {e.message}")
            page = [_legacy_entry(item) for item in (data.get("entries") or [])]
            all_files.extend(page)
            logger.info(f"_paginated_list page {page_count}, files count: {len(page)}")
            cursor = data.get("nextCursor")
            if not cursor:
                break
        logger.info(f"_paginated_list total files count: {len(all_files)}")
        return all_files, None

    # ========== 文件/文件夹查询方法 ==========

    def _find_items_by_name(self, name, parent_folder_id=None, fields=None):
        """
        按名称查子项（父目录省略 = 云盘根目录）。

        :param fields: 兼容旧签名保留（管道返回固定字段集）
        :return: (files, error_result) —— 成功 (list, None)，失败 (None, error_dict)
        """
        all_files, error = self._paginated_list(parent_folder_id or "root")
        if error:
            return None, error
        return [item for item in all_files if item.get("fileName") == name], None

    def about_get(self):
        """
        云空间用量：管道端点 /drive/space → 组装成旧的 about_get 形态（storageQuota），
        让 get_space_detail / get_clouddrive_available_space 不用改。

        :return: {"storageQuota": {...}}；票据类失败 {"error": <code>}；其他失败 None
        """
        try:
            data = self._call("/drive/space", {})
        except DriveCallError as e:
            logger.error(f"查询云空间容量失败: {e.message}")
            if _is_auth_failure(e.code):
                return {"error": e.code}
            return None
        return {
            "storageQuota": {
                "userCapacity": str(data.get("totalBytes", 0)),
                "usedSpace": str(data.get("usedBytes", 0)),
            }
        }

    def get_celiaclaw_file_id(self):
        """获取小艺Work根目ID"""
        files, error = self._find_items_by_name(PARENT_FOLDER_NAME, None, "files(id)")
        if error:
            return "TOKEN_EXPIRED"
        return files[0]["id"] if files else ""


    def get_file_list(self, folder_id):
        """
        查询云盘指定目录下的所有文件列表（内部分页取全量）。

        :return: 文件列表；失败返回 "查询失败,<原因>"（兼容旧的字符串返回）
        """
        all_files, error = self._paginated_list(folder_id)
        if error:
            return f"{QUERY_FAIL},{error.get('message', '')}"
        return all_files

    def get_space_detail(self):
        result = self.about_get()
        if result is None:
            logger.error(f"get cloud drive space failed")
            return 0
        if "error" in result:
            return "TOKEN_EXPIRED"
        print(f"总空间：{result["storageQuota"]["userCapacity"]}")
        print(f"已用空间：{result["storageQuota"]["usedSpace"]}")
        available_space = max(0, int(result["storageQuota"]["userCapacity"]) - int(result["storageQuota"]["usedSpace"]))
        print(f"可用空间：{available_space}")
        if result["storageQuota"]["userCapacity"] == 0:
            print("您当前为基础服务用户，不支持上传文件")
        elif available_space == 0:
            print("云空间可用容量不足，建议尽快升级云空间")
        self.with_space_be_full(int(result["storageQuota"]["userCapacity"]), available_space)
        return result

    def with_space_be_full(self, total_sapce, available_space):
        if available_space < total_sapce * 0.2:
            print("云空间可用空间将满")
            return True
        else:
            return False

    def get_clouddrive_available_space(self):
        result = self.about_get()
        if result is None:
            logger.error(f"get cloud drive space failed")
            return 0
        if "error" in result:
            return "TOKEN_EXPIRED"
        available_space = max(0, int(result["storageQuota"]["userCapacity"]) - int(result["storageQuota"]["usedSpace"]))
        print(f"可用空间{available_space}")
        return available_space

    def check_space(self, file_size):
        available_space = self.get_clouddrive_available_space()
        if available_space == "TOKEN_EXPIRED":
            return "TOKEN_EXPIRED"
        if available_space < file_size:
            logger.error(f"file size {file_size} is less than available space {available_space}")
            return False
        else:
            return True

    def check_file_exists_recursive(self, file_name, folder_id):
        """
        递归查询云盘小艺Work文件夹下是否存在指定文件名的文件或文件夹
        :param file_name: 文件名
        :param folder_id: 文件夹ID
        :return: 存在返回True，不存在返False
        """
        # 先检查当前文件夹
        ret = self.check_file_exists(file_name, folder_id)
        if ret is not None:
            return create_success_result(result=f"{file_name} exist", file=ret)
        
        # 使用 _paginated_list 获取分页文件列表
        all_files, error = self._paginated_list(folder_id)
        if error:
            return error

        # 递归处理子文件夹
        for file_info in all_files:
            is_folder = file_info.get("mimeType") == "application/vnd.huawei-apps.folder"
            file_info["is_folder"] = is_folder

            # 如果是文件夹，递归获取其内容
            if is_folder:
                current_folder_id = file_info["id"]
                result = self.check_file_exists_recursive(file_name, current_folder_id)
                if result["status"] == "success":
                    return result

        logger.info(f"{file_name} does not exist in {folder_id}")
        return create_error_result("NOT_FOUND", f"{file_name} does not exist")


    def check_file_exists(self, file_name, folder_id):
        """
        检查云盘中是否存在指定文件名的文件
        :param file_name: 文件名
        :param folder_id: 文件夹ID
        :return: 存在返回文件列表，不存在返回None
        """
        files, error = self._find_items_by_name(file_name, folder_id)
        if error:
            return None
        if files:
            logger.info(f"the file {file_name} exists in {folder_id}")
            return files
        else:
            logger.info(f"the file {file_name} does not exists in {folder_id}")
            return None


    def check_folder_exists(self, folder_name):
        """
        检查云盘根目录下是否存在指定名称的文件夹
        :param folder_name: 文件夹名称
        :return: 存在返回True，不在返回False
        """
        files, error = self._find_items_by_name(folder_name, None, "files(id)")
        if error:
            return "TOKEN_EXPIRED"
        if files:
            logger.info(f"the folder {folder_name} exists in the cloud drive")
            return "小艺Work目录存在"
        else:
            logger.info(f"the folder {folder_name} does not exists in cloud drive")
            return "小艺Work目录不存在"


    def create_file_dir(self, dir_name, parent_folder_id):
        """
        在指定父目录下建文件夹（管道端点 /drive/mkdir）。

        :return: 成功 {"id": ...}；票据类失败 "TOKEN_EXPIRED"；其他失败 None
        """
        logger.info("create dir: {} in parent: {}".format(dir_name, parent_folder_id))
        try:
            data = self._call("/drive/mkdir", {"name": dir_name, "parentId": parent_folder_id})
        except DriveCallError as e:
            if _is_auth_failure(e.code):
                logger.error(f"创建目录失败（票据类）: {e.message}")
                return "TOKEN_EXPIRED"
            logger.error(f"创建目录失败: {e.message}")
            return None
        return {"id": data.get("id")}

    def query_file(self, file_name, parent_folder_id):
        """
        查询指定文件夹中是否存在指定文件
        :param file_name: 件名
        :param parent_folder_id: 父文件夹ID
        :return: 文件ID或空字符串
        """
        files, error = self._find_items_by_name(file_name, parent_folder_id, "files(id)")
        if error:
            return "TOKEN_EXPIRED"
        if files:
            return files[0]["id"]
        return ""


    def upload_local_file(self, file_path, parent_folder_id, mode):
        """
        上传本地文件到指定云盘目录（管道端点 /drive/upload；主进程走 resume 分片）。

        :param mode: overwrite=覆盖同名文件；rename=同名时交给服务端另存
        :return: 成功 {"file_id": ...}；失败 {"error": <code>, "message": ...}
        """
        payload = {
            "localPath": file_path,
            "name": os.path.basename(file_path),
            "parentId": parent_folder_id,
            "overwrite": mode != "rename",
        }
        logger.info(f"上传文件经云盘代理: {payload['name']} → parent={parent_folder_id} mode={mode}")
        try:
            data = self._call("/drive/upload", payload)
        except DriveCallError as e:
            return {"error": e.code, "message": e.message}
        return {"file_id": data.get("fileId")}

    def download_file(self, file_id, download_path):
        """
        下载云盘文件到本地（管道端点 /drive/download；主进程流式落盘）。

        :return: 结果字典（status / error_code / message；成功再带 download_path）
        """
        result = {
            "status": "success",
            "file_id": file_id,
            "download_path": download_path,
        }
        logger.info(f"下载云盘文件经云盘代理: {file_id} → {download_path}")
        try:
            data = self._call("/drive/download", {"fileId": file_id, "destPath": download_path})
        except DriveCallError as e:
            if _is_auth_failure(e.code):
                result.update(_auth_failure_result(e.code))
                return result
            result["status"] = "error"
            result["error_code"] = "DOWNLOAD_FAILED"
            result["message"] = f"下载文件失败: {e.message}"
            return result
        # 目标已有同名文件时主进程会另存（如 xxx (1).txt），以实际落地路径为准
        result["download_path"] = data.get("path") or download_path
        result["message"] = "文件下载成功"
        logger.info(f"文件下载成功: {result['download_path']}")
        return result

    def rename_file(self, file_id, new_file_name):
        """
        重命名云盘条目（管道端点 /drive/rename）。

        :return: 结果字典
        """
        try:
            self._call("/drive/rename", {"fileId": file_id, "newName": new_file_name})
        except DriveCallError as e:
            if _is_auth_failure(e.code):
                return _auth_failure_result(e.code)
            logger.error(f"文件重命名失败: {e.message}")
            return create_error_result("RENAME_FAILED", f"重命名失败: {e.message}")
        logger.info(f"文件重命名成功，file_id: {file_id}, new_name: {new_file_name}")
        return create_success_result(file_id=file_id, new_file_name=new_file_name, message="文件重命名成功")

    def move_file(self, file_id, source_parent_id, destination_parent_id):
        """
        移动文件到指定父目录（管道端点 /drive/move）。

        :return: 结果字典（status / error_code / message）
        """
        try:
            self._call("/drive/move", {
                "fileId": file_id,
                "removeParentFolder": source_parent_id,
                "addParentFolder": destination_parent_id,
            })
        except DriveCallError as e:
            if _is_auth_failure(e.code):
                return _auth_failure_result(e.code)
            logger.error(f"文件移动失败: {e.message}")
            return create_error_result("MOVE_FAILED", f"移动失败: {e.message}")
        logger.info(f"文件移动成功，file_id: {file_id}, destination_parent_id: {destination_parent_id}")
        return create_success_result(
            file_id=file_id,
            destination_parent_id=destination_parent_id,
            message="文件移动成功",
        )

    def get_file_list_recursive(self, folder_id, depth=0):
        """
        递归遍历指定文件夹下的所有子文件及子文件夹
        :param folder_id: 云盘文件夹ID
        :param depth: 当前递归深度，用于缩进显示
        :return: 文件夹下所有文件和文件夹的列表
        """
        result = {
            "status": "success",
            "folder_id": folder_id,
            "files": []
        }
        
        # 使用 _paginated_list 获取分页文件列表
        all_files, error = self._paginated_list(folder_id)
        if error:
            return error
        
        # 递归处理子件夹
        for file_info in all_files:
            file_info["depth"] = depth
            is_folder = file_info.get("mimeType") == "application/vnd.huawei-apps.folder"
            file_info["is_folder"] = is_folder
            result["files"].append(file_info)
            
            # 如果是文件夹，递归获取其内容
            if is_folder:
                sub_result = self.get_file_list_recursive(file_info["id"], depth + 1)
                if sub_result["status"] == "error":
                    return sub_result
                result["files"].extend(sub_result["files"])
        
        logger.info(f"Total files and folders in folder {folder_id}: {len(result['files'])}")
        return result


def set_upload_result(result, status, message):
    result["status"] = status
    result["message"] = message
    logger.info(json.dumps(result))
    print(json.dumps(result, ensure_ascii=False))


def query_space_detail(auth):
    """
    查询云空间详情
    :param auth: 认证token
    :return: int类型可用空间
    """
    hw_drive = UploadFileHwDrive(auth)
    result = hw_drive.get_space_detail()
    return result

def query_available_space(auth):
    """
    查询云空间剩余可用空间
    :param auth: 认证token
    :return: int类型可用空间
    """
    hw_drive = UploadFileHwDrive(auth)
    available_space = hw_drive.get_clouddrive_available_space()
    if available_space == "TOKEN_EXPIRED":
        print_drive_unavailable()
        return -1
    logger.info(f"available space is {available_space}")
    return int(available_space)


def get_celiaclaw_file_list(auth):
    """
    查询文件是否存在
    :param auth: 认证token
    :return: 小艺Work目录下的文件列表
    """
    hw_drive = UploadFileHwDrive(auth)
    folder_id = hw_drive.get_celiaclaw_file_id()
    if folder_id == "TOKEN_EXPIRED":
        print_drive_unavailable()
        return "TOKEN_EXPIRED"
    if folder_id == "":
        print(f"{FOLDER_NOT_EXIST}")
        return f"{FOLDER_NOT_EXIST}"
    # 递归查询文件列表
    result = hw_drive.get_file_list_recursive(folder_id)
    print(result)
    return result

def query_file_exists(auth, file_name):
    """
    查询文件是否存在
    :param auth: 认证token
    :param file_name: 文件名
    :return: 0表示存在，1表示不存在
    """
    hw_drive = UploadFileHwDrive(auth)
    parent_folder_id = hw_drive.get_celiaclaw_file_id()
    if parent_folder_id == "TOKEN_EXPIRED":
        print_drive_unavailable()
        return "TOKEN_EXPIRED"
    if parent_folder_id == "":
        # 文件夹不存在，文件也不存在
        print(f"{FILE_NOT_EXIST}")
        return f"{FILE_NOT_EXIST}"
    result = hw_drive.check_file_exists_recursive(file_name, parent_folder_id)
    print(result)
    return result


def query_folder_exists(auth, folder_name):
    """
    查询文件夹是否存在
    :param auth: 认证token
    :param folder_name: 文件夹名称
    :return: 0表示存在，1表示不存在,
    """
    hw_drive = UploadFileHwDrive(auth)
    result = hw_drive.check_folder_exists(folder_name)
    if result == "TOKEN_EXPIRED":
        print_drive_unavailable()
    print(result)
    return result


def create_folder(auth, folder_name):
    """
    在云盘根路径下创建文件夹
    :param auth: 认证token
    :param folder_name: 文件夹名称
    """
    if (folder_name != PARENT_FOLDER_NAME):
        logger.error("the folder name is not allowed")
        return 1
    hw_drive = UploadFileHwDrive(auth)
    create_result = hw_drive.create_file_dir(folder_name, "root")
    if create_result == "TOKEN_EXPIRED":
        print_drive_unavailable()
        return -1
    if create_result:
        logger.info(f"create the folder {folder_name} success")
        return 0
    else:
        logger.info(f"create the folder {folder_name} fail")
        return 1

def create_folder_in_parent(auth, folder_name, parent_folder_name):
    """
    在云盘指定路径下创建文件夹
    :param auth: 认证token
    :param folder_name: 文件夹名称
    :param parent_folder_name 父目录文件夹名称
    """
    hw_drive = UploadFileHwDrive(auth)
    celiaclaw_folder_id = hw_drive.get_celiaclaw_file_id()
    if celiaclaw_folder_id == "TOKEN_EXPIRED":
        print_drive_unavailable()
        return "TOKEN_EXPIRED"
    if celiaclaw_folder_id == "":
        # 文件夹不存在，文件也不存在
        print(f"{FILE_NOT_EXIST}")
        return f"{FILE_NOT_EXIST}"
    parent_folder = hw_drive.check_file_exists_recursive(parent_folder_name, celiaclaw_folder_id)
    parent_folder_file = parent_folder["file"]
    parent_folder_id = parent_folder_file[0]["id"]
    create_result = hw_drive.create_file_dir(folder_name, parent_folder_id)
    print(json.dumps(create_result, ensure_ascii=False))
    return create_result

def download_file_by_name(auth, file_name, download_path):
    """
    通过文件名下载云盘文件
    :param auth: 认证token
    :param file_name: 云盘文件名
    :param download_path: 本地下载路径
    :return: 下载结果字典
    """
    hw_drive = UploadFileHwDrive(auth)
    parent_folder_id = hw_drive.get_celiaclaw_file_id()
    
    if parent_folder_id == "TOKEN_EXPIRED":
        return print_drive_unavailable()
    
    if parent_folder_id == "":
        result = {
            "status": "error",
            "error_code": "FOLDER_NOT_EXIST",
            "message": "小艺Work目录不存在"
        }
        logger.error("小艺Work目录不存在")
        print(json.dumps(result, ensure_ascii=False))
        return result
    
    # 递归查找文件
    file_result = hw_drive.check_file_exists_recursive(file_name, parent_folder_id)
    
    if file_result["status"] == "error":
        logger.error(f"文件 {file_name} 不存在")
        print(json.dumps(file_result, ensure_ascii=False))
        return file_result
    
    file_info = file_result["file"]
    file_id = file_info[0]["id"]
    logger.info(f"找到文件 {file_name}, file_id: {file_id}")
    
    # 下载文件
    result = hw_drive.download_file(file_id, download_path)
    
    if result["status"] == "error" and result.get("error_code") == "TOKEN_EXPIRED":
        print_drive_unavailable()
        return result
    
    logger.info(json.dumps(result))
    print(json.dumps(result, ensure_ascii=False))
    return result


def download_file_by_fileId(auth, file_id, download_path):
    """
    下载云盘文件
    :param auth: 认证token
    :param file_id: 云盘文件ID
    :param download_path: 本地下载路径
    :return: 下载结果字典
    """
    hw_drive = UploadFileHwDrive(auth)
    result = hw_drive.download_file(file_id, download_path)
    
    if result["status"] == "error" and result.get("error_code") == "TOKEN_EXPIRED":
        print_drive_unavailable()
        return result
    
    logger.info(json.dumps(result))
    print(json.dumps(result, ensure_ascii=False))
    return result


def rename_file_in_celiaclaw(auth, file_id, new_file_name):
    """
    重命名云盘文件
    :param auth: 认证token
    :param file_id: 云盘文件ID
    :param new_file_name: 新文件名
    :return: 重命名结果字典
    """
    hw_drive = UploadFileHwDrive(auth)
    result = hw_drive.rename_file(file_id, new_file_name)
    
    if result["status"] == "error" and result.get("error_code") == "TOKEN_EXPIRED":
        print_drive_unavailable()
        return result
    
    logger.info(json.dumps(result))
    print(json.dumps(result, ensure_ascii=False))
    return result


def move_file_to_folder(auth, file_id, source_parent_id, destination_parent_id):
    """
    移动文件到指定文件夹
    :param auth: 认证token
    :param file_id: 云盘文件ID
    :param source_parent_id: 原父目录ID
    :param destination_parent_id 目标父目录ID
    :return: 移动结果字典
    """
    hw_drive = UploadFileHwDrive(auth)
    result = hw_drive.move_file(file_id, source_parent_id, destination_parent_id)
    
    if result["status"] == "error" and result.get("error_code") == "TOKEN_EXPIRED":
        print_drive_unavailable()
        return result
    
    logger.info(json.dumps(result))
    print(json.dumps(result, ensure_ascii=False))
    return result


def query_folder_file_list(auth, folder_id):
    """
    递归查询指定文件夹下的所有子文件及子文件夹
    :param auth: 认证token
    :param folder_id: 件夹ID
    :return: 文件列表结果
    """
    hw_drive = UploadFileHwDrive(auth)
    result = hw_drive.get_file_list_recursive(folder_id)
    
    if result["status"] == "error" and result.get("error_code") == "TOKEN_EXPIRED":
        print_drive_unavailable()
        return result
    
    # 打印所有文件信息
    logger.info(json.dumps(result))
    print(json.dumps(result, ensure_ascii=False))
    return result

def upload_file_to_drive(hw_drive, file_path, parent_folder_id, mode, result):
    """把本地文件传到指定云盘目录（保持旧签名，父目录由调用方解析）。"""
    if not os.path.exists(file_path):
        set_upload_result(result, "error", f"本地文件不存在: {file_path}")
        return
    upload_result = hw_drive.upload_local_file(file_path, parent_folder_id, mode)
    if upload_result.get("error"):
        if _is_auth_failure(upload_result["error"]):
            print_drive_unavailable(upload_result["error"])
            return -1
        set_upload_result(result, "error", f"文件上传失败: {upload_result.get('message', '')}")
        return
    result["file_id"] = upload_result.get("file_id")
    set_upload_result(result, "success", "文件上传成功")

def upload_file_to_celiaclaw(auth, file_path, mode):
    """上传文件到云盘根目录下的「小艺Work」（管道端点 /drive/upload）。"""
    result = {
        "status": "success",
        "mode": "upload",
        "file_id": None,
        "file_path": file_path,
    }
    if not os.path.exists(file_path):
        set_upload_result(result, "error", f"本地文件不存在: {file_path}")
        return
    hw_drive = UploadFileHwDrive(auth)
    parent_folder_id = hw_drive.get_celiaclaw_file_id()
    if parent_folder_id == "TOKEN_EXPIRED":
        print_drive_unavailable()
        return -1
    if parent_folder_id == "":
        created = hw_drive.create_file_dir(PARENT_FOLDER_NAME, "root")
        if created == "TOKEN_EXPIRED":
            print_drive_unavailable()
            return -1
        parent_folder_id = created.get("id") if isinstance(created, dict) else ""
    if not parent_folder_id:
        set_upload_result(result, "error", "创建文件夹失败")
        return
    upload_file_to_drive(hw_drive, file_path, parent_folder_id, mode, result)

def upload_file_to_folder(auth, file_path, parent_folder_name, mode):
    result = {
        "status": "success",
        "mode": mode,
        "file_id": None,
        "file_path": file_path
    }
    hw_drive = UploadFileHwDrive(auth)
    celiaclaw_folder_id = hw_drive.get_celiaclaw_file_id()
    if celiaclaw_folder_id == "TOKEN_EXPIRED":
        print_drive_unavailable()
        return "TOKEN_EXPIRED"
    if celiaclaw_folder_id == "":
        # 文件夹不存在，文件也不存在
        print(f"{FILE_NOT_EXIST}")
        return f"{FILE_NOT_EXIST}"
    parent_folder = hw_drive.check_file_exists_recursive(parent_folder_name, celiaclaw_folder_id)
    # if parent_folder.get("file")
    parent_folder_file = parent_folder["file"]
    parent_folder_id = parent_folder_file[0]["id"]
    upload_file_to_drive(hw_drive, file_path, parent_folder_id, mode, result)
    print(json.dumps(result, ensure_ascii=False))
    return result

def parse_arguments():
    parser = argparse.ArgumentParser(description="Huawei Cloud Drive CLI")
    parser.add_argument("--command", type=str, 
                        choices=["query", "query_folder", "upload", "create", "download", "rename", "move"],
                        help="命令类型: query, query_folder, upload, create, download, rename, move")
    parser.add_argument("--key", type=str, help="查询ID，用于query命令")
    parser.add_argument("--file_name", type=str, help="文件名，用于query或query_folder命令")
    parser.add_argument("--file_id", type=str, help="文件ID，用于download、rename和move命令")
    parser.add_argument("--source_parent_id", type=str, help="原父目录ID，用于move命令")
    parser.add_argument("--destination_parent_id", type=str, help="目标父目录ID，用于move命令")
    parser.add_argument("--mode", type=str, 
                        choices=["overwrite", "rename"],
                        help="上传模式: overwrite或rename")
    parser.add_argument("--folder_name", type=str, help="文件夹名称，用于create命令")
    parser.add_argument("--parent_folder_name", type=str, help="父目录名称，用于create命令")
    parser.add_argument("--path", type=str, help="文件路径: path=上传文件路径或download下载目标路径")
    return parser.parse_args()

def main():
    args = parse_arguments()
    # 凭据由小艺Work主进程托管（经 np://claw-cloud-drive 注入），这里不需要任何 token
    auth = ""

    # 根据command分发到不同处理逻辑
    command = args.command
    
    if command == "query":
        # 查询命令
        if args.key == "space":
            # 查询可用空间
            return query_space_detail(auth)
        elif args.key == "available_space":
            # 查询可用空间
            return query_available_space(auth)
        elif args.key == "file_list":
            if args.file_id:
                # 递归查询指定文件夹下的所有子文件及子文件夹
                return query_folder_file_list(auth, args.file_id)
            else:
                # 查询小艺Work目录下的文件列表
                return get_celiaclaw_file_list(auth)
        elif args.file_name:
            # 查询文件是否存在
            return query_file_exists(auth, args.file_name)
        else:
            print("please specify --key available_space or --file_name <file_name>")
            sys.exit(1)
    
    elif command == "query_folder":
        # 查询文件夹是否存在
        if args.file_name:
            return query_folder_exists(auth, args.file_name)
        else:
            print("please specify --file_name <folder_name>")
            sys.exit(1)
    
    elif command == "upload":
        # 上传命令
        if not args.path:
            print("please input --path xxx")
            sys.exit(1)
        if not args.mode:
            print("please specify --mode overwrite or --mode rename")
            sys.exit(1)
        if not args.parent_folder_name:
            return upload_file_to_celiaclaw(auth, args.path, args.mode)
        return upload_file_to_folder(auth, args.path, args.parent_folder_name, args.mode)
    
    elif command == "create":
        # 创建文件夹命令
        if not args.folder_name:
            print("please specify --folder_name <folder_name>")
            sys.exit(1)
        if not args.parent_folder_name:
            return create_folder(auth, args.folder_name)
        return create_folder_in_parent(auth, args.folder_name, args.parent_folder_name)
    
    elif command == "download":
        # 下载文件命令
        if not args.path:
            print("please specify --path <download_path>")
            sys.exit(1)
        if args.file_name:
            # 通过文件名下载
            return download_file_by_name(auth, args.file_name, args.path)
        elif args.file_id:
            # 通过文件ID下载
            return download_file_by_fileId(auth, args.file_id, args.path)
        else:
            print("please specify --file_name <file_name> or --file_id <file_id>")
            sys.exit(1)
    
    elif command == "rename":
        # 重命名文件命令
        if not args.file_id:
            print("please specify --file_id <file_id>")
            sys.exit(1)
        if not args.file_name:
            print("please specify --file_name <new_file_name>")
            sys.exit(1)
        return rename_file_in_celiaclaw(auth, args.file_id, args.file_name)
    
    elif command == "move":
        # 移动文件命令
        if not args.file_id:
            print("please specify --file_id <file_id>")
            sys.exit(1)
        if not args.source_parent_id:
            print("please specify --source_parent_id <source_parent_folder_id>")
            sys.exit(1)
        if not args.destination_parent_id:
            print("please specify --destination_parent_id <destination_parent_folder_id>")
            sys.exit(1)
        return move_file_to_folder(auth, args.file_id, args.source_parent_id, args.destination_parent_id)

if __name__ == "__main__":
    main()