# 本地 Word XML：Drawing 与文字效果预设值

仅在新建对象或更换预设时读取本表；未修改的值沿用 Fetch，无需加载。结构、身份、尺寸、颜色、清除和更新方式见 [`canvas-doc-drawing.md`](canvas-doc-drawing.md)。下表列出公开 XML 的全部合法值，大小写敏感；不得根据 UI 名称、OOXML 全量枚举或命名规律扩展取值。

> 使用前须完整读取本页；未见末行「全文完」时，调整 offset 继续读取至该标记。

## Shape preset

`<shape preset>` 支持以下 113 个值；例如椭圆为 `ellipse`，圆角矩形为 `roundRect`。更新使用原 Shape identity，新建使用 Drawing 专项的新建语法。

- `line`、`straightConnector1`、`bentConnector3`、`curvedConnector3`、`rect`、`roundRect`。
- `ellipse`、`triangle`、`rtTriangle`、`diamond`、`flowChartDecision`、`parallelogram`。
- `trapezoid`、`pentagon`、`hexagon`、`heptagon`、`octagon`、`decagon`。
- `dodecagon`、`rightArrow`、`downArrow`、`leftArrow`、`upArrow`、`leftRightArrow`。
- `upDownArrow`、`leftRightUpArrow`、`leftUpArrow`、`quadArrow`、`stripedRightArrow`、`notchedRightArrow`。
- `chevron`、`homePlate`、`bentArrow`、`bentUpArrow`、`curvedDownArrow`、`curvedLeftArrow`。
- `curvedRightArrow`、`curvedUpArrow`、`circularArrow`、`uturnArrow`、`downArrowCallout`、`leftArrowCallout`。
- `rightArrowCallout`、`upArrowCallout`、`leftRightArrowCallout`、`quadArrowCallout`、`leftBrace`、`rightBrace`。
- `bracePair`、`leftBracket`、`rightBracket`、`bracketPair`、`arc`、`bevel`。
- `blockArc`、`can`、`cloud`、`cube`、`donut`、`foldedCorner`。
- `frame`、`mathDivide`、`mathEqual`、`mathMinus`、`mathMultiply`、`mathNotEqual`。
- `mathPlus`、`noSmoking`、`pie`、`plaque`、`plus`、`wedgeEllipseCallout`。
- `wedgeRectCallout`、`wedgeRoundRectCallout`、`flowChartAlternateProcess`、`flowChartCollate`、`flowChartConnector`、`flowChartDelay`。
- `flowChartDisplay`、`flowChartDocument`、`flowChartExtract`、`flowChartInputOutput`、`flowChartInternalStorage`、`flowChartMagneticDisk`。
- `flowChartMagneticDrum`、`flowChartMagneticTape`、`flowChartManualInput`、`flowChartManualOperation`、`flowChartMerge`、`flowChartMultidocument`。
- `flowChartOffpageConnector`、`flowChartOnlineStorage`、`flowChartOr`、`flowChartPredefinedProcess`、`flowChartPreparation`、`flowChartProcess`。
- `flowChartPunchedCard`、`flowChartPunchedTape`、`flowChartSort`、`flowChartSummingJunction`、`flowChartTerminator`、`lightningBolt`。
- `moon`、`round1Rect`、`round2DiagRect`、`round2SameRect`、`snip1Rect`、`snip2DiagRect`。
- `snip2SameRect`、`snipRoundRect`、`star5`、`sun`、`wave`。

## WordArt warp

`<shape word-art-warp>` 支持以下 41 个值。新建必须同时声明 `word-art="true"` 并含一个 TextBox；不能用 warp 把普通 Shape 转成 WordArt。`textNoShape` 是合法 warp，不能替换成 `none` 或 `clear`。

- `textNoShape`、`textPlain`、`textStop`、`textTriangle`、`textTriangleInverted`、`textChevron`。
- `textChevronInverted`、`textRingInside`、`textRingOutside`、`textArchUp`、`textArchDown`、`textCircle`。
- `textButton`、`textArchUpPour`、`textArchDownPour`、`textCirclePour`、`textButtonPour`、`textCurveUp`。
- `textCurveDown`、`textCanUp`、`textCanDown`、`textWave1`、`textWave2`、`textDoubleWave1`。
- `textWave4`、`textInflate`、`textDeflate`、`textInflateBottom`、`textDeflateBottom`、`textInflateTop`。
- `textDeflateTop`、`textDeflateInflate`、`textDeflateInflateDeflate`、`textFadeRight`、`textFadeLeft`、`textFadeUp`。
- `textFadeDown`、`textSlantUp`、`textSlantDown`、`textCascadeUp`、`textCascadeDown`。

## 文字阴影

`text-shadow` 支持以下 23 个预设，或使用 `none` 清除：

- `outer-bottom-right`、`outer-bottom`、`outer-bottom-left`、`outer-right`、`outer-center`、`outer-left`。
- `outer-top-right`、`outer-top`、`outer-top-left`、`inner-top-left`、`inner-top`、`inner-top-right`。
- `inner-left`、`inner-center`、`inner-right`、`inner-bottom-left`、`inner-bottom`、`inner-bottom-right`。
- `perspective-upper-left`、`perspective-upper-right`、`perspective-below`、`perspective-lower-left`、`perspective-lower-right`。

## 文字映像

`text-reflection` 支持以下 9 个预设，或使用 `none` 清除：

- `reflection-tight-touching`、`reflection-half-touching`、`reflection-full-touching`、`reflection-tight-4pt`、`reflection-half-4pt`、`reflection-full-4pt`。
- `reflection-tight-8pt`、`reflection-half-8pt`、`reflection-full-8pt`。

## 文字发光

`text-glow` 支持以下 24 个预设，或使用 `none` 清除。需要自定义颜色时用 `text-glow-color`，仍保留合法的发光预设，不改写预设名称。

- `glow-blue-5`、`glow-orange-5`、`glow-dark-green-5`、`glow-cyan-5`、`glow-purple-5`、`glow-green-5`。
- `glow-blue-8`、`glow-orange-8`、`glow-dark-green-8`、`glow-cyan-8`、`glow-purple-8`、`glow-green-8`。
- `glow-blue-11`、`glow-orange-11`、`glow-dark-green-11`、`glow-cyan-11`、`glow-purple-11`、`glow-green-11`。
- `glow-blue-18`、`glow-orange-18`、`glow-dark-green-18`、`glow-cyan-18`、`glow-purple-18`、`glow-green-18`。

`shadow-none`、`reflection-none`、`glow-none` 是 UI 标识，不是 XML 值。清除阴影或发光时还须移除对应颜色属性；文字效果不支持任意阴影距离、映像参数或发光半径。

===== 全文完 =====
