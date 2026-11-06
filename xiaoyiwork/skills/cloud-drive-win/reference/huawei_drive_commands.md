# Huawei Drive 命令快速参考

## 目录

- [查询命令](#查询命令)
- [上传命令](#上传命令)
- [文件夹命令](#文件夹命令)
- [下载命令](#下载命令)
- [文件更新命令](#文件更新命令)

---

## 查询命令

### 查询云空间详情

```bash
cloud_drive.py --command query --key space
```

**返回**：云盘总空间、已用空间、可用空间（单位：Byte）

### 查询可用空间

```bash
cloud_drive.py --command query --key available_space
```

**返回**：int 类型，云空间剩余可用空间（单位：Byte）

### 查询文件列表

```bash
cloud_drive.py --command query --key file_list
```

**返回**：`小艺Work` 文件夹下的所有文件列表，包括所有子文件夹下的子文件

### 递归查询某个文件夹下的文件列表

```
cloud_drive.py --command query --key file_list --file_id {folder_id}
```

**返回**：文件夹`{folder_id}`下的所有文件，包括所有子文件夹下的子文件

### 检查文件/文件夹是否存在

```bash
cloud_drive.py --command query --file_name {file_name}
```

**返回**：

- 成功：文件详细信息
- 失败：失败原因

---

## 上传命令

### 覆盖上传

1、上传文件到`小艺Work`文件夹中，文件已存在则覆盖：

```bash
cloud_drive.py --command upload --mode overwrite --path {file_path}
```

2、上传文件到指定文件夹（`parent_folder_name`）下，文件已存在则覆盖：

```bash
cloud_drive.py --command upload --mode overwrite --path {file_path} --parent_folder_name {parent_folder_name}
```

### 重命名上传

1、上传文件到`小艺Work`文件夹中，文件已存在则自动重命名（添加 `(1)` 后缀）

```bash
cloud_drive.py --command upload --mode rename --path {file_path}
```

2、上传文件到指定文件夹（`parent_folder_name`）下，文件已存在则自动重命名（添加 `(1)` 后缀）

```bash
cloud_drive.py --command upload --mode rename --path {file_path} --parent_folder_name {parent_folder_name}
```

---

## 文件夹命令

### 创建文件夹

1、默认在云盘`root`目录下创建`小艺Work`文件夹

```bash
cloud_drive.py --command create --folder_name 小艺Work
```

**说明**：在云盘根路径下创建 `小艺Work` 文件夹

2、在`{parent_folder_name}`目录下创建`{folder_name}`文件夹

```bash
cloud_drive.py --command create --folder_name {folder_name} --parent_folder_name {parent_folder_name}
```

说明：`{folder_name}`为需要创建的文件夹名称，`{parent_folder_name}`为创建文件夹的父目录

---

## 下载命令

### 下载文件

根据文件名下载云盘文件

```bash
cloud_drive.py --command download --file_name {file_name} --path {download_path}
```

**示例：**

```bash
cloud_drive.py --command download --file_name abc.txt --path "%USERPROFILE%\Downloads\abc.txt"
```

根据文件Id下载云盘文件（`--path` 给完整文件路径，或只给目标目录——此时按云盘上的文件名落盘；命令返回的 `download_path` 是实际落地路径，同名冲突会另存为 `xxx (1).ext`，以它为准）

```bash
cloud_drive.py --command download --file_id {file_id} --path {download_path}
```

**示例**：

```bash
cloud_drive.py --command download --file_id abc123def456 --path "%USERPROFILE%\Downloads\downloaded_file.txt"
```

---

## 文件更新命令

### 重命名文件

```bash
cloud_drive.py --command rename --file_id {file_id} --file_name {new_file_name}
```

**说明**：根据文件ID重命名云盘文件

**示例**：

```bash
cloud_drive.py --command rename --file_id abc123def456 --file_name new_name.txt
```

---

### 移动文件

```bash
cloud_drive.py --command move --file_id {file_id} --source_parent_id {source_parent_id} --destination_parent_id {destination_parent_id}
```



## 参数说明

| 参数 | 说明 | 示例 |
|-----|------|------|
| `--command` | 操作类型 | `query`, `upload`, `create`, `query_folder`, `download`, `rename` |
| `--key` | 查询类型 | `space`, `available_space`, `file_list` |
| `--file_name` | 文件名 | `test.txt` |
| `--file_id` | 文件ID | `abc123def456` |
| `--mode` | 上传模式 | `overwrite`（覆盖）, `rename`（重命名） |
| `--path` | 文件路径 | `/path/to/file.txt` |
| `--folder_name` | 文件夹名称 | `小艺Work` |
| `--source_parent_id` | 原父目录ID |  |
| `--destination_parent_id` | 目标父目录ID |  |

