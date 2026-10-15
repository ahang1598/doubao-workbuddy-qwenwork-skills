# 路书章节结构——HTML 模板参考

> 本文件是 Stage 4 的参照资源。写作路书时，按照以下五部分结构和 HTML 模板生成内容。
> 所有 SVG 装饰元素均内联在 HTML 中，不使用任何外部图片。

## 目录

- [第一部分：出发前（Before You Go）](#第一部分出发前before-you-go)
  - [1.1 封面](#11-封面)
  - [1.2 旅程概览](#12-旅程概览journey-overview)
  - [1.3 行前准备](#13-行前准备before-you-go)
- [第二部分：每日行程（Day by Day）](#第二部分每日行程day-by-day核心主体)
- [第三部分：目的地深度（Deep Dives）](#第三部分目的地深度deep-dives)
- [第四部分：实用附录（Appendix）](#第四部分实用附录appendix)
- [第五部分：封底（Back Cover）](#第五部分封底back-cover)
- [内容写作规范](#内容写作规范)

---

## 第一部分：出发前（Before You Go）

### 1.1 封面

```html
<div class="cover"><!-- 双线边框装饰（纯 CSS） -->
  
  <!-- 指南针装饰 --><div class="compass-rose" aria-hidden="true">
    <svg width="80" height="80" viewBox="0 0 80 80" fill="none" xmlns="http://www.w3.org/2000/svg">
      <circle cx="40" cy="40" r="38" stroke="currentColor" stroke-width="0.75"></circle>
      <circle cx="40" cy="40" r="32" stroke="currentColor" stroke-width="0.5" stroke-dasharray="2 4"></circle>
      <polygon points="40,8 43,36 40,32 37,36" fill="var(--terracotta)"></polygon>
      <polygon points="40,72 37,44 40,48 43,44" fill="currentColor" opacity="0.3"></polygon>
      <polygon points="8,40 36,37 32,40 36,43" fill="currentColor" opacity="0.3"></polygon>
      <polygon points="72,40 44,43 48,40 44,37" fill="currentColor" opacity="0.3"></polygon>
      <text x="40" y="7" text-anchor="middle" font-size="6" font-family="'Noto Serif SC', serif" font-weight="700" fill="var(--terracotta)">N</text>
      <text x="40" y="79" text-anchor="middle" font-size="6" font-family="'Noto Serif SC', serif" fill="currentColor" opacity="0.5">S</text>
      <text x="3" y="42" text-anchor="middle" font-size="6" font-family="'Noto Serif SC', serif" fill="currentColor" opacity="0.5">W</text>
      <text x="77" y="42" text-anchor="middle" font-size="6" font-family="'Noto Serif SC', serif" fill="currentColor" opacity="0.5">E</text>
      <circle cx="40" cy="40" r="2.5" fill="var(--terracotta)"></circle>
    </svg></div>
  
  <h1 class="cover-title">{路线名称}</h1><div class="cover-subtitle">{天数}天 · {主题标签} · {季节}</div><div class="cover-tagline">一句话概括这条路线的精髓</div></div>
```

### 1.2 旅程概览（Journey Overview）

```html
<div class="overview"><h2>旅程概览</h2>
  
  <div class="overview-grid">
    <div class="overview-item">
      <i class="ti ti-calendar"></i>
      <span class="overview-label">总天数</span>
      <span class="overview-value">X 天</span>
    </div>
    <div class="overview-item">
      <i class="ti ti-route"></i>
      <span class="overview-label">总里程</span>
      <span class="overview-value">XXX km</span>
    </div>
    <div class="overview-item">
      <i class="ti ti-sun"></i>
      <span class="overview-label">最佳季节</span>
      <span class="overview-value">X-X 月</span>
    </div>
    <div class="overview-item">
      <i class="ti ti-coin"></i>
      <span class="overview-label">预算范围</span>
      <span class="overview-value">¥XXX-XXX/人</span>
    </div></div>
  
  <div class="overview-highlights">
    <h3>核心亮点</h3>
    <ul>
      <li><i class="ti ti-star"></i> 亮点 1</li>
      <li><i class="ti ti-star"></i> 亮点 2</li>
      <li><i class="ti ti-star"></i> 亮点 3</li>
    </ul></div>
  
  <!-- Flourish 分隔线 --><div class="divider divider-flourish" aria-hidden="true">
    <svg width="240" height="20" viewBox="0 0 240 20" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M120 10 C100 10, 90 2, 60 2 S20 10, 0 10" stroke="currentColor" stroke-width="1" fill="none"></path>
      <path d="M120 10 C140 10, 150 2, 180 2 S220 10, 240 10" stroke="currentColor" stroke-width="1" fill="none"></path>
      <circle cx="120" cy="10" r="3" fill="currentColor"></circle>
    </svg></div></div>
```

### 1.3 行前准备（Before You Go）

```html
<div class="preparation"><h2>行前准备</h2>
  
  <div class="prep-section">
    <h3><i class="ti ti-id"></i> 证件与文件</h3>
    <ul>
      <li>身份证 / 护照</li>
      <li>驾驶证（自驾必备）</li>
      <li>...</li>
    </ul></div>
  
  <div class="prep-section">
    <h3><i class="ti ti-backpack"></i> 装备清单</h3>
    <ul>
      <li>根据季节和路线定制</li>
    </ul></div>
  
  <div class="prep-section">
    <h3><i class="ti ti-coin"></i> 预算参考</h3>
    <table>
      <tbody><tr><td>交通</td><td>¥XXX</td></tr>
      <tr><td>住宿</td><td>¥XXX</td></tr>
      <tr><td>餐饮</td><td>¥XXX</td></tr>
      <tr><td>门票</td><td>¥XXX</td></tr>
      <tr><td>其他</td><td>¥XXX</td></tr>
    </tbody></table></div></div>
```

---

## 第二部分：每日行程（Day by Day）——核心主体

每天一个独立章节，结构统一：

```html
<div class="day-chapter"><!-- DAY 编号装饰框 --><div class="day-badge" aria-hidden="true">
    <svg width="72" height="72" viewBox="0 0 72 72" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect x="2" y="2" width="68" height="68" rx="12" stroke="var(--terracotta)" stroke-width="1.5" fill="var(--ivory)"></rect>
      <rect x="6" y="6" width="60" height="60" rx="9" stroke="var(--terracotta)" stroke-width="0.5" stroke-dasharray="3 3" fill="none"></rect>
      <text x="36" y="30" text-anchor="middle" font-size="10" font-family="'JetBrains Mono', monospace" font-weight="500" letter-spacing="3" fill="var(--text-tertiary)">DAY</text>
      <text x="36" y="54" text-anchor="middle" font-size="26" font-family="'Noto Serif SC', serif" font-weight="900" fill="var(--terracotta)">01</text>
    </svg></div>
  
  <!-- 日程卡片 --><div class="day-card">
    <h2 class="day-title">{起点} → {终点}</h2>
    
    <div class="day-meta">
      <span class="meta-item"><i class="ti ti-car"></i> {里程}km</span>
      <span class="meta-item"><i class="ti ti-clock"></i> {用时}h</span>
      <span class="meta-item"><i class="ti ti-mountain"></i> 海拔 {海拔}m</span>
      <span class="meta-item"><i class="ti ti-sun"></i> {天气}</span>
      <span class="meta-item"><i class="ti ti-temperature"></i> {温度}°C</span>
    </div>
    
    <div class="day-highlight">
      <i class="ti ti-star-filled"></i> 今日亮点：{一句话概括}
    </div></div>
  
  <!-- 路线描述（带首字下沉） --><div class="route-description">
    <h3>路线描述</h3>
    <p>
      文学化的路线描写，不只是"从 A 到 B"，而是沿途风景的感性描述。
      例如："离开大理古城后，公路沿洱海西岸蜿蜒，左手边是苍山的十九峰，
      右手边是湖水从碧蓝渐变为翡翠绿..."
    </p></div>
  
  <!-- 菱形分隔线 --><div class="divider divider-diamond" aria-hidden="true">
    <svg width="200" height="12" viewBox="0 0 200 12" fill="none" xmlns="http://www.w3.org/2000/svg">
      <line x1="0" y1="6" x2="88" y2="6" stroke="currentColor" stroke-width="0.5"></line>
      <rect x="94" y="0" width="12" height="12" rx="1" transform="rotate(45 100 6)" fill="currentColor"></rect>
      <line x1="112" y1="6" x2="200" y2="6" stroke="currentColor" stroke-width="0.5"></line>
    </svg></div>
  
  <!-- 必停点 --><div class="must-stops">
    <h3>必停点</h3>
    
    <div class="stop-card">
      <span class="stop-badge"><i class="ti ti-star-filled"></i> 必停</span>
      <h4 class="stop-name">{地点名称}</h4>
      <div class="stop-name-en">{English Name}</div>
      
      <p class="stop-description">
        通俗易懂的介绍，融合历史文化和实用信息。
      </p>
      
      <div class="stop-info">
        <span><i class="ti ti-map-pin"></i> {地址}</span>
        <span><i class="ti ti-clock"></i> 建议 {时长}</span>
        <span><i class="ti ti-coin"></i> {价格}</span>
        <span><i class="ti ti-parking"></i> {停车信息}</span>
      </div>
    </div>
    
    <!-- 重复 2-3 个必停点 --></div>
  
  <!-- 三点分隔 --><div class="divider divider-dots" aria-hidden="true">
    <svg width="60" height="8" viewBox="0 0 60 8" fill="none" xmlns="http://www.w3.org/2000/svg">
      <circle cx="10" cy="4" r="2" fill="currentColor"></circle>
      <circle cx="30" cy="4" r="2.5" fill="currentColor"></circle>
      <circle cx="50" cy="4" r="2" fill="currentColor"></circle>
    </svg></div>
  
  <!-- 美食推荐 --><div class="food-recommendations">
    <h3><i class="ti ti-tools-kitchen-2"></i> 美食推荐</h3>
    
    <div class="food-card">
      <h4 class="food-name">{餐厅名称}</h4>
      <p class="food-description">
        推荐理由和招牌菜介绍
      </p>
      <div class="food-info">
        <span><i class="ti ti-map-pin"></i> {地址}</span>
        <span><i class="ti ti-coin"></i> 人均 ¥{价格}</span>
        <span><i class="ti ti-clock-hour-4"></i> {营业时间}</span>
        <span><i class="ti ti-phone"></i> {电话}</span>
      </div>
    </div>
    
    <!-- 1-2 个美食推荐 --></div>
  
  <!-- 住宿推荐 --><div class="stay-recommendations">
    <h3><i class="ti ti-bed"></i> 住宿推荐</h3>
    
    <div class="stay-card">
      <h4 class="stay-name">{酒店/客栈名称}</h4>
      <p class="stay-description">
        一句话点评：位置、特色、性价比
      </p>
      <div class="stay-info">
        <span><i class="ti ti-map-pin"></i> {地址}</span>
        <span><i class="ti ti-coin"></i> ¥{价格区间}</span>
        <span><i class="ti ti-phone"></i> {预订方式}</span>
      </div>
    </div>
    
    <!-- 1-2 个住宿推荐 --></div>
  
  <!-- 贴士栏 --><div class="tips-box">
    <h3><i class="ti ti-bulb"></i> 今日贴士</h3>
    <ul>
      <li><i class="ti ti-alert-triangle"></i> 路况提醒</li>
      <li><i class="ti ti-shield-check"></i> 安全注意</li>
      <li><i class="ti ti-coin"></i> 省钱技巧</li>
      <li><i class="ti ti-info-circle"></i> 文化禁忌</li>
    </ul></div>
  
  <!-- 空白笔记区 --><div class="journal-space">
    <h3><i class="ti ti-pencil"></i> 今日手记</h3>
    <p class="journal-prompt">今天最打动你的瞬间是什么？</p>
    <div class="journal-lines">
      <div class="journal-line"></div>
      <div class="journal-line"></div>
      <div class="journal-line"></div>
      <div class="journal-line"></div>
    </div>
    <p class="journal-prompt"><i class="ti ti-paperclip"></i> 贴上今天的票根、明信片或树叶</p></div></div>
```

---

## 第三部分：目的地深度（Deep Dives）

对线路中最重要的 2-3 个目的地做深度介绍：

```html
<div class="deep-dive"><h2>{目的地名称} 深度游</h2>
  
  <div class="deep-dive-intro">
    <p>引言：用文学化的语言介绍这个地方的气质</p></div>
  
  <div class="deep-dive-history">
    <h3>历史脉络</h3>
    <p>简明的历史梳理，不超过 500 字</p></div>
  
  <div class="deep-dive-culture">
    <h3>文化特色</h3>
    <p>民俗、建筑、艺术、生活方式</p></div>
  
  <div class="deep-dive-local">
    <h3>当地人的一天</h3>
    <p>通过一个虚构或真实的当地人视角，展现日常生活</p></div>
  
  <div class="deep-dive-tips">
    <h3>深度游建议</h3>
    <ul>
      <li><i class="ti ti-camera"></i> 最佳拍摄点</li>
      <li><i class="ti ti-compass"></i> 小众体验</li>
      <li><i class="ti ti-alert-circle"></i> 避坑指南</li>
    </ul></div></div>
```

---

## 第四部分：实用附录（Appendix）

```html
<div class="appendix"><h2>实用附录</h2>
  
  <div class="appendix-section">
    <h3><i class="ti ti-phone-call"></i> 紧急联系</h3>
    <ul>
      <li>报警：110</li>
      <li>急救：120</li>
      <li>路况查询：XXX</li>
      <li>沿途医院列表</li>
    </ul></div>
  
  <div class="appendix-section">
    <h3><i class="ti ti-language"></i> 常用语言</h3>
    <p>当地方言/少数民族语言常用词汇对照</p></div>
  
  <div class="appendix-section">
    <h3><i class="ti ti-coin"></i> 费用明细参考</h3>
    <table>
      <tbody><tr><th>项目</th><th>预算</th><th>实际</th></tr>
      <tr><td>Day 1</td><td>¥XXX</td><td>_____</td></tr>
      <!-- ... -->
    </tbody></table></div>
  
  <div class="appendix-section">
    <h3><i class="ti ti-music"></i> 推荐歌单</h3>
    <p>适合这条路线的音乐/播客推荐</p></div></div>
```

---

## 第五部分：封底（Back Cover）

```html
<div class="back-cover"><div class="back-quote">
    "旅行不是为了到达，而是为了在路上。"
  </div>
  
  <div class="back-info">
    {个性化信息：制作者、团队、公众号等}
  </div>
  
  <div class="back-space">
    <i class="ti ti-pencil"></i> 旅行感言
    <div class="journal-line"></div>
    <div class="journal-line"></div></div></div>
```

---

## 内容写作规范

### 写作风格规则

**定向需求（Where）——精准清晰**

- 地名、方向、里程、用时必须准确无误
- 使用"左手边"、"右手边"、"前方 200 米"等具身化描述
- 路况描述要具体："连续 15km 的盘山路，弯道多，限速 40km/h"

**决策需求（What）——替用户筛选**

- 每个目的地只推荐 2-3 个必停点，不堆砌
- 美食推荐不超过 2 个，附推荐理由
- 住宿推荐 1-2 个，覆盖不同预算
- 用"必停"、"可选"、"时间充裕可去"明确优先级

**情感需求（Why）——赋予意义**

- 每个地点都要讲"为什么值得来"
- 融入历史故事、文化背景、当地人视角
- 用文学化语言描述风景，而非枯燥罗列
- 例如："喜洲的清晨，白族阿妈在四方街摆出刚出炉的喜洲粑粑，麦香混着玫瑰花瓣的甜，这是大理最地道的味道。"

### 贴士栏写作原则

贴士栏是路书的"安全网"，必须包含：

- **路况提醒**：山路、土路、限行、施工、季节性封路
- **安全注意**：高海拔反应、野生动物、天气突变、通讯盲区
- **省钱技巧**：避开旺季、团购、当地人推荐
- **文化禁忌**：少数民族禁忌、宗教场所注意事项

### 空白笔记区设计

每天行程末尾留出空白区域——这让路书从"工具"变成"纪念品"，旅行结束后就是一本独一无二的旅行日记。

```html
<div class="journal-space"><h3><i class="ti ti-pencil"></i> 今日手记</h3><p class="journal-prompt">今天最打动你的瞬间是什么？</p><div class="journal-lines">
    <div class="journal-line"></div>
    <div class="journal-line"></div>
    <div class="journal-line"></div>
    <div class="journal-line"></div>
    <div class="journal-line"></div></div><p class="journal-prompt"><i class="ti ti-paperclip"></i> 贴上今天的票根、明信片或树叶</p></div>
```
