# 输入规格

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| round_agreements | file[] | 是 | 各轮投资协议（A轮/B轮/C轮...的SPA+SHA） |
| round_info | list | 是 | 融资轮次信息（轮次/日期/估值/投资额） |
| focus_dimensions | list | 否 | 聚焦维度（C1-C9子集） |
| exit_scenario | text | 否 | 退出场景假设（如"以2亿估值被收购"） |

## 输入模式

- Mode A：全轮比对（所有轮次协议一次性比对）
- Mode B：新轮预检（新轮协议vs已有各轮协议）
- Mode C：专项叠加（聚焦某维度的叠加效应分析）
