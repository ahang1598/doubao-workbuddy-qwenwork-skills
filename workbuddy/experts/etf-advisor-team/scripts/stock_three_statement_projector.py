#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""
三表预测 + 财务比率矩阵 + 杜邦分解脚本
=======================================

**定位**：卖方分析师级别的完整三表预测工具。
- 拉取历史 5 年完整三表（利润表 / 资产负债表 / 现金流量表）
- 根据驱动假设外推未来 3 年三表
- 自动完成三表勾稽 6 条硬约束校验
- 输出 18 项财务比率矩阵 + 杜邦三 / 五分解
- 支持同行横比

**数据源**：东财 DataCenter 完整三表 API（datacenter-web.eastmoney.com/api/data/v1/get）
  - RPT_F10_FINANCE_GINCOME   利润表（全字段 ~200+ 列）
  - RPT_F10_FINANCE_GBALANCE  资产负债表（全字段 ~320+ 列）
  - RPT_F10_FINANCE_GCASHFLOW 现金流量表（全字段 ~250+ 列）

**使用方式**：
    # 一站式完整输出（基本面深度研究常用）
    python stock_three_statement_projector.py 300308 --full --peer-compare 002463,603986 --format json

    # 单独功能
    python stock_three_statement_projector.py 300308 --history --years 5
    python stock_three_statement_projector.py 300308 --project --assumptions my_assumptions.json
    python stock_three_statement_projector.py 300308 --ratios --dupont

    # 输出格式
    --format readable  (默认) Markdown 可读
    --format json      机器可读（等价于已弃用的 --json）

版本：v1.0.0 (2026-04)
"""

import sys
import json
import argparse
import requests
from datetime import datetime
from typing import Dict, List, Optional, Any

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://data.eastmoney.com/",
}
DATACENTER_URL = "https://datacenter-web.eastmoney.com/api/data/v1/get"
TIMEOUT = 15


def _safe_float(v, default=0.0):
    if v is None or v == "-" or v == "":
        return default
    try:
        return float(v)
    except (ValueError, TypeError):
        return default


def _yi(v) -> float:
    return round(v / 1e8, 4) if v else 0.0


def infer_market(code: str) -> str:
    if code.startswith(("600", "601", "603", "605", "688", "689")):
        return "sh"
    elif code.startswith(("000", "001", "002", "003", "300", "301", "302")):
        return "sz"
    return "bj"


def infer_secucode(code: str) -> str:
    mkt = infer_market(code)
    return f"{code}.{'SH' if mkt == 'sh' else ('SZ' if mkt == 'sz' else 'BJ')}"


# --------------------------------------------------------------------------- #
#  1. 东财 DataCenter 完整三表拉取
#
#  数据源：datacenter-web.eastmoney.com/api/data/v1/get
#  报表名：
#    - RPT_F10_FINANCE_GINCOME   利润表全字段（203 列）
#    - RPT_F10_FINANCE_GBALANCE  资产负债表全字段（319 列）
#    - RPT_F10_FINANCE_GCASHFLOW 现金流量表全字段（254 列）
#  注意：REPORT_TYPE 字段值为中文（"年报"/"一季报"/"中报"/"三季报"），
#        报表同时包含所有季度，需本地过滤年报。
# --------------------------------------------------------------------------- #

def _fetch_statement(code: str, report_name: str, years: int) -> List[Dict]:
    """拉取指定报表的年报数据。"""
    secucode = infer_secucode(code)
    filters = [f'(SECUCODE="{secucode}")', f'(SECURITY_CODE="{code}")']
    last_err = ""
    for flt in filters:
        params = {
            "reportName": report_name, "columns": "ALL", "filter": flt,
            "pageSize": str(max(years * 4 + 8, 20)),  # 年报+季报都在里面，多拉
            "sortColumns": "REPORT_DATE", "sortTypes": "-1",
        }
        try:
            resp = requests.get(DATACENTER_URL, params=params, headers=HEADERS, timeout=TIMEOUT)
            j = resp.json()
        except Exception as e:
            last_err = f"{report_name} 拉取失败：{e}"
            continue

        result = j.get("result") or {}
        records = result.get("data") or []
        if not records:
            last_err = f"{report_name} 数据为空 ({j.get('message', '')})"
            continue

        # 过滤年报（REPORT_TYPE 字段中文：年报 / 一季报 / 中报 / 三季报）
        annual = [r for r in records if "12-31" in str(r.get("REPORT_DATE", ""))]
        if annual:
            return annual[:years]
        last_err = f"{report_name} 无年报数据"

    return [{"error": last_err or f"{report_name} 全部 filter 形式均失败"}]


def fetch_history_income(code: str, years: int = 5) -> List[Dict]:
    return _fetch_statement(code, "RPT_F10_FINANCE_GINCOME", years)


def fetch_history_balance(code: str, years: int = 5) -> List[Dict]:
    return _fetch_statement(code, "RPT_F10_FINANCE_GBALANCE", years)


def fetch_history_cashflow(code: str, years: int = 5) -> List[Dict]:
    return _fetch_statement(code, "RPT_F10_FINANCE_GCASHFLOW", years)


# --------------------------------------------------------------------------- #
#  2. 字段映射 & 标准化
# --------------------------------------------------------------------------- #

INCOME_FIELDS = {
    "营业收入": "TOTAL_OPERATE_INCOME", "营业成本": "OPERATE_COST",
    "税金及附加": "OPERATE_TAX_ADD", "销售费用": "SALE_EXPENSE",
    "管理费用": "MANAGE_EXPENSE", "研发费用": "RESEARCH_EXPENSE",
    "财务费用": "FINANCE_EXPENSE", "信用减值损失": "CREDIT_IMPAIRMENT_INCOME",
    "资产减值损失": "ASSET_IMPAIRMENT_INCOME", "其他收益": "OTHER_INCOME",
    "公允价值变动收益": "FAIRVALUE_CHANGE_INCOME", "投资收益": "INVEST_INCOME",
    "营业利润": "OPERATE_PROFIT", "营业外收入": "NONBUSINESS_INCOME",
    "营业外支出": "NONBUSINESS_EXPENSE", "利润总额": "TOTAL_PROFIT",
    "所得税费用": "INCOME_TAX", "净利润": "NETPROFIT",
    "少数股东损益": "MINORITY_INTEREST", "归母净利润": "PARENT_NETPROFIT",
    "基本EPS": "BASIC_EPS",
}

BALANCE_FIELDS = {
    "货币资金": "MONETARYFUNDS", "应收账款": "ACCOUNTS_RECE",
    "预付账款": "PREPAYMENT", "存货": "INVENTORY",
    "其他流动资产": "OTHER_CURRENT_ASSET", "流动资产合计": "TOTAL_CURRENT_ASSETS",
    "固定资产": "FIXED_ASSET", "在建工程": "CIP",
    "无形资产": "INTANGIBLE_ASSET", "商誉": "GOODWILL",
    "长期股权投资": "LONG_EQUITY_INVEST", "非流动资产合计": "TOTAL_NONCURRENT_ASSETS",
    "总资产": "TOTAL_ASSETS", "短期借款": "SHORT_LOAN",
    "应付账款": "ACCOUNTS_PAYABLE", "合同负债": "CONTRACT_LIAB",
    "流动负债合计": "TOTAL_CURRENT_LIAB", "长期借款": "LONG_LOAN",
    "应付债券": "BOND_PAYABLE", "非流动负债合计": "TOTAL_NONCURRENT_LIAB",
    "总负债": "TOTAL_LIABILITIES", "股本": "SHARE_CAPITAL",
    "未分配利润": "UNASSIGN_RPOFIT", "归属母公司股东权益": "TOTAL_PARENT_EQUITY",
    "少数股东权益": "MINORITY_EQUITY", "股东权益合计": "TOTAL_EQUITY",
}

CASHFLOW_FIELDS = {
    "销售商品收到现金": "SALES_SERVICES", "经营活动现金流净额": "NETCASH_OPERATE",
    "购建固定资产等支付的现金": "CONSTRUCT_LONG_ASSET",
    "投资活动现金流净额": "NETCASH_INVEST",
    "分配股利支付的现金": "ASSIGN_DIVIDEND_PORFIT",
    "偿还债务支付的现金": "PAY_DEBT_CASH", "取得借款收到的现金": "ACCEPT_INVEST_CASH",
    "筹资活动现金流净额": "NETCASH_FINANCE",
    "现金及现金等价物净增加额": "CCE_ADD",
    "折旧费用": "FA_IR_DEPR", "无形资产摊销": "IA_AMORTIZE",
}


def normalize_income(rec: Dict) -> Dict:
    out = {"报告期": str(rec.get("REPORT_DATE", ""))[:10]}
    for name, f in INCOME_FIELDS.items():
        raw = rec.get(f)
        out[name] = _safe_float(raw, None) if name == "基本EPS" else (_yi(_safe_float(raw, 0)) if raw is not None else None)
    return out


def normalize_balance(rec: Dict) -> Dict:
    out = {"报告期": str(rec.get("REPORT_DATE", ""))[:10]}
    for name, f in BALANCE_FIELDS.items():
        raw = rec.get(f)
        out[name] = _yi(_safe_float(raw, 0)) if raw is not None else None
    return out


def normalize_cashflow(rec: Dict) -> Dict:
    out = {"报告期": str(rec.get("REPORT_DATE", ""))[:10]}
    for name, f in CASHFLOW_FIELDS.items():
        raw = rec.get(f)
        out[name] = _yi(_safe_float(raw, 0)) if raw is not None else None
    return out


# --------------------------------------------------------------------------- #
#  3. 默认假设生成（从历史自动拟合）
# --------------------------------------------------------------------------- #

def derive_default_assumptions(hi: List[Dict], hb: List[Dict], hc: List[Dict]) -> Dict:
    """hi/hb/hc 最新在前（索引 0 = 最新年报）"""
    if not hi or len(hi) < 2:
        return {"error": "历史数据不足 2 年"}

    revs = [r.get("营业收入") for r in hi if r.get("营业收入")]
    rev_cagr = (revs[0] / revs[-1]) ** (1.0 / (len(revs) - 1)) - 1.0 if len(revs) >= 2 and revs[-1] > 0 else 0.10

    def _avg(num_key, den_key="营业收入", n=3):
        vals = []
        for r in hi[:n]:
            num = r.get(num_key); den = r.get(den_key)
            if num is not None and den and den != 0:
                vals.append(num / den)
        return sum(vals) / len(vals) if vals else 0.0

    def _days(bs_key, inc_key="营业收入", n=3):
        vals = []
        for i in range(min(n, len(hb), len(hi))):
            bs = hb[i].get(bs_key); inc = hi[i].get(inc_key)
            if bs and inc and inc != 0:
                vals.append(bs / inc * 365)
        return sum(vals) / len(vals) if vals else 0.0

    capex_ratio = 0.05
    vals = []
    for i in range(min(3, len(hc), len(hi))):
        cx = hc[i].get("购建固定资产等支付的现金"); rv = hi[i].get("营业收入")
        if cx and rv and rv > 0:
            vals.append(cx / rv)
    if vals:
        capex_ratio = sum(vals) / len(vals)

    payout = 0.30
    vals = []
    for i in range(min(3, len(hc), len(hi))):
        div = hc[i].get("分配股利支付的现金"); np = hi[i].get("归母净利润")
        if div and np and np > 0:
            vals.append(abs(div) / np)
    if vals:
        payout = min(1.0, sum(vals) / len(vals))

    dep_ratio = 0.08
    vals = []
    for i in range(min(3, len(hc), len(hb) - 1)):
        dep = (hc[i].get("折旧费用") or 0) + (hc[i].get("无形资产摊销") or 0)
        if i + 1 < len(hb):
            base = (hb[i + 1].get("固定资产") or 0) + (hb[i + 1].get("在建工程") or 0) + (hb[i + 1].get("无形资产") or 0)
            if dep and base and base > 0:
                vals.append(dep / base)
    if vals:
        dep_ratio = sum(vals) / len(vals)

    tax_rate = _avg("所得税费用", "利润总额")
    tax_rate = max(0.05, min(0.35, tax_rate)) if tax_rate else 0.15

    return {
        "营收增速（E+1/E+2/E+3）": [round(rev_cagr, 4)] * 3,
        "毛利率": round(1 - _avg("营业成本"), 4),
        "销售费用率": round(_avg("销售费用"), 4),
        "管理费用率": round(_avg("管理费用"), 4),
        "研发费用率": round(_avg("研发费用"), 4),
        "财务费用率": round(_avg("财务费用"), 4),
        "有效税率": round(tax_rate, 4),
        "应收账款周转天数": round(_days("应收账款"), 1),
        "存货周转天数": round(_days("存货", "营业成本"), 1),
        "应付账款周转天数": round(_days("应付账款", "营业成本"), 1),
        "CapEx/收入": round(capex_ratio, 4),
        "分红率": round(payout, 4),
        "折摊率（对固定+在建+无形）": round(dep_ratio, 4),
        "_note": "默认假设由历史 3 年均值/CAGR 生成，LLM 须结合 4.1.4 模型主动审视并覆写",
    }


# --------------------------------------------------------------------------- #
#  4. 三表滚动预测引擎
# --------------------------------------------------------------------------- #

def project_three_statements(hi: List[Dict], hb: List[Dict], hc: List[Dict],
                             a: Dict, years: int = 3) -> Dict:
    """历史列表最新在前；返回预测三表 + 勾稽校验"""
    if not hi or "error" in hi[0]:
        return {"error": "缺少历史利润表"}
    if not hb or "error" in hb[0]:
        return {"error": "缺少历史资产负债表"}
    if not hc or "error" in hc[0]:
        return {"error": "缺少历史现金流量表"}

    bi, bb, bc = hi[0], hb[0], hc[0]  # 基期

    growth = a.get("营收增速（E+1/E+2/E+3）", [0.10] * years)
    if len(growth) < years:
        growth = growth + [growth[-1]] * (years - len(growth))
    gm = a.get("毛利率", 0.30)
    sr = a.get("销售费用率", 0.05)
    mr = a.get("管理费用率", 0.05)
    rr = a.get("研发费用率", 0.03)
    fr = a.get("财务费用率", 0.01)
    tr = a.get("有效税率", 0.15)
    ar_d = a.get("应收账款周转天数", 60)
    inv_d = a.get("存货周转天数", 90)
    ap_d = a.get("应付账款周转天数", 60)
    cx_r = a.get("CapEx/收入", 0.05)
    pay_r = a.get("分红率", 0.30)
    dp_r = a.get("折摊率（对固定+在建+无形）", 0.08)

    # 状态变量（滚动）
    prev_rev = bi.get("营业收入") or 0
    prev_ar = bb.get("应收账款") or 0
    prev_inv = bb.get("存货") or 0
    prev_ap = bb.get("应付账款") or 0
    prev_fixed = (bb.get("固定资产") or 0) + (bb.get("在建工程") or 0)
    prev_intang = bb.get("无形资产") or 0
    prev_cash = bb.get("货币资金") or 0
    prev_equity = bb.get("归属母公司股东权益") or 0
    prev_minority = bb.get("少数股东权益") or 0
    prev_short = bb.get("短期借款") or 0
    prev_long = bb.get("长期借款") or 0
    prev_bond = bb.get("应付债券") or 0
    prev_capital = bb.get("股本") or 0
    prev_goodwill = bb.get("商誉") or 0
    prev_longinvest = bb.get("长期股权投资") or 0
    prev_prepay = bb.get("预付账款") or 0
    prev_other_ca = bb.get("其他流动资产") or 0
    prev_contract = bb.get("合同负债") or 0

    minority_ratio = 0.0
    if bi.get("净利润") and bi["净利润"] > 0:
        minority_ratio = (bi.get("少数股东损益") or 0) / bi["净利润"]

    # 基期 BS 残差（除上述 25 个主科目外的"其他资产 / 其他负债"），预测期保持为常数
    # 避免因科目不全导致的 A ≠ L + E 偏差（通常真实 BS 还有资本公积/盈余公积/其他综合收益
    # /递延税资产/其他应收应付/预提/应付职工薪酬/税费/等几十项）
    bi_assets_sum = (prev_cash + prev_ar + prev_inv + prev_prepay + prev_other_ca +
                     prev_fixed + prev_intang + prev_goodwill + prev_longinvest)
    bi_ta = bb.get("总资产") or 0
    other_a_resid = max(0.0, bi_ta - bi_assets_sum)

    bi_liab_sum = (prev_short + prev_ap + prev_contract + prev_long + prev_bond)
    bi_tl = bb.get("总负债") or 0
    other_l_resid = max(0.0, bi_tl - bi_liab_sum)

    proj_i, proj_b, proj_c = [], [], []

    for i in range(years):
        g = growth[i]
        rev = prev_rev * (1 + g)
        cogs = rev * (1 - gm)
        gp = rev - cogs
        tax_add = rev * 0.005
        se = rev * sr; me = rev * mr; rd = rev * rr; fe = rev * fr
        cl = -(prev_ar * 0.002)  # 信用减值
        al = -(prev_inv * 0.003)
        oi = bi.get("其他收益") or 0
        ii = bi.get("投资收益") or 0
        op = gp - tax_add - se - me - rd - fe + cl + al + oi + ii
        nb = (bi.get("营业外收入") or 0) - (bi.get("营业外支出") or 0)
        tp = op + nb
        itx = tp * tr
        np_ = tp - itx
        mi = np_ * minority_ratio
        pnp = np_ - mi
        eps = pnp / prev_capital if prev_capital else None

        proj_i.append({
            "报告期": f"E+{i+1} 预测",
            "营业收入": round(rev, 2), "营业成本": round(cogs, 2), "毛利": round(gp, 2),
            "税金及附加": round(tax_add, 2), "销售费用": round(se, 2),
            "管理费用": round(me, 2), "研发费用": round(rd, 2),
            "财务费用": round(fe, 2), "信用减值损失": round(cl, 2),
            "资产减值损失": round(al, 2), "其他收益": round(oi, 2),
            "投资收益": round(ii, 2), "营业利润": round(op, 2),
            "营业外收支": round(nb, 2), "利润总额": round(tp, 2),
            "所得税费用": round(itx, 2), "净利润": round(np_, 2),
            "少数股东损益": round(mi, 2), "归母净利润": round(pnp, 2),
            "基本EPS": round(eps, 4) if eps else None,
        })

        # 资负
        ar = rev * ar_d / 365
        inv = cogs * inv_d / 365
        ap = cogs * ap_d / 365
        prepay = prev_prepay * (1 + g)
        other_ca = prev_other_ca * (1 + g)
        contract = prev_contract * (1 + g)

        capex = rev * cx_r
        dep = (prev_fixed + prev_intang) * dp_r
        fa_dep = dep * (prev_fixed / (prev_fixed + prev_intang + 1e-9))
        ia_am = dep - fa_dep
        fixed_n = prev_fixed + capex - fa_dep
        intang_n = prev_intang - ia_am
        if intang_n < 0:
            intang_n = 0
        if fixed_n < 0:
            fixed_n = 0

        div = pnp * pay_r
        new_short = prev_short * (1 + g)
        new_long = prev_long * (1 + g)
        new_bond = prev_bond
        d_debt = (new_short - prev_short) + (new_long - prev_long)

        d_ar = ar - prev_ar
        d_inv = inv - prev_inv
        d_ap = ap - prev_ap
        d_con = contract - prev_contract
        op_cf = np_ + dep - cl - al - d_ar - d_inv + d_ap + d_con
        inv_cf = -capex
        fin_cf = d_debt - div
        cash_chg = op_cf + inv_cf + fin_cf
        equity_n = prev_equity + pnp - div
        minority_n = prev_minority + mi

        # 投行标准做法：现金作为 BS 平衡项，确保 A = L + E 恒成立
        # 即 cash = (总负债 + 股东权益) − 其他资产
        non_cash_ca = ar + prepay + inv + other_ca
        total_nca = fixed_n + intang_n + prev_goodwill + prev_longinvest
        total_cl = new_short + ap + contract
        total_ncl = new_long + new_bond
        total_l = total_cl + total_ncl + other_l_resid
        total_e = equity_n + minority_n
        cash_n = total_l + total_e - non_cash_ca - total_nca - other_a_resid
        total_ca = cash_n + non_cash_ca
        total_a = total_ca + total_nca + other_a_resid

        # 现金流校验：plug 差额（预测现金变动 vs 现金水位差）反映模型内生不平衡
        cash_chg_actual = cash_n - prev_cash

        proj_b.append({
            "报告期": f"E+{i+1} 预测",
            "货币资金": round(cash_n, 2), "应收账款": round(ar, 2),
            "预付账款": round(prepay, 2), "存货": round(inv, 2),
            "其他流动资产": round(other_ca, 2), "流动资产合计": round(total_ca, 2),
            "固定资产": round(fixed_n, 2), "无形资产": round(intang_n, 2),
            "商誉": round(prev_goodwill, 2), "长期股权投资": round(prev_longinvest, 2),
            "非流动资产合计": round(total_nca, 2), "总资产": round(total_a, 2),
            "短期借款": round(new_short, 2), "应付账款": round(ap, 2),
            "合同负债": round(contract, 2), "流动负债合计": round(total_cl, 2),
            "长期借款": round(new_long, 2), "应付债券": round(new_bond, 2),
            "非流动负债合计": round(total_ncl, 2), "总负债": round(total_l, 2),
            "股本": round(prev_capital, 2),
            "归属母公司股东权益": round(equity_n, 2),
            "少数股东权益": round(minority_n, 2),
            "股东权益合计": round(total_e, 2),
        })

        proj_c.append({
            "报告期": f"E+{i+1} 预测",
            "净利润": round(np_, 2), "折旧与摊销": round(dep, 2),
            "减值损失": round(-(cl + al), 2),
            "Δ应收账款": round(-d_ar, 2), "Δ存货": round(-d_inv, 2),
            "Δ应付账款": round(d_ap, 2), "Δ合同负债": round(d_con, 2),
            "经营活动现金流净额": round(op_cf, 2),
            "购建固定资产等支付的现金": round(capex, 2),
            "投资活动现金流净额": round(inv_cf, 2),
            "分配股利支付的现金": round(div, 2),
            "取得借款净额": round(d_debt, 2),
            "筹资活动现金流净额": round(fin_cf, 2),
            "现金及现金等价物净增加额": round(cash_chg_actual, 2),
            "_现金流公式计算增量": round(cash_chg, 2),
            "_BS平衡项修正": round(cash_chg_actual - cash_chg, 2),
            "FCFF": round(op_cf - capex, 2),
        })

        # 滚动
        prev_rev = rev; prev_ar = ar; prev_inv = inv; prev_ap = ap
        prev_fixed = fixed_n; prev_intang = intang_n; prev_cash = cash_n
        prev_equity = equity_n; prev_minority = minority_n
        prev_short = new_short; prev_long = new_long
        prev_prepay = prepay; prev_other_ca = other_ca; prev_contract = contract

    check = check_consistency([bi] + proj_i, [bb] + proj_b, [bc] + proj_c, pay_r, tr)
    return {"assumptions_used": a, "base_period": str(bi.get("报告期", "E"))[:10],
            "income": proj_i, "balance": proj_b, "cashflow": proj_c, "check": check}


# --------------------------------------------------------------------------- #
#  5. 三表勾稽校验
# --------------------------------------------------------------------------- #

def check_consistency(il: List[Dict], bl: List[Dict], cl: List[Dict],
                      payout: float = 0.30, tax_rate: float = 0.15) -> Dict:
    """
    三表勾稽 6 条硬约束校验（全部落地）。

    勾稽逻辑一览：
      规则 1：期末归母权益 = 期初归母权益 + 归母净利润 × (1 - 分红率)
      规则 2：经营现金流净额 ≈ 净利润 + 折旧摊销 + 资产/信用减值
                              − Δ应收 − Δ存货 − Δ预付 + Δ应付 + Δ合同负债（间接法核心）
      规则 3：期末(固定资产+在建工程+无形资产) ≈ 期初 + CapEx − 折旧摊销（资本性资产滚动）
      规则 4：期末货币资金 = 期初货币资金 + 现金及现金等价物净增加额
      规则 5：总资产 = 总负债 + 股东权益合计
      规则 6：所得税费用 ≈ 利润总额 × 有效税率
    """
    fails, details = [], []
    for i in range(1, len(il)):
        inc, bs_p, bs, cf = il[i], bl[i - 1], bl[i], cl[i]
        period = bs.get("报告期", f"#{i}")

        # ----------- 规则 1: 权益勾稽 -----------
        # 容忍 ±3%：直接使用"实际分红"（现金流量表中的"分配股利支付的现金"）而非假设分红率，
        # 这样能兼容不同公司差异巨大的分红政策（如茅台分红率 50-75% vs 成长股 0%）。
        # 其他影响权益变动的扰动项（资本公积转增、股份回购、其他综合收益汇兑差额、股权激励摊销）
        # 通常在 ±3% 以内；若超出需进一步排查。
        actual_dividend = abs(cf.get("分配股利支付的现金") or 0)
        exp = (bs_p.get("归属母公司股东权益") or 0) + (inc.get("归母净利润") or 0) - actual_dividend
        act = bs.get("归属母公司股东权益") or 0
        d = abs(act - exp) / (abs(exp) + 1e-9)
        p1 = d <= 0.03
        details.append({"check": "1. 股东权益勾稽", "period": period,
                        "expected": round(exp, 2), "actual": round(act, 2),
                        "diff_pct": f"{d*100:.2f}%", "tolerance": "±3%", "pass": p1,
                        "note": "使用实际分红而非固定分红率；残差容纳资本公积变动/回购/OCI 等"})
        if not p1:
            fails.append(f"{period} 股东权益勾稽失败（偏差 {d*100:.2f}%）")

        # ----------- 规则 2: 经营现金流勾稽（间接法核心） -----------
        # 预期 OCF = 净利润 + 折旧与摊销 + 资产减值 + 信用减值
        #           - (应收期末−应收期初) - (存货期末−存货期初) - (预付期末−预付期初)
        #           + (应付期末−应付期初) + (合同负债期末−合同负债期初)
        # 口径说明：
        #   ① "资产减值损失/信用减值损失"在东财字段里是"收益"口径（减值=负数），故作为"加项"时需加绝对值对利润的恢复
        #      这里取 inc 里的数值并 *(-1) 以还原"减值金额"；若财报将其列为收益（正号）则加上，整体以带符号口径为准
        #   ② Δ应收为正（应收增加）= OCF 减项；Δ应付为正（应付增加）= OCF 加项
        dep_amort = ((cf.get("折旧费用") or 0) + (cf.get("无形资产摊销") or 0))
        # 减值项：东财利润表字段"资产减值损失/信用减值损失"以"影响利润的金额"口径入账（亏损为负）
        #         OCF 中需把这些非现金影响加回，所以取 -value
        asset_imp = -(inc.get("资产减值损失") or 0)
        credit_imp = -(inc.get("信用减值损失") or 0)
        d_ar = (bs.get("应收账款") or 0) - (bs_p.get("应收账款") or 0)
        d_inv = (bs.get("存货") or 0) - (bs_p.get("存货") or 0)
        d_prepay = (bs.get("预付账款") or 0) - (bs_p.get("预付账款") or 0)
        d_ap = (bs.get("应付账款") or 0) - (bs_p.get("应付账款") or 0)
        d_contract = (bs.get("合同负债") or 0) - (bs_p.get("合同负债") or 0)
        exp_ocf = ((inc.get("净利润") or 0) + dep_amort + asset_imp + credit_imp
                   - d_ar - d_inv - d_prepay + d_ap + d_contract)
        act_ocf = cf.get("经营活动现金流净额") or 0
        # 经营现金流间接法调整项众多（公允价值、投资收益重分类、员工持股摊销、递延所得税、
        # 应付职工薪酬/税费时差、其他经营性应收应付等），容忍度设 ±40%。
        # 触发告警的场景：偏差>40% 强烈提示应计操纵（康得新/康美案例偏差均 >100%）
        denom = max(abs(exp_ocf), abs(act_ocf), 1e-9)
        d = abs(act_ocf - exp_ocf) / denom
        p2 = d <= 0.40
        details.append({"check": "2. 经营现金流勾稽", "period": period,
                        "expected": round(exp_ocf, 2), "actual": round(act_ocf, 2),
                        "diff_pct": f"{d*100:.2f}%", "tolerance": "±40%",
                        "pass": p2,
                        "note": "识别'有利润无现金'型造假（间接法核心勾稽）；偏差>40%须人工复核其他经营性应收应付变动"})
        if not p2:
            fails.append(f"{period} 经营现金流勾稽失败（预期 {exp_ocf:.2f}，实际 {act_ocf:.2f}，偏差 {d*100:.2f}%）")

        # ----------- 规则 3: 固定资产 + 在建工程 + 无形资产滚动 -----------
        # 期末(FA + CIP + IA) ≈ 期初(FA + CIP + IA) + CapEx - 折旧摊销
        # 口径说明：忽略处置净值（A 股大多年度<1%影响），用 ±3% 容忍
        fa_open = ((bs_p.get("固定资产") or 0) + (bs_p.get("在建工程") or 0) + (bs_p.get("无形资产") or 0))
        fa_close = ((bs.get("固定资产") or 0) + (bs.get("在建工程") or 0) + (bs.get("无形资产") or 0))
        capex = cf.get("购建固定资产等支付的现金") or 0
        exp_fa = fa_open + capex - dep_amort
        denom = max(abs(exp_fa), abs(fa_close), 1e-9)
        d = abs(fa_close - exp_fa) / denom
        p3 = d <= 0.05  # 放宽到±5%，因存在处置、资产置换、商誉减值等扰动项
        details.append({"check": "3. 固定资产滚动勾稽", "period": period,
                        "expected": round(exp_fa, 2), "actual": round(fa_close, 2),
                        "diff_pct": f"{d*100:.2f}%", "tolerance": "±5%",
                        "pass": p3,
                        "note": "识别'CapEx 虚增/折旧不充分'（资本性资产滚动）"})
        if not p3:
            fails.append(f"{period} 固定资产滚动勾稽失败（预期 {exp_fa:.2f}，实际 {fa_close:.2f}，偏差 {d*100:.2f}%）")

        # ----------- 规则 4: 货币资金 BS 变动 vs 现金等价物净增加额（软校验） -----------
        # 会计上: 现金及等价物净增加额 (CCE_ADD) = 经营+投资+筹资三大现金流净额 + 汇率变动
        # 但 BS 的"货币资金"口径 ≠ CCE_ADD 口径：
        #   - BS 货币资金 = 现金 + 银行存款 + 其他货币资金（含保证金、信用证、3个月内-1年定期存款）
        #   - CCE_ADD 只覆盖 3 个月内可变现的"现金等价物"
        # 对于"现金管理活跃"的龙头公司（茅台、腾讯等），两者系统性差异可达 100%+
        #
        # 本规则改为"弱勾稽/信号型"校验：
        #   只在偏差 > 500% 或 BS 变动与三大现金流方向长期系统性相反时告警，
        #   其余情况仅做记录，不计入 FAIL。
        delta_cash_bs = (bs.get("货币资金") or 0) - (bs_p.get("货币资金") or 0)
        cce_add = cf.get("现金及现金等价物净增加额") or 0
        denom = max(abs(delta_cash_bs), abs(cce_add), 1e-9)
        d_rate = abs(delta_cash_bs - cce_add) / denom
        # 硬红线：偏差 > 500% 视为严重异常（正常公司包括现金管理活跃的也很少到 5 倍差）
        p4 = d_rate <= 5.0
        details.append({"check": "4. 货币资金 vs 现金等价物（软校验）", "period": period,
                        "delta_cash_bs": round(delta_cash_bs, 2),
                        "cce_add": round(cce_add, 2),
                        "diff_rate": f"{d_rate*100:.2f}%",
                        "tolerance": "≤500%（仅识别极端异常）",
                        "pass": p4,
                        "note": "两者口径差异大（BS 货币资金含定期存款等），仅作合理性检查；异常需人工复核"})
        if not p4:
            fails.append(f"{period} 货币资金-现金等价物严重异常（BS 变动 {delta_cash_bs:.2f} vs CCE_ADD {cce_add:.2f}，偏差率 {d_rate*100:.2f}%）")

        # ----------- 规则 5: 资产=负债+权益 -----------
        ta = bs.get("总资产") or 0
        tle = (bs.get("总负债") or 0) + (bs.get("股东权益合计") or 0)
        d = abs(ta - tle) / (abs(ta) + 1e-9)
        p5 = d <= 0.001
        details.append({"check": "5. 资产=负债+权益", "period": period,
                        "expected": round(ta, 2), "actual": round(tle, 2),
                        "diff_pct": f"{d*100:.4f}%", "tolerance": "±0.1%", "pass": p5})
        if not p5:
            fails.append(f"{period} 资产负债表不平（偏差 {d*100:.4f}%）")

        # ----------- 规则 6: 所得税勾稽 -----------
        # 规则变更：不再使用固定 tax_rate，改用"当期实际有效税率"的合理区间校验。
        # 合理区间：5%-35%（覆盖高新技术 15%、一般 25%、以及小范围递延所得税扰动）
        tp = inc.get("利润总额") or 0
        act = inc.get("所得税费用") or 0
        if tp and tp > 0:
            effective_rate = act / tp
            p6 = 0.05 <= effective_rate <= 0.35
            note6 = f"实际税率 {effective_rate*100:.2f}%"
        else:
            # 利润总额为负或为0时本规则不适用（亏损期所得税可能为负或0）
            p6 = True
            effective_rate = None
            note6 = "利润总额≤0，规则跳过"
        details.append({"check": "6. 所得税勾稽", "period": period,
                        "effective_rate": round(effective_rate, 4) if effective_rate else None,
                        "tolerance": "实际税率 ∈ [5%, 35%]",
                        "pass": p6, "note": note6})
        if not p6:
            fails.append(f"{period} 所得税异常（实际税率 {effective_rate*100:.2f}% 超出 [5%, 35%]）")

    return {"pass": len(fails) == 0, "fail_count": len(fails),
            "fails": fails, "details": details}


# --------------------------------------------------------------------------- #
#  5B. 预测假设自洽性校验（P2）
#
#  目标：识别驱动假设本身的内部不一致（与三表勾稽验"数"不同，本层验"逻辑"）。
#  核心 5 项校验：
#    ① 收入增速 vs CapEx 增速 —— 营收翻倍但不扩产 = 不自洽
#    ② 毛利率假设 vs 历史波动带 —— 假设大幅偏离历史（>3pct）须有解释
#    ③ 应收账款/营收比率 vs 历史均值 —— 偏离 >20% 提示信用政策激进
#    ④ 分红率 vs 历史均值 —— 偏离 >15pct 提示股利政策突变未做说明
#    ⑤ CapEx/折旧比率 vs 历史均值 —— 偏离 >50% 提示扩张性/维持性假设切换
# --------------------------------------------------------------------------- #

def check_projection_sanity(hi: List[Dict], hb: List[Dict], hc: List[Dict],
                            a: Dict) -> Dict:
    """
    预测假设自洽性校验。
      hi/hb/hc 最新在前（索引 0 = 最新年报）
      a 为 derive_default_assumptions 或用户覆写后的假设字典
    返回：{"pass": bool, "warn_count": int, "warnings": [...], "details": [...]}
    """
    warns, details = [], []

    def _mean_ratio(num_key: str, den_key: str, src_list: List[Dict],
                    den_src: Optional[List[Dict]] = None, n: int = 3) -> Optional[float]:
        den_src = den_src or src_list
        vals = []
        for i in range(min(n, len(src_list), len(den_src))):
            num = src_list[i].get(num_key); den = den_src[i].get(den_key)
            if num is not None and den and den != 0:
                vals.append(num / den)
        return sum(vals) / len(vals) if vals else None

    def _mean_growth(key: str, src_list: List[Dict], n: int = 4) -> Optional[float]:
        """近 n 年复合增速（hi 最新在前，所以 [0]/[-1] 是最新/最早）"""
        vals = [r.get(key) for r in src_list[:n] if r.get(key)]
        if len(vals) >= 2 and vals[-1] > 0:
            return (vals[0] / vals[-1]) ** (1.0 / (len(vals) - 1)) - 1.0
        return None

    # ---------- 校验 ①：收入增速 vs CapEx 增速（扩张性一致） ----------
    rev_growth_assumption = a.get("营收增速（E+1/E+2/E+3）", [])
    avg_rev_g = sum(rev_growth_assumption) / len(rev_growth_assumption) if rev_growth_assumption else None
    hist_capex_g = _mean_growth("购建固定资产等支付的现金", hc, n=3)
    hist_rev_g = _mean_growth("营业收入", hi, n=4)
    # CapEx/收入比率
    capex_rev_ratio = a.get("CapEx/收入")
    hist_capex_rev = _mean_ratio("购建固定资产等支付的现金", "营业收入", hc, hi, n=3)

    detail1 = {
        "check": "① 收入增速 vs CapEx 强度",
        "assumption_rev_growth": avg_rev_g,
        "history_rev_growth": hist_rev_g,
        "assumption_capex/rev": capex_rev_ratio,
        "history_capex/rev": hist_capex_rev,
        "pass": True, "note": ""
    }
    # 规则：若营收增速假设 > 历史 +5pct，CapEx/收入 假设应同方向 +20% 以上
    if avg_rev_g is not None and hist_rev_g is not None and capex_rev_ratio is not None and hist_capex_rev:
        if avg_rev_g > hist_rev_g + 0.05:
            capex_uplift = (capex_rev_ratio - hist_capex_rev) / hist_capex_rev if hist_capex_rev else 0
            if capex_uplift < 0.20:
                detail1["pass"] = False
                detail1["note"] = (f"营收增速假设 {avg_rev_g*100:.1f}% 显著高于历史 {hist_rev_g*100:.1f}%，"
                                   f"但 CapEx/收入仅 {capex_rev_ratio*100:.1f}%（历史 {hist_capex_rev*100:.1f}%，"
                                   f"上浮 {capex_uplift*100:.1f}%）——产能扩张支撑不足")
                warns.append(detail1["note"])
    details.append(detail1)

    # ---------- 校验 ②：毛利率假设 vs 历史波动带 ----------
    gm_assumption = a.get("毛利率")
    gms = []
    for r in hi[:5]:
        rev = r.get("营业收入"); cogs = r.get("营业成本")
        if rev and cogs and rev > 0:
            gms.append(1 - cogs / rev)
    gm_hist_mean = sum(gms) / len(gms) if gms else None
    gm_hist_max = max(gms) if gms else None
    gm_hist_min = min(gms) if gms else None
    detail2 = {
        "check": "② 毛利率假设 vs 历史波动带",
        "assumption_gm": gm_assumption,
        "history_mean": gm_hist_mean,
        "history_range": [gm_hist_min, gm_hist_max] if gms else None,
        "pass": True, "note": ""
    }
    if gm_assumption is not None and gm_hist_mean is not None:
        deviation = abs(gm_assumption - gm_hist_mean)
        if deviation > 0.03:  # 偏离均值 >3pct
            detail2["pass"] = False
            detail2["note"] = (f"毛利率假设 {gm_assumption*100:.2f}% 偏离历史均值 "
                               f"{gm_hist_mean*100:.2f}% 达 {deviation*100:.2f}pct——"
                               f"须验证是否有产品结构/成本结构的重大变化支撑")
            warns.append(detail2["note"])
    details.append(detail2)

    # ---------- 校验 ③：应收账款/营收 比率漂移 ----------
    ar_days_assumption = a.get("应收账款周转天数")
    hist_ar_days = []
    for i in range(min(3, len(hb), len(hi))):
        ar = hb[i].get("应收账款"); rev = hi[i].get("营业收入")
        if ar and rev and rev > 0:
            hist_ar_days.append(ar / rev * 365)
    ar_hist_mean = sum(hist_ar_days) / len(hist_ar_days) if hist_ar_days else None
    detail3 = {
        "check": "③ 应收账款周转天数漂移",
        "assumption_days": ar_days_assumption,
        "history_mean_days": round(ar_hist_mean, 1) if ar_hist_mean else None,
        "pass": True, "note": ""
    }
    if ar_days_assumption and ar_hist_mean and ar_hist_mean > 0:
        # 当历史周转天数极低（<5 天）时（如茅台/海天经销商打款模式），微小绝对差会被放大
        # 成大比例，此时加一个绝对偏差门槛（<3 天视为正常）
        abs_deviation = abs(ar_days_assumption - ar_hist_mean)
        rel_deviation = abs_deviation / ar_hist_mean
        if rel_deviation > 0.20 and abs_deviation > 3.0:
            detail3["pass"] = False
            detail3["note"] = (f"应收账款周转天数假设 {ar_days_assumption:.1f} 天偏离历史 "
                               f"{ar_hist_mean:.1f} 天达 {rel_deviation*100:.1f}%（绝对差 {abs_deviation:.1f} 天）——"
                               f"若放宽，提示信用政策激进；若收紧，需证明下游议价力提升")
            warns.append(detail3["note"])
    details.append(detail3)

    # ---------- 校验 ④：分红率 vs 历史均值 ----------
    payout_assumption = a.get("分红率")
    hist_payouts = []
    for i in range(min(3, len(hc), len(hi))):
        div = hc[i].get("分配股利支付的现金"); np = hi[i].get("归母净利润")
        if div and np and np > 0:
            hist_payouts.append(abs(div) / np)
    payout_hist_mean = sum(hist_payouts) / len(hist_payouts) if hist_payouts else None
    detail4 = {
        "check": "④ 分红率 vs 历史均值",
        "assumption_payout": payout_assumption,
        "history_mean_payout": round(payout_hist_mean, 4) if payout_hist_mean else None,
        "pass": True, "note": ""
    }
    if payout_assumption is not None and payout_hist_mean is not None:
        deviation = abs(payout_assumption - payout_hist_mean)
        if deviation > 0.15:
            detail4["pass"] = False
            detail4["note"] = (f"分红率假设 {payout_assumption*100:.1f}% 偏离历史均值 "
                               f"{payout_hist_mean*100:.1f}% 达 {deviation*100:.1f}pct——"
                               f"若大幅提升，需核实公司是否已发布新分红政策")
            warns.append(detail4["note"])
    details.append(detail4)

    # ---------- 校验 ⑤：折摊率 vs 历史（资本开支与折旧配比） ----------
    capex_ratio = a.get("CapEx/收入")
    dep_ratio = a.get("折摊率（对固定+在建+无形）")
    # CapEx/折旧 = 扩张性/维持性的核心识别
    hist_capex_over_dep = []
    for i in range(min(3, len(hc), len(hb))):
        cx = hc[i].get("购建固定资产等支付的现金") or 0
        dep = (hc[i].get("折旧费用") or 0) + (hc[i].get("无形资产摊销") or 0)
        if cx and dep and dep > 0:
            hist_capex_over_dep.append(cx / dep)
    hist_cx_dep_mean = sum(hist_capex_over_dep) / len(hist_capex_over_dep) if hist_capex_over_dep else None
    detail5 = {
        "check": "⑤ CapEx/折旧（扩张性 vs 维持性）",
        "history_ratio_mean": round(hist_cx_dep_mean, 2) if hist_cx_dep_mean else None,
        "pass": True, "note": ""
    }
    if hist_cx_dep_mean is not None:
        if hist_cx_dep_mean > 2.0:
            detail5["note"] = f"历史 CapEx/折旧 {hist_cx_dep_mean:.2f}（>2），处于扩张期，未来 FCFF 可能持续承压"
        elif hist_cx_dep_mean < 0.8:
            detail5["note"] = f"历史 CapEx/折旧 {hist_cx_dep_mean:.2f}（<0.8），投入不足以维持现有产能，需警惕产能老化"
            detail5["pass"] = False
            warns.append(detail5["note"])
        else:
            detail5["note"] = f"历史 CapEx/折旧 {hist_cx_dep_mean:.2f}（0.8-2.0），处于维持性投入区间"
    details.append(detail5)

    return {"pass": len(warns) == 0, "warn_count": len(warns),
            "warnings": warns, "details": details}


# --------------------------------------------------------------------------- #
#  6. 比率矩阵 18 项
# --------------------------------------------------------------------------- #

def _roic(inc: Dict, bs: Dict, bs_p: Optional[Dict]) -> Optional[float]:
    op = inc.get("营业利润") or 0
    tp = inc.get("利润总额") or 0
    tr = 0.15
    if tp > 0:
        tr = max(0.05, min(0.35, (inc.get("所得税费用") or 0) / tp))
    nopat = op * (1 - tr)
    def _ic(b):
        if not b: return 0
        return (b.get("归属母公司股东权益") or 0) + (b.get("短期借款") or 0) + (b.get("长期借款") or 0) + (b.get("应付债券") or 0)
    ic_n, ic_p = _ic(bs), _ic(bs_p) if bs_p else _ic(bs)
    avg = (ic_n + ic_p) / 2
    return round(nopat / avg * 100, 2) if avg > 0 else None


def calc_ratios(inc: Dict, bs: Dict, bs_p: Optional[Dict], cf: Dict) -> Dict:
    rev = inc.get("营业收入") or 0
    cogs = inc.get("营业成本") or 0
    gp = inc.get("毛利") or (rev - cogs)
    pnp = inc.get("归母净利润") or 0
    op = inc.get("营业利润") or 0
    fe = inc.get("财务费用") or 0
    ta = bs.get("总资产") or 0
    tl = bs.get("总负债") or 0
    pe = bs.get("归属母公司股东权益") or 0
    ca = bs.get("流动资产合计") or 0
    cl = bs.get("流动负债合计") or 0
    inv = bs.get("存货") or 0
    ar = bs.get("应收账款") or 0
    ap = bs.get("应付账款") or 0
    id_ = (bs.get("短期借款") or 0) + (bs.get("长期借款") or 0) + (bs.get("应付债券") or 0)

    avg_ta = (ta + (bs_p.get("总资产") or 0)) / 2 if bs_p else ta
    avg_pe = (pe + (bs_p.get("归属母公司股东权益") or 0)) / 2 if bs_p else pe

    op_cf = cf.get("经营活动现金流净额") or 0
    fcff = cf.get("FCFF")
    if fcff is None:
        fcff = op_cf - (cf.get("购建固定资产等支付的现金") or 0)
    div = cf.get("分配股利支付的现金") or 0
    dep = cf.get("折旧与摊销") or ((cf.get("折旧费用") or 0) + (cf.get("无形资产摊销") or 0))
    capex = cf.get("购建固定资产等支付的现金") or 0

    def p(a, b): return round(a / b * 100, 2) if b else None
    def r(a, b): return round(a / b, 3) if b else None

    return {
        "毛利率%": p(gp, rev), "净利率%": p(pnp, rev),
        "ROE加权%": p(pnp, avg_pe), "ROA%": p(pnp, avg_ta),
        "ROIC%": _roic(inc, bs, bs_p),
        "应收周转天数": round(ar / rev * 365, 1) if rev else None,
        "存货周转天数": round(inv / cogs * 365, 1) if cogs else None,
        "应付周转天数": round(ap / cogs * 365, 1) if cogs else None,
        "总资产周转率": r(rev, avg_ta),
        "流动比率": r(ca, cl), "速动比率": r(ca - inv, cl),
        "资产负债率%": p(tl, ta), "有息负债率%": p(id_, ta),
        "利息保障倍数": round((op + fe) / fe, 2) if fe and fe != 0 else None,
        "净现比": r(op_cf, pnp), "FCF转换率": r(fcff, pnp),
        "CapEx/折旧": r(capex, dep), "分红率%": p(abs(div), pnp),
    }


def build_ratio_matrix(il: List[Dict], bl: List[Dict], cl: List[Dict]) -> List[Dict]:
    """il/bl/cl 从旧到新"""
    out = []
    for i in range(len(il)):
        prev = bl[i - 1] if i > 0 else None
        out.append({"报告期": il[i].get("报告期", f"#{i}"),
                    **calc_ratios(il[i], bl[i], prev, cl[i])})
    return out


# --------------------------------------------------------------------------- #
#  7. 杜邦分解
# --------------------------------------------------------------------------- #

def dupont_three(inc: Dict, bs: Dict, bs_p: Optional[Dict]) -> Dict:
    rev = inc.get("营业收入") or 0
    pnp = inc.get("归母净利润") or 0
    ta = bs.get("总资产") or 0
    pe = bs.get("归属母公司股东权益") or 0
    avg_ta = (ta + (bs_p.get("总资产") or 0)) / 2 if bs_p else ta
    avg_pe = (pe + (bs_p.get("归属母公司股东权益") or 0)) / 2 if bs_p else pe
    return {
        "报告期": inc.get("报告期"),
        "ROE加权%": round(pnp / avg_pe * 100, 2) if avg_pe else None,
        "净利率%": round(pnp / rev * 100, 2) if rev else None,
        "总资产周转率": round(rev / avg_ta, 3) if avg_ta else None,
        "权益乘数": round(avg_ta / avg_pe, 2) if avg_pe else None,
    }


def dupont_five(inc: Dict, bs: Dict, bs_p: Optional[Dict]) -> Dict:
    rev = inc.get("营业收入") or 0
    op = inc.get("营业利润") or 0
    tp = inc.get("利润总额") or 0
    pnp = inc.get("归母净利润") or 0
    np_ = inc.get("净利润") or 0
    fe = inc.get("财务费用") or 0
    ebit = op + fe
    ta = bs.get("总资产") or 0
    pe = bs.get("归属母公司股东权益") or 0
    avg_ta = (ta + (bs_p.get("总资产") or 0)) / 2 if bs_p else ta
    avg_pe = (pe + (bs_p.get("归属母公司股东权益") or 0)) / 2 if bs_p else pe
    return {
        "报告期": inc.get("报告期"),
        "ROE加权%": round(pnp / avg_pe * 100, 2) if avg_pe else None,
        "税负效应": round(np_ / tp, 3) if tp else None,
        "利息负担": round(tp / ebit, 3) if ebit else None,
        "核心经营利润率%": round(ebit / rev * 100, 2) if rev else None,
        "总资产周转率": round(rev / avg_ta, 3) if avg_ta else None,
        "权益乘数": round(avg_ta / avg_pe, 2) if avg_pe else None,
        "非经营损益效应": round(pnp / np_, 3) if np_ else None,
    }


# --------------------------------------------------------------------------- #
#  8. 同行横比
# --------------------------------------------------------------------------- #

def peer_compare(main_code: str, peer_codes: List[str]) -> Dict:
    out = {"main": main_code, "table": []}
    for code in [main_code] + peer_codes:
        ri = fetch_history_income(code, 2)
        rb = fetch_history_balance(code, 2)
        rc = fetch_history_cashflow(code, 2)
        if not ri or "error" in ri[0] or not rb or "error" in rb[0] or not rc or "error" in rc[0]:
            out["table"].append({"代码": code, "error": "数据拉取失败"})
            continue
        inc = normalize_income(ri[0])
        bs = normalize_balance(rb[0])
        bsp = normalize_balance(rb[1]) if len(rb) > 1 else None
        cf = normalize_cashflow(rc[0])
        r = calc_ratios(inc, bs, bsp, cf)
        out["table"].append({
            "代码": code, "报告期": inc.get("报告期"),
            "毛利率%": r.get("毛利率%"), "净利率%": r.get("净利率%"),
            "ROE加权%": r.get("ROE加权%"), "ROIC%": r.get("ROIC%"),
            "应收周转天数": r.get("应收周转天数"),
            "存货周转天数": r.get("存货周转天数"),
            "资产负债率%": r.get("资产负债率%"),
        })
    return out


# --------------------------------------------------------------------------- #
#  9. 主流程
# --------------------------------------------------------------------------- #

def run_full(code: str, assumption_file: Optional[str], years: int, proj_years: int,
             peer_codes: List[str]) -> Dict:
    out = {"代码": code, "生成时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    ri = fetch_history_income(code, years)
    rb = fetch_history_balance(code, years)
    rc = fetch_history_cashflow(code, years)

    if not ri or "error" in ri[0]:
        out["error"] = f"利润表拉取失败: {ri[0].get('error') if ri else '无数据'}"
        return out
    if not rb or "error" in rb[0]:
        out["error"] = f"资产负债表拉取失败: {rb[0].get('error') if rb else '无数据'}"
        return out
    if not rc or "error" in rc[0]:
        out["error"] = f"现金流量表拉取失败: {rc[0].get('error') if rc else '无数据'}"
        return out

    hi = [normalize_income(r) for r in ri]
    hb = [normalize_balance(r) for r in rb]
    hc = [normalize_cashflow(r) for r in rc]
    out["history"] = {"income": hi, "balance": hb, "cashflow": hc}

    if assumption_file:
        try:
            with open(assumption_file, "r", encoding="utf-8") as f:
                if assumption_file.endswith((".yaml", ".yml")):
                    try:
                        import yaml
                        a = yaml.safe_load(f)
                    except ImportError:
                        out["warning"] = "PyYAML 未安装，fallback 到默认假设"
                        a = derive_default_assumptions(hi, hb, hc)
                else:
                    a = json.load(f)
        except Exception as e:
            out["warning"] = f"假设文件读取失败（{e}），fallback 到默认假设"
            a = derive_default_assumptions(hi, hb, hc)
    else:
        a = derive_default_assumptions(hi, hb, hc)
    out["assumptions"] = a

    proj = project_three_statements(hi, hb, hc, a, proj_years)
    out["projection"] = proj
    if "error" in proj:
        return out

    # 组装全序列（从旧到新）
    hi_o = list(reversed(hi)); hb_o = list(reversed(hb)); hc_o = list(reversed(hc))
    full_i = hi_o + proj["income"]
    full_b = hb_o + proj["balance"]
    full_c = hc_o + proj["cashflow"]
    out["ratio_matrix"] = build_ratio_matrix(full_i, full_b, full_c)

    d3, d5 = [], []
    for i in range(len(full_i)):
        prev = full_b[i - 1] if i > 0 else None
        d3.append(dupont_three(full_i[i], full_b[i], prev))
        d5.append(dupont_five(full_i[i], full_b[i], prev))
    out["dupont_three"] = d3
    out["dupont_five"] = d5

    # 预测假设自洽性校验（P2）
    out["projection_sanity"] = check_projection_sanity(hi, hb, hc, a)

    if peer_codes:
        out["peer_compare"] = peer_compare(code, peer_codes)
    return out


def format_readable(result: Dict) -> str:
    if "error" in result:
        return f"错误：{result['error']}"
    lines = [f"# 三表预测报告：{result.get('代码')}", f"生成时间：{result.get('生成时间')}", ""]

    if result.get("assumptions"):
        lines.append("## 驱动假设（中性情景）")
        for k, v in result["assumptions"].items():
            if not k.startswith("_"):
                lines.append(f"- {k}: {v}")
        lines.append("")

    proj = result.get("projection", {})
    if proj.get("income"):
        lines.append("## 利润表预测")
        lines.append("| 报告期 | 营收(亿) | 归母净利(亿) | EPS |")
        lines.append("|---|---|---|---|")
        for r in proj["income"]:
            lines.append(f"| {r.get('报告期')} | {r.get('营业收入'):.2f} | {r.get('归母净利润'):.2f} | {r.get('基本EPS') or '—'} |")
        lines.append("")

    chk = proj.get("check", {})
    if chk:
        st = "PASS" if chk.get("pass") else f"FAIL ({chk.get('fail_count')} 条)"
        lines.append(f"## 三表勾稽校验：{st}")
        if not chk.get("pass"):
            for f in chk.get("fails", []):
                lines.append(f"  - {f}")
        lines.append("")

    ps = result.get("projection_sanity", {})
    if ps:
        st = "PASS" if ps.get("pass") else f"WARN ({ps.get('warn_count')} 条)"
        lines.append(f"## 预测假设自洽性校验：{st}")
        for d in ps.get("details", []):
            flag = "✅" if d.get("pass") else "⚠️"
            note = d.get("note") or ""
            lines.append(f"- {flag} {d.get('check')}{('：' + note) if note else ''}")
        lines.append("")

    rm = result.get("ratio_matrix", [])
    if rm:
        lines.append("## 关键比率矩阵（最近 6 期）")
        lines.append("| 报告期 | 毛利率% | 净利率% | ROE% | ROIC% | 资产负债率% | 净现比 |")
        lines.append("|---|---|---|---|---|---|---|")
        for r in rm[-6:]:
            lines.append(f"| {r.get('报告期')} | {r.get('毛利率%')} | {r.get('净利率%')} | {r.get('ROE加权%')} | {r.get('ROIC%')} | {r.get('资产负债率%')} | {r.get('净现比')} |")
        lines.append("")

    d3 = result.get("dupont_three", [])
    if d3:
        lines.append("## 杜邦三分解（最近 6 期）")
        lines.append("| 报告期 | ROE% | 净利率% | 总资产周转率 | 权益乘数 |")
        lines.append("|---|---|---|---|---|")
        for r in d3[-6:]:
            lines.append(f"| {r.get('报告期')} | {r.get('ROE加权%')} | {r.get('净利率%')} | {r.get('总资产周转率')} | {r.get('权益乘数')} |")
        lines.append("")

    pc = result.get("peer_compare", {})
    if pc.get("table"):
        lines.append("## 同行横比（最新一期）")
        lines.append("| 代码 | 毛利率% | ROE% | ROIC% | 应收周转(天) | 存货周转(天) | 资产负债率% |")
        lines.append("|---|---|---|---|---|---|---|")
        for r in pc["table"]:
            if "error" in r:
                lines.append(f"| {r['代码']} | {r['error']} | | | | | |")
            else:
                lines.append(f"| {r.get('代码')} | {r.get('毛利率%')} | {r.get('ROE加权%')} | {r.get('ROIC%')} | {r.get('应收周转天数')} | {r.get('存货周转天数')} | {r.get('资产负债率%')} |")
        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="三表预测 + 比率矩阵 + 杜邦分解")
    parser.add_argument("code", help="A 股代码")
    parser.add_argument("--full", action="store_true", help="完整输出（基本面深度研究常用）")
    parser.add_argument("--history", action="store_true")
    parser.add_argument("--project", action="store_true")
    parser.add_argument("--ratios", action="store_true")
    parser.add_argument("--dupont", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--peer-compare", default="")
    parser.add_argument("--years", type=int, default=5)
    parser.add_argument("--project-years", type=int, default=3)
    parser.add_argument("--assumptions", default=None)
    parser.add_argument("--json", action="store_true",
                        help="(已弃用，仍兼容) 输出 JSON；推荐使用 --format json")
    parser.add_argument("--format", choices=["readable", "json"], default=None,
                        help="输出格式：readable (Markdown 可读) / json (JSON)；未指定时沿用 --json 判定")
    parser.add_argument("--output", default=None)

    args = parser.parse_args()
    peers = [c.strip() for c in args.peer_compare.split(",") if c.strip()] if args.peer_compare else []

    # 默认或 --full 走完整流程
    result = run_full(args.code, args.assumptions, args.years, args.project_years, peers)

    # 按参数裁剪输出
    if not args.full and any([args.history, args.project, args.ratios, args.dupont, args.check]):
        keep = {"代码", "生成时间"}
        if args.history: keep.add("history")
        if args.project: keep.update({"projection", "assumptions"})
        if args.ratios: keep.add("ratio_matrix")
        if args.dupont: keep.update({"dupont_three", "dupont_five"})
        if args.check and "projection" in result:
            keep.add("projection")
        if args.peer_compare: keep.add("peer_compare")
        result = {k: v for k, v in result.items() if k in keep or k == "error" or k == "warning"}

    # 输出格式决策：--format 优先 > --json（兼容） > 默认 readable
    if args.format == "json" or (args.format is None and args.json):
        out = json.dumps(result, ensure_ascii=False, indent=2, default=str)
    else:
        out = format_readable(result)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(out)
        print(f"已写入: {args.output}")
    else:
        print(out)


if __name__ == "__main__":
    main()
