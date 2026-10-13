"""固定 AI 表格表的 schema 定义。

新架构（3 张固定表 + 动态任务实例表 + 动态任务通知表）：
- 门店清单：门店与店长基础信息
- 巡店模版：任务蓝图，含管理员自定义字段定义（JSON 存储）
- 任务记录：每次派发的元数据（模板、发起人、发起时间、任务实例表等）
- 通知明细（已废弃固定表）：改为与巡检表一对一的动态表

动态任务实例表（Task Instance）：
- 每次创建巡店任务时，根据模版动态创建一张独立的 AI 表格表
- 命名规则：「{模版名称}-{YYYYMMDD}」，如「每日巡检-20260424」
- 字段由模版的 custom_fields 定义，加上系统骨架字段（store_id、store_name 等）
- 店长通过带 prefill 参数的表单链接提交巡检数据（纯 prefill，不预写骨架记录）
- 「店长」（user 类型）不支持 URL prefill，需在表单中手动选择并设为必填
- 建表策略：auto / per_year / per_month / once，由模版 table_strategy 字段控制

动态任务通知表（Task Notification）：
- 每次创建任务时同步创建，命名规则：「{任务实例表名}-通知」
- 字段与原通知明细固定表一致，但每次任务独立一张表

约束：
- dws table create 单次最多携带 15 个字段
- dws field create 单次也是 15 个字段上限
- primary_field 对应表的第一列 primaryDoc，AI 表格会做主键约束
"""

from __future__ import annotations

from typing import Any, Dict, List

# ---------------------------------------------------------------------------
# 固定表名常量
# ---------------------------------------------------------------------------

MAPPING_TABLE = "门店清单"
TEMPLATE_TABLE = "巡店模版"
TASK_RECORD_TABLE = "任务记录"
# 通知明细已废弃为固定表，保留常量供历史兼容
NOTIFICATION_TABLE = "通知明细"

# 当前有效的固定表（不含已废弃的通知明细）
ALL_TABLE_NAMES: List[str] = [
    MAPPING_TABLE,
    TEMPLATE_TABLE,
    TASK_RECORD_TABLE,
]

# ---------------------------------------------------------------------------
# 动态通知明细表命名
# ---------------------------------------------------------------------------

NOTIFICATION_TABLE_SUFFIX = "-通知"

def build_notification_table_name(task_table_name: str) -> str:
    """生成动态通知明细表名：「{任务表名}-通知」，如「每日巡检-20260424-通知」。"""
    return f"{task_table_name}{NOTIFICATION_TABLE_SUFFIX}"

# ---------------------------------------------------------------------------
# dws table create / field create 单次字段数上限
# ---------------------------------------------------------------------------

TABLE_CREATE_FIELD_LIMIT = 15
FIELD_CREATE_LIMIT = 15

# 表单视图类型
FORM_VIEW_TYPE = "FormDesigner"
DEFAULT_FORM_VIEW_NAME = "巡检上报表单"

# ---------------------------------------------------------------------------
# 字段定义
# ---------------------------------------------------------------------------

_DATE_TIME_CONFIG = {"formatter": "YYYY-MM-DD HH:mm:ss"}

# 门店清单字段
_MAPPING_FIELDS: List[Dict[str, Any]] = [
    {"name": "store_id", "type": "text"},
    {"name": "store_name", "type": "text"},
    {
        "name": "tags",
        "type": "multipleSelect",
        "config": {"options": [{"name": "华北"}, {"name": "华东"}, {"name": "旗舰店"}]},
    },
    {"name": "manager", "type": "user"},
    {
        "name": "status",
        "type": "singleSelect",
        "config": {"options": [{"name": "active"}, {"name": "inactive"}]},
    },
    {"name": "created_at", "type": "createdTime", "config": {"formatter": "YYYY-MM-DD HH:mm"}},
]

# 巡店模版字段
#
# 字段总数 21 > 单次 ``dws table create`` 上限（15），因此拆分为：
#   phase1（12 个）：建表时一次性创建（核心字段）
#   phase2（ 9 个）：建表后通过 ``dws aitable field create`` 追加
# phase2 字段包含消息模板扩展（3个）和任务实例管理扩展（6个），
# 对老库做"补字段"升级时也走 phase2 路径
# （``init url --auto-repair`` / ``check --repair`` 会按 missing_fields 增量补齐）。
_TEMPLATE_FIELDS_PHASE1: List[Dict[str, Any]] = [
    {"name": "template_id", "type": "text"},
    {"name": "name", "type": "text"},
    # 模板介绍文本（管理后台展示用，不参与消息渲染）
    {"name": "description", "type": "richText"},
    {
        "name": "status",
        "type": "singleSelect",
        "config": {"options": [{"name": "enabled"}, {"name": "disabled"}]},
    },
    {"name": "custom_fields", "type": "text"},
    {"name": "summary_receivers", "type": "text"},
    {"name": "remind_time", "type": "text"},
    {"name": "created_by", "type": "text"},
    {"name": "created_at", "type": "date", "config": _DATE_TIME_CONFIG},
    {"name": "updated_at", "type": "date", "config": _DATE_TIME_CONFIG},
]

# phase2 字段（建表后增量追加）
# 注意：消息字段重构后，提醒消息复用派发模板（message_title + dispatch_message），
# 老库可能仍残留 remind_topic / remind_message 字段，AI 表格 schema 校验只检查
# missing 不检查 extra，因此不主动声明这两个字段，也不会去删除它们；代码侧完全
# 不读取 remind_topic / remind_message。
_TEMPLATE_FIELDS_PHASE2: List[Dict[str, Any]] = [
    {"name": "message_title", "type": "text"},           # 派发消息标题模板
    {"name": "dispatch_message", "type": "richText"},    # 派发消息正文 Markdown 模板
    # 任务粒度：per_year（按年，默认）/ per_month（按月）
    # per_year 时表名格式：{模版名称}-{YYYY}，如「每日巡检-2026」
    # per_month 时表名格式：{模版名称}-{YYYY}-{MM}，如「每日巡检-2026-04」
    {"name": "granularity", "type": "text"},
    # 期望完成时长：格式 "Xh" / "Xm" / "XhYm"，如 "2h"、"30m"、"1h30m"
    # 创建任务时自动计算 deadline = task_date + expected_duration，写入任务记录
    {"name": "expected_duration", "type": "text"},
    # 当前活跃任务实例表 ID，系统维护
    {"name": "active_instance_id", "type": "text"},
    # 历史任务实例表 ID 列表，JSON 数组字符串，系统维护
    {"name": "managed_instance_ids", "type": "text"},
]

# 完整字段列表（供 mapping_cache / template_service 等读取所有字段名时使用）
_TEMPLATE_FIELDS: List[Dict[str, Any]] = (
    _TEMPLATE_FIELDS_PHASE1 + _TEMPLATE_FIELDS_PHASE2
)

# 任务记录字段：记录每次派发的元数据
#
# 字段总数 19 > 单次 ``dws table create`` 上限（15），因此拆分为：
#   phase1（15 个）：建表时一次性创建（task_id → status）
#   phase2（ 4 个）：建表后追加（dispatch_log、deadline、extra_info、reminder_round）
# 注意：phase 边界由 _TASK_RECORD_PHASE2_FIELD_NAMES 显式维护，
# 新增字段时请同步更新该集合，避免魔法切片导致字段悄悄落入错误的 phase。
_TASK_RECORD_FIELDS: List[Dict[str, Any]] = [
    {"name": "task_id", "type": "text"},           # 主键，格式：TASK_{template_id}_{yyyyMMddHHmm}
    {"name": "template_id", "type": "text"},
    {"name": "template_name", "type": "text"},
    {"name": "instance_table_name", "type": "text"},   # 任务实例表名
    {"name": "instance_table_id", "type": "text"},     # 任务实例表 tableId
    {"name": "notification_table_name", "type": "text"},  # 任务通知表名
    {"name": "notification_table_id", "type": "text"},    # 任务通知表 tableId
    {"name": "form_url", "type": "url"},           # 任务表的表单分享链接（首次派发后持久化，复用任务时直接读取）
    {"name": "form_view_id", "type": "text"},      # 任务表的表单视图 ID（用于复用时拼接引导链接）
    {"name": "initiated_by", "type": "user"},     # 发起人（user 类型）
    {"name": "task_date", "type": "date", "config": _DATE_TIME_CONFIG},  # 业务日期（这是哪天的任务），精确到天
    {"name": "target_store_count", "type": "number"},
    {"name": "success_count", "type": "number"},
    {"name": "failed_count", "type": "number"},
    {
        "name": "status",
        "type": "singleSelect",
        "config": {
            "options": [
                {"name": "进行中"},
                {"name": "已完成"},
                {"name": "部分失败"},
                {"name": "已禁用"},
            ]
        },
    },
    {"name": "dispatch_log", "type": "richText"},
    # 派发日志：JSON 数组，每次派发追加一条 {time, scope_desc, store_count, success_count}
    # 计划截止时间：由 task_date + template.expected_duration 计算得出，毫秒时间戳
    {"name": "deadline", "type": "date", "config": _DATE_TIME_CONFIG},
    # 派发时透传给店长的额外信息（CLI --extra-info 参数）。会渲染到消息模板的
    # {额外信息} 占位符；模板未使用占位符时追加到正文末尾。提醒消息也会复用该值。
    {"name": "extra_info", "type": "text"},
    # 已发送的提醒次数（首次派发不计入；每次 reminder 触发后 +1 并写回）。
    # 当此值 ≥ 2 时，提醒消息标题前缀会自动加 `【第N次提醒】`。
    {"name": "reminder_round", "type": "number"},
]

# 动态通知明细表字段（每次任务创建一张，字段与原固定通知明细表一致）
NOTIFICATION_TABLE_FIELDS: List[Dict[str, Any]] = [
    {"name": "notification_id", "type": "text"},
    {"name": "task_id", "type": "text"},
    {"name": "task_table_name", "type": "text"},
    {"name": "template_id", "type": "text"},
    {"name": "store_id", "type": "text"},
    {"name": "store_name", "type": "text"},
    {"name": "manager", "type": "user"},
    {
        "name": "notify_status",
        "type": "singleSelect",
        "config": {
            "options": [
                {"name": "pending"},
                {"name": "sent"},
                {"name": "failed"},
            ]
        },
    },
    {"name": "notify_fail_reason", "type": "text"},
    {"name": "message_id", "type": "text"},
    {"name": "form_link", "type": "url"},
    {"name": "dispatched_at", "type": "date", "config": _DATE_TIME_CONFIG},   # 首次派发时间，写入后不再更新
    {"name": "last_contacted_at", "type": "date", "config": _DATE_TIME_CONFIG},  # 最近一次联系时间（首发/重发/催办均更新），用于冷却保护
    # 重发计数：首次派发=1，每次重发同一 notification_id 时 +1。
    # 用于在不增加重复记录的前提下追溯重发次数（一个人 + 一个任务只保留一条记录）。
    {"name": "send_count", "type": "number"},
]

# ---------------------------------------------------------------------------
# 骨架字段展示名常量
# ---------------------------------------------------------------------------
# 骨架字段中对店长可见的字段使用中文展示名，隐藏字段保留英文内部名。
# 代码中通过常量引用，避免魔法字符串散落各处。
# inspection_id 是首字段 / 主键（primaryDoc），钉钉 AI 表格要求 primary_field
# 必须在表单 visibleFieldIds 中，否则表单创建会失败。
# 因此使用中文展示名「巡店任务编号」，使店长看到的字段名更友好。
FIELD_DISPLAY_INSPECTION_ID = "巡店任务编号"
FIELD_DISPLAY_DISPATCH_DATE = "派发日期"
FIELD_DISPLAY_MANAGER = "店长"
FIELD_DISPLAY_SPECIAL_NOTE = "特殊情况备注"

# 动态任务实例表的骨架字段（每次创建任务实例表时必须包含）
#
# 字段顺序约束：
#   首字段必须是 ``inspection_id``（text 类型）。AI 表格要求首字段（primaryDoc）类型
#   不能是 attachment 等类型，否则 ``aitable_table_create`` 会返回
#   ``InvalidRequest.Forbidden: The first field you specified is 'attachment',
#   which can not be used as the primary field.``。
#   ``inspection_id`` 承担主键职责（每行唯一）：
#     1. 格式：INSP_{task_id}_{store_id}，每行唯一；
#     2. 必须加入 visibleFieldIds（AI 表格要求主键字段在表单可见字段列表中，
#        否则表单创建失败），通过 URL prefill 自动填入，店长无感知也无法修改；
#     3. task_id 字段关联任务记录，同一次任务所有行值相同；
#     4. 其余骨架字段（store_id、store_name 等）同样通过 prefill 初始化，
#        但在表单视图中直接隐藏（不加入 visibleFieldIds）。
#
# 骨架字段共 10 个，自定义字段（来自模版 custom_fields）追加在这些骨架字段之后。
# Phase 2 分阶段建表触发阈值：自定义字段 > 4 个时触发（骨架 10 个 + 自定义 5 个 = 15 个，
# 恰好达到单次 table create 上限）。
TASK_INSTANCE_SKELETON_FIELDS: List[Dict[str, Any]] = [
    # 主键字段：放在第 0 位，作为整张表的 primaryDoc。
    # 中文展示名「巡店任务编号」，必须加入 visibleFieldIds（AI 表格要求主键字段
    # 在表单可见字段列表中，否则表单创建失败），通过 URL prefill 自动填入，店长无感知。
    {"name": FIELD_DISPLAY_INSPECTION_ID, "type": "text"},
    # 关联任务记录的任务 ID，同一次任务所有行相同，隐藏字段
    {"name": "task_id", "type": "text"},
    # 关联任务通知表的 notification_id，用于判断是否已提交，隐藏字段
    {"name": "notification_id", "type": "text"},
    # 派发日期，通过 prefill 带入，店长在表单中可见
    {"name": FIELD_DISPLAY_DISPATCH_DATE, "type": "date", "config": {"formatter": "YYYY-MM-DD"}},
    {"name": "store_id", "type": "text"},
    {"name": "store_name", "type": "text"},
    # 店长（user/成员类型），表单中可见且必须设为必填。
    # user 类型不支持 URL prefill，店长在表单中手动选择自己。
    # 中文展示名，对齐 store-inspection 的做法。
    {"name": FIELD_DISPLAY_MANAGER, "type": "user"},
    {"name": "template_id", "type": "text"},
    # 提交时间：使用 AI 表格内置 createdTime 系统字段，自动记录记录创建时间。
    # 纯 prefill 模式下不预写骨架记录，记录仅在店长提交表单时创建，
    # 因此 createdTime 即为实际提交时间。
    # 完成判定：巡检实例表中存在记录即视为已提交（不依赖 submit_status 字段，
    # 因为 singleSelect 不支持 URL prefill，无法在提交时自动赋值）。
    {"name": "submitted_at", "type": "createdTime", "config": {"formatter": "YYYY-MM-DD HH:mm"}},
    # 特殊情况备注：店长在表单中填写的文本备注，用于记录巡检中的异常情况。
    # 作为骨架字段固定创建，确保每张任务表都有此字段，避免依赖提示词不稳定地创建。
    # AI 审核 prompt 中会参考此字段内容做豁免判定（合理原因直接视为通过）。
    {"name": FIELD_DISPLAY_SPECIAL_NOTE, "type": "richText"},
]

# 向后兼容别名（旧代码引用 TASK_TABLE_SKELETON_FIELDS 时不报错）
TASK_TABLE_SKELETON_FIELDS = TASK_INSTANCE_SKELETON_FIELDS

# 骨架字段名集合（用于区分哪些字段需要在表单中隐藏）
TASK_INSTANCE_SKELETON_FIELD_NAMES: List[str] = [
    f["name"] for f in TASK_INSTANCE_SKELETON_FIELDS
]
# 向后兼容别名
TASK_TABLE_SKELETON_FIELD_NAMES = TASK_INSTANCE_SKELETON_FIELD_NAMES

# 各表中 url 类型字段的字段名集合（读取时需用 extract_url_value 解包为字符串）
TASK_RECORD_URL_FIELD_NAMES: frozenset = frozenset(
    f["name"] for f in _TASK_RECORD_FIELDS if f.get("type") == "url"
)
NOTIFICATION_URL_FIELD_NAMES: frozenset = frozenset(
    f["name"] for f in NOTIFICATION_TABLE_FIELDS if f.get("type") == "url"
)
TASK_INSTANCE_URL_FIELD_NAMES: frozenset = frozenset(
    f["name"] for f in TASK_INSTANCE_SKELETON_FIELDS if f.get("type") == "url"
)
# 向后兼容别名
TASK_TABLE_URL_FIELD_NAMES = TASK_INSTANCE_URL_FIELD_NAMES

# 任务记录表 phase2 字段名集合（显式维护，避免魔法切片）
# 新增字段时：若字段需要在建表后追加（phase2），请将字段名加入此集合；
# 若字段属于建表时创建（phase1），则无需修改此集合（但需确保 phase1 总数 ≤ 15）。
_TASK_RECORD_PHASE2_FIELD_NAMES: frozenset = frozenset({
    "dispatch_log",
    "deadline",
    "extra_info",
    "reminder_round",
})

# ---------------------------------------------------------------------------
# 固定表 schema 总表
# ---------------------------------------------------------------------------

TABLES: Dict[str, Dict[str, Any]] = {
    MAPPING_TABLE: {
        "primary_field": "store_id",
        "fields": _MAPPING_FIELDS,
        "phase1_fields": _MAPPING_FIELDS,
        "phase2_fields": [],
    },
    TEMPLATE_TABLE: {
        "primary_field": "template_id",
        "fields": _TEMPLATE_FIELDS,
        "phase1_fields": _TEMPLATE_FIELDS_PHASE1,  # 12 字段，建表时创建（核心字段）
        "phase2_fields": _TEMPLATE_FIELDS_PHASE2,  # 9 字段，建表后追加（消息模板扩展 + 任务实例管理扩展）
    },
    TASK_RECORD_TABLE: {
        "primary_field": "task_id",
        "fields": _TASK_RECORD_FIELDS,
        # 17 字段超过单次建表上限(15)，phase1=15（task_id → status），phase2=2（dispatch_log、deadline）
        # 注意：边界由 _TASK_RECORD_PHASE2_FIELD_NAMES 显式维护，新增字段时请同步更新。
        "phase1_fields": [f for f in _TASK_RECORD_FIELDS if f["name"] not in _TASK_RECORD_PHASE2_FIELD_NAMES],
        "phase2_fields": [f for f in _TASK_RECORD_FIELDS if f["name"] in _TASK_RECORD_PHASE2_FIELD_NAMES],
    },
}

# ---------------------------------------------------------------------------
# 模块级 schema 自检（import 时立即执行）
# ---------------------------------------------------------------------------
# 目的：让字段定义错误在 import 阶段就暴露，而不是等到实际建表时才失败。
# 检查项：
#   1. phase1 字段数不超过单次建表上限（TABLE_CREATE_FIELD_LIMIT）
#   2. phase1 + phase2 字段集合 == fields 完整集合（无遗漏、无多余）
#   3. 每张表内字段名不重复
def _assert_table_schemas() -> None:
    for table_name, schema in TABLES.items():
        all_fields = schema["fields"]
        phase1_fields = schema["phase1_fields"]
        phase2_fields = schema.get("phase2_fields", [])

        all_names = [f["name"] for f in all_fields]
        phase1_names = [f["name"] for f in phase1_fields]
        phase2_names = [f["name"] for f in phase2_fields]

        # 1. 字段名不重复
        duplicate_names = {n for n in all_names if all_names.count(n) > 1}
        if duplicate_names:
            raise AssertionError(
                f"[schema] 表 {table_name!r} 存在重复字段名: {sorted(duplicate_names)}"
            )

        # 2. phase1 不超过单次建表上限
        if len(phase1_fields) > TABLE_CREATE_FIELD_LIMIT:
            raise AssertionError(
                f"[schema] 表 {table_name!r} 的 phase1 字段数 {len(phase1_fields)} "
                f"超过单次建表上限 {TABLE_CREATE_FIELD_LIMIT}，"
                f"请将超出的字段移入 phase2"
            )

        # 3. phase1 + phase2 == fields（无遗漏、无多余）
        combined_names = set(phase1_names) | set(phase2_names)
        expected_names = set(all_names)
        missing_in_phases = expected_names - combined_names
        extra_in_phases = combined_names - expected_names
        if missing_in_phases:
            raise AssertionError(
                f"[schema] 表 {table_name!r} 的字段 {sorted(missing_in_phases)} "
                f"未出现在 phase1/phase2 中，会导致建表时永远缺失这些字段"
            )
        if extra_in_phases:
            raise AssertionError(
                f"[schema] 表 {table_name!r} 的 phase1/phase2 包含不在 fields 中的字段 "
                f"{sorted(extra_in_phases)}，请检查是否拼写错误"
            )

_assert_table_schemas()

def get_table_schema(table_name: str) -> Dict[str, Any]:
    """按表名获取固定表的 schema 定义。

    Raises:
        KeyError: 表名不在固定表中。
    """
    if table_name not in TABLES:
        raise KeyError(
            f"未知的固定表名 {table_name!r}，仅支持: {ALL_TABLE_NAMES}"
        )
    return TABLES[table_name]

def get_required_field_names(table_name: str) -> List[str]:
    """返回某张固定表必须存在的 fieldName 列表（用于校验）。"""
    return [f["name"] for f in get_table_schema(table_name)["fields"]]

def build_task_instance_fields(custom_fields: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """构建动态任务实例表的完整字段列表。

    Args:
        custom_fields: 来自模版 custom_fields 的自定义字段定义列表。

    Returns:
        骨架字段 + 自定义字段的完整列表。

    设计说明：
    - 骨架字段共 10 个，排在前面，首字段为 ``inspection_id``（text 类型），
      作为整张任务实例表的 primaryDoc 主键（每行唯一）。这样即使自定义字段里
      有 attachment 等 AI 表格不支持做主键的类型，也不会触发
      ``InvalidRequest.Forbidden: The first field you specified is 'attachment'``
      错误。
    - ``inspection_id``（巡店任务编号）必须加入 visibleFieldIds（AI 表格要求主键字段
      在表单可见字段列表中，否则表单创建失败），通过 URL prefill 自动填入，店长无感知；
    - task_id 字段关联任务记录，同一次任务所有行值相同，隐藏字段；
    - notification_id 通过 prefill 带入，在表单视图中直接隐藏；
    - 「派发日期」通过 prefill 带入，在表单视图中对店长可见。
    - 其余骨架字段（store_id 等）也通过 prefill 带入，在表单视图中直接隐藏。
    - 自定义字段保留模版中的原始顺序，追加在骨架字段之后，便于店长按管理员
      设计的顺序填写。
    - Phase 2 分阶段建表触发阈值：自定义字段 > 5 个时触发（骨架 10 个 +
      自定义 5 个 = 15 个，恰好达到单次 table create 上限）。
    """
    return list(TASK_INSTANCE_SKELETON_FIELDS) + list(custom_fields)

# 向后兼容别名
build_task_table_fields = build_task_instance_fields

def get_hidden_custom_field_names(custom_fields: List[Dict]) -> List[str]:
    """返回 custom_fields 中 hidden=True 的字段名列表。

    Args:
        custom_fields: 来自模版 custom_fields 的自定义字段定义列表，每个元素
            可包含可选属性 ``hidden: bool``。

    Returns:
        所有 ``hidden=True`` 字段的 ``name`` 列表，顺序与输入一致。

    Example::

        fields = [
            {"name": "评分", "type": "number"},
            {"name": "内部标记", "type": "text", "hidden": True},
        ]
        get_hidden_custom_field_names(fields)  # -> ["内部标记"]
    """
    return [f["name"] for f in custom_fields if f.get("hidden")]


def get_ai_review_fields(custom_fields: List[Dict]) -> List[Dict]:
    """返回 custom_fields 中需要 AI 审核的 attachment 字段列表。

    筛选条件：``type == "attachment"`` 且 ``ai_review == True``。

    Args:
        custom_fields: 来自模版 custom_fields 的自定义字段定义列表，每个元素
            可包含可选属性 ``ai_review: bool``、``ai_standards: list[str]``、
            ``ai_prompt: str``。

    Returns:
        满足条件的字段定义列表（保持原始顺序），每项至少包含
        ``name``、``type``、``ai_review`` 三个键。无符合条件的字段时返回空列表。

    Example::

        fields = [
            {"name": "鲜食柜照片", "type": "attachment", "ai_review": True,
             "ai_standards": ["核心单品≥5个"]},
            {"name": "备注", "type": "richText"},
            {"name": "收银台照片", "type": "attachment"},
        ]
        get_ai_review_fields(fields)
        # -> [{"name": "鲜食柜照片", "type": "attachment", "ai_review": True, ...}]
    """
    return [
        f for f in custom_fields
        if f.get("type") == "attachment" and f.get("ai_review", False)
    ]


__all__ = [
    "MAPPING_TABLE",
    "TEMPLATE_TABLE",
    "TASK_RECORD_TABLE",
    "NOTIFICATION_TABLE",
    "ALL_TABLE_NAMES",
    "NOTIFICATION_TABLE_SUFFIX",
    "NOTIFICATION_TABLE_FIELDS",
    "TABLE_CREATE_FIELD_LIMIT",
    "FIELD_CREATE_LIMIT",
    "FORM_VIEW_TYPE",
    "DEFAULT_FORM_VIEW_NAME",
    # 新命名（推荐使用）
    "TASK_INSTANCE_SKELETON_FIELDS",
    "TASK_INSTANCE_SKELETON_FIELD_NAMES",
    "TASK_INSTANCE_URL_FIELD_NAMES",
    # 向后兼容别名
    "TASK_TABLE_SKELETON_FIELDS",
    "TASK_TABLE_SKELETON_FIELD_NAMES",
    "TASK_TABLE_URL_FIELD_NAMES",
    "TABLES",
    "build_notification_table_name",
    "get_table_schema",
    "get_required_field_names",
    # 新命名（推荐使用）
    "build_task_instance_fields",
    # 向后兼容别名
    "build_task_table_fields",
    # 自定义字段 hidden 属性辅助
    "get_hidden_custom_field_names",
    # AI 审核字段辅助
    "get_ai_review_fields",
]
