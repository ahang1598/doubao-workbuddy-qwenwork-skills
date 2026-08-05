<!-- Source: HKUSTDial/Supervisor-Skills. Adapted for doubao-academic-evaluator. -->

# AI 腔、过度声明与破折号

审稿人对 AI 生成的痕迹越来越敏感。这份清单列出最容易暴露 AI 痕迹、最该避免的几类表达。

## 破折号误用

长破折号当句子连接词用，在本项目的写作规范里是不允许的。两种典型误用：

- **连接两个独立分句**：不要 "The pipeline closes the research loop — it covers literature analysis, hypothesis generation, and deployment."，改成带从句的 "... closes the research loop, covering literature analysis, hypothesis generation, and deployment."
- **插入补充说明**：不要 "This approach — though simple — is highly effective."，改成 "Although simple, this approach is highly effective."

学术写作里能正当使用长破折号的场合很少，拿不准就别用，逗号、冒号、句号几乎能处理所有情况。正文里每出现一次都按"一审会被点"算（除非在代码示例或保留的引文里）。

## AI 腔的词

下面这些词会向有经验的审稿人暴露 AI 撰写或辅助的痕迹。同一个词出现三次以上，就按"一审会被点"算。

- **创新吹嘘**：innovative、pioneering、revolutionary paradigm、transformative framework
- **性能吹嘘**：superior、surpass、excel、remarkable、unprecedented、achieves SOTA、breakthrough performance
- **贡献总结套话**：general-purpose、is capable of
- **逻辑连接套话**：notably、yet、yielding、at its essence
- **滥用的动词**：encompass、differentiate、reveal、underscore、exhibit superior capability、exceed、pave the way for、highlight the potential of
- **滥用的短语**：profound challenges（属夸张措辞，宜换成具体的困难描述）、stems from
- **其他**：rigid、impede

换成中性的技术动词：propose、introduce、design、present、show、demonstrate、report、observe。

## 过度声明

草稿里常见的过度声明，每一处都按"一审会被点"算，并要求作者限定或拿出依据：

- "Our method is state-of-the-art" 不加限定：要说清在哪个基准上、什么条件下。
- 把 "comprehensive experiments" 当贡献：实验本来就该做，关键是具体展示了什么。
- "extensive analysis"：要说清分析发现了什么，而不是"做了分析"这件事本身。
- "We solve the problem of X"：注意 "solve" 是很强的词，通常论文只是改进了 X 而非解决。
- "We are the first to ..."：仔细核实，错了审稿人会当场抓住并引用。

审稿人对在引言里过度声明的论文会记仇，这个代价在整个审稿周期里会累积。

## 图表垃圾

不增加信息、只添视觉噪声的图表元素：3D 柱状图/饼图、柱子或点上的阴影、除非编码连续变量否则的渐变填充、重网格线、装饰性的交叉影线、和图题重复的图标题、超过六项的图例（试着分组）。视严重程度按"打磨级"或"一审会被点"算。

## 抄袭（红线）

绝不抄别人论文的句子，包括作者自己未声明复用的旧论文。这适用于相关工作对前人方法的总结、引言对前人工作的引述、以及和基线论文自述太像的方法描述。抄袭是足以拒稿的硬伤。相关工作或引言里如果对前人工作的转述贴得太近，要用作者自己的话重写。最终投稿前建议过一遍外部查重工具。
