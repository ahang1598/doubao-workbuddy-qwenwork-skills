# Citation Style Reference

## 默认格式：Numeric Citation (Citation-Sequence)

未指定时一律采用 numeric citation system，具体使用 citation-sequence 排列方式：正文中按引用首次出现的顺序分配编号 `[1]`, `[2]`, ...，全文连续编号，文末 References 按编号顺序排列。此格式与 IEEE reference format 一致，广泛用于工程、计算机科学和自然科学领域。

### In-text citation

```
Transformer architectures have become the dominant paradigm in NMT [1]. Smith et al. [2]
extended this line of work by introducing adaptive scheduling, while several concurrent
efforts explored curriculum-based approaches [3, 4, 7].
```

| 场景 | 写法 |
|---|---|
| 单篇引用 | `[1]` |
| 多篇引用 | `[2, 5, 7]` |
| 连续范围 | `[1-3]` |
| 作者名 + 引用 | `Smith et al. [2] proposed...` |
| 尚无来源 | 用 scholar_search 搜索，找不到则改写句子去掉引用需求 |

### References 条目格式

每条独立一段。字段顺序：

**会议论文**：
```
[N] 作者, "标题," in Proc. 会议缩写, 年份, pp. 起页–止页.
```
```
[1] A. Vaswani, N. Shazeer, N. Parmar, et al., "Attention is all you need," in Proc. NeurIPS, 2017, pp. 5998–6008.
```

**期刊论文**：
```
[N] 作者, "标题," 期刊名, vol. X, no. Y, pp. 起页–止页, 年份.
```
```
[2] Y. LeCun, Y. Bengio, and G. Hinton, "Deep learning," Nature, vol. 521, no. 7553, pp. 436–444, 2015.
```

**预印本 / arXiv**：
```
[N] 作者, "标题," arXiv:XXXX.XXXXX, 年份.
```

**书籍**：
```
[N] 作者, 书名. 出版地: 出版社, 年份.
```

### 作者著录规则

- 3 人及以内：全部列出，末位前加 "and"
- 4 人及以上：列前 3 人加 "et al."
- 姓在前名缩写在后：`A. B. Smith`

### 缺失字段处理

| 缺失内容 | 处理 |
|---|---|
| 出处（会议/期刊名） | 省略出处字段（预印本引用常规操作），或用 scholar_search 补全 |
| 页码 | 省略 `pp.` 字段（常规操作） |
| 年份 | 用 scholar_search 补全；补不到则省略该条目 |
| 整条来源不确定 | 不生成条目，不写引用该文献的句子 |

---

## 备选格式：用户指定时切换

当用户明确要求以下格式时，按对应规则调整 in-text citation 和 References。未指定时不使用这些格式。

### APA 7th

适用场景：心理学、教育学、社会科学类期刊。

**In-text**：`(Author, Year)` 或 `Author (Year)`。直接引用加页码 `(Author, Year, p. 12)`。

```
Several studies have examined this relationship (Smith & Jones, 2023).
Smith and Jones (2023) found that the effect was moderated by context.
```

- 2 人：`(Smith & Jones, 2023)`
- 3 人及以上：首次及后续均用 `(Smith et al., 2023)`

**References 条目**：
```
Smith, A. B., Jones, C. D., & Lee, E. F. (2023). Title of article. Journal Name, 45(3), 123–145. https://doi.org/10.xxxx/xxxxx
```

- 按作者姓氏字母排序，不编号
- 期刊名斜体，文章标题仅首词大写（sentence case）
- 最多列 20 位作者；21 位及以上列前 19 位 + ... + 末位

### Chicago Author-Date

适用场景：部分社会科学、经济学类期刊。

**In-text**：`(Author Year)` 或 `Author (Year)`。注意与 APA 的区别：无逗号。

```
(Smith 2023)
Smith (2023) argues that...
```

**References 条目**：
```
Smith, Adam B. 2023. "Title of Article." Journal Name 45 (3): 123–145.
```

- 按作者姓氏字母排序
- 文章标题加引号，期刊名斜体

### Chicago Notes-Bibliography

适用场景：人文学科（历史、文学、哲学）。

**In-text**：上标脚注编号。

**脚注**（首引）：
```
1. Adam B. Smith, "Title of Article," Journal Name 45, no. 3 (2023): 125.
```

**脚注**（再引）：
```
2. Smith, "Title of Article," 130.
```

**Bibliography 条目**：
```
Smith, Adam B. "Title of Article." Journal Name 45, no. 3 (2023): 123–145.
```

### Harvard

适用场景：部分英国/澳洲期刊。

**In-text**：`(Author Year)` 或 `Author (Year)`，与 Chicago Author-Date 接近。

**References 条目**：
```
Smith, A.B. (2023) 'Title of article', Journal Name, 45(3), pp. 123–145.
```

### Vancouver

适用场景：医学、生物医学类期刊。

**In-text**：与 numeric citation-sequence 相同，用 `(1)`、`(2)` 或上标。

**References 条目**：
```
1. Smith AB, Jones CD, Lee EF. Title of article. Journal Name. 2023;45(3):123-145.
```

- 作者名不加逗号分隔名与姓：`Smith AB`
- 期刊名用 NLM 标准缩写

---

## 引用纪律（所有格式通用）

无论使用哪种 citation style，以下规则始终适用：

1. **双向一一对应**：正文中每个引用标识必须在 References 中有对应条目；References 中每条必须在正文中被引用
2. **逐条独立成段**：References 列表中每条条目独占一行/段，不将多条挤在同一段内
3. **条目内部语义连续**：单条条目不机械硬换行切断标题、期刊名或页码
4. **综合段保留标注**：将多篇文献压缩为一个综合判断时，必须保留对应引用标识（如 `[1-3]` 或 `(Smith, 2023; Jones, 2024)`），不能因合并观点就抹掉引用
5. **不写引用计数**：正文中不写"被引 N 次""高被引论文"等引用计数声明，除非用户明确要求文献计量分析
6. **来源可追溯**：正文中的每个引用条目要么来自用户输入（L1/L2），要么来自 scholar_search 返回（L3）。不凭模型记忆生成参考文献
