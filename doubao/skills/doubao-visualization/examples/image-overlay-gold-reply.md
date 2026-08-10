# Gold reply —— agent 实际输出的样子（干净、单趟、零泄漏）

> 迁移说明：本例完整保留原 Skill 的单图结构、0-999 process 驱动、两层舞台、图例与桌面 hover 代码，用于避免丢失成熟实现细节。融合版正式输出时还必须遵循 `references/image-overlay-authoring-spec.md` 的修订规则：补充 click/tap 联动；不要宣称 JS 解析失败后动态标记仍一定存在；内嵌 process 应包含与规范一致的 `final_answer`（或由执行方明确采用融合版 `answer` schema，二者不可混用）。

这是一道机箱风道题（对应 `gold-process.md` 那份 process）的**最终回复全文**。注意它的形状（=你要交付的目标）：

- ✅ **按此顺序**：讲解正文 → 最终答案（方案表格 + 细节）→ 收尾**一句自然衔接**（"我把…都标在图上了，照着看更直观"）→ **末尾**一张 ` ```html type="renderer" ` 可视化。**先把方案讲完、给出答案，可视化放最后**——用户不必等图形生成就能先读到结论，可视化作为佐证附在末尾。
- ✅ process 的四条证据（bbox_zoom 进风区 + path_grow 气流路径 + node_walk 排风方向 + count_pop 出风位）**合并进同一张图**，不是四张。
- ✅ 可视化是**自己手写**的 freehand 代码：内嵌 process JSON（step 只有 `type`+`coords`，coord 只有 `kind`/坐标/`label`，**无 color**）+ 自写 JS——**自己按语义挑配色**（进风/气流=靛灰蓝、出风=红褐、区域=墨绿）、按 §B 百分比/viewBox 把 0~999 画到画面、配图例与 hover 双向联动。唯一的"动"是 hover。
- ✅ **无畸变写法**：圆点 `dot()`、字幕 `pill()` 全是 `.layer` 里的 HTML `<div>`（百分比定位，圆是正圆、字不拉伸）；`.lines` 这个 `preserveAspectRatio="none"` 的 SVG **只画 `<line>`/`<path>`/`<rect>`**（带 `non-scaling-stroke`，node_walk 用 `<marker>` 画真箭头头），里面**没有任何 `<circle>`/`<text>`**——这是不让点/字被拉伸的关键。
- ✅ **idle 半透明按 skill 口径**：点 `__idle≈0.55`、胶囊 `≈0.7`、线/框/路径 `≈0.7~0.8`、连线 `≈0.45`，让原图透出、标记彼此重叠时也能看清下面内容；hover 聚焦项升 1.0、其余降 ~0.12。
- ✅ **图幅限高（纯静态固定 px，不用 vh/JS）**：舞台 `display:inline-block` 收缩包住图、`#svp` 居中；`<img>` 用 `width:auto;height:auto;max-width:100%;max-height:720px`——竖高图按固定高度收进一屏、不再撑满宽度要下滑，横图/方图先命中 `max-width:100%` 不受影响。**只用固定 px、不用 `vh`/`min()`**（端上无真实视口，`vh` 会时而被忽略、时而≈0 把图缩成极小）；覆盖层 `.lines`/`.layer` 仍 `inset:0` 随舞台对齐、标记不错位。
- ✅ **process 驱动 + 全覆盖交互**：坐标全部从内嵌 `#svpdata` 的 process JSON `JSON.parse` 后算出，无手敲坐标；每个标记和每行图例都进 `groups` 并 `bindHover`，`setActive` 让 hover 项升 1.0、其余降 0.12，图上↔图例双向联动。
- ✅ 这份渲染器 JS **覆盖全部标注类型**（count_pop / match_pair / bbox_zoom / **path_grow**(白垫底 polyline) / **node_walk**(marker 箭头) / default 各有分支）；本例数据用到 bbox_zoom + path_grow + node_walk + count_pop，其余分支是给别的题照抄的成品。
- ❌ 没有"我来帮你分析…并把风道可视化出来 / 做可视化标记 / 让我先看图 / 创建 / 校验 / 渲染 / 验证通过"这类**机制预告或旁白**；没有工具/文件/process/JSON/坐标/skill 字样；没有思维链。（收尾那句"标在图上、照着看"是**面向内容的自然衔接**，指给用户看什么、不是宣告要生成图，允许；"下面是可视化 / 见下图 / 让我渲染"这类**机制式预告**仍禁。）
- 回复**第一个字符**就是讲解正文；可视化默默出现在**最末尾**，不预告、不点名。

图片真实 URL：`https://tosv.byted.org/obj/ailab-content-quality-public/selfvis/skill_example_inline/case_airflow.jpg`（实战里就用本题当下读到的那条真实 https URL，逐字一致）。

下面 `---` 之间就是回复正文（原样输出，不含本说明）。

---

前面板无开孔的情况下，传统"前进后出"风道走不通，需要换思路——**底部进风 + 顶部+后部出风**是这套机箱最合理的方案。

## 风道方案：下进上出 + 后出（负压风道）

### 核心思路
前面板无开孔 → **放弃前进风**，利用底部电源仓开孔作为主要进风口，3 把出风扇（后 1 + 顶 2）全部向外排风，形成**微负压**，冷空气从底部和缝隙被吸入机箱。

### 风扇安装配置

| 位置 | 数量 | 风向 | 作用 |
|------|------|------|------|
| 底部（电源仓上方） | 1-2 把（如有位） | 向内吹（进风） | 给显卡底部供冷空气 |
| 后部 | 1 把 | 向外吹（出风） | 与 CPU 散热器同高，水平排风 |
| 顶部 | 2 把 | 全部向外吹（出风） | 顺应热空气上升，快速排热 |

### 关键细节

1. **CPU 散热器风向**：塔式散热器的风扇**朝后吹**（吹向机箱后风扇），形成 CPU → 后风扇的水平辅助风道，效率最高。

2. **顶部一定不要装进风**：热空气自然上升，顶部装进风等于把已经上升的热空气又往下压，会严重抵消自然对流效果。**两把都做出风**。

3. **底部进风要通畅**：电源线材尽量往后面/背板侧整理，不要堆在底部开孔正上方挡住进风。

4. **右侧线材是隐患**：图中右侧（后部）线材较多，如果太乱会阻挡后风扇的进风面，建议尽量理到背板侧。

### 如果温度还压不住
优先在**底部加装进风扇**直吹显卡底部——这是当前配置下进风最薄弱的环节，加强进风比加出风收益更大。
结合你机箱的实际布局，我把进风口、气流走向和几处关键出风位都标在图上了，照着看更直观。

```html type="renderer"
<html style="margin:0;padding:0;">
<div style="background:transparent;width:100%;">
  <div id="svp" style="width:100%;font-family:-apple-system,'PingFang SC','Segoe UI',sans-serif;text-align:center;">
    <div class="stage" style="position:relative;display:inline-block;max-width:100%;">
      <img src="https://tosv.byted.org/obj/ailab-content-quality-public/selfvis/skill_example_inline/case_airflow.jpg" alt="机箱内部" style="width:auto;max-width:100%;height:auto;max-height:720px;border-radius:6px;display:block;"/>
      <svg class="lines" viewBox="0 0 999 999" preserveAspectRatio="none" style="position:absolute;inset:0;width:100%;height:100%;pointer-events:none;overflow:visible;"></svg>
      <div class="layer" style="position:absolute;inset:0;pointer-events:none;"></div>
    </div>
    <ol class="legend" style="list-style:none;margin:12px 0 0;padding:0;text-align:left;"></ol>
    <script type="application/json" id="svpdata">{"steps":[{"type":"bbox_zoom","coords":[{"kind":"bbox","xyxy":[100,740,760,960],"label":"底部进风区：电源仓上方开孔，冷空气主要入口"}]},{"type":"path_grow","coords":[{"kind":"point","x":400,"y":940,"label":"底部进风"},{"kind":"point","x":400,"y":840,"label":"·"},{"kind":"point","x":360,"y":720,"label":"·"},{"kind":"point","x":340,"y":600,"label":"·"},{"kind":"point","x":370,"y":450,"label":"·"},{"kind":"point","x":380,"y":300,"label":"·"},{"kind":"point","x":380,"y":160,"label":"·"},{"kind":"point","x":380,"y":80,"label":"顶部出风"}]},{"type":"node_walk","coords":[{"kind":"point","x":500,"y":400,"label":"CPU散热器后部"},{"kind":"point","x":870,"y":400,"label":"后部风扇"}]},{"type":"count_pop","coords":[{"kind":"point","x":870,"y":400,"label":"后部出风：1把风扇向外排风"},{"kind":"point","x":280,"y":70,"label":"顶部出风位①：靠前风扇位"},{"kind":"point","x":560,"y":70,"label":"顶部出风位②：靠后风扇位"}]}]}</script>
    <script>
    (function(){
      try{
        var root=document.getElementById('svp'); if(!root) return;
        var dataEl=root.querySelector('#svpdata'); if(!dataEl) return;
        var data=JSON.parse(dataEl.textContent||'{}');
        var svg=root.querySelector('.lines'), layer=root.querySelector('.layer'), legend=root.querySelector('.legend');
        if(!svg||!layer||!legend) return;
        var NS='http://www.w3.org/2000/svg';
        // 配色：进风/气流=靛灰蓝，出风=红褐，区域=墨绿（process 里没有颜色字段，自己按语义挑）
        var INTAKE={m:'#4F46E5',r:'#4F46E5'};
        var EXHAUST={m:'#7A3F3F',r:'#C06A6A'};
        var ZONE={m:'#355E4B',r:'#5B9279'};
        function pct(v){return (v/999*100)+'%';}
        var groups=[], connectors=[];
        function addGroup(){var g={els:[]};groups.push(g);return g;}
        function pill(text,c,lx,ty,place){
          var d=document.createElement('div');
          var tf = (place==='top') ? 'translate(-50%,-145%)' : (place==='bottom' ? 'translate(-50%,45%)' : 'translate(12px,-50%)');
          d.textContent=text;
          d.style.cssText='position:absolute;left:'+pct(lx)+';top:'+pct(ty)+';transform:'+tf+';background:rgba(17,24,39,0.62);color:#fff;border:1px solid '+c.r+';border-radius:6px;padding:2px 7px;font-size:12px;line-height:1.3;white-space:nowrap;max-width:46vw;overflow:hidden;text-overflow:ellipsis;pointer-events:auto;cursor:default;';
          d.__idle=0.7; layer.appendChild(d); return d;
        }
        function dot(lx,ty,c){
          var d=document.createElement('div');
          d.style.cssText='position:absolute;left:'+pct(lx)+';top:'+pct(ty)+';transform:translate(-50%,-50%);width:15px;height:15px;border-radius:50%;background:'+c.m+';border:2px solid #fff;box-sizing:border-box;pointer-events:auto;cursor:default;';
          d.__idle=0.55; layer.appendChild(d); return d;
        }
        function legendRow(c,label){
          var li=document.createElement('li');
          li.style.cssText='display:flex;gap:8px;align-items:flex-start;margin:0 0 6px;font-size:13px;color:#374151;cursor:default;';
          li.innerHTML='<span style="flex:0 0 auto;width:10px;height:10px;border-radius:50%;margin-top:5px;background:'+c.m+';"></span><span><b style="color:#111827;">'+label+'</b></span>';
          li.__idle=1; legend.appendChild(li); return li;
        }
        function bindHover(g,i){
          g.els.forEach(function(el){ if(!el)return;
            el.addEventListener('mouseenter',function(){setActive(i);});
            el.addEventListener('mouseleave',function(){setActive(null);});
          });
        }
        function setActive(a){
          groups.forEach(function(g,i){ g.els.forEach(function(el){ if(!el)return;
            el.style.transition='opacity .18s';
            el.style.opacity = (a==null) ? el.__idle : (i===a?1:0.12);
          });});
          connectors.forEach(function(cn){
            cn.el.style.transition='opacity .18s';
            cn.el.style.opacity = (a==null) ? cn.idle : (cn.members.indexOf(a)>=0?0.95:0.1);
          });
        }
        var stepIdx=0;
        (data.steps||[]).forEach(function(step){
          var anim=step.type, coords=step.coords||[];
          if(anim==='count_pop'){
            coords.forEach(function(co){ if(co.kind!=='point')return;
              var g=addGroup();
              g.els.push(dot(co.x,co.y,EXHAUST), pill(co.label,EXHAUST,co.x,co.y,'right'), legendRow(EXHAUST,co.label));
              bindHover(g,groups.length-1);
            });
          } else if(anim==='match_pair' && coords.length>=2){
            var base=groups.length;
            coords.forEach(function(co,k){ if(co.kind!=='point')return;
              var c=k===0?INTAKE:EXHAUST; var g=addGroup();
              g.els.push(dot(co.x,co.y,c), pill(co.label,c,co.x,co.y,'right'), legendRow(c,co.label));
              bindHover(g,groups.length-1);
            });
            for(var k=0;k+1<coords.length;k+=2){
              var a=coords[k],b=coords[k+1];
              var ln=document.createElementNS(NS,'line');
              ln.setAttribute('x1',a.x);ln.setAttribute('y1',a.y);ln.setAttribute('x2',b.x);ln.setAttribute('y2',b.y);
              ln.setAttribute('stroke',INTAKE.r);ln.setAttribute('stroke-width','2');
              ln.setAttribute('stroke-dasharray','7 5');ln.setAttribute('vector-effect','non-scaling-stroke');
              svg.appendChild(ln);
              connectors.push({el:ln,members:[base+k,base+k+1],idle:0.45});
            }
          } else if(anim==='bbox_zoom' || (coords[0]&&coords[0].kind==='bbox')){
            coords.forEach(function(co){
              if(co.kind==='bbox'){
                var g=addGroup();
                var x=co.xyxy[0],y=co.xyxy[1],w=co.xyxy[2]-co.xyxy[0],h=co.xyxy[3]-co.xyxy[1];
                var r=document.createElementNS(NS,'rect');
                r.setAttribute('x',x);r.setAttribute('y',y);r.setAttribute('width',w);r.setAttribute('height',h);r.setAttribute('rx','6');
                r.setAttribute('fill',ZONE.m);r.setAttribute('fill-opacity','0.06');
                r.setAttribute('stroke',ZONE.m);r.setAttribute('stroke-width','2.5');r.setAttribute('vector-effect','non-scaling-stroke');
                r.__idle=0.75; svg.appendChild(r);
                g.els.push(r, pill(co.label,ZONE,(co.xyxy[0]+co.xyxy[2])/2,co.xyxy[1],'top'), legendRow(ZONE,co.label));
                bindHover(g,groups.length-1);
              } else if(co.kind==='point'){
                var c2=INTAKE; var g2=addGroup();
                g2.els.push(dot(co.x,co.y,c2), pill(co.label,c2,co.x,co.y,'right'), legendRow(c2,co.label));
                bindHover(g2,groups.length-1);
              }
            });
          } else if(anim==='path_grow'){
            var pts=coords.filter(function(co){return co.kind==='point';});
            if(pts.length>=2){
              var g=addGroup(), c=INTAKE;
              var dd='M'+pts.map(function(p){return p.x+' '+p.y;}).join(' L');
              var under=document.createElementNS(NS,'path');        // 白垫底：任何底色/墙色上都看得清
              under.setAttribute('d',dd);under.setAttribute('fill','none');under.setAttribute('stroke','#fff');
              under.setAttribute('stroke-width','5');under.setAttribute('stroke-linejoin','round');under.setAttribute('stroke-linecap','round');
              under.setAttribute('vector-effect','non-scaling-stroke');under.__idle=0.7;svg.appendChild(under);
              var pth=document.createElementNS(NS,'path');
              pth.setAttribute('d',dd);pth.setAttribute('fill','none');pth.setAttribute('stroke',c.m);
              pth.setAttribute('stroke-width','2.5');pth.setAttribute('stroke-linejoin','round');pth.setAttribute('stroke-linecap','round');
              pth.setAttribute('vector-effect','non-scaling-stroke');pth.__idle=0.8;svg.appendChild(pth);
              var s=pts[0],e=pts[pts.length-1];
              g.els.push(under,pth,dot(s.x,s.y,c),pill(s.label,c,s.x,s.y,'right'),dot(e.x,e.y,c),pill(e.label,c,e.x,e.y,'right'),legendRow(c,'主气流路径：底部→显卡→CPU→顶部'));
              bindHover(g,groups.length-1);
            }
          } else if(anim==='node_walk' && coords.length>=2){
            var a=coords[0],b=coords[1],c=EXHAUST,g=addGroup();
            if(!svg.querySelector('#svp-ah')){                      // 箭头 marker 只定义一次
              var defs=document.createElementNS(NS,'defs'),mk=document.createElementNS(NS,'marker');
              mk.setAttribute('id','svp-ah');mk.setAttribute('markerWidth','9');mk.setAttribute('markerHeight','9');
              mk.setAttribute('refX','7');mk.setAttribute('refY','3');mk.setAttribute('orient','auto');
              var mp=document.createElementNS(NS,'path');mp.setAttribute('d','M0,0 L7,3 L0,6 Z');mp.setAttribute('fill',c.m);
              mk.appendChild(mp);defs.appendChild(mk);svg.appendChild(defs);
            }
            var uw=document.createElementNS(NS,'line');             // 白垫底
            uw.setAttribute('x1',a.x);uw.setAttribute('y1',a.y);uw.setAttribute('x2',b.x);uw.setAttribute('y2',b.y);
            uw.setAttribute('stroke','#fff');uw.setAttribute('stroke-width','5');uw.setAttribute('vector-effect','non-scaling-stroke');uw.__idle=0.7;svg.appendChild(uw);
            var ln=document.createElementNS(NS,'line');
            ln.setAttribute('x1',a.x);ln.setAttribute('y1',a.y);ln.setAttribute('x2',b.x);ln.setAttribute('y2',b.y);
            ln.setAttribute('stroke',c.m);ln.setAttribute('stroke-width','2.5');
            ln.setAttribute('marker-end','url(#svp-ah)');ln.setAttribute('vector-effect','non-scaling-stroke');ln.__idle=0.8;svg.appendChild(ln);
            g.els.push(uw,ln,dot(a.x,a.y,c),pill(a.label,c,a.x,a.y,'top'),pill(b.label,c,b.x,b.y,'top'),legendRow(c,'后部出风方向：CPU→后风扇'));
            bindHover(g,groups.length-1);
          } else {
            coords.forEach(function(co){ if(co.kind!=='point')return;
              var c3=INTAKE; var g=addGroup();
              g.els.push(dot(co.x,co.y,c3), pill(co.label,c3,co.x,co.y,'right'), legendRow(c3,co.label));
              bindHover(g,groups.length-1);
            });
          }
          stepIdx++;
        });
        // 直接置 idle 半透明
        groups.forEach(function(g){g.els.forEach(function(el){if(el)el.style.opacity=el.__idle;});});
        connectors.forEach(function(cn){cn.el.style.opacity=cn.idle;});
      }catch(e){console.error('svp render error:',e);}
    })();
    </script>
  </div>
</div>
</html>
```
