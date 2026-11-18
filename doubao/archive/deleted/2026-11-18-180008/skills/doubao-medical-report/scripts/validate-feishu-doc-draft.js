#!/usr/bin/env node
/*
飞书个人健康管理报告草稿校验脚本。
用法：node scripts/validate-feishu-doc-draft.js path/to/draft.xml
*/

const fs = require('fs');
const file = process.argv[2];

if (!file) {
  console.error('用法：node validate-feishu-doc-draft.js <draft.xml>');
  process.exit(2);
}

const text = fs.readFileSync(file, 'utf8');
const failures = [];

function must(condition, message) {
  if (!condition) failures.push(message);
}

must(/<title>[\s\S]*个人健康管理报告[\s\S]*<\/title>/.test(text), '缺少文档标题');
must(/报告总览/.test(text), '缺少报告总览');
must(!/[（(]\s*普通用户版\s*[）)]/.test(text), '报告正文不得出现“（普通用户版）”这类内部写作标签');
must(!/危急值|critical value|panic value/i.test(text), '报告正文不得出现内部紧急风险术语');
must(!/未识别到.{0,20}(紧急|高风险)|未发现.{0,20}(紧急|高风险)|不判定为.{0,20}(紧急|高风险)/.test(text), '未触发紧急风险时不要输出“未识别到/未发现”等默认说明');
must(/健康问题分类|主要问题（一句话）|主要问题\(一句话\)/.test(text), '缺少健康问题分类');
must(/这意味着什么/.test(text), '健康问题分类缺少“这意味着什么”通俗解释列');
must(/对应指标\/证据|对应指标|证据/.test(text), '健康问题分类缺少对应指标/证据列');
must(/一句话|普通用户|看懂|意味着/.test(text), '健康问题分类缺少面向普通用户的表达');
must(/异常指标详细解读|异常指标解读|主要异常解读/.test(text), '缺少异常指标详细解读');
must(/异常项目[\s\S]*本次结果[\s\S]*参考范围|本次结果[\s\S]*参考范围[\s\S]*异常程度/.test(text), '缺少异常指标摘要表字段');
must(/按系统\/类别分组|按系统分组|按类别分组|白细胞系|红细胞系|肝胆|肾功能|代谢/.test(text), '单张检查单缺少按系统/类别分组解读');
must(/评估指标/.test(text), '异常模块缺少评估指标');
must(/当前结果/.test(text), '异常模块缺少当前结果');
must(/异常解读/.test(text), '异常模块缺少异常解读');
must(/预警信号|预警|提醒|需医生确认/.test(text), '异常模块缺少预警信号、提醒或需医生确认内容');
must(/相关风险|风险因素|管理含义/.test(text), '异常模块缺少相关风险或管理含义');
must(/建议动作|建议限期就医|建议复查随访|建议长期管理/.test(text), '异常模块缺少建议动作');
must(/立即|现在|24\s*[-到至]\s*72\s*小时|24小时|72小时|1周内|一周内|1-4周|1\s*[-到至]\s*3个月|3\s*[-到至]\s*6个月/.test(text), '就医/复查/管理建议缺少明确时间窗口');
must(/重点指标趋势|趋势状态|单次指标可视化|单次异常指标可视化|异常分类分布|偏离程度/.test(text), '缺少趋势或单次指标可视化');
must(/图表|趋势图|分布图|图表助手|Chart Assistant|可视化/.test(text), '缺少图表或可视化说明');
must(/图表解读|解读要点|管理含义/.test(text), '缺少图表解读或管理含义');
must(/"block_type"\s*:\s*40|block_type\s*40|add_ons|图表助手卡片未能插入/.test(text), '趋势图必须包含飞书图表助手卡片 block JSON，或明确说明图表助手卡片未能插入');
must(!/OCR|文字识别|识别置信度|OCR置信度|识别文本/.test(text), '报告不应输出 OCR/文字识别过程');
must(!/(低置信度|资料不清|无法复核|数值不确定)[\s\S]{0,40}(用于|支撑|生成|判定|判断|确认)[\s\S]{0,40}(紧急|确诊|治疗方案|趋势图|图表助手|风险分层)/.test(text), '低置信度或无法复核的数值不得支撑紧急风险、诊断、治疗方案、趋势图或风险分层');
must(/综合健康分析/.test(text), '缺少综合健康分析');
must(/疾病风险评估|疾病风险|风险因素/.test(text), '缺少疾病风险评估');
must(/历年异常|历年.*对比|历史.*对比/.test(text), '缺少历年异常数据对比');
must(/定制健康方案/.test(text), '缺少定制健康方案');
must(/营养|饮食/.test(text), '缺少营养饮食建议');
must(/运动/.test(text), '缺少运动健身建议');
must(/信息来源|来源/.test(text), '缺少信息来源');
must(/信息来源[\s\S]*<a\s+[^>]*href=["']https?:\/\//.test(text), '信息来源缺少可点击外部参考链接');
must(/国家|卫健委|卫生健康|指南|共识|教材|期刊|文献|医院|学会|官方|MedicalSearch|general_search/.test(text), '信息来源缺少权威来源类型或发布机构说明');
must(/免责声明|不构成疾病诊断|不替代医生|医生判断/.test(text), '缺少医疗免责声明或免责声明过弱');
must(/<table>[\s\S]*<\/table>/.test(text), '至少需要一个表格承载趋势或证据');
must(/<td[^>]+background-color=["'](?:light-green|light-yellow|light-orange|light-red|orange)["']/.test(text), '风险分层表格缺少递进单元格底色');
must(/动作示意图|image_generation|示意图用于|非诊断性示意图/.test(text), '涉及建议动作时应包含动作示意图或生图说明');
must(/[🩺📈⚠️📅🧪❤️🥗🏃🌙]/u.test(text), '缺少严肃 emoji 作为章节或提示锚点');
const abnormalIndex = text.search(/异常指标详细解读|异常指标解读|主要异常解读/);
const trendIndex = text.search(/重点指标趋势|趋势状态/);
must(abnormalIndex === -1 || trendIndex === -1 || abnormalIndex < trendIndex, '异常指标详细解读应位于重点指标趋势之前');
const singleTimepointMode = /只有一?个时间点|单次检查|单张检查单|不能判断趋势|不足以判断趋势/.test(text);
must(!singleTimepointMode || !/重点指标趋势/.test(text), '只有单时间点时不得生成“重点指标趋势”模块');
must(!singleTimepointMode || /单次指标可视化|单次异常指标可视化|异常分类分布|偏离程度/.test(text), '只有单时间点时应生成单次异常指标可视化');
const urgentRiskDetected = /情况紧急|立即联系医生|立即医学评估|立即联系报告出具机构|立即急诊/.test(text);
must(!urgentRiskDetected || /background-color=["']light-red["']|border-color=["']red["']|text-color=["']red["']/.test(text), '识别到紧急情况时必须使用红色或浅红色警示样式');
must(!urgentRiskDetected || /立即|现在|第一时间/.test(text), '识别到紧急情况时必须写明立即/现在/第一时间处理');
must(!urgentRiskDetected || /主管医师|主管医生|报告出具机构|急诊|120/.test(text), '识别到紧急情况时必须写明联系主管医生/报告机构/急诊/120');
must(!/\{\{[^}]+\}\}/.test(text), '文档草稿中不得残留模板占位符');
must(!/<!DOCTYPE html>|<html\b|<style\b|<\/html>|class=|\.health-report/.test(text), '飞书文档草稿不得包含 HTML 页面结构或 CSS');
must(!/(确诊你|你已确诊|诊断为|确诊为|治疗方案是|具体治疗方案|建议服用.{0,20}(mg|毫克|片|粒|次\/日|每日|疗程)|保证|必然治愈|必须服药|立即停药|自行停药|建议手术|不需要手术|无需就医|排除.{0,10}风险)/.test(text), '发现不安全的诊断或治疗方案表达');

if (failures.length) {
  console.error(`校验失败（${failures.length}项）：`);
  for (const failure of failures) console.error(`- ${failure}`);
  process.exit(1);
}

console.log('校验通过');
