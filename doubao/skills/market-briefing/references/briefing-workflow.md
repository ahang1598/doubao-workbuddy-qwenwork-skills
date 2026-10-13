# 命题验证与可复现交付

仅在答案含重要方向判断、验证计划、实际计数，或用户明确要求文件与复现时读取。普通短答和零工具任务不运行脚本。

## 语义契约

重要判断先写成可判真的命题，内部记录当前 ID/版本、目标、范围、时间尺度、前提、观点、证据、支持与证伪信号、替代解释及结论变化。风险缓解不自动等于整体看多；正面、负面、中性和混合观点采用同一验证方法。

每份证据只有一个当前状态：来源、位置、可用时间、`confirmed|unknown|disputed|superseded`、证据层和允许的最高表述强度。最终使用必须引用当前版本。已公开、任务可用和市场已计价是不同命题；公开时间或价格变化不能单独证明部分或充分计价。字段中的 `confirmed` 仍是输入声明，不是来源真实性证明。

含命题或最终使用的任务图必须提供顶层 `as_of`。`as_of` 和已知 `available_at` 使用带显式 UTC 偏移的 ISO 8601 时间；证据恰好在截止时点可用，晚于截止时点则以结构化 `cutoff_error` 拒绝。只做正文哈希、实际计数、项目数量或与证据图无关的离线结构检查时可以省略 `as_of`，不得为此虚构截止时间。提供 `as_of` 时，所有已知证据可用时间都不得晚于它；`available_at=unknown` 不能用于自称已支持或已证伪的决定性使用。

证据层与最高表述强度只能采用固定组合：`observation->observation`、`association->association`、`mechanism_hypothesis->hypothesis`、`causal_conclusion->causal`。脚本拒绝以不匹配的 `max_strength` 放宽证据层。

同一指标只定义一次对象、样本、运算、单位、窗口、基准、来源和版本。条件中的谓词只定义一次指标、运算符、阈值和单位；同一条件内谓词 ID 不得重复，不同条件可以使用相同局部 ID。缺失输入为 `unknown`，不能变成 `false` 或零。当前水平、单期变化、均值、比率和复合收益保持不同身份。

信号标记 `market_reaction`、`participation`、`implementation` 或 `economic_transmission`。每个命题附着的市场反应和参与信号至少需要 `observation` 层证据，实施信号至少需要 `association`，经济传导信号需要 `causal_conclusion`；较高层可以满足较低层结构下限。价格与成交可以验证反应或参与，不能单独确认实施或经营传导。脚本只检查命题证据集合是否达到层级下限，不证明该证据与具体信号在经济语义上真正对应。

每个决定性句子建立内部 `use`，绑定当前命题、证据、信号、指标、条件和实际正文片段。内部字段不进入普通答案。

以下内容必须由人或模型裁决，脚本不得冒充完成：命题极性、信号方向、替代解释、来源真实性、证据层分类是否属实、证据与信号的具体语义对应、跨层因果以及客观表是否足以支持经济叙述。

## 助手与调用

`scripts/briefing_checks.py` 保持原有观察 CLI。`scripts/briefing_workflow.py` 处理上述绑定、实际文本计数，以及从原始 CSV 重建客观表。

- 文件：`python3 scripts/briefing_workflow.py INPUT.json`
- 标准输入：`python3 scripts/briefing_workflow.py -`
- Python：`process(doc)` 成功返回字典；无效输入抛出 `WorkflowError`。

程序不联网、不执行命令、不调用任意表达式、不自动重试。成功只将 `deterministic` 标为 `passed`；`semantic_review` 和 `source_truth` 保持 `not-run`。错误输出 `ok=false`、`error.type`、`error.message`、`error.path`，退出码非零。截止错误使用 `cutoff_error`；原始文件读取、UTF-8 解码和 CSV 解析错误使用 `input_error`；有限源数值在聚合、除法、收益、缩放、复合乘法或比较中产生非有限结果时使用 `arithmetic_error`，不得以 traceback 代替结构化 JSON。

## 输入契约

公共顶层字段为 `schema_version=market-briefing-workflow-v1`、`mode=validate|build`，以及可省略的 `as_of` 和数组 `evidence`、`metrics`、`conditions`、`claims`、`signals`、`uses`、`subjects`、`limits`。引用格式为 `id@revision`。只要 `claims` 或 `uses` 非空，`as_of` 就是必填字段。

- `evidence`：`id,revision,source_id,locator,available_at,status,layer,max_strength`。
- `metrics`：公共字段 `id,revision,source_id,operation,object,universe,unit,window,baseline,sample,keys`。
- `conditions`：`id,revision,logic,predicates`；谓词为 `id,metric,operator,value,unit`。
- `claims`：`id,revision,proposition,target,scope,horizon,view,premises,state,evidence,support,falsify,alternatives,on_support,on_falsify`。
- `signals`：`id,revision,claim,condition,key,direction,polarity,layer,adjudication`。
- `uses`：`id,claim,state,strength,evidence,signals,metrics,conditions,subject,fragment`。
- 文本主体：`id,kind=text,content`；项目主体：`id,kind=items,items`。
- 计数约束：`id,subject,measure`，以及 `exact` 或 `minimum`/`maximum`。度量为 `characters|utf8_bytes|whitespace_words|items`。

证据层为 `observation|association|mechanism_hypothesis|causal_conclusion`；表述强度为 `observation|association|hypothesis|causal`。命题时间尺度为 `intraday|multi_day|multi_week|quarter|unknown`。

指标运算附加字段：

- `sum|mean|group_mean`：`field`。
- `count`：可选 `field`。
- `ratio`：`numerator,denominator`。
- `return`：`start,end,output_scale`，每组至多一行。
- `window_mean`：`field,order_by,order_by_type,window_rows`。
- `compound_return`：`field,input_scale,output_scale`。

尺度只能为 `decimal|percent`。`window_mean.order_by_type` 必须为 `number|timestamp|string`：数值解析为有限浮点数，时间解析为带显式 UTC 偏移的 ISO 8601，只有显式 `string` 才按字符串排序。同一键组内排序值必须唯一；非法数字、非有限数字、无偏移时间和重复值都会失败。窗口和生成表行均按解析后的类型排序，因此数值 `1,2,10` 不按 `1,10,2` 排列。

所有计算后置条件使用 `math.isfinite`。`finite(v,p)` 对 `None` 保持未知，拒绝布尔值和非整数/浮点类型，并在转换为 `float` 后拒绝正负无穷与 NaN；`fsum(values,p)` 使用 `math.fsum`，将溢出和非有限结果转换为含 `non-finite` 文案的 `arithmetic_error`。聚合总和、均值、窗口均值、比率、`B/A-1`、收益百分比缩放、每一次复合乘法及最终缩放都必须通过该后置条件。`rec` 还复核 `value`、`observed_sum`、`numerator`、`denominator`、`start`、`end` 和 `gross_product`。

谓词比较前复核左右操作数。任何非有限操作数以 `arithmetic_error` 失败；任一操作数为 `None` 时结果保持 `unknown`，包括 `ne`，不得把缺失值变成 `true`。条件结果只允许 `true|false|unknown`。

合成结构示意，不代表市场事实或默认限制；该示意没有命题或证据图，因此不需要虚构 `as_of`：

```json
{"schema_version":"market-briefing-workflow-v1","mode":"validate","subjects":[{"id":"answer","kind":"text","content":"合成示意文本"}],"limits":[{"id":"length","subject":"answer","measure":"characters","exact":6}]}
```

## 文件重建

`build` 模式另需：

- `requirements`：每项 `id,path,fields`，在生成前独立声明预期客观文件和完整有序字段。
- `build.input_root`：已存在的绝对原始输入根目录。
- `build.output_root`：父目录已存在、目标尚不存在的绝对新目录。
- `build.sources`：每项 `id,path,role=raw,encoding=utf-8,delimiter,required_columns`。
- `build.tables`：每项 `id,requirement,path,metrics,conditions`。

表 ID 必须等于 CSV 文件名去掉 `.csv` 后的部分。每个要求恰好绑定一张表。表头先放键字段，再为每个指标生成 `value,operation,object,universe,unit,window,baseline,sample,source_id,source_sha256,sample_count,missing_count,observed_sum,numerator,denominator,start,end,gross_product`，最后为每个条件生成 `result,logic,predicate_ids`。不适用或不可计算值写 `unknown`。

路径拒绝绝对子路径、空段、`.`、`..`、反斜线和符号链接。输入与输出根目录互不包含；输出根目录必须全新，因此不会覆盖既有文件或采用预先派生文件捷径。

原始文件必须可读、为合法 UTF-8，并能由严格 CSV 解析器解析。缺失或不可读文件、无效 UTF-8、CSV 语法错误和行宽不一致均以结构化 `input_error` 失败。输出目录创建后的计算、写入、重开或清单失败会清理本次输出根目录，不生成成功清单；失败构建不得留下本次输出根目录。

每个指标输出单元在 CSV 序列化前都经过 `render_value`：`None` 写为 `unknown`，布尔值和非有限浮点数被拒绝，有限浮点数使用 `.17g`。只有计算、谓词、序列化和重开有限性检查全部通过后，确定性覆盖才可加入 `raw-csv-arithmetic`。

程序从本次读取的原始 CSV 字节计算全部表，排他写入后逐个重新打开，复核表头、行宽和行数并计算 SHA-256。重开的每个指标数值列 `value`、`sample_count`、`missing_count`、`observed_sum`、`numerator`、`denominator`、`start`、`end`、`gross_product` 都重新解析；字面量 `Infinity`、`-Infinity`、`NaN`、其他非有限解析结果或非数字内容均以 `build_error` 拒绝。该规则要求 CSV 和清单不得出现 `non-finite reopened` 成功路径。

所有表复核后才生成并重开 `manifest.json`。重开使用 `json.loads(..., parse_constant=reject_json_constant)`；`reject_json_constant` 对 JSON 的 `Infinity`、`-Infinity` 和 `NaN` 抛出 `malformed_json`，重开对象还必须与刚写入的清单一致。清单记录实际输入与输出哈希、字段、行数、需求绑定和依赖 ID；提供 `as_of` 时也记录原始截止字符串。它证明本次字节级重建、有限算术和结构检查，不证明 `role=raw` 声明、来源真实性、样本代表性、证据层自报真实性或经济结论。
