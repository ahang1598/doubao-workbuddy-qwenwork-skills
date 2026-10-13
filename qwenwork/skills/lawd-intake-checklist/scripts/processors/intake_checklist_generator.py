"""
咨询信息采集清单生成器 v1.4
============================

来源技能: intake_checklist
用途: 根据法律问题类型生成定制化的信息采集清单
适用范围: 中国大陆法律服务场景（不含港澳台地区）

⚠️ 重要提示:
- 问题类型识别基于关键词匹配
- 清单内容仅供参考，需根据实际情况调整
- 复杂案件建议人工判断

v1.4 变更（0811 真机测试整改 N1/N2/N4）:
- 合同纠纷新增 4 个子类模板（建设工程/买卖/租赁/服务），brief_description 参与子类识别与场景细化
- 置信度校准：精确匹配=high，子类/包含匹配=medium
- 问题模板支持 depends_on 逻辑关系标注，材料模板支持 related_to 关联关系标注
- 输出新增 contract_subtype / upgrade_alert / legal_basis 字段
"""

from typing import Any, Dict, List, Optional, TypedDict
from enum import Enum
from datetime import datetime
import re


# ==================== 数据类型定义 ====================

class ProblemType(str, Enum):
    """问题类型枚举"""
    CIVIL_DISPUTE = "民事纠纷"
    LABOR_DISPUTE = "劳动争议"
    FAMILY_LAW = "婚姻家事"
    CONTRACT_DISPUTE = "合同纠纷"
    TRAFFIC_ACCIDENT = "交通事故"
    REAL_ESTATE = "房产纠纷"
    IP_DISPUTE = "知识产权"
    CORPORATE = "公司股权"
    GENERAL = "通用"


class Importance(str, Enum):
    """重要程度"""
    REQUIRED = "必问"
    IMPORTANT = "重要"
    OPTIONAL = "可问"


class MaterialImportance(str, Enum):
    """材料重要程度"""
    REQUIRED = "必备"
    IMPORTANT = "重要"
    OPTIONAL = "可选"


class ChecklistInput(TypedDict, total=False):
    """清单生成输入"""
    problem_type: str  # 问题类型
    brief_description: str  # 简要案情描述
    detail_level: str  # 详细程度：standard/detailed
    focus_areas: List[str]  # 重点关注领域
    client_type: str  # 当事人类型：individual/enterprise
    urgency: str  # 紧急程度


class QuestionItem(TypedDict):
    """问题项"""
    id: str
    category: str
    question: str
    importance: str
    order: int
    purpose: str
    follow_up: str
    depends_on: List[str]  # 逻辑依赖的前置问题 id（Step 2.4）


class MaterialItem(TypedDict):
    """材料项"""
    id: str
    category: str
    material: str
    importance: str
    order: int
    purpose: str
    source_hint: str
    related_to: List[str]  # 关联材料 id（Step 3.4，证明链关系）


class ChecklistOutput(TypedDict):
    """清单生成输出"""
    checklist_id: str
    problem_type: str
    problem_type_code: str
    contract_subtype: Optional[str]
    confidence: str
    generated_at: str
    jurisdiction: str
    questions: List[QuestionItem]
    materials: List[MaterialItem]
    collection_tips: List[str]
    upgrade_alert: List[str]
    legal_basis: List[str]
    disclaimer: str


# ==================== 问题类型识别 ====================

# 问题类型关键词映射
TYPE_KEYWORDS = {
    ProblemType.LABOR_DISPUTE: [
        "劳动", "工资", "加班", "辞退", "解除", "经济补偿", "赔偿金",
        "社保", "工伤", "劳动合同", "劳动争议", "仲裁"
    ],
    ProblemType.FAMILY_LAW: [
        "离婚", "结婚", "抚养", "抚养权", "抚养费", "继承", "遗产",
        "婚姻", "家暴", "财产分割", "探视", "赡养"
    ],
    ProblemType.CONTRACT_DISPUTE: [
        "合同", "违约", "买卖", "租赁", "服务合同", "定金", "违约金",
        "解除合同", "合同纠纷", "欠款"
    ],
    ProblemType.TRAFFIC_ACCIDENT: [
        "交通事故", "车祸", "撞车", "肇事", "伤残", "人伤",
        "车辆", "保险理赔", "交警", "认定书"
    ],
    ProblemType.REAL_ESTATE: [
        "房产", "房屋", "买卖", "租赁", "物业", "装修", "房东",
        "租客", "住房", "商品房", "二手房"
    ],
    ProblemType.IP_DISPUTE: [
        "商标", "专利", "著作权", "版权", "知识产权", "侵权",
        "盗版", "假冒", "注册"
    ],
    ProblemType.CORPORATE: [
        "股权", "股东", "公司", "转让", "分红", "公司治理",
        "董事会", "增资", "减资"
    ],
    ProblemType.CIVIL_DISPUTE: [
        "侵权", "债务", "借款", "欠款", "损害", "赔偿",
        "物权", "邻里", "噪音", "相邻"
    ],
}


def _keyword_scores(text: str) -> Dict[ProblemType, int]:
    """计算文本对各问题类型的关键词命中得分"""
    scores = {}
    for pt, keywords in TYPE_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text)
        if score > 0:
            scores[pt] = score
    return scores


def identify_problem_type(problem_type: str, description: str = "") -> tuple:
    """
    识别问题类型
    
    Args:
        problem_type: 用户输入的问题类型
        description: 案情描述
        
    Returns:
        (问题类型枚举, 置信度)
        
    置信度校准（N1）:
    - high: 输入与类型名完全相等（精确匹配）
    - medium: 包含/子类匹配（如"建设工程合同纠纷"含"合同纠纷"），清单针对性待验证
    - low: 无法识别，使用通用清单
    """
    # 1. 精确匹配
    for pt in ProblemType:
        if problem_type == pt.value:
            return pt, "high"
    
    # 2. 包含/子类匹配（降为 medium）
    for pt in ProblemType:
        if pt.value in problem_type or problem_type in pt.value:
            return pt, "medium"
    
    # 3. 从描述推断
    if description:
        text = problem_type + description
        match_scores = _keyword_scores(text)
        
        if match_scores:
            best_type = max(match_scores, key=match_scores.get)
            score = match_scores[best_type]
            confidence = "high" if score >= 3 else "medium"
            return best_type, confidence
    
    # 4. 返回通用类型
    return ProblemType.GENERAL, "low"


# ==================== 问题模板库 ====================

QUESTION_TEMPLATES = {
    ProblemType.LABOR_DISPUTE: [
        {
            "category": "劳动关系确认",
            "question": "入职时间和离职时间分别是什么？",
            "importance": Importance.REQUIRED,
            "purpose": "确定劳动关系存续期间，计算工龄",
            "follow_up": "如存在多次入职/离职，需分别说明"
        },
        {
            "category": "劳动关系确认",
            "question": "是否签订劳动合同？签订时间？",
            "importance": Importance.REQUIRED,
            "purpose": "判断是否存在书面劳动合同关系",
            "follow_up": "如未签订，需确认是否有其他劳动关系证明"
        },
        {
            "category": "工资待遇",
            "question": "月工资是多少？工资构成包括哪些？",
            "importance": Importance.REQUIRED,
            "purpose": "计算经济补偿金/赔偿金基数",
            "follow_up": "需确认基本工资、绩效、奖金、补贴等构成"
        },
        {
            "category": "工资待遇",
            "question": "是否有拖欠工资？拖欠多久？",
            "importance": Importance.IMPORTANT,
            "purpose": "判断是否存在拖欠工资情形",
            "follow_up": "需提供工资条、银行流水等证明",
            "depends_on": [3]
        },
        {
            "category": "解除原因",
            "question": "离职原因是什么？谁提出的？",
            "importance": Importance.REQUIRED,
            "purpose": "判断解除性质（协商/辞退/违法解除）",
            "follow_up": "需确认是否有解除通知书"
        },
        {
            "category": "社保公积金",
            "question": "社保和公积金是否足额缴纳？",
            "importance": Importance.IMPORTANT,
            "purpose": "判断社保公积金缴纳情况",
            "follow_up": "需确认是否存在少缴、漏缴"
        },
        {
            "category": "加班情况",
            "question": "是否存在加班？加班费是否支付？",
            "importance": Importance.OPTIONAL,
            "purpose": "判断是否可主张加班费",
            "follow_up": "需提供考勤记录、加班审批等证明"
        },
        {
            "category": "工伤情形",
            "question": "是否发生工伤？伤残等级？",
            "importance": Importance.OPTIONAL,
            "purpose": "判断是否涉及工伤赔偿",
            "follow_up": "需提供工伤认定书、劳动能力鉴定"
        },
    ],
    
    ProblemType.FAMILY_LAW: [
        {
            "category": "婚姻状况",
            "question": "结婚时间？是否为再婚？",
            "importance": Importance.REQUIRED,
            "purpose": "确定婚姻关系存续时间",
            "follow_up": "需提供结婚证"
        },
        {
            "category": "婚姻状况",
            "question": "婚后感情状况？分居时间？",
            "importance": Importance.REQUIRED,
            "purpose": "判断夫妻感情是否确已破裂",
            "follow_up": "分居满2年是法定离婚情形之一"
        },
        {
            "category": "子女抚养",
            "question": "是否有子女？子女年龄？",
            "importance": Importance.REQUIRED,
            "purpose": "确定抚养权和抚养费问题",
            "follow_up": "2岁以下子女一般随母亲生活"
        },
        {
            "category": "子女抚养",
            "question": "子女由谁主要照顾？",
            "importance": Importance.IMPORTANT,
            "purpose": "判断抚养权归属可能性",
            "follow_up": "需考虑子女意愿（8岁以上）"
        },
        {
            "category": "财产分割",
            "question": "婚后有哪些共同财产？",
            "importance": Importance.REQUIRED,
            "purpose": "确定财产分割范围",
            "follow_up": "包括房产、车辆、存款、股票等"
        },
        {
            "category": "财产分割",
            "question": "是否有婚前财产协议？",
            "importance": Importance.IMPORTANT,
            "purpose": "判断财产分割方式",
            "follow_up": "有协议按协议处理"
        },
        {
            "category": "债务承担",
            "question": "婚后是否有共同债务？",
            "importance": Importance.IMPORTANT,
            "purpose": "确定债务承担方式",
            "follow_up": "需区分共同债务和个人债务"
        },
        {
            "category": "继承情形",
            "question": "被继承人何时去世？有无遗嘱？",
            "importance": Importance.REQUIRED,
            "purpose": "判断继承方式和份额",
            "follow_up": "有遗嘱按遗嘱继承，无遗嘱按法定继承"
        },
    ],
    
    ProblemType.CONTRACT_DISPUTE: [
        {
            "category": "合同基本信息",
            "question": "合同类型是什么？签订时间？",
            "importance": Importance.REQUIRED,
            "purpose": "确定合同性质和效力",
            "follow_up": "需提供合同原件"
        },
        {
            "category": "合同基本信息",
            "question": "合同主要条款有哪些？",
            "importance": Importance.REQUIRED,
            "purpose": "分析合同权利义务",
            "follow_up": "重点关注价款、履行期限、违约责任"
        },
        {
            "category": "履行情况",
            "question": "合同履行情况如何？",
            "importance": Importance.REQUIRED,
            "purpose": "判断违约责任",
            "follow_up": "需确认双方履行情况"
        },
        {
            "category": "履行情况",
            "question": "对方违约的具体表现？",
            "importance": Importance.REQUIRED,
            "purpose": "确定违约事实",
            "follow_up": "需收集违约证据",
            "depends_on": [3]
        },
        {
            "category": "损失情况",
            "question": "造成什么损失？损失金额？",
            "importance": Importance.IMPORTANT,
            "purpose": "计算赔偿金额",
            "follow_up": "需提供损失证明材料",
            "depends_on": [4]
        },
        {
            "category": "违约金",
            "question": "合同是否有违约金条款？金额多少？",
            "importance": Importance.IMPORTANT,
            "purpose": "判断违约金主张可行性",
            "follow_up": "违约金过高可能被法院调整"
        },
    ],
    
    ProblemType.TRAFFIC_ACCIDENT: [
        {
            "category": "事故基本情况",
            "question": "事故发生时间、地点？",
            "importance": Importance.REQUIRED,
            "purpose": "确定事故基本信息",
            "follow_up": "需提供事故认定书"
        },
        {
            "category": "事故基本情况",
            "question": "责任认定结果？",
            "importance": Importance.REQUIRED,
            "purpose": "确定赔偿比例",
            "follow_up": "全责/主责/同责/次责/无责"
        },
        {
            "category": "人员伤亡",
            "question": "是否有人员伤亡？伤情如何？",
            "importance": Importance.REQUIRED,
            "purpose": "确定赔偿项目",
            "follow_up": "需提供诊断证明、病历"
        },
        {
            "category": "伤残鉴定",
            "question": "是否进行伤残鉴定？等级？",
            "importance": Importance.IMPORTANT,
            "purpose": "计算残疾赔偿金",
            "follow_up": "伤残等级1-10级",
            "depends_on": [3]
        },
        {
            "category": "保险情况",
            "question": "车辆投保情况？保险公司？",
            "importance": Importance.REQUIRED,
            "purpose": "确定保险理赔范围",
            "follow_up": "交强险+商业三者险"
        },
        {
            "category": "医疗费用",
            "question": "医疗费用多少？后续治疗费？",
            "importance": Importance.IMPORTANT,
            "purpose": "计算医疗费赔偿",
            "follow_up": "需提供医疗费发票"
        },
    ],
    
    ProblemType.CIVIL_DISPUTE: [
        {
            "category": "纠纷类型",
            "question": "具体纠纷类型是什么？",
            "importance": Importance.REQUIRED,
            "purpose": "确定法律关系",
            "follow_up": "如侵权、债务、物权等"
        },
        {
            "category": "纠纷事实",
            "question": "纠纷发生的时间、地点、经过？",
            "importance": Importance.REQUIRED,
            "purpose": "了解案件基本事实",
            "follow_up": "需详细描述"
        },
        {
            "category": "损害结果",
            "question": "造成什么损害或损失？",
            "importance": Importance.REQUIRED,
            "purpose": "确定诉讼请求",
            "follow_up": "人身损害/财产损失"
        },
        {
            "category": "对方信息",
            "question": "对方当事人是谁？联系方式？",
            "importance": Importance.REQUIRED,
            "purpose": "确定被告主体",
            "follow_up": "个人或企业"
        },
        {
            "category": "证据情况",
            "question": "现有哪些证据？",
            "importance": Importance.IMPORTANT,
            "purpose": "评估证据充分性",
            "follow_up": "书面证据/电子证据/证人证言"
        },
    ],
    
    ProblemType.GENERAL: [
        {
            "category": "基本信息",
            "question": "您的法律问题涉及哪个领域？",
            "importance": Importance.REQUIRED,
            "purpose": "确定问题类型",
            "follow_up": "如民事、劳动、婚姻、合同等"
        },
        {
            "category": "基本信息",
            "question": "问题发生的时间？",
            "importance": Importance.REQUIRED,
            "purpose": "判断时效问题",
            "follow_up": "注意诉讼时效"
        },
        {
            "category": "当事人信息",
            "question": "涉及哪些当事人？",
            "importance": Importance.REQUIRED,
            "purpose": "确定主体关系",
            "follow_up": "需确认各方身份"
        },
        {
            "category": "核心诉求",
            "question": "您希望解决什么问题？",
            "importance": Importance.REQUIRED,
            "purpose": "确定法律服务目标",
            "follow_up": "明确期望结果"
        },
        {
            "category": "证据材料",
            "question": "现有哪些证据材料？",
            "importance": Importance.IMPORTANT,
            "purpose": "评估案件可行性",
            "follow_up": "书面材料/电子证据"
        },
    ],
}


# ==================== 材料模板库 ====================

MATERIAL_TEMPLATES = {
    ProblemType.LABOR_DISPUTE: [
        {
            "category": "身份证明",
            "material": "身份证复印件",
            "importance": MaterialImportance.REQUIRED,
            "purpose": "确认当事人身份，立案必需",
            "source_hint": "当事人提供"
        },
        {
            "category": "劳动关系证明",
            "material": "劳动合同",
            "importance": MaterialImportance.REQUIRED,
            "purpose": "证明劳动关系存在",
            "source_hint": "当事人保留或用人单位提供"
        },
        {
            "category": "劳动关系证明",
            "material": "工资条/银行流水",
            "importance": MaterialImportance.REQUIRED,
            "purpose": "证明工资数额",
            "source_hint": "银行打印或用人单位提供"
        },
        {
            "category": "劳动关系证明",
            "material": "社保缴纳记录",
            "importance": MaterialImportance.IMPORTANT,
            "purpose": "证明劳动关系及社保情况",
            "source_hint": "社保局打印或APP查询"
        },
        {
            "category": "解除证明",
            "material": "解除劳动合同通知书",
            "importance": MaterialImportance.IMPORTANT,
            "purpose": "证明解除事实和原因",
            "source_hint": "用人单位出具"
        },
        {
            "category": "考勤记录",
            "material": "考勤记录/打卡记录",
            "importance": MaterialImportance.OPTIONAL,
            "purpose": "证明加班情况",
            "source_hint": "用人单位提供"
        },
    ],
    
    ProblemType.FAMILY_LAW: [
        {
            "category": "身份证明",
            "material": "身份证复印件",
            "importance": MaterialImportance.REQUIRED,
            "purpose": "确认当事人身份",
            "source_hint": "当事人提供"
        },
        {
            "category": "婚姻证明",
            "material": "结婚证",
            "importance": MaterialImportance.REQUIRED,
            "purpose": "证明婚姻关系",
            "source_hint": "当事人提供"
        },
        {
            "category": "子女证明",
            "material": "出生医学证明",
            "importance": MaterialImportance.IMPORTANT,
            "purpose": "证明子女身份",
            "source_hint": "当事人提供"
        },
        {
            "category": "财产证明",
            "material": "房产证",
            "importance": MaterialImportance.IMPORTANT,
            "purpose": "证明房产归属",
            "source_hint": "不动产登记中心查询"
        },
        {
            "category": "财产证明",
            "material": "车辆行驶证",
            "importance": MaterialImportance.OPTIONAL,
            "purpose": "证明车辆归属",
            "source_hint": "当事人提供"
        },
        {
            "category": "财产证明",
            "material": "银行存款证明",
            "importance": MaterialImportance.OPTIONAL,
            "purpose": "证明存款情况",
            "source_hint": "银行打印"
        },
    ],
    
    ProblemType.CONTRACT_DISPUTE: [
        {
            "category": "身份证明",
            "material": "身份证复印件/营业执照",
            "importance": MaterialImportance.REQUIRED,
            "purpose": "确认当事人身份",
            "source_hint": "当事人提供"
        },
        {
            "category": "合同文件",
            "material": "合同原件/复印件",
            "importance": MaterialImportance.REQUIRED,
            "purpose": "证明合同关系和条款",
            "source_hint": "当事人提供"
        },
        {
            "category": "履行证明",
            "material": "付款凭证",
            "importance": MaterialImportance.REQUIRED,
            "purpose": "证明合同履行情况",
            "source_hint": "银行流水、收据等",
            "related_to": [2]
        },
        {
            "category": "履行证明",
            "material": "交付/履行凭证（按合同类型确定：发货单、收货单、成果交付签收单等）",
            "importance": MaterialImportance.IMPORTANT,
            "purpose": "证明交付情况",
            "source_hint": "当事人保留",
            "related_to": [2]
        },
        {
            "category": "违约证明",
            "material": "违约证据",
            "importance": MaterialImportance.IMPORTANT,
            "purpose": "证明违约事实",
            "source_hint": "根据具体情况收集",
            "related_to": [2]
        },
    ],
    
    ProblemType.TRAFFIC_ACCIDENT: [
        {
            "category": "身份证明",
            "material": "身份证复印件",
            "importance": MaterialImportance.REQUIRED,
            "purpose": "确认当事人身份",
            "source_hint": "当事人提供"
        },
        {
            "category": "事故认定",
            "material": "交通事故认定书",
            "importance": MaterialImportance.REQUIRED,
            "purpose": "证明事故责任",
            "source_hint": "交警部门出具"
        },
        {
            "category": "医疗证明",
            "material": "诊断证明/病历",
            "importance": MaterialImportance.REQUIRED,
            "purpose": "证明伤情",
            "source_hint": "医院出具"
        },
        {
            "category": "医疗证明",
            "material": "医疗费发票",
            "importance": MaterialImportance.REQUIRED,
            "purpose": "证明医疗费用",
            "source_hint": "医院出具"
        },
        {
            "category": "伤残鉴定",
            "material": "伤残鉴定报告",
            "importance": MaterialImportance.IMPORTANT,
            "purpose": "证明伤残等级",
            "source_hint": "鉴定机构出具"
        },
        {
            "category": "保险证明",
            "material": "保险单",
            "importance": MaterialImportance.REQUIRED,
            "purpose": "证明保险情况",
            "source_hint": "保险公司或当事人提供"
        },
    ],
    
    ProblemType.GENERAL: [
        {
            "category": "身份证明",
            "material": "身份证复印件",
            "importance": MaterialImportance.REQUIRED,
            "purpose": "确认当事人身份",
            "source_hint": "当事人提供"
        },
        {
            "category": "证据材料",
            "material": "相关证据材料",
            "importance": MaterialImportance.REQUIRED,
            "purpose": "证明案件事实",
            "source_hint": "根据具体案件收集"
        },
        {
            "category": "联系方式",
            "material": "对方当事人联系方式",
            "importance": MaterialImportance.IMPORTANT,
            "purpose": "便于联系和送达",
            "source_hint": "当事人提供"
        },
    ],
}


# ==================== 合同子类模板库（N1：子类细化） ====================
# 子类模板追加在通用合同模板之后：问题索引自 7 起（通用合同 6 问），材料索引自 6 起（通用合同 5 项）

CONTRACT_SUBTYPES = {
    "construction_engineering": {
        "name": "建设工程合同（设计/施工/监理）",
        "keywords": ["建设工程", "设计合同", "设计费", "施工", "监理", "施工图",
                     "勘察设计", "工程款", "竣工", "质保金", "造价"],
        "legal_basis": [
            "《民法典》合同编第十八章 建设工程合同",
            "《民法典》第788条（建设工程合同定义）",
            "《建筑法》《建设工程质量管理条例》",
        ],
        "collection_tips": [
            "按「合同签订→设计/施工成果交付→对方确认→付款条件成就→催告→未付」证据链固定证据",
            "对方以质量问题拒付的，先固定书面异议内容，核对合同异议期与验收条款",
            "涉及设计变更/增减项的，单独整理签证单或书面确认文件",
        ],
        "questions": [
            {
                "category": "合同主体与资质",
                "question": "合同双方主体是谁？承包方是否具备相应资质（如工程设计资质等级）？",
                "importance": Importance.REQUIRED,
                "purpose": "建设工程合同对承包方资质有要求，影响合同效力认定",
                "follow_up": "需调取营业执照与资质证书"
            },
            {
                "category": "合同主体与资质",
                "question": "项目是否已办理立项、规划许可等审批手续？",
                "importance": Importance.IMPORTANT,
                "purpose": "项目合法性影响合同履行与付款条件认定",
                "follow_up": "未取得规划许可可能影响合同效力"
            },
            {
                "category": "价款约定",
                "question": "价款（如设计费/工程款）总额、计价方式和付款节点如何约定？",
                "importance": Importance.REQUIRED,
                "purpose": "确定给付金额与付款条件是否成就",
                "follow_up": "需区分固定总价、按面积单价或按阶段比例付款"
            },
            {
                "category": "价款约定",
                "question": "合同约定的工作范围、阶段（如方案/初设/施工图）和成果深度要求是什么？",
                "importance": Importance.REQUIRED,
                "purpose": "界定履约完成度的判断标准",
                "follow_up": "对照合同附件中的任务书或技术要求"
            },
            {
                "category": "履行与交付",
                "question": "已完成哪些工作阶段？成果文件是否有交付记录（签收单、邮件发送记录）？",
                "importance": Importance.REQUIRED,
                "purpose": "证明己方已按约履行",
                "follow_up": "无签收记录的，整理邮件/即时通讯交付痕迹",
                "depends_on": [10]
            },
            {
                "category": "履行与交付",
                "question": "成果文件是否通过审查（如施工图审查合格）或经对方确认？",
                "importance": Importance.IMPORTANT,
                "purpose": "判断付款节点是否成就、质量异议是否成立",
                "follow_up": "需调取审查合格书或对方书面确认",
                "depends_on": [11]
            },
            {
                "category": "付款与违约",
                "question": "对方已支付多少款项？尚欠哪一期/多少金额未付？",
                "importance": Importance.REQUIRED,
                "purpose": "确定诉讼请求金额",
                "follow_up": "与合同付款节点逐一对账",
                "depends_on": [9]
            },
            {
                "category": "付款与违约",
                "question": "对方主张拒付/拖延付款的理由是什么（质量异议、未验收、资金困难等）？",
                "importance": Importance.REQUIRED,
                "purpose": "不同拒付理由对应不同证据与应对策略",
                "follow_up": "需收集对方书面或口头拒付理由的证据",
                "depends_on": [13]
            },
            {
                "category": "催告与时效",
                "question": "是否书面催告过付款（催款函、律师函、邮件/微信）？最近一次催告时间？",
                "importance": Importance.IMPORTANT,
                "purpose": "诉讼时效中断与违约起算认定",
                "follow_up": "保留催告送达凭证"
            },
            {
                "category": "特殊情形",
                "question": "是否存在合同解除、停工窝工、设计变更或增减项情形？",
                "importance": Importance.OPTIONAL,
                "purpose": "识别额外索赔或反诉风险",
                "follow_up": "变更项需有签证或书面确认"
            },
        ],
        "materials": [
            {
                "category": "主体与资质",
                "material": "营业执照与资质证书（如工程设计资质证书）",
                "importance": MaterialImportance.REQUIRED,
                "purpose": "证明主体资格与资质等级",
                "source_hint": "当事人提供"
            },
            {
                "category": "合同文件",
                "material": "建设工程合同及附件（补充协议、设计任务书、技术要求）",
                "importance": MaterialImportance.REQUIRED,
                "purpose": "确定工作范围、价款与付款节点约定",
                "source_hint": "当事人提供"
            },
            {
                "category": "成果与交付",
                "material": "各阶段成果文件及交付签收凭证（签收单、邮件记录、对方确认函）",
                "importance": MaterialImportance.REQUIRED,
                "purpose": "证明已按约交付成果",
                "source_hint": "当事人整理，含电子交付痕迹",
                "related_to": [7]
            },
            {
                "category": "成果与交付",
                "material": "审查批准文件（如施工图设计文件审查合格书）",
                "importance": MaterialImportance.IMPORTANT,
                "purpose": "证明成果符合法定与约定标准",
                "source_hint": "审查机构出具或当事人留存",
                "related_to": [8]
            },
            {
                "category": "付款凭证",
                "material": "已付款项的银行流水、收据、发票",
                "importance": MaterialImportance.REQUIRED,
                "purpose": "与合同付款节点对账，确定欠付金额",
                "source_hint": "银行打印或财务凭证",
                "related_to": [7]
            },
            {
                "category": "催告与沟通",
                "material": "催款函、律师函及付款协商往来记录",
                "importance": MaterialImportance.IMPORTANT,
                "purpose": "证明欠付事实、催告事实与时效中断",
                "source_hint": "当事人提供，保留送达凭证",
                "related_to": [10]
            },
            {
                "category": "结算确认",
                "material": "结算书、对账单或付款确认函（如有）",
                "importance": MaterialImportance.IMPORTANT,
                "purpose": "直接证明欠款金额",
                "source_hint": "双方往来文件",
                "related_to": [10]
            },
            {
                "category": "项目文件",
                "material": "项目立项、规划许可等审批文件（如有）",
                "importance": MaterialImportance.OPTIONAL,
                "purpose": "证明项目合法性",
                "source_hint": "发包方或主管部门"
            },
        ],
    },
    "sales": {
        "name": "买卖合同",
        "keywords": ["买卖", "货物", "采购", "供货", "货款", "标的物"],
        "legal_basis": ["《民法典》合同编第九章 买卖合同"],
        "collection_tips": [
            "重点核对交付凭证与验收记录，确认标的物风险转移节点",
            "质量异议需在约定异议期内提出，注意固定异议时间与内容",
        ],
        "questions": [
            {
                "category": "标的与质量",
                "question": "标的物的名称、规格、数量和质量标准如何约定？",
                "importance": Importance.REQUIRED,
                "purpose": "确定履约标准与质量争议基准",
                "follow_up": "有封样或技术协议的需一并提供"
            },
            {
                "category": "交付与验收",
                "question": "货物是否已交付？是否有送货单、验收记录？",
                "importance": Importance.REQUIRED,
                "purpose": "证明交付义务履行情况",
                "follow_up": "分批交付的需逐批核对"
            },
            {
                "category": "付款情况",
                "question": "货款支付情况如何？尚欠多少？",
                "importance": Importance.REQUIRED,
                "purpose": "确定欠款金额",
                "follow_up": "与对账单核对",
                "depends_on": [8]
            },
            {
                "category": "质量异议",
                "question": "对方是否提出质量异议？何时提出？",
                "importance": Importance.IMPORTANT,
                "purpose": "判断异议是否在约定期限内、是否成立",
                "follow_up": "需固定异议书面内容",
                "depends_on": [8]
            },
            {
                "category": "催告与时效",
                "question": "是否催告过付款或交货？",
                "importance": Importance.IMPORTANT,
                "purpose": "违约认定与时效中断",
                "follow_up": "保留催告凭证"
            },
        ],
        "materials": [
            {
                "category": "合同文件",
                "material": "买卖合同、订单、技术协议或封样",
                "importance": MaterialImportance.REQUIRED,
                "purpose": "确定标的与质量标准",
                "source_hint": "当事人提供"
            },
            {
                "category": "交付验收",
                "material": "送货单、签收单、验收记录",
                "importance": MaterialImportance.REQUIRED,
                "purpose": "证明交付事实",
                "source_hint": "当事人保留",
                "related_to": [6]
            },
            {
                "category": "质量证明",
                "material": "质检报告、合格证或质量异议函",
                "importance": MaterialImportance.IMPORTANT,
                "purpose": "应对或主张质量争议",
                "source_hint": "检测机构或双方往来",
                "related_to": [7]
            },
        ],
    },
    "lease": {
        "name": "租赁合同",
        "keywords": ["租赁", "租金", "押金", "承租", "出租", "租期"],
        "legal_basis": ["《民法典》合同编第十四章 租赁合同"],
        "collection_tips": [
            "核对押金退还条件与房屋交接单，区分正常损耗与损坏",
            "转租、装修添附需单独收集书面同意文件",
        ],
        "questions": [
            {
                "category": "租赁标的",
                "question": "租赁物的位置、面积/状况和租期如何约定？",
                "importance": Importance.REQUIRED,
                "purpose": "确定租赁关系基本内容",
                "follow_up": "需提供租赁合同"
            },
            {
                "category": "租金押金",
                "question": "租金、押金金额和支付方式如何约定？",
                "importance": Importance.REQUIRED,
                "purpose": "确定给付义务与押金退还基准",
                "follow_up": "核对支付记录"
            },
            {
                "category": "履行情况",
                "question": "租赁物是否已交付/腾退？有无交接单？",
                "importance": Importance.REQUIRED,
                "purpose": "确定占用费与押金退还节点",
                "follow_up": "交接时的状况需有记录",
                "depends_on": [7]
            },
            {
                "category": "违约情形",
                "question": "违约情形是什么（欠租、擅自转租、提前解约等）？",
                "importance": Importance.REQUIRED,
                "purpose": "确定违约责任与解约权",
                "follow_up": "需对应合同条款"
            },
            {
                "category": "装修添附",
                "question": "是否有装修或添附？如何处理？",
                "importance": Importance.OPTIONAL,
                "purpose": "识别装修损失补偿争议",
                "follow_up": "需装修同意书与费用凭证",
                "depends_on": [9]
            },
        ],
        "materials": [
            {
                "category": "权属证明",
                "material": "租赁物权属证明（房产证/产权证明）",
                "importance": MaterialImportance.IMPORTANT,
                "purpose": "确认出租方有权出租",
                "source_hint": "当事人提供或登记机构查询"
            },
            {
                "category": "交接证明",
                "material": "交付/腾退交接单及状况记录",
                "importance": MaterialImportance.IMPORTANT,
                "purpose": "确定占用与损耗争议基准",
                "source_hint": "双方签署",
                "related_to": [6]
            },
            {
                "category": "付款凭证",
                "material": "租金、押金支付凭证",
                "importance": MaterialImportance.REQUIRED,
                "purpose": "证明支付情况",
                "source_hint": "银行流水、收据",
                "related_to": [2]
            },
            {
                "category": "催告解约",
                "material": "催告记录、解约通知",
                "importance": MaterialImportance.IMPORTANT,
                "purpose": "证明解约程序合法",
                "source_hint": "当事人提供，保留送达凭证"
            },
        ],
    },
    "service": {
        "name": "服务合同",
        "keywords": ["服务合同", "技术服务", "咨询服务", "委托开发", "外包", "运维"],
        "legal_basis": ["《民法典》合同编（按服务性质适用对应典型合同分编）"],
        "collection_tips": [
            "服务成果无形，重点固定交付与验收的书面痕迹（邮件、验收单、上线记录）",
            "核对服务标准与验收标准条款，防止'成果不达标'类抗辩",
        ],
        "questions": [
            {
                "category": "服务内容",
                "question": "服务内容、范围和交付标准如何约定？",
                "importance": Importance.REQUIRED,
                "purpose": "确定履约判断基准",
                "follow_up": "对照合同附件的服务清单/SOW"
            },
            {
                "category": "服务价款",
                "question": "服务费金额和付款节点如何约定？",
                "importance": Importance.REQUIRED,
                "purpose": "确定给付义务",
                "follow_up": "区分预付款、进度款、尾款"
            },
            {
                "category": "服务履行",
                "question": "服务是否已完成并交付？有何交付凭证？",
                "importance": Importance.REQUIRED,
                "purpose": "证明己方履约",
                "follow_up": "整理邮件、验收单、上线/交付记录",
                "depends_on": [7]
            },
            {
                "category": "验收异议",
                "question": "对方是否验收？是否提出异议？",
                "importance": Importance.IMPORTANT,
                "purpose": "判断付款条件是否成就",
                "follow_up": "需固定异议内容与时间",
                "depends_on": [9]
            },
            {
                "category": "违约解除",
                "question": "是否存在违约或提前解除情形？",
                "importance": Importance.IMPORTANT,
                "purpose": "确定违约责任与结算范围",
                "follow_up": "核对合同解除条款"
            },
        ],
        "materials": [
            {
                "category": "交付验收",
                "material": "服务成果交付与验收凭证（验收单、邮件确认、上线记录）",
                "importance": MaterialImportance.REQUIRED,
                "purpose": "证明服务已完成交付",
                "source_hint": "当事人整理",
                "related_to": [2]
            },
            {
                "category": "成果文件",
                "material": "服务工作成果文件（报告、系统、方案等）",
                "importance": MaterialImportance.IMPORTANT,
                "purpose": "证明成果符合约定",
                "source_hint": "当事人提供",
                "related_to": [2]
            },
            {
                "category": "沟通催告",
                "material": "服务过程沟通记录与催款凭证",
                "importance": MaterialImportance.IMPORTANT,
                "purpose": "证明履约过程与欠付事实",
                "source_hint": "邮件、即时通讯记录"
            },
        ],
    },
}


def identify_contract_subtype(text: str) -> Optional[str]:
    """
    识别合同子类（N1：场景细化）
    
    Args:
        text: problem_type + brief_description 合并文本
        
    Returns:
        子类代码（construction_engineering/sales/lease/service）或 None
    """
    best_code, best_score = None, 0
    for code, sub in CONTRACT_SUBTYPES.items():
        score = sum(1 for kw in sub["keywords"] if kw in text)
        if score > best_score:
            best_code, best_score = code, score
    return best_code if best_score > 0 else None


# ==================== 升级条件与法律依据（N4） ====================

# 无专用模板的特殊领域关键词 → 触发升级提示（对应 SKILL.md「特殊领域案件」升级条件）
SPECIAL_DOMAIN_KEYWORDS = {
    "医疗纠纷": ["医疗", "医疗事故", "医患"],
    "环境污染": ["环境污染", "生态破坏"],
    "证券期货": ["证券", "期货", "虚假陈述"],
    "海事海商": ["海事", "海商", "船舶"],
    "破产清算": ["破产", "破产重整", "破产清算"],
    "涉外争议": ["国际仲裁", "涉外", "跨境"],
}

LEGAL_BASIS = {
    ProblemType.CIVIL_DISPUTE: [
        "《民事诉讼法》第119条（起诉条件）",
        "《民法典》侵权责任编",
    ],
    ProblemType.LABOR_DISPUTE: [
        "《劳动法》",
        "《劳动合同法》",
        "《劳动争议调解仲裁法》",
    ],
    ProblemType.FAMILY_LAW: [
        "《民法典》婚姻家庭编",
        "《民法典》继承编",
    ],
    ProblemType.CONTRACT_DISPUTE: [
        "《民法典》第509条（全面履行义务）",
        "《民法典》第577条（违约责任）",
        "《民法典》第585条（违约金）",
    ],
    ProblemType.TRAFFIC_ACCIDENT: [
        "《道路交通安全法》",
        "《民法典》侵权责任编",
    ],
    ProblemType.REAL_ESTATE: [
        "《民法典》物权编",
        "《城市房地产管理法》",
    ],
    ProblemType.IP_DISPUTE: [
        "《商标法》《专利法》《著作权法》",
    ],
    ProblemType.CORPORATE: [
        "《公司法》",
    ],
    ProblemType.GENERAL: [
        "《民事诉讼法》第119条（起诉条件）",
    ],
}


# ==================== 主处理函数 ====================

def process(payload: ChecklistInput) -> ChecklistOutput:
    """
    咨询信息采集清单生成主处理器
    
    Args:
        payload: 输入参数
        
    Returns:
        结构化清单输出
    """
    # 1. 提取输入参数
    problem_type_input = payload.get("problem_type", "")
    brief_description = payload.get("brief_description", "")
    detail_level = payload.get("detail_level", "standard")
    focus_areas = payload.get("focus_areas", [])
    client_type = payload.get("client_type", "individual")
    urgency = payload.get("urgency", "normal")
    
    # 2. 识别问题类型
    problem_type, confidence = identify_problem_type(problem_type_input, brief_description)
    
    # 2.5 合同子类识别（Step 1.4：brief_description 参与场景细化）
    subtype_info = None
    if problem_type == ProblemType.CONTRACT_DISPUTE:
        subtype_code = identify_contract_subtype(problem_type_input + " " + brief_description)
        if subtype_code:
            subtype_info = CONTRACT_SUBTYPES[subtype_code]
    
    # 3. 生成问题清单（通用模板 + 子类模板合并，解析 depends_on 逻辑关系）
    base_questions = QUESTION_TEMPLATES.get(problem_type, QUESTION_TEMPLATES[ProblemType.GENERAL])
    merged_questions = list(base_questions)
    if subtype_info:
        merged_questions += subtype_info["questions"]
    
    kept_questions = [
        (tidx, t) for tidx, t in enumerate(merged_questions, 1)
        if not (detail_level == "standard" and t["importance"] == Importance.OPTIONAL)
    ]
    q_temp_to_id = {tidx: f"Q{i + 1:03d}" for i, (tidx, _) in enumerate(kept_questions)}
    
    questions = []
    for i, (tidx, template) in enumerate(kept_questions, 1):
        deps = [q_temp_to_id[d] for d in template.get("depends_on", []) if d in q_temp_to_id]
        questions.append({
            "id": f"Q{i:03d}",
            "category": template["category"],
            "question": template["question"],
            "importance": template["importance"].value,
            "order": i,
            "purpose": template["purpose"],
            "follow_up": template["follow_up"],
            "depends_on": deps
        })
    
    # 4. 生成材料清单（通用模板 + 子类模板合并，解析 related_to 关联关系）
    base_materials = MATERIAL_TEMPLATES.get(problem_type, MATERIAL_TEMPLATES[ProblemType.GENERAL])
    merged_materials = list(base_materials)
    if subtype_info:
        merged_materials += subtype_info["materials"]
    
    kept_materials = [
        (tidx, t) for tidx, t in enumerate(merged_materials, 1)
        if not (detail_level == "standard" and t["importance"] == MaterialImportance.OPTIONAL)
    ]
    m_temp_to_id = {tidx: f"M{i + 1:03d}" for i, (tidx, _) in enumerate(kept_materials)}
    
    materials = []
    for i, (tidx, template) in enumerate(kept_materials, 1):
        rels = [m_temp_to_id[r] for r in template.get("related_to", []) if r in m_temp_to_id]
        materials.append({
            "id": f"M{i:03d}",
            "category": template["category"],
            "material": template["material"],
            "importance": template["importance"].value,
            "order": i,
            "purpose": template["purpose"],
            "source_hint": template["source_hint"],
            "related_to": rels
        })
    
    # 5. 生成采集提示（通用 + 类型化 + 子类化）
    collection_tips = [
        "建议优先采集「必问」问题和「必备」材料",
        "采集过程中注意记录信息来源",
    ]
    
    if problem_type == ProblemType.LABOR_DISPUTE:
        collection_tips.append("部分材料可能需要从用人单位调取，建议提前沟通")
    elif problem_type == ProblemType.FAMILY_LAW:
        collection_tips.append("财产情况需详细核实，建议当事人提前梳理")
    elif problem_type == ProblemType.TRAFFIC_ACCIDENT:
        collection_tips.append("注意保留所有医疗票据和相关费用凭证")
    elif problem_type == ProblemType.CONTRACT_DISPUTE:
        collection_tips.append("合同纠纷按「合同签订→合同履行→违约事实→催告→损失」链条固定证据")
    
    if subtype_info:
        collection_tips.extend(subtype_info["collection_tips"])
    
    # 6. 升级条件识别（N4：upgrade_alert）
    upgrade_alerts = []
    if confidence == "low":
        upgrade_alerts.append("问题类型未能明确识别，已使用通用清单，建议律师根据经验制定个性化采集方案")
    
    # 多类型交叉检测：描述文本命中两个以上类型且得分接近
    text_for_cross = problem_type_input + brief_description
    cross_scores = _keyword_scores(text_for_cross)
    if len(cross_scores) >= 2:
        top2 = sorted(cross_scores.values(), reverse=True)[:2]
        if top2[0] >= 2 and top2[0] - top2[1] <= 1:
            upgrade_alerts.append("案件涉及多类型交叉，建议律师综合判断")
    
    # 特殊领域检测：命中无专用模板的领域关键词
    for domain, kws in SPECIAL_DOMAIN_KEYWORDS.items():
        if any(kw in text_for_cross for kw in kws):
            upgrade_alerts.append(f"案件涉及{domain}领域，暂无专用采集模板，建议律师根据经验补充")
    
    # 合同纠纷未匹配到子类：通用模板针对性有限
    if problem_type == ProblemType.CONTRACT_DISPUTE and not subtype_info:
        upgrade_alerts.append("未识别到合同子类专用模板，已使用通用合同清单，建议律师根据合同类型补充子类专项问题")
    
    # 7. 法律依据（N4：legal_basis）
    legal_basis = list(LEGAL_BASIS.get(problem_type, []))
    if subtype_info:
        legal_basis.extend(subtype_info.get("legal_basis", []))
    
    # 8. 生成清单ID
    checklist_id = f"CL-{datetime.now().strftime('%Y%m%d')}-{datetime.now().strftime('%H%M%S')}"
    
    return {
        "checklist_id": checklist_id,
        "problem_type": problem_type.value,
        "problem_type_code": problem_type.name.lower(),
        "contract_subtype": subtype_info["name"] if subtype_info else None,
        "confidence": confidence,
        "generated_at": datetime.now().isoformat(),
        "jurisdiction": "中国大陆",
        "questions": questions,
        "materials": materials,
        "collection_tips": collection_tips,
        "upgrade_alert": upgrade_alerts,
        "legal_basis": legal_basis,
        "disclaimer": "本清单仅供参考，具体案件需根据实际情况调整。"
    }


# ==================== 测试用例 ====================

if __name__ == "__main__":
    # 测试1：劳动争议
    print("=" * 60)
    print("测试用例1：劳动争议")
    print("=" * 60)
    
    result1 = process({
        "problem_type": "劳动争议",
        "detail_level": "standard"
    })
    
    print(f"问题类型: {result1['problem_type']}")
    print(f"置信度: {result1['confidence']}")
    print(f"问题数量: {len(result1['questions'])}")
    print(f"材料数量: {len(result1['materials'])}")
    print("\n问题清单:")
    for q in result1['questions'][:5]:
        print(f"  [{q['importance']}] {q['question']}")
    
    # 测试2：婚姻家事
    print("\n" + "=" * 60)
    print("测试用例2：婚姻家事")
    print("=" * 60)
    
    result2 = process({
        "problem_type": "离婚",
        "brief_description": "结婚5年，有一个孩子，想离婚",
        "detail_level": "detailed"
    })
    
    print(f"问题类型: {result2['problem_type']}")
    print(f"置信度: {result2['confidence']}")
    print(f"问题数量: {len(result2['questions'])}")
    print(f"材料数量: {len(result2['materials'])}")
    
    # 测试3：通用类型
    print("\n" + "=" * 60)
    print("测试用例3：通用类型")
    print("=" * 60)
    
    result3 = process({
        "problem_type": "其他",
        "detail_level": "standard"
    })
    
    print(f"问题类型: {result3['problem_type']}")
    print(f"置信度: {result3['confidence']}")
    print(f"问题数量: {len(result3['questions'])}")
    
    # 测试4：建设工程设计合同（子类识别 + 新字段验证）
    print("\n" + "=" * 60)
    print("测试用例4：建设工程设计合同（子类模板）")
    print("=" * 60)
    
    result4 = process({
        "problem_type": "建设工程合同纠纷",
        "brief_description": "建设工程设计合同纠纷，客户是设计方，被发包人拖欠设计费300万元",
        "detail_level": "detailed",
        "client_type": "enterprise",
        "urgency": "normal",
        "focus_areas": ["设计费追讨", "合同履行", "违约责任"]
    })
    
    print(f"问题类型: {result4['problem_type']}（子类: {result4['contract_subtype']}）")
    print(f"置信度: {result4['confidence']}")
    print(f"问题数量: {len(result4['questions'])}")
    print(f"材料数量: {len(result4['materials'])}")
    print(f"升级提示: {result4['upgrade_alert']}")
    print(f"法律依据: {result4['legal_basis']}")
    deps_demo = [(q['id'], q['depends_on']) for q in result4['questions'] if q['depends_on']]
    rels_demo = [(m['id'], m['related_to']) for m in result4['materials'] if m['related_to']]
    print(f"逻辑关系示例: {deps_demo[:3]}")
    print(f"关联关系示例: {rels_demo[:3]}")
