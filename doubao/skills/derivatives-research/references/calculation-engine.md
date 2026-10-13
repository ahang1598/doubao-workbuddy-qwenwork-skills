# 确定性计算与交付校验

当任务包含国债期货基差、账户保证金与现金桥、短期权回补、多个压力情景，或要求交付多份可复算文件时，使用 `scripts/derivatives_engine.py`。脚本只负责确定性核算与文件一致性；合约规则、数据口径、权限、可执行性和建议仍须依据当前材料判断。

## 目录

- 使用顺序
- 输入结构
- 国债期货基差
- 账户与情景
- 短期权回补
- 输出与边界

## 使用顺序

1. 从当前任务允许使用的材料提取字段，记录字段来源和截至时点。缺失值保持缺失，不用案例经验、市场常识或脚本默认值补齐。
2. 写入版本为 `derivatives-engine-input-v6` 的 JSON。金额统一为当前任务声明的币种，价格字段按每单位或每百元口径使用字段名明确区分。每个数值输入都必须在顶层 `field_sources` 中以 JSON Pointer 路径登记 `source` 和带时区的 `as_of`，需要时补 `unit`、`currency`；缺少字段级来源时 CLI 停止。
3. 运行 `python scripts/derivatives_engine.py calculate input.json --out-dir outputs/calculation`。输入文件、既有父目录和输出目录逐级拒绝符号链接；输出目录必须尚不存在。脚本排他创建目录和每个文件，不覆盖或清理既有证据。失败后保留未带成功回执的部分目录，重跑必须改用新的输出目录。
4. 检查 `summary.json` 与各 CSV，确认方向、单位、符号和来源映射，再运行 `python scripts/derivatives_engine.py verify outputs/calculation/manifest.json`。
5. 只有 manifest 校验通过且实际文件存在时，才在答复中声称文件已经生成。用户要求 Excel、Word 或其他格式时，以这些核算结果为数据层生成，并重新打开检查最终文件；不得只列文件名或虚构下载链接。

## 输入结构

顶层字段如下，未涉及的数组可省略；`scenarios` 存在时必须提供 `account`：

```json
{
  "version": "derivatives-engine-input-v6",
  "basis_trades": [],
  "account": null,
  "short_options": [],
  "instruments": [],
  "scenario_definitions": [],
  "scenario_plans": [],
  "scenarios": [],
  "field_sources": {
    "/account/starting_equity": {
      "source": "授权账户快照",
      "as_of": "2026-09-30T16:00:00+08:00",
      "currency": "CNY"
    }
  }
}
```

`field_sources` 的键对应输入 JSON 中实际数值字段；示例只展示一个路径，不表示其他数值可以省略来源。脚本把完整映射保留在 `summary.json`，并把与每行有关的子集写入 CSV 的 `source_fields` 列。
历史版本 `derivatives-engine-input-v5` 已废弃，不得继续用于当前入口。
输入采用严格字段白名单：顶层对象以及账户、交易、合约、方案、情景和各嵌套明细中出现未声明字段时立即停止，不得静默忽略拼写错误或自定义字段。字段级来源为所有公共计算、写出和校验入口的强制条件，不能通过参数或修改 manifest 标志关闭。

### 国债期货基差

每条 `basis_trades` 需要：

- `id`：本次任务内唯一标识。
- `direction`：`buy_basis` 表示多现货、空期货；`sell_basis` 表示空现货、多期货。
- `cash_clean_price_per_100`、`accrued_interest_per_100`、`futures_price_per_100`、`conversion_factor`。
- `financing_rate_decimal`、`days_to_delivery`、`day_basis`、`carry_income_per_100`。
- `face_value`：实际分析面值，不在脚本内固定交易规模。

脚本固定使用同一组可推导口径：

```text
全价 = 净价 + 应计利息
融资成本 = 全价 × 资金利率 × 天数 / 日计数基准
理论期货价 = (净价 + 融资成本 - 持有期收入) / 转换因子
净价基差 = 净价 - 市场期货价 × 转换因子
净持有收益 = 持有期收入 - 融资成本
BNOC = 净价基差 - 净持有收益
IRR = (市场期货价 × 转换因子 + 持有期收入 - 净价) / 全价 × 日计数基准 / 天数
```

买入基差的总收敛损益为“净持有收益减净价基差”；卖出基差取反。BNOC 是这两个分项的合并诊断值，不能再作为第三项收益加入。市场期货价高于理论价称期货相对高估，对应买入基差；低于理论价称相对低估，对应卖出基差。若材料采用不同定义，停止混算，分别列示并解释差异。

### 账户与情景

`account` 需要 `starting_equity`、`existing_margin`、`proposed_margin`、`verified_margin_offset`、`equity_adjustments` 和 `cash_restrictions`。没有调整、抵扣或限制时也必须分别显式填写空数组或 `0`，不能用字段缺失暗示不存在。可另行提供：

- `equity_adjustments`：每项含唯一 `id`、`amount` 和 `already_in_starting_equity`。已经包含在起始权益中的项目不会再次加入。
- `verified_margin_offset`：只有材料明确支持的保证金抵扣才能填写。
- `cash_restrictions`：每项含唯一 `id` 与非负 `amount`。
- `reported_available_cash`、`cash_floor`、`margin_cap`：用于对账和约束检查。

脚本按“存量保证金 + 新增保证金 - 已核实抵扣”计算总保证金，不能仅拿新增保证金与上限比较。可用资金为桥接权益减总保证金和独立限制；对账差额固定为“脚本计算可用资金 - 报告可用资金”。输出同时保留每条 `equity_adjustments` 的金额、是否已进入起始权益、是否实际进入桥接计算，以及每条 `cash_restrictions` 的非负金额；不得仅用汇总值替代逐项审计桥。

情景计算分为四层，不能把合约参数重复写进各方案或各情景：

1. `instruments` 冻结合约主数据。每项包含唯一 `id`、`kind` 和 `base_mark`；期货还必须提供正数 `multiplier`。现货/现金头寸的 multiplier 固定为 1。
2. `scenario_definitions` 定义共同压力集。每个定义包含唯一 `id` 和 `marks`，每个 mark 用 instrument `id` 对应一个 `scenario_price`。每个定义必须覆盖全部已冻结 instruments，可同时提供上涨、持平、中度下跌和尾部压力等多个定义。
3. `scenario_plans` 定义待比较方案。每个 position 只提供唯一 `id`、`instrument_id` 和带符号数量；期货使用整数 `signed_contracts`，现货使用 `signed_quantity`。position 禁止覆盖 `kind`、`base_mark` 或 `multiplier`。
4. `scenarios` 是执行矩阵。每行引用一个 `plan_id` 和一个 `definition_id`，并始终提供带时区的 `as_of`。脚本要求每个方案与每个压力定义恰好组合一次；同一 `definition_id` 下所有方案必须使用完全相同的 `as_of`，以冻结共同压力时点。现金调整、存量/新增保证金和已核实抵扣属于方案级条件，可以逐方案提供并必须保留对应来源，不得为了通过可比性检查而复用不真实的金额。缺行、重复行、只给部分方案或混用不同压力时点都会停止。

脚本根据冻结的合约主数据、方案数量和共同压力价格直接计算并保留逐腿结果：

```text
期货损益 = signed_contracts × multiplier × (scenario_price - base_mark)
现货/现金头寸损益 = signed_quantity × (scenario_price - base_mark)
```

脚本仍允许 `external_valued_components`，用于当前引擎不负责重估的期权或其他复杂部件。每项必须提供唯一 `id`、`amount` 和非空 `valuation_source`；输出固定标记 `engine_calculated: false` 和 `caller_provided_external_valuation`，不得把调用方给出的金额描述成脚本计算结果。兼容字段 `pnl_components` 仅按同样的外部估值规则处理，不能与 `external_valued_components` 同时使用。

输出保留全部 instruments、方案持仓、共同压力定义、计算分项、外部估值分项、情景 marks 和现金调整，并检查分项之和严格等于 `pnl_total`。情景行可覆盖存量、新增保证金和已核实抵扣，但不得在摘要中另写一套损益、基准价、乘数或冲击数值。

情景级 `cash_adjustments` 只用于桥接权益中尚未计入、截至该情景时点已经确认且可用的不受限现金变化；没有调整时也必须显式填写空数组。每个情景始终提供带时区的 ISO-8601 `as_of`；每项现金调整必须提供唯一 `id`、`amount`、非空 `source`、`confirmed: true`、带时区的 `available_at`、`restriction_status: "unrestricted"` 和 `already_in_bridge_equity: false`。脚本会拒绝以下情况：调整 ID 与账户 `equity_adjustments` 或 `cash_restrictions` 重复、到账时间晚于情景时点、资金未确认、资金受限，或该金额已计入桥接权益。受限资金应进入账户 `cash_restrictions`，不得作为可用现金调整加入。

### 短期权回补

每条 `short_options` 需要 `option_type`、`side: short`、`contracts`、`multiplier`、`strike`、`close_ask_per_unit` 和 `close_fees`。买回空头使用 ask：

```text
回补现金支出 = ask × 张数 × 合约单位 + 已知费用
```

`close_fees` 必须由材料明确提供；明确的零费用可以填 `0` 并登记来源，缺失时脚本停止，答复中的精确回补成本和盯市损益保持 unknown，不得默认补零。不得用权利金差额、每张报价或 bid 代替上述支出。短认沽只有在材料明确给出该合约适用的有限 `underlying_price_floor` 时才计算有限最大损失；不得默认标的下限为零。若缺少该下限，最大损失保持 `unknown_without_underlying_price_floor`。给定下限后：

```text
权利金前最大损失 = max(0, (strike - underlying_price_floor) × contracts × multiplier)
权利金后最大损失 = max(0, 权利金前最大损失 - premium_received_total)
```

缺少 `premium_received_total` 时权利金后最大损失保持未知。短认购单腿最大损失保持无有限上界。对允许负价格或没有可证有限下限的标的，不得用零下限替代真实合约边界。

## 输出与边界

脚本排他生成原字节 `input.json`、`summary.json`、`basis.csv`、`account.csv`、`short_options.csv`、`scenarios.csv` 和 `manifest.json`，先完成输入、数据文件哈希、来源映射、行数与数值列校验，最后才排他创建 `run.log`。`run.log` 的 `status=passed` 必须同时绑定已验证 manifest 的 SHA-256；缺少该回执或哈希不匹配时不得声称生成成功。CLI 解析 JSON 时直接把整数和小数读为 `Decimal`，不经过二进制浮点；manifest 的 `input_sha256` 绑定用户输入的原始字节。只在写 `summary.json` 时把 Decimal 转换为无精度损失的十进制文本，写 CSV 时可信计算数值仍按数值文本输出。只有原本就是字符串且以 `=`、`+`、`-` 或 `@` 开头的单元格才加前导单引号，防止外部文本被电子表格解释成公式；不得给负数计算结果加单引号。嵌套分项和来源映射会先转换为 JSON 文本后写入 CSV。

manifest 除数据文件哈希和行数外还固定数值列清单。`verify` 会从保存的原始 `input.json` 重新执行确定性计算，完整比对 `summary.json` 的所有字段，并逐字节重建和核对各 CSV 的全部列；数值列还会重新解析为有限十进制数。最后核对成功回执绑定的 manifest 哈希；出现 `'-123`、缺列、任意字段分歧、符号链接或回执不一致时必须失败。

脚本不会推断缺失的规则、报价、波动率、保证金抵扣、权限或成交结果，也不会替代期权完整重估。它不执行交易，不联网，不读取输入 JSON 之外的业务材料。若输出与人工摘要冲突，以重新核对输入和脚本输出为先，不手工覆盖结果。
