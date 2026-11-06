---
name: xiaoyi-health-cli-index
description: "查询个人运动健康相关数据，提供分析解读。覆盖领域：心率、静息心率、HRV、心律（房颤/早搏）、血压；睡眠时长/阶段/质量、午睡；步数、活动量、锻炼时长、运动记录（跑步/骑行/健身）、VO2Max、体能趋势、训练负荷、恢复状态；压力、情绪、焦虑、倦怠；血氧（SpO2）；血糖、餐后血糖；体温、发烧；体重、BMI、体脂率；营养摄入、饮食热量；月经周期、经期、基础体温（BBT）、排卵；今日健康概览、每周健康总结；体重管理、减脂、增肌；饮食记录、饮食打卡、记一下吃了什么、吃了XX、早上喝了XX、拍照记录饮食、食物图片识别、照片打卡。读此索引确定应加载的具体 skill，再按需加载，不得一次性加载所有 skill。"
metadata:
  {
    "pha": {
      "emoji": "📋",
      "category": "health-cli-index",
      "tags": ["index", "routing", "cli", "health"]
    }
  }
---

# xiaoyi-health CLI 技能索引

> **桌面接入说明（小艺 Work Desktop）**
> 
> - 本技能的 `bin/pha-claw.js` 已将业务接口（`/celia-claw/v1/rest-api/skill/execute`）迁移为经主进程 skill API 代理（Windows 命名管道 `\\.\pipe\claw-skill`）调用，业务鉴权由主进程自动注入，本 Skill **零业务凭证**，仅需主进程注入的环境变量 `CLAW_SKILL_TOKEN`。
> - 旧云沙箱兼容：`SERVICE_URL` 为空 → 默认 `np://claw-skill`（管道）；`np://` 开头 → 命名管道；`http(s)://` 开头 → 原 HTTP 直连（从 `~/.openclaw/.xiaoyienv` 读 `PERSONAL_API_KEY`/`PERSONAL_UID` 鉴权）。
> - 环境文件路径已改为 portable：默认 `~/.openclaw/.xiaoyienv`，可用 `CLAW_ENV_FILE` 覆盖。
> - 命令调用方式不变：`node ./skills/xiaoyi-health-win/bin/pha-claw.js <command>`。

> **使用原则**：先读此索引，根据用户意图定位具体 skill，再按需加载该 skill 的完整内容。**不要一次性加载所有 skill。**

## 一、CLI 执行方式

所有命令使用相对路径调用：

```bash
node ./skills/xiaoyi-health-win/bin/pha-claw.js <command> [args]
```

---

## 二、技能路由表

| 用户意图                                            | 加载 skill                       |
| ----------------------------------------------- | ------------------------------ |
| 心率、BPM、心跳、静息心率、HRV、心律、房颤、早搏、血压                  | `cardiovascular/SKILL.md`      |
| 睡眠时长、睡眠质量、睡眠阶段、深睡、REM、入睡时间、失眠                   | `sleep-coach/SKILL.md`         |
| 午睡、小睡、白天有没有睡觉                                   | `naps/SKILL.md`                |
| 压力、焦虑、紧张、情绪、心情、倦怠、情绪低落                          | `mental-health/SKILL.md`       |
| 步数、活动量、锻炼时长、卡路里消耗、运动记录、健身、训练负荷、恢复状态、VO2Max、体能趋势 | `fitness/SKILL.md`             |
| 跑步能力、配速、步频、跑步技术、跑力、跑步训练计划、跑步效率                  | `running/SKILL.md`             |
| 血氧、SpO2                                         | `blood-oxygen/SKILL.md`        |
| 血糖、餐后血糖、糖尿病风险、饮食与血糖                             | `blood-sugar-coach/SKILL.md`   |
| 体温、发烧                                           | `body-temperature/SKILL.md`    |
| 体重、BMI、体脂率、体成分、减脂、增肌、体重管理                       | `weight-management/SKILL.md`   |
| 营养摄入、饮食热量、膳食记录                                  | `nutrition/SKILL.md`           |
| 月经周期、经期、基础体温、BBT、排卵、经前症状、女性健康                   | `reproductive-health/SKILL.md` |
| 每周健康总结、周回顾、周报、这周怎么样                             | `weekly-review/SKILL.md`       |
| 今天怎么样、整体健康概览、健康总结                               | `health-overview/SKILL.md`     |
| 吃了XX、记一下、记录饮食、饮食打卡、早上喝了XX、我吃了xxx                | `diet-logging/SKILL.md`        |
| 用户发送食物图片/照片、拍照记录饮食、照片打卡、看图识别食物                  | `photo-diet-logging/SKILL.md`  |

---

## 三、加载策略

```
用户提问
  → 读本索引，定位 skill
  → 加载对应 skill 完整内容（含 healthy-shared）
  → 执行 CLI 命令获取数据
  → 按 skill 分析框架输出结论
```

每个 skill 内部已根据问题复杂度区分取数路径——简单查询只取单个工具，综合分析并行取数。

不确定时：先加载最相关的 skill 获取数据；若问题明确横跨多个不相关领域，分别加载各自 skill 并行取数。
