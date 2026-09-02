# SIF ASIN 概览数据解读维度

基于 `linkfox-sif-asin-summary` 返回的字段，对 Top ASIN 做 8 个维度的流量结构深度解读。适用于市场洞察报告中对头部竞品的流量拆解。

## 返回字段总览

### 基础信息
| 字段 | 说明 |
|------|------|
| asin | ASIN |
| productTitle | 商品标题 |
| productPrice | 当前价格 |
| productStarRating | 星级 |
| customerRatingCount | 评论数 |
| isVariantProduct | 是否变体 |
| dataPeriodStartDate | 数据周期起始日 |

### 曝光得分（本期 + 上期 + 占比）
| 字段 | 说明 |
|------|------|
| totalExposureScore / Prev | 总曝光得分（及上期） |
| naturalSearchExposureScore / Prev / Ratio | 自然搜索曝光得分（及上期、占比） |
| sponsoredProductsExposureScore / Prev / Ratio | SP 广告曝光得分（及上期、占比） |
| brandAdExposureScore / Prev / Ratio | 品牌广告曝光 |
| videoAdExposureScore / Prev / Ratio | 视频广告曝光 |
| amazonsChoiceExposureScore / Prev / Ratio | Amazon's Choice 曝光 |
| editorialRecommendationsExposureScore / Ratio | 编辑推荐曝光 |
| topRatedExposureScore / Ratio | Top Rated 曝光 |
| recommendAdExposureScore | 推荐位广告曝光 |
| recommendNonadExposureScore | 推荐位非广告曝光 |
| recommendPositionExposureScore | 推荐位总曝光 |
| nonAcRecommendExposureScore | 非 AC 推荐曝光 |

### 关键词数量（本期 + 上期 + 新进/退出）
| 字段 | 说明 |
|------|------|
| totalTrafficKeywordCount / Prev / In / Out | 总流量词数（及上期、新进、退出） |
| naturalSearchKeywordCount / Prev / In / Out | 自然搜索词数 |
| sponsoredProductsKeywordCount | SP 广告词数 |
| amazonsChoiceKeywordCount / In / Out | AC 词数 |
| videoAdKeywordCount | 视频广告词数 |
| recommendKeywordCount | 推荐词总数 |
| recommendAdKeywordCount | 推荐广告词数 |
| recommendNonadKeywordCount | 推荐非广告词数 |

## 8 个解读维度

### 维度 1：流量来源构成（曝光占比分析）
- **自然搜索占比** = `naturalSearchExposureRatio`：>90% 为自然流量主导型，<50% 为广告驱动型
- **SP 广告占比** = `sponsoredProductsExposureRatio`：判断付费依赖度
- **推荐位占比** = `editorialRecommendationsExposureRatio + topRatedExposureRatio`：AC/ER/TR 推荐带来的曝光
- **判断**：自然主导型（品牌力强）/ 广告驱动型（烧钱撑排名）/ 推荐位依赖型（靠 Amazon 算法推荐）

### 维度 2：曝光趋势（本期 vs 上期）
- **总曝光变化率** = `(totalExposureScore - totalExposureScorePrev) / totalExposureScorePrev × 100%`
- **自然曝光变化率** = `(naturalSearchExposureScore - naturalSearchExposureScorePrev) / naturalSearchExposureScorePrev × 100%`
- **SP 广告曝光变化率** = `(sponsoredProductsExposureScore - sponsoredProductsExposureScorePrev) / sponsoredProductsExposureScorePrev × 100%`
- **判断**：正增长=流量扩大；负增长=流量萎缩；自然+广告双增=健康增长；广告增自然降=靠加大投放弥补自然流失

### 维度 3：关键词覆盖广度（流量入口数量）
- **总流量词数** = `totalTrafficKeywordCount`：该 ASIN 被多少个关键词收录
- **自然词数** = `naturalSearchKeywordCount`：自然排名覆盖的词数
- **SP 广告词数** = `sponsoredProductsKeywordCount`：投放广告的词数
- **判断**：自然词远多于广告词 = 自然流量底盘扎实；广告词占比高 = 靠广告覆盖长尾

### 维度 4：关键词流动性（新进/退出）
- **总词新进数** = `totalTrafficKeywordCountIn`：本期新获得的流量词
- **总词退出数** = `totalTrafficKeywordCountOut`：本期失去的流量词
- **自然词新进/退出** = `naturalSearchKeywordCountIn / Out`
- **AC 词新进/退出** = `amazonsChoiceKeywordCountIn / Out`
- **判断**：新进 > 退出 = 流量扩张期；退出 > 新进 = 流量收缩期；AC 词频繁进出 = Amazon's Choice 标签不稳定

### 维度 5：Amazon's Choice 标签分析
- **AC 词数** = `amazonsChoiceKeywordCount`：当前持有 AC 标签的关键词数
- **AC 曝光得分** = `amazonsChoiceExposureScore`：AC 标签带来的曝光量
- **AC 词新进/退出** = `amazonsChoiceKeywordCountIn / Out`：标签获取/流失
- **判断**：AC 词数多 = Amazon 算法认可度高；AC 词退出 > 新进 = 标签流失风险；AC 曝光占比高 = 严重依赖标签流量

### 维度 6：推荐位曝光分析
- **ER 编辑推荐** = `editorialRecommendationsExposureScore / Ratio`：Amazon 编辑推荐位
- **Top Rated** = `topRatedExposureScore / Ratio`：高评分推荐位
- **推荐广告** = `recommendAdExposureScore`：推荐位中的广告曝光
- **推荐非广告** = `recommendNonadExposureScore`：推荐位中的自然曝光
- **判断**：推荐位曝光占比高 = Amazon 算法偏好该 ASIN；推荐广告 > 推荐非广告 = 推荐位也是花钱买的

### 维度 7：变体流量分布（如果返回多个 ASIN）
- 当 `isVariantProduct = true` 时，API 可能返回同一父体下多个子 ASIN 的数据
- 对比各子 ASIN 的 `totalExposureScore`：哪个变体是流量主力？
- 对比各子 ASIN 的 `naturalSearchExposureRatio` vs `sponsoredProductsExposureRatio`：主力变体靠自然还是广告？
- **判断**：单变体主导 = 集中运营；多变体均分 = 矩阵打法；子变体全靠广告 = 变体策略低效

### 维度 8：广告投放强度评估
- **SP 广告词数 vs 自然词数** = `sponsoredProductsKeywordCount / naturalSearchKeywordCount`：广告覆盖密度
- **SP 曝光占比** = `sponsoredProductsExposureRatio`：广告贡献的曝光份额
- **SP 曝光变化** = `(sponsoredProductsExposureScore - sponsoredProductsExposureScorePrev)`：广告投入趋势
- **判断**：广告词数 > 自然词数 = 重度广告依赖；SP 曝光占比 > 30% = 广告是核心流量来源；SP 曝光持续增长 = 卖家在加投

## 报告输出建议

用 Data Table 展示 8 个维度的诊断结果。流量来源构成用饼图（自然/SP/推荐/其他占比）。曝光趋势用双柱状图（本期 vs 上期）。关键词流动性用对比柱状图（新进 vs 退出）。
