"""门店任务中心自动派发系统（store-inspection）。

按层组织（依赖方向自上而下，单向）：

- :mod:`scripts.commands`        — CLI 命令注册（基类 + 装饰器自动注册）
- :mod:`scripts.app`             — Application/IoC 容器
- :mod:`scripts.services`        — 业务编排（initializer / dispatcher / reminder ...）
- :mod:`scripts.infrastructure`  — 基础设施（dws_client / mapping_cache / config / sync_state）
- :mod:`scripts.domain`          — 领域常量与纯函数（schema / filters / records / form_link_builder / exceptions）
- :mod:`scripts.utils`           — 通用工具（output）

详细需求见 ``docs/requirements-store-inspection.md``。
"""

__version__ = "0.1.0"
