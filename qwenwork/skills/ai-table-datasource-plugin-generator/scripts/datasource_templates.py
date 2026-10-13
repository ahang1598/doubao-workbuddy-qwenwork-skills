#!/usr/bin/env python3
"""
数据源模板库（主入口）。

各数据库的 Service 模板拆分到 scripts/templates/ 子目录中：
  - templates/mysql_sheet_meta.py      MySQL SheetMetaService
  - templates/mysql_record.py          MySQL RecordService
  - templates/postgresql_sheet_meta.py PostgreSQL SheetMetaService
  - templates/postgresql_record.py     PostgreSQL RecordService
  - templates/sqlserver_templates.py   SQL Server SheetMetaService + RecordService
  - templates/oracle_templates.py      Oracle SheetMetaService + RecordService
  - templates/common.py                pom.xml 依赖 + .env 配置示例

设计说明：
  - Service 实现与模板保持相同的方法签名（接收 SheetMetaRequest / RecordsRequest）
  - 数据库连接参数通过 Spring @Value 从 backend/.env 注入
  - tableName 从 request.params 解析（前端 saveConfigAndGoNext 传入）
  - SQL 中表名统一加引号，防止大小写折叠和保留字冲突：
      MySQL:      反引号  `tableName`
      PostgreSQL: 双引号  "tableName"
      SQL Server: 方括号  [tableName]
      Oracle:     双引号  "tableName"
  - DatabaseMetaData 调用传入原始 tableName，不做大小写转换
"""

import sys
import os as _os
sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))

from templates.mysql_sheet_meta import get_mysql_sheet_meta_service
from templates.mysql_record import get_mysql_record_service as _get_mysql_record
from templates.postgresql_sheet_meta import get_postgresql_sheet_meta_service
from templates.postgresql_record import get_postgresql_record_service as _get_pg_record
from templates.sqlserver_templates import get_sqlserver_sheet_meta_service, get_sqlserver_record_service
from templates.oracle_templates import get_oracle_sheet_meta_service, get_oracle_record_service
from templates.common import get_pom_dependency, get_datasource_config_example


def get_mysql_service_impl() -> str:
    """获取 MySQL SheetMetaService 实现。"""
    return get_mysql_sheet_meta_service()


def get_mysql_record_service() -> str:
    """获取 MySQL RecordService 实现。"""
    return _get_mysql_record()


def get_postgresql_service_impl() -> str:
    """获取 PostgreSQL SheetMetaService 实现。"""
    return get_postgresql_sheet_meta_service()


def get_postgresql_record_service() -> str:
    """获取 PostgreSQL RecordService 实现。"""
    return _get_pg_record()


def get_sqlserver_service_impl() -> str:
    """获取 SQL Server SheetMetaService 实现。"""
    return get_sqlserver_sheet_meta_service()


def get_sqlserver_record_service_impl() -> str:
    """获取 SQL Server RecordService 实现。"""
    return get_sqlserver_record_service()


def get_oracle_service_impl() -> str:
    """获取 Oracle SheetMetaService 实现。"""
    return get_oracle_sheet_meta_service()


def get_oracle_record_service_impl() -> str:
    """获取 Oracle RecordService 实现。"""
    return get_oracle_record_service()
