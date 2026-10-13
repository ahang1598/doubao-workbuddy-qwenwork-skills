"""基础设施层：与外部系统交互的客户端 + 持久化 + 缓存。

依赖方向：
- 上游：services / commands 通过本层访问 dws / 文件系统
- 下游：domain（仅用 exceptions）
"""
