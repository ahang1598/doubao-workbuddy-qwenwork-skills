# CLI 帮助兼容入口：lark-base-workflow

此文件保留 CLI 帮助使用的路径。执行前先按对应场景确定任务范围，再读取所需协议；具体规则由以下文档维护。

- [Workflow 场景与目标运行态](../scenes/workflow.md)
- [Workflow JSON 骨架](workflow-schema.md)
- [完整工作流示例与构造说明](workflow-examples.md)
- [值类型与条件](workflow-values.md)
- [输出与引用](workflow-outputs.md)

按场景中的任务类型加载协议：仅列出流程或读取状态时无需加载 JSON 骨架与完整示例；创建或修改步骤结构时，读取骨架及对应的完整示例和结构说明。涉及条件、赋值或引用时，仍须完整读取对应协议。
