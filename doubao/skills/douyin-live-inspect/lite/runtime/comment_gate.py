"""Conservative local admission before semantic comment extraction."""
import collections
import hashlib
import json
import math
from pathlib import Path
import re
import unicodedata

MODEL_PATH = Path(__file__).resolve().parents[1]/'config/comment-gate-model.json'
MIN_THRESHOLD = 0.995
MIN_COVERAGE = 0.8
SCHEMA = 'comment_gate_char_tfidf_v1'

# Exact templates only; conditions, references and multiple intents go to the model.
QUESTION_RULES = [
    ({'多少钱','什么价格','啥价格','价格多少','售价多少'},'价格是多少？','price','价格'),
    ({'发什么快递','发哪个快递','什么快递'},'发什么快递？','delivery','快递承运商'),
    ({'什么时候发货','多久发货','几天发货'},'预计什么时候发货？','delivery','发货时间'),
    ({'怎么下单','怎么买','在哪下单'},'如何下单购买？','purchase','下单方式'),
]
EMOTICONS = re.compile(r'(?:\[(?:赞|比心|爱心|玫瑰|鼓掌|微笑|大笑)\])+')
REACTIONS = set('👍👏❤💕💖💗💓💞💘😊😄😁😂🤣🙏🌹💐🙌🤝')
# Never let a statistical negative decision suppress likely requests or feedback.
PROTECTED = re.compile(r'[\d?？@❓❔⁉❗❕]|吗|么|啥|何|哪|几|多少|多久|多大|能|可|不|没|无|未|别|再|想|要|求|上|补|抢|买|购|货|价|钱|券|码|号|链|送|退|换|我|你|他|她|这|那|订单|售后|地址|尺寸|物流|快递|质量|包装|味|口感|硬|甜|贵|差|坏|臭|漏|破|便宜|吃|喝|穿')


def normalize(text):
    return re.sub(r'\s+',' ',unicodedata.normalize('NFKC',text)).strip().lower()


def features(text):
    return collections.Counter(text[i:i+n] for n in (1,2,3) for i in range(len(text)-n+1))


def score(model, text):
    counts=features(text);weights=model['features'];values={}
    for token,count in counts.items():
        if token in weights:values[token]=(1+math.log(count))*weights[token][0]
    norm=math.sqrt(sum(v*v for v in values.values()))
    coverage=sum(counts[t] for t in values)/max(1,sum(counts.values()))
    if not norm:return 0.0,coverage
    logit=model['intercept']+sum(v/norm*weights[t][1] for t,v in values.items())
    probability=1/(1+math.exp(-max(-700,min(700,logit))))
    return probability,coverage


def model_eligible(text):
    return 3<=len(text)<=120 and not PROTECTED.search(text)


def qualified(metrics):
    return (isinstance(metrics,dict) and metrics.get('session_disjoint') is True
        and metrics.get('text_disjoint') is True
        and all(type(metrics.get(k)) is int for k in ('accepted','false_dismissals','validation_sessions','meaningful_samples'))
        and metrics['accepted']>=300 and metrics['false_dismissals']==0
        and metrics['validation_sessions']>=2 and metrics['meaningful_samples']>=100)


def load_model(path=None):
    path=Path(path or MODEL_PATH)
    try:
        if path.stat().st_size>8_000_000:return None,'invalid'
        raw=path.read_bytes();model=json.loads(raw)
        finite=lambda v:type(v) in (int,float) and abs(v)<=1_000_000 and math.isfinite(v)
        if (model.get('schema')!=SCHEMA or not finite(model.get('threshold'))
                or not MIN_THRESHOLD<=model['threshold']<=1 or not finite(model.get('intercept'))
                or not isinstance(model.get('features'),dict) or not 1<=len(model['features'])<=20000):return None,'invalid'
        for token,weight in model['features'].items():
            if not isinstance(token,str) or not 1<=len(token)<=3 or not isinstance(weight,list) or len(weight)!=2 or not all(finite(v) for v in weight) or weight[0]<=0:return None,'invalid'
        if not qualified(model.get('validation')):return None,'not_qualified'
        model['model_id']=hashlib.sha256(raw).hexdigest()
        return model,'ready'
    except FileNotFoundError:return None,'not_installed'
    except (OSError,ValueError,TypeError,AttributeError,RecursionError):return None,'invalid'


def decide(comment, model=None):
    if comment.get('author_role') in {'host','room_admin'}:return None
    text=normalize(comment['text'])
    key=re.sub(r'[?？!！。\.]+$','',text)
    for aliases,detail,category,topic in QUESTION_RULES:
        if key in aliases:
            return {'processor':'local_rule','question':{'question_detail':detail,'question_scope':'public',
                    'question_category':category,'topic':topic}}
    emoji=any(c in REACTIONS for c in text) and all(c in REACTIONS or c in '\ufe0f ' or 0x1f3fb<=ord(c)<=0x1f3ff for c in text)
    if emoji or EMOTICONS.fullmatch(text) or text in {'谢谢','谢谢主播','感谢'}:
        return {'processor':'local_rule','reason':'纯表情或致谢，无明确提问；原评论保留'}
    if model and model_eligible(text):
        probability,coverage=score(model,text)
        if probability>=model['threshold'] and coverage>=MIN_COVERAGE:
            return {'processor':'local_classifier','reason':'本地分类器判为非经营请求；原评论保留',
                    'confidence':round(probability,6),'model_id':model['model_id']}
    return None
