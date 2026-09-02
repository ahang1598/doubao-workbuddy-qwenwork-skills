# 三步回环验证

> 借鉴 `browser-act-skill-forge` Phase 3b。
> 每个 `scripts/*.py` 文件交付前必须过这三步。

---

## 为什么要三步

只看一次成功调用不能证明脚本可靠：
- **第 1 步** 证明"脚本能跑、输出结构合法"——排除参数解析错、输出格式错。
- **第 2 步** 证明"脚本输出和真实业务匹配"——排除字段映射错、单位错、空值降级错。
- **第 3 步** 证明"脚本不会因为坏输入崩溃"——排除"在生产里第一次遇到不存在的 ASIN 就直接 stack trace"。

少跑任何一步都是隐患。

---

## 第 1 步：基本运行 + 结构合法

```bash
python scripts/get-product-detail.py B08N5WRWNW --marketplace US
```

通过条件：
- 退出码 0（错误路径退出码 1）。
- stdout 是有效 JSON。

不通过的常见原因：argparse 参数名拼错、stdout 混入 stderr、JSON 序列化失败。

---

## 第 2 步：真实跑通 + 数据匹配预期

跑一个真实业务参数，肉眼或机器化对比预期：

```bash
python scripts/get-product-detail.py B08N5WRWNW --marketplace US | jq '.title, .price, .review_count'
```

**Tier 2 / Tier 3（流程编排 skill）**：在端到端流程里跑——上游步骤的输出能流入下游步骤的输入，最后报告/UI 章节字段填齐。每个 Tier 1 调用拿一个已知业务键（ASIN / keyword / shop_id 等），对比 vendor 文档或界面上的真实数据，关键字段准确。

不通过 → 业务逻辑有错，回去修。**不要降级标准**（"差不多就行"）——这一步过不了，skill 是坏的。

---

## 第 3 步：错误参数 → 优雅返回

故意传坏参数，确认返回 `{"error": true, "message": "..."}` 而不是崩溃：

| 测试用例 | 期望 |
|---------|------|
| `python scripts/get-product-detail.py INVALID-ASIN` | `{"error": true, "message": "ASIN not found"}` 或类似 |
| `python scripts/get-product-detail.py B08N5WRWNW --marketplace XX` | `{"error": true, "message": "Unsupported marketplace"}` |
| `python scripts/get-product-detail.py` （缺必填）| argparse 报错（这个允许走 stderr） |
| 网络错误（断网模拟） | `{"error": true, "message": "network unreachable"}` |

不通过 → scripts 缺 try/catch 或错误传播路径——补全。

---

## 自动化执行

跑 `python scripts/verify_skill_scripts.py <skill 目录>` 一次性执行三步。

它会：
1. 扫描 `scripts/*.py`。
2. 从 `examples/trial-prompts.md` 或 `examples/test-cases.md`（如有）读测试用例。如果都没有，提示作者补一份最小测试用例。
3. 对每个脚本顺序跑三步，记录通过/失败。
4. 输出 JSON 报告（pass / fail 数 + 失败详情）。
5. 任何一步失败退出码非 0。

---

## 测试用例格式

放在 `examples/test-cases.md` 或 `examples/trial-prompts.md`。结构示例：

```markdown
## scripts/get-product-detail.py

### 正常用例
- B08N5WRWNW US → 期望 title 含 "Echo"，price > 0
- B0XXX_有效 UK → 期望 marketplace 字段 = "UK"

### 错误用例
- INVALID-ASIN US → 期望 error: true
- B08N5WRWNW XX → 期望 error: true (Unsupported marketplace)
```

`verify_skill_scripts.py` 解析该文件结构，自动跑用例。

---

## 跨 Tier 适配

| Tier | 第 1 步 | 第 2 步 | 第 3 步 |
|-----------|--------|--------|--------|
| Tier 2（跨源组合 / 流程编排） | 每个 scripts/*.py 单独跑 | 端到端在试跑 prompt 中验证，Tier 1 调用结果与 vendor 文档对齐 | 单个脚本 + 端到端各一次错误注入（含 Tier 1 限频 / 空数据 / 网络错误） |
| Tier 3（业务 SOP 复刻） | 同 Tier 2 | 同 Tier 2，且报告产物章节内"数据来自哪步、关键字段"在端到端跑后字段都能填齐 | 同 Tier 2，再加一次"某 Tier 1 返回空 → 对应报告章节是否标注好降级文案"测试 |

---

## 失败处理

任一步失败 → 修脚本 → 重跑全部三步。**不要只重跑失败的那步**——fix 可能引入新回归。
