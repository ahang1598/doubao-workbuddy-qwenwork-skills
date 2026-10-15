# Docker 错误分层速查

| 现象 | 层级 | 只读证据 | 安全处理方向 |
|---|---|---|---|
| Docker Desktop / WSL / 虚拟化错误 | 宿主层 | 系统版本、虚拟化状态、Docker 错误日志 | 按官方系统要求修复；不要用容器命令绕过 |
| Cannot connect to Docker daemon | daemon | `docker info`、服务状态、daemon 日志 | 查服务与配置；重启前说明会中断容器并确认 |
| No such container | 镜像/容器 | `docker ps -a`、`docker images` | 区分镜像和容器；创建/启动前核对名称 |
| 容器名冲突 | 镜像/容器 | `docker ps -a --filter name=<name>` | 展示旧容器状态；需删除或改名时先确认精确对象和影响 |
| 端口不通 | 应用配置 | `docker ps` PORTS、容器监听端口、健康检查 | 修正映射或监听；修改后双层复验 |
| 配置/环境变量未生效 | 应用配置 | `docker inspect`、容器内只读检查 | 核对启动命令、挂载和应用读取路径 |

禁止把删除容器、卷、镜像或 prune 写成默认恢复动作。
