"""应用层（IoC 容器）。

`AppContext` 是命令层与服务层之间的桥梁，提供：
- 共享的 :class:`DwsClient` 与 :class:`MappingCache`（全局复用，减少子进程开销）
- 各 Service 的懒加载实例（首次访问时构造，后续复用）

使用 ``functools.cached_property`` 实现懒加载 + 单例缓存。
命令层只依赖本类，不直接构造 Service，便于在测试中替换/Mock。
"""

from __future__ import annotations

from functools import cached_property

from scripts.infrastructure.dws_client import DwsClient
from scripts.infrastructure.mapping_cache import MappingCache
from scripts.services.dispatcher import Dispatcher
from scripts.services.initializer import Initializer
from scripts.services.messenger import Messenger
from scripts.services.monitor import Monitor
from scripts.services.reminder import Reminder
from scripts.services.stats import StatsService
from scripts.services.store_service import StoreManager
from scripts.services.summary import Summarizer
from scripts.services.sync_engine import SyncEngine
from scripts.services.template_service import TemplateManager


class AppContext:
    """命令层访问服务的统一入口（IoC 容器）。

    所有 Service 都共享同一个 :class:`DwsClient` 与 :class:`MappingCache`，
    避免在一次 CLI 调用中重复创建子进程 / 重复读取 base 元数据。
    """

    # ------------------------------------------------------------------
    # 基础设施（最先构造，其他都依赖它们）
    # ------------------------------------------------------------------

    @cached_property
    def client(self) -> DwsClient:
        return DwsClient()

    @cached_property
    def cache(self) -> MappingCache:
        return MappingCache(client=self.client)

    # ------------------------------------------------------------------
    # 基础服务
    # ------------------------------------------------------------------

    @cached_property
    def initializer(self) -> Initializer:
        return Initializer(client=self.client, cache=self.cache)

    @cached_property
    def store_manager(self) -> StoreManager:
        return StoreManager(client=self.client, cache=self.cache)

    @cached_property
    def template_manager(self) -> TemplateManager:
        return TemplateManager(client=self.client, cache=self.cache)

    @cached_property
    def messenger(self) -> Messenger:
        return Messenger(client=self.client)

    @cached_property
    def monitor(self) -> Monitor:
        return Monitor(client=self.client, cache=self.cache)

    # ------------------------------------------------------------------
    # 编排服务（依赖基础服务）
    # ------------------------------------------------------------------

    @cached_property
    def dispatcher(self) -> Dispatcher:
        return Dispatcher(
            client=self.client,
            cache=self.cache,
            store_manager=self.store_manager,
            template_manager=self.template_manager,
            messenger=self.messenger,
        )

    @cached_property
    def reminder(self) -> Reminder:
        return Reminder(
            client=self.client,
            cache=self.cache,
            template_manager=self.template_manager,
            messenger=self.messenger,
        )

    @cached_property
    def sync_engine(self) -> SyncEngine:
        return SyncEngine(
            client=self.client,
            cache=self.cache,
            template_manager=self.template_manager,
        )

    @cached_property
    def stats_service(self) -> StatsService:
        return StatsService(
            client=self.client,
            cache=self.cache,
            template_manager=self.template_manager,
            store_manager=self.store_manager,
        )

    @cached_property
    def summarizer(self) -> Summarizer:
        return Summarizer(
            client=self.client,
            cache=self.cache,
            template_manager=self.template_manager,
            messenger=self.messenger,
        )


__all__ = ["AppContext"]
