# 云空间操作指南

支持查询云空间总空间、已用空间和可用空间。

## 目录

- [查询云空间用量](#查询云空间用量)
- [特殊场景处理](#特殊场景处理)

---

## 查询云空间用量

### 命令

```bash
# 查询云空间详情（总空间、已用空间、可用空间）
cloud_drive.py --command query --key space

# 仅查询可用空间
cloud_drive.py --command query --key available_space
```

### 输出格式

**必须**严格按以下格式输出：

```markdown
云空间用量如下：
总空间：200 GB
已用空间：30 GB
可用空间：170 GB
```

若当前运行环境为鸿蒙操作系统，则输出如下链接：

[点击前往云空间 - 管理空间](superlink://vassistant?uri=hicloud%3A%2F%2FcloudDrive%2FgetInfo%3Fpage%3DSpaceManageDetails&bundleName=com.huawei.hmos.clouddrive) 查看详情。

若当前运行环境为Windows操作系统，则禁止输出以上跳转链接。

**数据说明**：查询结果单位为 Byte，需按二进制标准转换为 GB/MB/KB。

---

## 特殊场景处理

以下三个场景**必须**按以下提示语输出，并根据当前操作系统判断是否需要输出跳转链接或展示二维码图片。

### 基础服务用户（总空间 = 0）

若当前操作系统为**鸿蒙操作系统**，则按如下格式输出云空间升级套餐超链接：

```markdown
⚠️ 您当前为基础服务用户，不支持上传文件，请 [点击前往云空间升级套餐](superlink://vassistant?uri=hicloud%3A%2F%2FcloudDrive%2Fgetinfo%3Fpage%3DMemberBuyPage%26finishType%3D1%26pageDetails%3D%7B%22uri%22%3A%22buy_more%22%7D&bundleName=com.huawei.hmos.clouddrive)。
```

若当前操作系统为**Windows操作系统**，则按如下格式输出二维码图片：

⚠️ 您当前为基础服务用户，不支持上传文件，请通过手机浏览器扫描如下二维码升级云空间套餐

![升级云空间](升级云空间.png)

### 可用空间不足（总空间>0，可用空间=0）

若当前操作系统为**鸿蒙操作系统**，则按如下格式输出云空间升级套餐超链接：

```markdown
⚠️ 云空间可用空间不足，请 [点击前往云空间升级套餐](superlink://vassistant?uri=hicloud%3A%2F%2FcloudDrive%2Fgetinfo%3Fpage%3DMemberBuyPage%26finishType%3D1%26pageDetails%3D%7B%22uri%22%3A%22buy_more%22%7D&bundleName=com.huawei.hmos.clouddrive)。
```

若当前操作系统为**Windows操作系统**，则按如下格式输出二维码图片：

⚠️ 云空间可用空间不足，请通过手机浏览器扫描如下二维码升级云空间套餐

![升级云空间](升级云空间.png)

### 空间将满预警（可用空间 < 2% 总空间）

若当前操作系统为**鸿蒙操作系统**，则按如下格式输出云空间升级套餐超链接：

```markdown
⚠️ 云空间可用容量不足总容量的 2%，空间将满，建议尽快升级云空间，[点击前往云空间升级套餐](superlink://vassistant?uri=hicloud%3A%2F%2FcloudDrive%2Fgetinfo%3Fpage%3DMemberBuyPage%26finishType%3D1%26pageDetails%3D%7B%22uri%22%3A%22buy_more%22%7D&bundleName=com.huawei.hmos.clouddrive)。

当前总容量：{总空间}，可用容量：{可用空间}，详细用量请前往 云空间 — 管理存储空间 查看。
```

若当前操作系统为**Windows操作系统**，则按如下格式输出二维码图片：

⚠️ 云空间可用容量不足总容量的 2%，空间将满，建议尽快升级云空间，请通过手机浏览器扫描如下二维码进行升级

![升级云空间](升级云空间.png)

### 网络异常

```markdown
❌ 云空间用量查询失败，请检查网络后重试。
```

> 处理逻辑：自动重试 1 次，重试失败则终止操作。
