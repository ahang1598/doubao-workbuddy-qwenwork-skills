# 平台映射与排序字段（Step 1/2 必读）

本文件是 SKILL.md Step 1（调 search）和 Step 2（排序）的**字段权威源**。
所有平台 key、中文名、排序字段都从这里查，**禁止编造**。

---

## 1. 平台 key ↔ 中文名映射

`mcp-autocli.search` 的 `platforms` 参数和返回 `items[].platform` 字段都用**英文 key**。
`ask_human` option 给中文 label，存 value 时用英文 key，传给 search 时直接传英文 key。

### 海外 · 公共平台（免登录）

| 英文 key | 中文显示名 | 网络要求 | 登录要求 | 适用话题 |
|---|---|---|---|---|
| `hackernews`    | HackerNews    | 需外网 | 否 | 技术 / 创业 / 工具 |
| `lobsters`      | Lobsters      | 需外网 | 否 | 技术 / 工程深度 |
| `devto`         | Dev.to        | 需外网 | 否 | 编程 / 教程 / Web |
| `stackoverflow` | StackOverflow | 需外网 | 否 | 编程 / 问答 |
| `arxiv`         | Arxiv         | 需外网 | 否 | AI / 论文 / LLM / Agent / RAG |
| `hf`            | HuggingFace   | 需外网 | 否 | AI / 模型 / LLM |
| `wikipedia`     | Wikipedia     | 需外网 | 否 | 通用百科 / 概念解释 |

### 海外 · 需登录平台

| 英文 key | 中文显示名 | 网络要求 | 登录要求 | 适用话题 |
|---|---|---|---|---|
| `twitter`   | Twitter/X  | 需外网 | 是（Edge cookie） | 行业动态 / KOL 观点 |
| `youtube`   | YouTube    | 需外网 | 是（Edge cookie） | 视频教程 / 测评 |
| `instagram` | Instagram  | 需外网 | 是（Edge cookie） | 视觉内容 / 生活方式 / KOL 动态 |

### 国内 · 需登录平台

| 英文 key | 中文显示名 | 网络要求 | 登录要求 | 适用话题 |
|---|---|---|---|---|
| `xiaohongshu` | 小红书     | 国内可达 | 是（Edge cookie） | 生活方式 / 测评 / 攻略 |
| `bilibili`    | B站        | 国内可达 | 是（Edge cookie） | 视频 / 二次元 / 知识区 |
| `douyin`      | 抖音       | 国内可达 | 是（Edge cookie） | 短视频 / 大众内容 |
| `weibo`       | 微博搜索   | 国内可达 | 是（Edge cookie） | 实时热点 / 舆情 |

---

## 2. 网络环境过滤

| `network` | 可展示平台 |
|---|---|
| `overseas_ok`    | 全部 14 个 |
| `domestic_only` | 仅 4 个国内平台（xiaohongshu / bilibili / douyin / weibo），**禁止**展示任何"需外网"的平台 |

---

## 3. search 返回 items[] 关键字段

每条返回项的通用字段：`platform`（英文 key）、`title`、`url`、`author`。
此外按平台各有不同：

| 平台 | 排序字段 | 其他可用字段 | 备注 |
|---|---|---|---|
| `hackernews`    | `score`     | `comments`, `hn_url`     | score = HN points |
| `lobsters`      | `score`     | `comments`, `lobsters_url` | |
| `devto`         | `reactions` | `comments`, `published_at` | |
| `stackoverflow` | `score`     | `answers`, `views`       | score 可为负 |
| `arxiv`         | —           | `abstract`, `date`, `authors` | 按相关性，跳过排序 |
| `hf`            | `upvotes`   | `downloads`, `task`      | task = pipeline_tag；search ✅ |
| `wikipedia`     | —           | `summary`                | 按相关性，跳过排序 |
| `instagram`     | `likes`     | `comments`, `author`, `text` | text 替代 title；需登录 |
| `twitter`       | `likes`     | `views`, `replies`, `retweets`, `text` | text 替代 title |
| `youtube`       | `views`     | `channel`, `age`         | views 是字符串需解析 |
| `xiaohongshu`   | `likes`     | —                        | likes 是字符串（"5.2万"）需解析 |
| `bilibili`      | `plays`     | `author`                 | plays 来自 WBI API（数值） |
| `douyin`        | `likes`     | `author`                 | likes 字符串需解析 |
| `weibo`         | `likes`     | `reposts`, `comments`, `text` | text 替代 title |

> ⚠️ 字段缺失就跳过排序、不参与权重计算；不要假设默认值为 0 进行排序，会扭曲结果。

---

## 4. 数值解析规则（互动量字符串 → number）

部分平台返回的互动量是字符串（"5.2万"、"1.2K"、"3.4M"），排序前必须归一化为数值：

| 后缀 | 倍数 |
|---|---|
| `K` / `千` | × 1,000 |
| `M` / `万` | × 10,000 |
| `B` / `亿` | × 100,000,000 |
| `w` / `W`  | × 10,000（小红书 / 抖音常见）|

解析示例：
- `"5.2万"`  → 52000
- `"1.2K"`   → 1200
- `"3.4M"`   → 34000000（注意 M 在英文场景下是 million = 1e6，但在小红书/抖音的中文场景下应优先解析为 "万"。如果上下文不明，按平台来源决定：国内平台 M 视为"百万"罕见，按 million 处理即可；海外平台同义）

> 字段缺失或无法解析 → 视该条互动量为 0，可参与排序但通常会沉到底部。

---

## 5. 平台权重应用

`my-radar.yaml` 中可以给每个平台配 `weight`（默认 1.0）：

```yaml
platforms:
  - name: "xiaohongshu"
    weight: 1.5
  - name: "bilibili"
    weight: 1.2
```

`最终分数 = 排序字段数值 × 平台权重`

权重不影响平台内部排序，只影响跨平台合并后的总榜次序，及最终选题汇总时的排序基准。

---

## 6. 工具 ↔ 平台覆盖矩阵

下表列出 `mcp-autocli` 暴露的主要工具在各平台上的覆盖情况。「—」表示该平台
autocli 没有对应能力，调用时返回 `metadata.skip_reason = unsupported_platform_for_*`。

### 6.1 内容雷达核心工具（search / hot / user_timeline / following_feed / post_detail）

| 平台 \ 工具 | search | hot | user_timeline | following_feed | post_detail |
|---|:---:|:---:|:---:|:---:|:---:|
| hackernews    | ✅ | —  | — | — | — |
| lobsters      | ✅ | —  | — | — | — |
| devto         | ✅ | —  | — | — | — |
| stackoverflow | ✅ | —  | — | — | — |
| arxiv         | ✅ | —  | — | — | ✅（paper 元数据） |
| hf            | ✅ | —  | — | — | — |
| wikipedia     | ✅ | —  | — | — | — |
| xiaohongshu   | ✅ | —  | ✅ | — | ✅ |
| bilibili      | ✅ | ✅（hot / ranking） | ✅ | ✅ | — |
| douyin        | ✅ | —  | ✅ | — | — |
| weibo         | ✅ | ✅ | — | — | — |
| twitter       | ✅ | ✅（trending） | — | ✅ | ✅ |
| youtube       | ✅ | —  | — | — | ✅ |
| instagram     | ✅ | —  | — | — | — |

> **hot 额外支持的非雷达平台**（不在 Step 0.3 选择列表中，但 autocli 有对应能力）：
> reddit（hot / popular）、tiktok（explore）、google（trends）、steam（top-sellers）、
> bbc（news）、bloomberg（news）、apple-podcasts（top）。
>
> **post_detail 额外支持的平台**：zhihu（question + top answers）、douban（subject + reviews）。
> 这些平台不在 Step 0.3 列表中，但如果有其 URL 可直接调 post_detail 获取详情。

### 6.2 媒体 & 字幕工具（get_subtitle / download_media / transcribe_audio / extract_keyframes）

| 平台 \ 工具 | get_subtitle | download_media | transcribe_audio | extract_keyframes |
|---|:---:|:---:|:---:|:---:|
| xiaohongshu | — | ✅ | — | — |
| bilibili    | ✅ | ✅ | — | — |
| douyin      | ✅ | ✅ | — | — |
| weibo       | — | — | — | — |
| twitter     | — | ✅ | — | — |
| youtube     | ✅ | ✅（yt-dlp） | — | — |
| instagram   | — | ✅（yt-dlp） | — | — |

> `transcribe_audio` 和 `extract_keyframes` 不按平台区分，接受任意本地文件路径。
> 典型用法：`download_media` → `transcribe_audio` → `extract_keyframes`。

### 6.3 账号工具（account_dashboard / account_notifications / publish）

| 平台 \ 工具 | account_dashboard | account_notifications | publish |
|---|:---:|:---:|:---:|
| xiaohongshu | ✅（creator-profile + stats + notes） | ✅（mentions / likes / connections） | ✅（图文 / 视频） |
| bilibili    | ✅（me + favorite + history） | — | — |
| douyin      | — | ✅（all / like / comment / follow / at） | — |
| twitter     | ✅（profile + bookmarks） | ✅（combined inbox） | — |

### 调用示例

```
user_timeline(platform="bilibili", user_id="12345", limit=20)
following_feed(platform="twitter", limit=20)
post_detail(platform="xiaohongshu", url="https://...", comment_limit=30)
post_detail(platform="zhihu", url="https://www.zhihu.com/question/12345", comment_limit=30)
hot(platform="weibo", limit=20, variant="hot")    # bilibili 可传 variant="ranking"
get_subtitle(platform="douyin", post_id="<aweme_id>")
get_subtitle(platform="youtube", post_id="<video_url_or_id>")
account_dashboard(platform="xiaohongshu")
account_notifications(platform="douyin", notification_type="comment", limit=20)
download_media(platform="instagram", post_id="<post_url>", output_dir="/tmp/ig_media")
```

不支持的组合返回空 items + `metadata.skip_reason = unsupported_platform_for_*`，
SKILL 见到这个 reason 直接跳过该条，不要重试。

---

## 7. 跨平台合并去重

合并多平台 Top 10 时按以下规则去重：
- **完全同 URL** → 保留权重 × 互动最高那条
- **同标题 ≥ 80% 相似** → 保留互动最高那条
- **同主题的不同形态**（同一新闻在 HN 和 Twitter 都出现）→ 保留为不同条目，最终选题阶段再合并到同一个"选题"下作为多平台证据
