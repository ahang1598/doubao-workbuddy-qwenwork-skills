* 面板回归 Stata 模板
* 状态说明：发布时仅静态检查，尚未在 Stata 中实跑。
* 依赖说明：esttab 来自 estout 包，不属于 Stata 内置命令。
* 使用前把以下 local 宏替换为项目相对路径和实际变量名。

version 17
clear all
set more off

local data_path "inputs/your_data.dta"
local output_dir "outputs/stata-run"
local entity_id "city_id"
local time_id "year"
local depvar "outcome"
local core_var "treatment"
local controls "control_1 control_2"
local group_var "group_var"
local alternative_depvar "alternative_outcome"
local robustness_start_year 2020

capture mkdir "`output_dir'"
capture which esttab
if _rc {
    display as error "缺少 esttab。请由 Owner 在已授权的 Stata 环境安装 estout 后重试。"
    exit 499
}

confirm file "`data_path'"
use "`data_path'", clear
foreach variable in `entity_id' `time_id' `depvar' `core_var' `controls' {
    confirm variable `variable'
}
xtset `entity_id' `time_id'
log using "`output_dir'/regression_results.log", replace text

* 基准回归
xtreg `depvar' `core_var' i.`time_id', fe vce(cluster `entity_id')
estimates store baseline_1
xtreg `depvar' `core_var' `controls' i.`time_id', fe vce(cluster `entity_id')
estimates store baseline_2
esttab baseline_1 baseline_2 using "`output_dir'/table_baseline.rtf", replace ///
    b(%9.4f) se(%9.4f) star(* 0.1 ** 0.05 *** 0.01) ///
    keep(`core_var') mtitles("仅固定效应" "加入控制变量") ///
    title("基准回归结果") ///
    addnotes("标准误聚类到分析设定指定层级" "模型包含个体和时间固定效应")

* 异质性示例：确认分组预先定义且样本量足够后再执行
confirm variable `group_var'
xtreg `depvar' `core_var' `controls' i.`time_id' if `group_var' == 1, fe vce(cluster `entity_id')
estimates store heterogeneity_1
xtreg `depvar' `core_var' `controls' i.`time_id' if `group_var' == 0, fe vce(cluster `entity_id')
estimates store heterogeneity_0
esttab heterogeneity_1 heterogeneity_0 using "`output_dir'/table_heterogeneity.rtf", replace ///
    b(%9.4f) se(%9.4f) star(* 0.1 ** 0.05 *** 0.01) ///
    keep(`core_var') mtitles("组 1" "组 0") ///
    title("异质性分析") addnotes("分组规则与样本量应在正文中说明")

* 稳健性示例：替代结果变量与子样本规则必须有研究依据
confirm variable `alternative_depvar'
xtreg `alternative_depvar' `core_var' `controls' i.`time_id', fe vce(cluster `entity_id')
estimates store robustness_1
xtreg `depvar' `core_var' `controls' i.`time_id' if `time_id' >= `robustness_start_year', fe vce(cluster `entity_id')
estimates store robustness_2
esttab robustness_1 robustness_2 using "`output_dir'/table_robustness.rtf", replace ///
    b(%9.4f) se(%9.4f) star(* 0.1 ** 0.05 *** 0.01) ///
    keep(`core_var') mtitles("替代结果变量" "预设子样本") ///
    title("稳健性分析") addnotes("报告全部预先约定的稳健性设定")

log close
