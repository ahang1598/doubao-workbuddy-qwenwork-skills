"""
Bank Context Resolver — 基准行与按行 VIS 资产统一解析
=====================================================

本模块是 skill3/4/5 共享的「基准行解析 + 按行产物路径」单一本源。

解析优先级（高 → 低）：

1. 显式参数 ``base_bank`` / ``base_bank_short``（来自 Python 调用者）
2. 环境变量 ``RETAIL_ANALYSIS_BASE_BANK``
3. 自然语言 query（在 ``resolve_from_query()`` 中通过别名匹配抽取）
4. **无默认值**：三者均未命中时抛出 ``ValueError``，调用方必须确保用户已指定基准行

产物目录约定（与 SKILL.md 对齐）：

    ~/RetailAnalysis/output/<bank_short>/
        ├── benchmark_analysis.md                # skill3
        ├── benchmark_analysis_result.json       # skill3
        ├── benchmark_analysis_report.html       # skill3
        ├── 同业财报数据分析.pdf                  # skill3
        ├── insight_result.json                  # skill4
        ├── strategic_insight_report.html        # skill4
        ├── 同业战略洞察报告.pdf                  # skill4
        ├── strategy_governance_result.json      # skill5
        ├── strategy_governance_report.html      # skill5
        └── 战略与治理分析报告.pdf                 # skill5

视觉资产目录约定：

    ~/RetailAnalysis/report_assets/
        ├── by_bank/<bank_short>/
        │   ├── logo/{logo.png, logo_base64.txt, logo_source.txt}
        │   ├── vis/{palette.json, cover-*.png, toc-*.png, finance-*.png}
        │   └── brand.yaml                       # 采集来源 / 交叉校验结果
        ├── annual_report/<bank>_<year>_annual_report.pdf
        └── legacy/                              # 按行目录建立之前的历史资产
"""
from __future__ import annotations

import os
import pathlib
import re
from dataclasses import dataclass, field
from typing import Optional

try:
    import yaml  # PyYAML
except ImportError:  # pragma: no cover
    yaml = None

# 复用同目录的 paths.py
from paths import (  # type: ignore
    REPORT_ASSETS_DIR,
    OUTPUT_DIR,
    RUNTIME_MODE,
    RUNTIME_DIR,
)

ENV_BASE_BANK = "RETAIL_ANALYSIS_BASE_BANK"


# ---------------------------------------------------------------------------
# 可移植路径工具（2026-04-29 新增）
# ---------------------------------------------------------------------------
# 产物（brand.yaml / quality_report.yaml / logo_source.txt 等）中禁止写入
# 宿主机绝对路径，否则 copy 到其他电脑 / 其他人执行时需要大量手改。
# 统一通过 portable_path() 把绝对路径转换成 `~/RetailAnalysis/...` 形式，
# 或对 RETAIL_ANALYSIS_HOME 环境变量指定的 Home 目录转换成 `$RETAIL_ANALYSIS_HOME/...`。

def portable_path(p) -> str:
    """把绝对路径转换为可移植表示。

    规则：
      1. 若 p 在 `~/RetailAnalysis`（或 RETAIL_ANALYSIS_HOME 指定的 Home）内，
         返回 `~/RetailAnalysis/<rel>` 形式（或 `$RETAIL_ANALYSIS_HOME/<rel>`）
      2. 若 p 在用户 Home 内（$HOME），返回 `~/<rel>`
      3. 否则保留原绝对路径（并打上 "(absolute)" 前缀提示人工关注）

    None / 空值返回空字符串。
    """
    if not p:
        return ""
    p_path = pathlib.Path(str(p))
    abs_p = p_path if p_path.is_absolute() else p_path.resolve()

    # 优先匹配 RETAIL_ANALYSIS_HOME；未设置时按默认 ~/RetailAnalysis
    env_home = os.environ.get("RETAIL_ANALYSIS_HOME")
    if env_home:
        ra_home = pathlib.Path(env_home).expanduser().resolve()
        try:
            rel = abs_p.relative_to(ra_home)
            return f"$RETAIL_ANALYSIS_HOME/{rel.as_posix()}"
        except ValueError:
            pass

    ra_home_default = (pathlib.Path.home() / "RetailAnalysis").resolve()
    try:
        rel = abs_p.relative_to(ra_home_default)
        return f"~/RetailAnalysis/{rel.as_posix()}"
    except ValueError:
        pass

    # 一般 $HOME
    home = pathlib.Path.home().resolve()
    try:
        rel = abs_p.relative_to(home)
        return f"~/{rel.as_posix()}"
    except ValueError:
        pass

    return str(abs_p)


def portable_str(s) -> str:
    """对字符串中出现的绝对路径做批量替换，保持提示文案里的其他内容不变。"""
    if not s:
        return ""
    text = str(s)
    # 1) RETAIL_ANALYSIS_HOME 环境覆盖
    env_home = os.environ.get("RETAIL_ANALYSIS_HOME")
    if env_home:
        try:
            eh = str(pathlib.Path(env_home).expanduser().resolve())
            if eh and eh != "/":
                text = text.replace(eh, "$RETAIL_ANALYSIS_HOME")
        except Exception:
            pass
    # 2) ~/RetailAnalysis 默认根
    ra = str((pathlib.Path.home() / "RetailAnalysis").resolve())
    if ra and ra != "/":
        text = text.replace(ra, "~/RetailAnalysis")
    # 3) 用户 Home（放最后，避免先吃掉 ~/RetailAnalysis）
    home = str(pathlib.Path.home().resolve())
    if home and home != "/":
        text = text.replace(home, "~")
    return text

# 默认 7 家头部股份制银行的别名表，作为 banks.yaml 加载失败时的兜底
_DEFAULT_BANK_ALIAS = {
    "中信": {
        "name": "中信银行", "short": "中信",
        "aliases": ["中信", "中信银行", "citic", "CITIC", "601998"],
        "brand_identity": {"primary_official": "#C8102E", "accent_official": "#B58A34"},
    },
    "招商": {
        "name": "招商银行", "short": "招商",
        "aliases": ["招商", "招商银行", "招行", "cmb", "CMB", "600036"],
        "brand_identity": {"primary_official": "#C8102E", "accent_official": "#1A1A1A"},
    },
    "平安": {
        "name": "平安银行", "short": "平安",
        "aliases": ["平安", "平安银行", "pab", "PAB", "000001"],
        "brand_identity": {"primary_official": "#E60012", "accent_official": "#F68B1F"},
    },
    "兴业": {
        "name": "兴业银行", "short": "兴业",
        "aliases": ["兴业", "兴业银行", "cib", "CIB", "601166"],
        "brand_identity": {"primary_official": "#003399", "accent_official": "#E60012"},
    },
    "浦发": {
        "name": "浦发银行", "short": "浦发",
        "aliases": ["浦发", "浦发银行", "spdb", "SPDB", "600000"],
        "brand_identity": {"primary_official": "#0066B3", "accent_official": "#C8102E"},
    },
    "光大": {
        "name": "光大银行", "short": "光大",
        "aliases": ["光大", "光大银行", "ceb", "CEB", "601818", "06818",
                    "China Everbright Bank", "Everbright"],
        "brand_identity": {"primary_official": "#7F2987", "accent_official": "#C09A4F"},
    },
    "民生": {
        "name": "民生银行", "short": "民生",
        "aliases": ["民生", "民生银行", "cmbc", "CMBC", "600016", "01988"],
        "brand_identity": {"primary_official": "#006341", "accent_official": "#C8A14A"},
    },
}


# ---------------------------------------------------------------------------
# banks.yaml 加载
# ---------------------------------------------------------------------------
def _find_banks_yaml() -> Optional[pathlib.Path]:
    """只读取当前发布单元的配置；源码态读取共享事实源。"""
    if RUNTIME_MODE == "vendored":
        consumer_skill = RUNTIME_DIR.parent.parent
        skill_key = {
            "benchmark-analysis": "skill3",
            "strategic-insight": "skill4",
            "strategy-governance-analysis": "skill5",
        }.get(consumer_skill.name)
        override_root = os.environ.get("RETAIL_ANALYSIS_CONFIG_DIR")
        if override_root and skill_key:
            override = pathlib.Path(override_root).expanduser().resolve() / skill_key / "banks.yaml"
            if not override.is_file():
                raise FileNotFoundError(
                    f"配置覆盖已启用但文件不存在：{override}"
                )
            return override
        bundled = consumer_skill / "config" / "banks.yaml"
        if not bundled.is_file():
            raise FileNotFoundError(f"当前 Skill 缺少配置：{bundled}")
        return bundled

    if RUNTIME_MODE == "source":
        source = RUNTIME_DIR.parent / "config-sources" / "common" / "banks.yaml"
        if not source.is_file():
            raise FileNotFoundError(f"共享配置事实源不存在：{source}")
        return source
    raise FileNotFoundError("独立 PDF Runtime 未绑定业务 Skill，无法确定 banks.yaml")


def _load_banks_yaml() -> dict:
    path = _find_banks_yaml()
    if yaml is None:
        raise RuntimeError("读取 banks.yaml 需要 PyYAML")
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict) or not data:
        raise ValueError(f"banks.yaml 内容为空或格式错误：{path}")
    return data


# ---------------------------------------------------------------------------
# 银行识别
# ---------------------------------------------------------------------------
def _build_alias_index() -> tuple[dict, dict]:
    """返回 (alias -> short, short -> bank_config) 两份映射。"""
    cfg = _load_banks_yaml()
    banks_list = cfg.get("banks") or []
    # 如果 banks.yaml 没有 banks 列表（老版本），退回 peer_banks + base_bank 组装
    if not banks_list:
        base = cfg.get("base_bank") or {}
        peers = cfg.get("peer_banks") or []
        banks_list = []
        if base:
            banks_list.append({
                **base,
                "aliases": [base.get("name"), base.get("short_name")],
            })
        for p in peers:
            banks_list.append({
                **p,
                "aliases": [p.get("name"), p.get("short_name")],
            })

    alias_map: dict[str, str] = {}
    short_map: dict[str, dict] = {}
    for b in banks_list:
        short = b.get("short_name") or b.get("short")
        name = b.get("name")
        if not short:
            continue
        # brand_identity 缺失时，用 _DEFAULT_BANK_ALIAS 补齐（保证每家官方色不会串行）
        if not (b.get("brand_identity") or {}).get("primary_official"):
            fallback_brand = (_DEFAULT_BANK_ALIAS.get(short) or {}).get("brand_identity")
            if fallback_brand:
                merged = dict(b)
                existing = dict(b.get("brand_identity") or {})
                existing.update({k: v for k, v in fallback_brand.items() if k not in existing})
                merged["brand_identity"] = existing
                b = merged
        short_map[short] = b
        aliases = set((b.get("aliases") or []))
        aliases.update({short, name})
        # 附加默认别名表的别名（老配置没 aliases 字段时这里兜底）
        for da in (_DEFAULT_BANK_ALIAS.get(short) or {}).get("aliases", []):
            aliases.add(da)
        for a in aliases:
            if a:
                alias_map[a.lower()] = short

    # 如果配置里没识别到完整 7 家，用默认兜底补全
    for short, v in _DEFAULT_BANK_ALIAS.items():
        if short not in short_map:
            short_map[short] = {
                "name": v["name"],
                "short_name": short,
                "aliases": v["aliases"],
                "brand_identity": v["brand_identity"],
            }
            for a in v["aliases"] + [short, v["name"]]:
                alias_map.setdefault(a.lower(), short)

    return alias_map, short_map


_ALIAS_MAP, _SHORT_MAP = _build_alias_index()


def resolve_from_query(query: str) -> Optional[str]:
    """从自然语言 query 中匹配银行短名。返回 short（例如 "光大"）。

    策略：按「别名越长越优」的贪婪匹配，避免 "中国" 错配 "中信"。
    """
    if not query:
        return None
    low = query.lower()
    # 贪婪：先匹配长别名
    sorted_aliases = sorted(_ALIAS_MAP.keys(), key=len, reverse=True)
    for a in sorted_aliases:
        if a and a in low:
            return _ALIAS_MAP[a]
    return None


def resolve(
    base_bank: Optional[str] = None,
    *,
    query: Optional[str] = None,
    default: Optional[str] = None,
) -> "BankContext":
    """统一基准行解析入口。

    Args:
        base_bank: 显式参数（可以是短名/全称/别名/股票代码）。
        query: 自然语言；当 base_bank 为空时从 query 抽取。
        default: 兜底值。**默认为 None**，即不兜底；若三者均未命中则抛出 ValueError。
            调用方应确保用户已通过 SKILL.md 交互指定了基准行。

    Returns:
        BankContext 实例（含 short_name / name / brand / 各路径）。

    Raises:
        ValueError: 当 base_bank、query、default 均未命中时。
    """
    short: Optional[str] = None

    # 1) 显式参数
    if base_bank:
        short = _ALIAS_MAP.get(base_bank.lower()) or base_bank

    # 2) 环境变量
    if not short:
        env_val = os.environ.get(ENV_BASE_BANK, "").strip()
        if env_val:
            short = _ALIAS_MAP.get(env_val.lower()) or env_val

    # 3) 自然语言
    if not short and query:
        short = resolve_from_query(query)

    # 4) 默认
    if not short:
        short = default

    # 客户目录名必须来自 banks.yaml 的规范 short_name，禁止任意输入形成新目录或路径穿越。
    cfg = _SHORT_MAP.get(short)
    if not cfg:
        raise ValueError(
            f"未识别的客户名称：{short!r}。请使用 banks.yaml 中已配置的客户简称、全称或别名。"
        )

    return BankContext(short_name=short, config=cfg)


# ---------------------------------------------------------------------------
# 数据类：BankContext
# ---------------------------------------------------------------------------
@dataclass
class BankContext:
    short_name: str
    config: dict = field(default_factory=dict)

    # ---- 基础字段 ----
    @property
    def full_name(self) -> str:
        return self.config.get("name", f"{self.short_name}银行")

    @property
    def primary_color(self) -> str:
        return (self.config.get("brand_identity") or {}).get("primary_official", "#C8102E")

    @property
    def accent_color(self) -> str:
        return (self.config.get("brand_identity") or {}).get("accent_official", "#B58A34")

    # ---- 输出目录 ----
    @property
    def output_dir(self) -> pathlib.Path:
        d = OUTPUT_DIR / self.short_name
        d.mkdir(parents=True, exist_ok=True)
        return d

    def output_path(self, filename: str) -> pathlib.Path:
        return self.output_dir / filename

    # ---- 视觉资产目录 ----
    @property
    def assets_dir(self) -> pathlib.Path:
        """by_bank/<bank_short>/ 根目录（存在即返回；不存在也返回路径供后续创建）。"""
        return REPORT_ASSETS_DIR / "by_bank" / self.short_name

    @property
    def logo_dir(self) -> pathlib.Path:
        return self.assets_dir / "logo"

    @property
    def vis_dir(self) -> pathlib.Path:
        return self.assets_dir / "vis"

    @property
    def palette_json(self) -> pathlib.Path:
        return self.vis_dir / "palette.json"

    @property
    def logo_png(self) -> pathlib.Path:
        return self.logo_dir / "logo.png"

    @property
    def logo_base64_txt(self) -> pathlib.Path:
        return self.logo_dir / "logo_base64.txt"

    # ---- 资产存在性检查（用于 Agent 在生成 PDF 前判断是否需要先构建资产）----
    def assets_ready(self) -> bool:
        return (
            self.logo_png.exists()
            and self.logo_base64_txt.exists()
            and self.palette_json.exists()
        )

    def ensure_assets_dir(self) -> None:
        self.logo_dir.mkdir(parents=True, exist_ok=True)
        self.vis_dir.mkdir(parents=True, exist_ok=True)

    # ---- 兜底 palette：当 per-bank palette.json 不存在时合成一份 ----
    def fallback_palette(self) -> dict:
        primary = self.primary_color
        accent = self.accent_color
        return {
            "primary": primary,
            "primary_dark": _darken(primary, 0.6),
            "primary_light": _lighten(primary, 0.85),
            "accent": accent,
            "accent_light": _lighten(accent, 0.7),
            "text_primary": "#1A1A1A",
            "text_secondary": "#555555",
            "bg_white": "#FFFFFF",
            "bg_light": "#F7F7F7",
            "border": "#E0E0E0",
            "growth_green": "#2E7D32",
            "risk_red": "#C62828",
            "efficiency_blue": "#1565C0",
            "source": f"fallback from banks.yaml::{self.short_name}.brand_identity",
        }


# ---------------------------------------------------------------------------
# 色板辅助
# ---------------------------------------------------------------------------
_HEX_RE = re.compile(r"^#?([0-9A-Fa-f]{6})$")


def _hex_to_rgb(h: str) -> tuple[int, int, int]:
    m = _HEX_RE.match(h.strip())
    if not m:
        return (200, 16, 46)
    v = m.group(1)
    return int(v[0:2], 16), int(v[2:4], 16), int(v[4:6], 16)


def _rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    return "#{:02X}{:02X}{:02X}".format(*rgb)


def _darken(hex_color: str, ratio: float) -> str:
    r, g, b = _hex_to_rgb(hex_color)
    return _rgb_to_hex((max(0, int(r * ratio)), max(0, int(g * ratio)), max(0, int(b * ratio))))


def _lighten(hex_color: str, ratio: float) -> str:
    """向白色方向 lighten，ratio=0 不变，ratio=1 变白。"""
    r, g, b = _hex_to_rgb(hex_color)
    return _rgb_to_hex((
        min(255, int(r + (255 - r) * ratio)),
        min(255, int(g + (255 - g) * ratio)),
        min(255, int(b + (255 - b) * ratio)),
    ))


# ---------------------------------------------------------------------------
# CLI：便于 shell 调试
# ---------------------------------------------------------------------------
def _main() -> int:
    import argparse
    import json as _json

    parser = argparse.ArgumentParser(description="Bank Context Resolver")
    parser.add_argument("--query", help="自然语言 query（用于别名识别）")
    parser.add_argument("--base-bank", help="显式 base_bank")
    parser.add_argument("--list", action="store_true", help="列出所有已配置银行")
    args = parser.parse_args()

    if args.list:
        for short, cfg in sorted(_SHORT_MAP.items()):
            print(f"{short:<4} {cfg.get('name'):<10} primary={cfg.get('brand_identity',{}).get('primary_official','-')}")
        return 0

    ctx = resolve(base_bank=args.base_bank, query=args.query)
    info = {
        "short_name": ctx.short_name,
        "full_name": ctx.full_name,
        "primary": ctx.primary_color,
        "accent": ctx.accent_color,
        "output_dir": str(ctx.output_dir),
        "assets_dir": str(ctx.assets_dir),
        "assets_ready": ctx.assets_ready(),
    }
    print(_json.dumps(info, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_main())
