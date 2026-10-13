#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""面板回归与学术图表模板。

本文件提供可复用函数，不代表任何具体研究设定已被验证。
输入与输出路径由调用方显式传入，不在源码中保存个人路径。
"""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from linearmodels import PanelOLS


plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["font.size"] = 10
plt.rcParams["axes.spines.top"] = False
plt.rcParams["axes.spines.right"] = False
plt.rcParams["axes.grid"] = False


def run_panel_reg(y, x, entity_effects=True, time_effects=True, cluster_entity=True):
    """拟合面板模型；调用前由研究设计确定固定效应和聚类层级。"""
    if len(y) == 0 or len(x) == 0:
        raise ValueError("回归输入不能为空")
    if not y.index.equals(x.index):
        raise ValueError("y 与 x 的索引必须完全一致")
    model = PanelOLS(
        y,
        x,
        entity_effects=entity_effects,
        time_effects=time_effects,
        drop_absorbed=True,
        check_rank=False,
    )
    return model.fit(cov_type="clustered", cluster_entity=cluster_entity)


def format_reg_result(title, result, core_var):
    """返回可审计的核心回归结果字典，不把显著性解释为因果。"""
    if core_var not in result.params.index:
        raise KeyError(f"结果中不存在核心变量: {core_var}")
    coefficient = float(result.params[core_var])
    standard_error = float(result.std_errors[core_var])
    p_value = float(result.pvalues[core_var])
    stars = "***" if p_value < 0.01 else "**" if p_value < 0.05 else "*" if p_value < 0.1 else ""
    return {
        "title": title,
        "variable": core_var,
        "coefficient": coefficient,
        "standard_error": standard_error,
        "p_value": p_value,
        "stars": stars,
        "nobs": int(result.nobs),
        "r_squared": float(result.rsquared),
    }


def _prepare_output(save_path):
    path = Path(save_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def plot_coef_forest(names, coefficients, standard_errors, title, save_path):
    """绘制系数与 95% 正态近似置信区间。"""
    if not (len(names) == len(coefficients) == len(standard_errors)):
        raise ValueError("名称、系数和标准误数量必须一致")
    path = _prepare_output(save_path)
    y_positions = np.arange(len(names))
    coefficients = np.asarray(coefficients, dtype=float)
    standard_errors = np.asarray(standard_errors, dtype=float)
    fig, axis = plt.subplots(figsize=(8, 0.5 * len(names) + 2))
    axis.errorbar(coefficients, y_positions, xerr=1.96 * standard_errors, fmt="o", capsize=5, color="black")
    axis.axvline(x=0, color="gray", linestyle="--", linewidth=0.8)
    axis.set_yticks(y_positions)
    axis.set_yticklabels(names)
    axis.set_title(title, pad=15)
    axis.set_xlabel("回归系数")
    fig.tight_layout()
    fig.savefig(path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return path


def plot_event_study(periods, coefficients, standard_errors, title, save_path):
    """绘制动态系数与 95% 正态近似置信区间。"""
    if not (len(periods) == len(coefficients) == len(standard_errors)):
        raise ValueError("时期、系数和标准误数量必须一致")
    path = _prepare_output(save_path)
    coefficients = np.asarray(coefficients, dtype=float)
    standard_errors = np.asarray(standard_errors, dtype=float)
    lower = coefficients - 1.96 * standard_errors
    upper = coefficients + 1.96 * standard_errors
    fig, axis = plt.subplots(figsize=(10, 5))
    axis.plot(periods, coefficients, "o-", color="black", markersize=6)
    axis.fill_between(periods, lower, upper, color="gray", alpha=0.2)
    axis.axhline(y=0, color="gray", linestyle="--", linewidth=0.8)
    axis.axvline(x=0, color="black", linestyle=":", linewidth=0.8, label="事件期")
    axis.set_xlabel("事件期")
    axis.set_ylabel("回归系数")
    axis.set_title(title, pad=15)
    axis.legend()
    axis.set_xticks(periods)
    fig.tight_layout()
    fig.savefig(path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return path
