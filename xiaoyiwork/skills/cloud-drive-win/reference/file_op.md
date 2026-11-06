# 文件操作指南

支持文件上传、下载、列表查询、重命名、创建文件夹、文件存在性检查、移动文件。

## 目录

- [通用规范](#通用规范)
- [上传文件](#上传文件)
- [下载文件](#下载文件)
- [查询文件列表](#查询文件列表)
- [查询文件/文件夹是否存在](#查询文件文件夹是否存在)
- [创建文件夹](#创建文件夹)
- [重命名文件](#重命名文件)
- [移动文件](#移动文件)
- [常见错误处理](#常见错误处理)

---

## 通用规范

### 路径规则

1. 根目录：统一以 `/我的云盘/小艺Work` 为业务根目录，所有操作默认限定在此目录内。
2. 路径分隔符：统一使用 `/`，不支持 `\`。
3. 大小写：云盘路径、文件名**区分大小写**。
4. 路径类型：支持绝对路径、相对路径。

### 命名与字符约束

1. 文件名 / 文件夹名最大长度：单级名称不超过 255 字符，完整路径总长度不超过 4096 字符。
2. 禁止字符：`/ \ : * ? " < > |` 及全角对应符号、控制字符、隐藏字符。
3. 系统保留名：禁止使用 `con`、`nul`、`aux`、`com1`、`lpt1` 等系统保留名称。
4. Emoji：文件名 / 目录名**不支持 Emoji**。

### 全局变量说明

| 占位符 | 含义 | 是否必填 |
|--------|------|---------|
| `{file_path}` | 本地文件完整路径 | 是 |
| `{file_name}` | 文件/文件夹名称 | 是 |
| `{file_id}` | 云盘文件 fileId | 是 |
| `{download_path}` | 文件下载路径：完整文件路径，或只给目标目录（此时按云盘文件名落盘） | 是 |
| `{cloud_file_path}` | 云盘文件 / 目录完整路径 | 是 |
| `{local_save_path}` | 本地保存目录完整路径 | 是 |
| `{source_path}` | 移动 / 复制源路径 | 是 |
| `{target_path}` | 移动 / 复制目标路径 | 是 |
| `{old_path}` | 重命名原路径 | 是 |
| `{file_new_name}` | 新文件 / 目录名称 | 是 |
| `{parent_dir}` | 新建文件夹的父目录 | 是 |
| `{folder_name}` | 新建文件夹名称 | 是 |
| `{keyword}` | 搜索关键词 | 是 |

### 前置步骤（所有操作通用）

执行任何云盘操作前无需检查任何凭据：云盘操作经小艺Work的云盘代理（`np://claw-cloud-drive`）执行，鉴权由小艺Work主进程注入；票据暂时不可用时重试即可。

---

## 上传文件

### 执行流程

1. **前置步骤**：无需检查凭据（云盘鉴权由小艺Work托管）
2. **获取文件路径**：从用户输入或上下文确定 `{file_path}`
3. **确定目标文件夹**：从用户输入中确定 `{parent_folder_name}`，未指定则默认上传到 `小艺Work` 文件夹下
4. **检查文件大小**：计算 `{file_size}`
5. **检查可用空间**：查询云空间剩余 `{available_space}`
   - 若 `available_space < file_size`，提示用户升级套餐
6. **检查文件重名**：若文件已存在，询问用户选择：覆盖 / 重命名 / 跳过
   - 重命名规则：在原文件名后添加 `(1)`，如 `test.txt` → `test(1).txt`
7. **执行上传**：调用 `cloud_drive.py` 完成上传
8. **多文件处理**：循环执行上述步骤，最后输出汇总报告
9. **输出结果**：生成查看文件的超链接

> **重要**：必须上传用户原文件，严禁压缩后再上传。

### 命令

```bash
# 上传到小艺Work目录（覆盖模式）
cloud_drive.py --command upload --mode overwrite --path {file_path}

# 上传到小艺Work目录（重命名模式）
cloud_drive.py --command upload --mode rename --path {file_path}

# 上传到指定子文件夹
cloud_drive.py --command upload --mode overwrite --path {file_path} --parent_folder_name {parent_folder_name}
```

### 输出格式

**单个文件上传成功：**

```markdown
文件上传完成！

| 云盘路径           | 文件大小 | 状态   |
| ------------------ | -------- | ------ |
| 小艺Work/test1.txt | 2.45 MB  | ✅ 成功 |
```

若当前操作系统为鸿蒙操作系统，则输出如下超链接：

[点击前往 文件管理 - 我的云盘 查看文件](superlink://vassistant?startmode=appLink&appLink=filemanager://openDirectory?fileUri=file%3A%2F%2Fcom.huawei.hmos.filemanager%2Fdata%2Fstorage%2Fel2%2Fcloud%2F%E5%B0%8F%E8%89%BAClaw)。

**多个文件上传汇总：**

```markdown
文件上传完成！

| 云盘路径           | 文件大小 | 状态   |
| ------------------ | -------- | ------ |
| 小艺Work/test1.txt | 2.45 MB  | ✅ 成功 |
| 小艺Work/test2.txt | 4.0 KB   | ✅ 成功 |
| 小艺Work/test3.txt | 6.0 KB   | ❌ 失败 |
```

若当前操作系统为鸿蒙操作系统，则输出如下超链接：

[点击前往 文件管理 - 我的云盘 查看文件](superlink://vassistant?startmode=appLink&appLink=filemanager://openDirectory?fileUri=file%3A%2F%2Fcom.huawei.hmos.filemanager%2Fdata%2Fstorage%2Fel2%2Fcloud%2F%E5%B0%8F%E8%89%BAClaw)。

如果提示"路径不存在"，请确认云空间的云盘开关是否已开启。

---

## 下载文件

### 执行流程

1. **前置步骤**：无需检查凭据（云盘鉴权由小艺Work托管）
2. **云盘文件查询**：根据文件名查询云端文件是否存在，获取 `{file_id}`。若不存在则终止，返回`云端文件不存在`
3. **获取参数**：文件 `{file_id}`、下载路径 `{download_path}`（给完整文件路径；也可只给目录，此时按云盘上的文件名落盘）
4. **本地重名校验**：若本地存在同名文件，弹出选择：覆盖 / 重命名 / 跳过
5. **执行下载**：调用 `cloud_drive.py`，传入 `{file_id}` 及 `{download_path}`；**以命令返回的 `download_path` 为准**（目标同名已存在时会被另存为 `xxx (1).ext`）
6. **批量规则**：单次批量下载最多 100 个文件；目录下载默认**非递归**
7. **输出结果**：生成汇总结果

### 命令

```bash
cloud_drive.py --command download --file_id {file_id} --path {download_path}
```

### 输出格式

```markdown
文件下载完成！

| 云盘路径           | 本地保存路径                 | 文件大小 | 状态   |
| ------------------ | ---------------------------- | -------- | ------ |
| 小艺Work/test1.txt | C:/Users/Downloads/test1.txt | 2.45 MB  | ✅ 成功 |
| 小艺Work/test2.txt | C:/Users/Downloads/test2.txt | 4.0 KB   | ✅ 成功 |
| 小艺Work/test3.txt | C:/Users/Downloads/test3.txt | 6.0 KB   | ❌ 失败 |
```

---

## 查询文件列表

### 执行流程

1. **前置步骤**：无需检查凭据（云盘鉴权由小艺Work托管）
2. **查询小艺Work目录**（默认）：

```bash
cloud_drive.py --command query --key file_list
```

3. **查询指定目录**：先查询文件夹是否存在获取 `{folder_id}`，再执行：

```bash
cloud_drive.py --command query --key file_list --file_id {folder_id}
```

### 输出格式

**必须按文件路径层级显示，输出样例如下：**

```markdown
当前查询目录：/我的云盘/小艺Work, 详情如下：

我的云盘/小艺Work/
├── 📁 test20260908/
│   └── 📄 屏幕截图(7).png  (3.6 MB, 2026-09-08 20:56:02)
└── 📄 abc.exe  (462.9 MB, 2026-09-08 20:45:10)
```

若当前操作系统为鸿蒙操作系统，则输出如下超链接：

[点击前往 文件管理 - 我的云盘 查看文件](superlink://vassistant?startmode=appLink&appLink=filemanager://openDirectory?fileUri=file%3A%2F%2Fcom.huawei.hmos.filemanager%2Fdata%2Fstorage%2Fel2%2Fcloud%2F%E5%B0%8F%E8%89%BAClaw)。

### 数据说明

- **文件大小**：查询结果单位为 Byte，需转换为 GB/MB/KB
- **文件类型识别**：
  - 目录：`mimeType` = `application/vnd.huawei-apps.folder`
  - 其他：按文件后缀识别（图片、视频、音频、文件等）

---

## 查询文件/文件夹是否存在

### 命令

```bash
cloud_drive.py --command query --file_name {file_name}
```

### 输出格式

```markdown
当前查询目录：/我的云盘/小艺Work

| 类型 | 文件名称   | 文件大小 | 修改时间             |
| ---- | ---------- | -------- | -------------------- |
| 文件 | readme.txt | 1.5MB    | 2026-02-25  15:20:00 |
```

若当前操作系统为鸿蒙操作系统，则输出如下超链接：

[点击前往 文件管理 - 我的云盘 查看文件](superlink://vassistant?startmode=appLink&appLink=filemanager://openDirectory?fileUri=file%3A%2F%2Fcom.huawei.hmos.filemanager%2Fdata%2Fstorage%2Fel2%2Fcloud%2F%E5%B0%8F%E8%89%BAClaw)。

## 创建文件夹

### 执行流程

1. **前置步骤**：无需检查凭据（云盘鉴权由小艺Work托管）
2. **获取参数**：文件夹名称 `{folder_name}` 及父目录 `{parent_folder_name}`，未指定则默认为 `小艺Work`
3. **创建文件夹**：

```bash
cloud_drive.py --command create --folder_name {folder_name} --parent_folder_name {parent_folder_name}
```

4. **输出结果**：

```markdown
文件夹上传完成！

| 云盘路径      | 文件夹名称 | 状态    |
| -------------|--------- | ------ |
| 小艺Work/test | test     | ✅ 成功 |

```

若当前操作系统为鸿蒙操作系统，则输出如下超链接：

[点击前往 文件管理 - 我的云盘 查看文件](superlink://vassistant?startmode=appLink&appLink=filemanager://openDirectory?fileUri=file%3A%2F%2Fcom.huawei.hmos.filemanager%2Fdata%2Fstorage%2Fel2%2Fcloud%2F%E5%B0%8F%E8%89%BAClaw)。

## 重命名文件

### 执行流程

1. **前置步骤**：无需检查凭据（云盘鉴权由小艺Work托管）
2. **云盘文件查询**：根据原文件名查询云端文件是否存在，获取 `{file_id}`。若不存在则终止
3. **获取参数**：文件 `{file_id}`、新文件名 `{new_file_name}`
4. **合法性校验**：新名称遵循【通用规范】字符、长度、系统保留名规则
5. **重名校验**：同目录下已存在同名则直接拦截
6. **执行重命名**：

```bash
cloud_drive.py --command rename --file_id {file_id} --file_name {new_file_name}
```

7. **输出结果**：

```markdown
文件/文件夹重命名完成！

| 原名称    | 新名称     | 路径                | 状态   |
| --------- | ---------- | ------------------- | ------ |
| test1.txt | report.txt | 小艺Work/report.txt | ✅ 成功 |
```

若当前操作系统为鸿蒙操作系统，则输出如下超链接：

[点击前往 文件管理 - 我的云盘 查看文件](superlink://vassistant?startmode=appLink&appLink=filemanager://openDirectory?fileUri=file%3A%2F%2Fcom.huawei.hmos.filemanager%2Fdata%2Fstorage%2Fel2%2Fcloud%2F%E5%B0%8F%E8%89%BAClaw)。

## 移动文件

### 执行流程

1. **前置步骤**：无需检查凭据（云盘鉴权由小艺Work托管）
2. **云盘文件查询**：根据原文件名查询云端文件，获取 `{file_id}` 及当前父目录 `{source_parent_id}`。若不存在则终止
3. **目标路径查询**：根据目标文件夹名称查询云端 `{destination_parent_id}`。若不存在则终止
4. **重名校验**：若目标目录下已存在同名文件，提示用户文件将被重命名
5. **执行移动**：

```bash
cloud_drive.py --command move --file_id {file_id} --source_parent_id {source_parent_id} --destination_parent_id {destination_parent_id}
```

6. **输出结果**：输出移动结果（成功或失败）

---

## 常见错误处理

| 异常场景 | 处理逻辑 | 输出文案 |
|---------|---------|---------|
| **网络异常** | 自动重试 1 次，失败则终止 | 上传：`上传失败，请检查网络后重试`<br>多文件：`部分文件上传失败，请检查网络后重试`<br>查询：`❌ 文件列表查询失败，请检查网络后重试` |
| **文件过大** | 终止该文件，其他文件继续上传 | `❌ 上传失败，文件「文件名.ext」超出云盘单个文件大小限制` |
| **基础服务用户**（总空间=0） | 终止操作，引导升级 | `⚠️ 您当前为基础服务用户，不支持上传文件，请 [点击前往云空间升级套餐](superlink://vassistant?uri=hicloud%3A%2F%2FcloudDrive%2Fgetinfo%3Fpage%3DMemberBuyPage%26finishType%3D1%26pageDetails%3D%7B%22uri%22%3A%22buy_more%22%7D&bundleName=com.huawei.hmos.clouddrive)` |
| **空间不足**（总空间>0，可用空间=0） | 终止上传，引导升级 | `⚠️ 云空间空间不足，请 [点击前往云空间升级套餐](superlink://vassistant?uri=hicloud%3A%2F%2FcloudDrive%2Fgetinfo%3Fpage%3DMemberBuyPage%26finishType%3D1%26pageDetails%3D%7B%22uri%22%3A%22buy_more%22%7D&bundleName=com.huawei.hmos.clouddrive)` |
| **文件重名**（未选择） | 暂停，等待用户选择 | `📁 该文件已存在，请选择上传方式：1. 覆盖 2. 重命名 3. 跳过` |
| **文件重名**（用户选择后） | 按用户选择处理 | 覆盖：`📁 该文件已存在，已覆盖云端文件并上传`<br>重命名：`📁 该文件已存在，已重命名为「文件名 (1).ext」并上传`<br>跳过：`📁 该文件已存在，已跳过上传` |
| **目录创建失败** | 终止所有上传 | `❌ 上传失败，无法创建目标目录，请稍后重试` |
| **用户取消** | 终止所有操作 | `❌ 已取消文件上传` |
| **目录不存在** | 终止查询 | `❌ 查询目录不存在，请检查目录路径后重试` |
| **空间将满预警**（可用<2%） | 正常操作 + 预警提示 | `⚠️ 云空间可用容量不足总容量的 2%，空间将满，建议尽快升级云空间，[点击前往云空间升级套餐](superlink://vassistant?uri=hicloud%3A%2F%2FcloudDrive%2Fgetinfo%3Fpage%3DMemberBuyPage%26finishType%3D1%26pageDetails%3D%7B%22uri%22%3A%22buy_more%22%7D&bundleName=com.huawei.hmos.clouddrive)` |
| **云空间暂时不可用 / 登录已失效** | 前者稍后重试；后者提示用户重新登录小艺Work | `云空间暂时不可用，请稍后重试` / `登录已失效，请重新登录小艺Work` |

> 其他错误请参考 [华为状态码文档](https://developer.huawei.com/consumer/cn/doc/HMSCore-Guides/status-code-0000001050992633)。
