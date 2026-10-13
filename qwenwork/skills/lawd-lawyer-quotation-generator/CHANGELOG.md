# CHANGELOG

## v1.0.1 - 2026-08-10

- 结构整改：`generate_quotation.py` 由技能根目录移入 `scripts/`，与全库技能统一 `scripts/` 约定保持一致
- 同步更新 SKILL.md 中的脚本链接与调用命令为 `python3 scripts/generate_quotation.py ...`
- 脚本新增基于 `__file__` 的技能根目录解析（`SKILL_ROOT`）：`--json` 传入的文件名在当前工作目录找不到时回退到技能根目录查找，确保从任意目录调用均可读到 `quotation_data.json`
- `quotation_data.json` 仍保留在技能根目录（属数据/配置，非脚本），内容未改动；报价计算规则与输出格式未改动

## v1.0.0 - 2026-08-03

- 合规整改：纳入 QwenWork-Legal-Skill 统一治理，补建 CHANGELOG 版本记录
- 此前历史变更详见 git 提交记录
