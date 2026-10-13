# 参数化排版（可选）

仅在用户选择精确本地排版且当前工具规则允许时使用，普通生图无需运行此脚本或准备配置。脚本成功不代表构图合格；最终仍需检查图文体量、间距与大片无效空白。

`scripts/compose_poster.py` 负责已授权的本地排版：加载当前品牌字体/原始 Logo，合成已准备的底图、文字和矩形或圆角 CTA。它不调用生图 API，不安装系统字体，不将某种排版审美作为所有品牌的标准。

按当前工具规则和用户指定制作方式使用；艺术排版、曲线文字、复杂多语言塑形或可编辑设计文档需要合适的设计工具。此脚本不支持某种形状，不代表该品牌禁止该形状。复杂视觉继续使用图像工具，不能以纯色排版夹具替代用户要的完整视觉。

## 输入 layout.json

- `brand_profile`、`brand_id`、`profile_fingerprint`、`rule_overrides`：与 batch.json 相同，显式绑定品牌，无默认品牌。
- `width/height/output`：输出精确像素与 PNG 文件路径，路径相对 layout.json。`base_image` 可选，必须尺寸一致；不用它则为 background 指定的纯色画布。
- `palette`：角色名到十六进制颜色，例如 ink/accent/paper；从当前品牌和项目选择，没有固定蓝色。profile 的 palette 是参考值，最终按本次确认。脚本只验证角色组合，不会判断名为 blue 的颜色是否视觉上符合官方品牌蓝。
- `levels`：任意命名层级，值为 `{size,font,latin_font?,axes?,latin_axes?}`。font/latin_font 引用当前 profile.fonts。可按字体变量轴名称给出值；无西文专用字体则使用同一个已选字体，不回退到其他品牌。
- `lines`：单行数组，每项含 level、align(left/center/right)、x（按对齐方式解释的锚点）、baseline_y、max_width、runs（text/color）。字号不被自动缩小、文字不被挤压；溢出需重新排版。
- `logo`：可省略；需要时提供 asset（profile.assets 中的名称）、x/y/width/clear_space。保持原始比例与透明度，最小尺寸从该资产配置读取，不写死 25px。明确无 Logo 的任务不补 Logo。
- `ctas`：可为空数组；每项含 level、box[x,y,w,h]、padding、fill、shape、baseline_y、align、runs；rounded_rectangle 另含 radius。当前品牌禁止圆角时会拒绝，允许则正常渲染。CTA 文本加入投放颜色检查。

只为实际使用的品牌准备字体/资产。无文字且不含 Logo 的纯视觉任务允许 levels/palette 为空。脚本检查字体/Logo 文件存在和声明哈希，不知道用户是否拥有相应授权；不把 profile 文件当成外部权限凭证。

## 执行

先查看准备的底图，确保后置文字/按钮/Logo 区域没有重复内容。

```bash
python3 /absolute/skill/scripts/profile_utils.py /absolute/brand/profile.json
python3 /absolute/skill/scripts/compose_poster.py /absolute/task/layout.json
```

结果为 PNG 和 `.render.json`，包含品牌指纹、字体/Logo 哈希、实际文字与坐标，review_status 始终 pending。它不是审核通过证明。脚本拒绝覆盖成品，改版另取文件名。

根据本次任务在项目目录编写 layout.json；本技能不附带品牌排版夹具。无 Logo 时省略 logo，无文字时 levels 和 lines 可为空。技术排版输出仍需结合实际视觉自检，不能直接当成批量风格样张。

## 检查边界

脚本执行当前品牌允许的文字颜色角色组合、层级上限、对齐、按钮形状以及 Logo 最小尺寸；检查出界、文字溢出、前景文字/按钮/Logo 净空碰撞。最终文件还要按 [通用审核](quality-review.md) 和品牌清单审图。

脚本不识别底图内的字、不验证视觉区语义、不检查底图与前景全部干扰，也不判断角色是否合规或真伪。文本绘制默认水平，未实现旋转或任意形状；这些需求选择其他工具，不修改品牌规则来迁就脚本。

## 完整最小示例与依赖

Python 3.9+、Pillow 9.1+ 为接口下限；已验证 Python 3.9.6 / Pillow 11.3.0。先运行 `python3 -c "import sys, PIL; print(sys.version, PIL.__version__)"` 与 `python3 scripts/compose_poster.py --help` 确认当前环境。缺依赖时说明缺口，优先使用项目现有环境，不自动更改系统环境。

下面从技能根目录执行。它在临时目录生成完整的 profile.json、layout.json、32×18 PNG 和 render 记录，然后自动清理；无需品牌、字体或图片资产。**它只验证配置契约，不是宣传图示例，不用于替代生图。** 正式任务将输出指向独立任务目录，并按已授权内容添加底图、文字或 Logo。

```bash
python3 - <<'PY'
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import sys
sys.path.insert(0, str(Path('scripts').resolve()))
from profile_utils import load_profile
from compose_poster import compose
with TemporaryDirectory(prefix='layout-example-') as work:
    root = Path(work)
    profile = {'id': 'example-project', 'status': 'draft',
               'constraints': {}, 'review_rules': [], 'references': [],
               'assets': {}, 'fonts': {}}
    (root / 'profile.json').write_text(json.dumps(profile), encoding='utf-8')
    _, fingerprint = load_profile(root / 'profile.json')
    layout = {'brand_profile': 'profile.json', 'brand_id': 'example-project',
              'profile_fingerprint': fingerprint, 'rule_overrides': [],
              'width': 32, 'height': 18, 'output': 'example.png',
              'background': '#FFFFFF', 'palette': {}, 'levels': {},
              'lines': [], 'ctas': []}
    (root / 'layout.json').write_text(json.dumps(layout), encoding='utf-8')
    result = compose(root / 'layout.json')
    print(json.dumps({'size': result['size'],
                      'review_status': result['review_status']}, ensure_ascii=False))
PY
```

预期输出：`{"size": [32, 18], "review_status": "pending"}`。brand_profile、brand_id、profile_fingerprint、width、height、output 必填；rule_overrides、palette、levels、lines、ctas 默认空集合。base_image 与 background 是二选一的画布来源，有 base_image 时忽略 background；未指定任何来源时底色默认白色。logo 默认不绘制；文字的 align 默认 left，CTA 的 align 默认 center、shape 默认 rectangle。

CLI 失败返回非零退出码并输出 `Composition failed: ...`。例如再次写同一文件会报告 `output or render record already exists; choose a versioned filename`；尺寸 0 会报告 `width and height must be positive integers`。选择新文件名或修正配置再执行，不通过覆盖旧文件解决。含文字/Logo 时先准备本次授权文件并按字段说明填写 fonts/assets；这个无资产夹具不覆盖字体塑形与品牌精度检查。
