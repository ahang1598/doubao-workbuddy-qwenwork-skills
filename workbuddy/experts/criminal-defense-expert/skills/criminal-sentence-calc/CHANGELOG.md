# Changelog

## 版本历史

- **v2.2.0** (2026-06-12): 深度内容优化——2阻断+6严重修复+方法论增强。
  - 🔴阻断修复：date_calculator.py days_between()含首尾计vs数学差→折抵计算使用数学差(inclusive=False)
  - 🔴阻断修复：废弃30天/月概算→逐月推算(months_to_days)，29个月误差从13天→0天
  - 🟠严重修复：新增量刑情节竞合处理规则（自首+认罪认罚禁止重复评价、累计从轻上限60%、从轻vs减轻区分）
  - 🟠严重修复：刑法第69条补全第2款（有期徒刑吸收拘役）+第3款（附加刑并罚）
  - 🟠严重修复：指定居所监视居住2:1折抵（刑诉法第76条）
  - 🟠严重修复：量刑幅度速查表校准至法发〔2021〕21号（自首20%以下/立功20%以下/认罪认罚30%以下）
  - 增强methodology.md 5.02KB→≥10KB（新增§2量刑情节竞合+§1.3监视居住折抵+§1.5异种主刑+§1.8逐月推算+§5校准表+§6刑期起止日规则）
  - output-spec.md新增偏差范围标注（禁止精确到"月"不标±）、竞合检查列、含首尾/数学差双列、监视居住行
  - SKILL.md核心原则9→11条（P1含首尾vs数学差红线+P2量刑竞合红线+P3折抵+羁押类型匹配红线）
  - 新增P10刑期起算日区分、P11逐月推算强制
  - input-spec.md新增"指定居所监视居住期间"可选输入字段
  - legal-references.md新增刑诉法第76条、刑诉法解释第202条、第69条第2-3款
  - sentence_validator.py新增月天数校验+异种主刑校验+量刑竞合校验
- **v2.1.1** (2026-06-11): P0阻断修复——output-spec双轨输出对齐、O4计算错误880→870天修正及释放日连锁修正、script_necessity required→platform-api（SSOT §17.17三态模型）、manifest补齐infrastructure_dependencies、补齐methodology.md。
- **v2.0.0** (2026-06-05): 地区量刑细则检索+计算逻辑脚本化。新增 jurisdiction 输入字段、量刑幅度三级来源优先级(P0/P1/P2)、3个 Python 脚本（date_calculator/sentencing_data_retriever/sentence_validator）、script_necessity 升级为 required（L3 风险例外）。
- **v1.0.0** (2026-06-05): 初始版本。覆盖单罪+数罪刑期计算、3种羁押折抵比例、3种数罪并罚情形、刑期起止日精确计算。
