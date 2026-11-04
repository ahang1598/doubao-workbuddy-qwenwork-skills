# 当前数据协议与能力边界（revision 3）

只支持显式 contractRevision:3，不接受缺省版本、旧输入或迁移选项。内部视觉中间表示不是公开协议。

资源身份以 vendor.lock.json 和真实 Catalog 为准，本地修改不等于发布；不能改锁绕过能力门禁。

## 三协议与唯一数据源

- revision 3 MapSpec 保持事实模型；字段显式声明稳定 id、实体种类、property、valueType、来源数组及可选单位，不从 label 或字符串猜测类型。
- revision 3 Plan 根声明 dataSources 与 encodings；每个 View 声明 layers、filters、metrics。普通点线面使用 componentNodes/UI/layout/viewport 意图，不引入第四份公开协议。
- 数据源引用实体和 fieldId，rowIdentity 为 entity；相同地点的多次 occurrence 不重复增加分析样本。源行一次物化到 Graph 根表，跨 View 可共享该表，各 View 的条件互相隔离。
- revision 3 Graph 写入 fieldDefinitions、entityIndex、occurrenceIndex、dataSources（definition/rows/quality）、layers、encodings 和 expectedContent。索引仅含身份、名字及访问关系，不复制原始业务属性。
- 分析元素只引用 sourceId/encodingId/layerId，不内联 points。prepareGraph 在 Node Builder、浏览器 Runtime 与 checker 边界校验根表，再投影为既有 Kit Props。不可绕过根表消费 inline points。
- 路线/区域编码按稳定实体 ID 分配。seriesStyles 是根分类编码的确定性投影；投影被篡改则拒绝。数组重排不换颜色，不承诺增删实体后配色不变或扩大调色板容量。
- 分析编码保存 Catalog 解析后的视觉参数；动态蜂窝聚合、色域、高度和连续核仍复用 Kit 的唯一实现，不在 Compiler 新建第二套网格或声称已经实现完整通用 quantitative encoding/revision 模型。

analysis-declarations.schema.json 是三协议复用的结构片段；manifest 中 validationOnly 表示它不能作为第四份公开输入单独交付，不表示它可作为单独交付输入。修改任何 schema 后都必须重建离线校验器及 manifest。

## 热力图分析层

热力图分析层的 `elementIds` 仅填一个 `<viewId>:analysis:<自定义名称>`，作为编译器生成元素的 ID，无需在 `componentNodes` 中重复声明。

## 类型、质量与尺度

源级 missingValuePolicy 缺省 error，仅显式 skip 排除非法行；实体/字段断引用、重复身份和不安全选择器不能 skip。数值必须有限，布尔/字符串严格匹配；日期校验后转换为 epoch 毫秒。保留 0、false、空字符串，缺失/null 归一为 null。

统计值、连续权重和数值指标所需字段必须有效；权重非负。只用于筛选或 distinct-count 的缺失值保留未知语义。质量满足 inputCount = validCount + excludedCount；同一行可有多个原因，因此 reasons 总和不必等于 excludedCount。

源行、绘制、筛选、查询和动态指标共享有效身份。筛选缺省使用全源尺度，显式 filtered 才重新归一化。同层的连续权重、蜂窝颜色与高度尺度人口必须一致。柱高与颜色域独立；负数聚合不能进入声明了 3D 的层，筛选提交前调用 Kit 解析器验证，不先污染条件状态。空筛选结果合法并保留相机；初始空源的执行限制见下文。

## 四类筛选与六类指标

- enum：selected 为选项索引数组；null 不限，[] 零匹配，false/0 不转字符串。
- number-range / time-range：闭区间 [下限, 上限]，端点 null 表示无界；时间为 epoch 毫秒，表单要求含时区的合法日期。非法日期、非有限值或逆序输入保留旧状态。
- text：NFKC 归一化、不区分大小写、字面包含；不执行正则或代码。多个条件 AND，缺失值不匹配有效条件。
- count、distinct-count、sum、average、min、max：明确 sourceId、fieldId（count 无字段）、scope=all-source|filtered 及单位；distinct 忽略缺失，空集合 count/distinct 为 0，其他为 null 并显示“无数据”，溢出拒绝。
- 每个 (viewId, sourceId) 仅有宿主一份条件；四类 UI 为 Kit 受控表单，Kit 不持有第二套业务谓词或自动聚合。
- 静态来源摘要不猜测成动态公式，仍标记不随筛选变化。变化清除旧详情/查询，普通筛选与重置不触发相机全览。

## 当前显式拒绝的执行能力

以下结构可供声明校验/未来扩展，但不属于当前可执行能力，compileMap 返回明确错误，不降级为其他含义：

- 用 LayerDef 替代普通点线面的通用执行器；普通几何使用受控 componentNodes。
- 初始为空或清洗后为空的分析源（运行中筛选至空已支持）。
- 非 [0,0] 网格原点、min 蜂窝聚合、quantile 色域。
- comparisonScopeId、自定义 interaction.queryId、同层混合尺度人口。
- 没有关联分析层的独立源指标/筛选，以及任意关系树级联/路线网络过滤。

不得通过删除数据或改变统计口径绕过这些限制。

## 能力协商与验收

Catalog 与真实 UMD 必须声明支持 revision 3。分析图需要 ui.analysis-filter@2、ui.analysis-metrics@1；分析源还需要 heatmap.render-extent@1、controlled-filter 及实际模式能力。Compiler、Builder、页面初始化逐层核对包身份、Catalog 哈希与能力，旧资源不静默接收新图。

checker 从序列化根表独立重算，比较 Kit 实际 points/filter、状态中的有效集合、DOM 指标值与文本；不只相信 Runtime 自报 ready。原有路线、section、投影、布局、交互和无截图浏览器检查保持启用。篡改根引用、质量、类型、覆盖范围、points 或指标的负例应失败。

真实浏览器验收使用 tools/test-component-rules-browser.mjs；分析功能还需运行根表、四类筛选、六指标与三模式回归。生成产物执行 check-html.mjs --mode startup，不创建截图或模型看图报告。
