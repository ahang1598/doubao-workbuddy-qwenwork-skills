---
name: doubao-record
description: 启动当前飞书会话的录音。当用户需要发起录音，或对录音进行中的内容询问的时候，可以使用此技能。



---
## doubao-record（录音转写）
一句话描述：用户是想「发起录音」还是「录音过程中，询问录音相关问题」
- 想要发起录音 → 用 start_recording
- 录音过程中，用户询问与录音内容相关的问题 → 用 get_recording


## 工具是什么
- start_recording：启动当前飞书会话的录音，成功后立即返回 record_id 作为后续查询的唯一句柄。
- get_recording：按 record_id 查询指定录音的聚合信息，返回录音元信息(创建时间、创建地点、录音状态、创建人)、录音内容。录音过程中，当用户问『刚才说了什么』或『这场会的纪要给我』时调用。不要用它启动录音；不要传编造的 record_id。

## 使用场景
- 用户明确有语音记录/开始录音记录 → start_recording
- 用户录音中，要读取、查看、总结录音相关内容时 → get_recording

## 核心流程
- 调用 start_recording 时，成功后立即返回 record_id 作为后续查询的唯一句柄
- 调用 get_recording 时，按 record_id 查询指定录音的聚合信息，返回录音元信息(创建时间、创建地点、录音状态、创建人)、录音内容