---
name: docker-env-troubleshooting
description: "用于 Docker Desktop、dockerd、镜像、容器、端口、挂载或配置加载出现明确报错或异常，且用户能提供日志、截图或命令输出的场景。不用于 Kubernetes 集群治理或无 Docker 证据的一般网络故障。"
---

# Docker 分层排障

## 概述
按宿主/虚拟化、daemon、镜像容器、应用配置四层定位。先只读取证，后给最小修复；任何删除、重建、重启或配置覆盖都必须在执行前确认。

## 使用场景
### 应使用
- Docker Desktop 或 daemon 无法启动。
- 容器启动失败、退出、exec 对象错误或端口不通。
- 挂载、环境变量、代理或反向代理配置未生效。

### 不应使用
- Kubernetes、容器编排平台治理。
- 没有日志或命令输出的一般网络问题。
- 用户直接要求清空所有镜像、卷和容器。

## 核心流程
### 1. 只读取证
收集系统、Docker 版本、首个错误、docker info/ps/logs 和目标对象；不先改配置。

### 2. 确定故障层
宿主能力未满足时停止容器层试错；daemon 未运行时不改应用配置。

### 3. 给最小修复方案
每轮只处理一个根因，说明目标、影响、回滚和验证命令。

### 4. 高风险确认
restart、rm、prune、删除卷、覆盖 daemon.json 或防火墙规则前，必须列出精确对象并取得用户明确确认。

### 5. 双层复验
先验证服务/容器状态，再通过真实健康检查或业务请求验证。

## 工具与协作
- 诊断和命令执行使用 ShellExec/ShellWait/ShellView。
- 涉及应用代码修复时转 reproduce-fix-verify。

## 安全边界
- 只陈述已读取、已执行或有来源支持的结果；未验证项必须明确标注。
- 涉及删除、覆盖、发布、系统设置、生产数据或不可逆操作时，先展示目标、影响、回滚方式并取得明确确认。
- 不得记录或输出密钥、Cookie、访问令牌、身份证号、银行卡号等敏感信息；示例使用脱敏占位符。
- 默认禁止 docker system prune、删除卷或 `docker rm -f`；只有用户确认精确对象后才执行。
- 不得关闭系统安全功能或绕过容器权限来“修复”。

## 输出与验收
- 故障层与根因证据
- 建议命令及副作用
- 确认记录
- 服务级和业务级复验结果

## 冒烟用例
### Should trigger
- docker exec 报 No such container，日志在这里
- Docker Desktop 启动失败并提示 WSL2 缺失

### Should not trigger
- 把所有 Docker 数据都删掉
- Kubernetes Pod 一直 CrashLoopBackOff

### 边界输入
- 必须重启 Docker 服务，会中断现有容器

## 参考文件
- `references/error-map.md`
