"use strict";
const pendingSeeks = new WeakMap();
const renderJobs = new WeakMap();
// Native dialog provides focus containment and Esc; restore focus to its trigger.
window.LiteUI = {
  // Reuse keyed children in place: controls, focus, selection and scroll remain owned by the browser.
  domUpdate(root) {
    const plans = new Map([[root, []]]);
    const focused = document.activeElement;
    const restoreFocus = focused && root.contains?.(focused);
    const add = (parent, tag, text = '', cls = '', key) => {
      const plan = plans.get(parent) || [];
      plans.set(parent, plan);
      const slot = key === undefined ? `${tag}:${cls}:${plan.filter(n => n._domKind === `${tag}:${cls}`).length}` : `key:${key}`;
      let node = Array.from(parent.children).find(n => n._domSlot === slot && n._domKind === `${tag}:${cls}` && !plan.includes(n));
      if (!node) node = tag.startsWith('svg:') ? document.createElementNS('http://www.w3.org/2000/svg', tag.slice(4)) : document.createElement(tag);
      node._domSlot = slot; node._domKind = `${tag}:${cls}`;
      if (cls && node.className !== cls) node.className = cls;
      if (text !== '' && node.textContent !== String(text ?? '')) node.textContent = text ?? '';
      if (text === '') {
        if (node._domText) node.textContent = '';
        plans.set(node, []);
      }
      node._domText = text !== '';
      plan.push(node);
      return node;
    };
    return {add, retain: node => plans.delete(node), finish() {
      for (const [parent, children] of plans) {
        const retained = new Set(children);
        for (const child of Array.from(parent.children)) if (!retained.has(child)) parent.removeChild(child);
        children.forEach((child, index) => {
          if (parent.children[index] !== child) parent.insertBefore(child, parent.children[index] || null);
        });
      }
      if (restoreFocus && root.contains(focused) && document.activeElement !== focused) focused.focus({preventScroll:true});
    }};
  },
  commentAuthor(item) {
    const role = {host:"主播", room_admin:"管理员"}[item.author_role] || "观众（角色未确认）";
    return `${item.author_nickname || "昵称未采集"} · ${role}`;
  },
  questionerCounts(questions) {
    const comments = new Map();
    for (const q of questions) if (q.source === "viewer_comment") {
      for (const ref of q.evidence_ids || []) comments.set(ref, q);
    }
    const rows = [...comments.values()];
    return {comment_question_count:rows.length,
      questioner_count:new Set(rows.map(q => q.author_id).filter(Boolean)).size,
      unknown_author_question_count:rows.filter(q => !q.author_id).length};
  },
  questionerLabel(counts) {
    return `提问 ${counts.comment_question_count} 次 · 已识别提问人数 ${counts.questioner_count} 人${counts.unknown_author_question_count ? ` · 另有 ${counts.unknown_author_question_count} 次身份未知` : ""}`;
  },
  // Collapse only the generated ambiguity notice; explicit failures keep their time ranges.
  reportGapDetail(gap) {
    return gap.kind !== "image_unsampled" && !(gap.kind === "judgment" &&
      gap.reason === "规则结果缺失或证据不足，具体原因见规则判断依据");
  },
  reportScope(report) {
    const gaps = report.coverage?.gaps || [];
    const notes = ["结论仅适用于已完成判定的范围。"];
    const counts = report.conclusion?.coverage_summary?.counts;
    if (counts?.unchecked) notes.push(`${counts.unchecked} 段未完成检测。`);
    if (counts?.pending) notes.push(`${counts.pending} 段待判定。`);
    if (!gaps.length && (report.conclusion?.has_incomplete_results || report.conclusion?.coverage_complete === false))
      notes.push("存在未完成检测或未确认的内容。");
    if (gaps.some(g => g.kind === "image_unsampled")) notes.push("画面采用抽样检测，仅覆盖抽检时刻。");
    if (gaps.some(g => g.kind === "judgment" && !this.reportGapDetail(g)) || report.remediation?.pending?.length || counts?.evidence_insufficient)
      notes.push("部分规则尚无法确认，不计为已确认风险。");
    const reasons = [...new Set(gaps.filter(g => this.reportGapDetail(g)).map(g => g.reason).filter(Boolean))];
    if (reasons.length) notes.push(`检测范围限制：${reasons.join("；")}。`);
    return notes.join(" ");
  },
  renderRows(container, rows, render, empty = "", revealIndex = -1) {
    const job = {};
    renderJobs.set(container, job);
    let end = Math.min(rows.length, Math.max(40, revealIndex + 1));
    container.innerHTML = rows.slice(0, end).map(render).join("") || empty;
    function next() {
      if (renderJobs.get(container) !== job) return;
      const start = end;
      end = Math.min(rows.length, start + 40);
      container.insertAdjacentHTML("beforeend", rows.slice(start, end).map(render).join(""));
      if (end < rows.length) setTimeout(next, 0);
    }
    if (end < rows.length) setTimeout(next, 0);
  },
  seek(video, seconds) {
    if (video.readyState >= 1) {
      pendingSeeks.delete(video);
      video.currentTime = seconds;
      return;
    }
    if (!pendingSeeks.has(video)) {
      video.addEventListener(
        "loadedmetadata",
        () => {
          if (pendingSeeks.has(video))
            video.currentTime = pendingSeeks.get(video);
          pendingSeeks.delete(video);
        },
        { once: true },
      );
      // preload=none otherwise leaves a timecode click waiting indefinitely.
      if (video.preload === "none") { video.preload = "metadata"; video.load(); }
    }
    pendingSeeks.set(video, seconds);
  },
  preview(url, alt, trigger) {
    const allowed = value => {
      return /^data:image\/(jpeg|png|webp|gif);base64,[A-Za-z0-9+/=]+$/.test(value) ? value : null;
    };
    const source = allowed(url);
    if (!source) return;
    const existing = document.getElementById("lite-image-dialog");
    if (existing) existing.close();
    const dialog = document.createElement("dialog");
    dialog.id = "lite-image-dialog";
    dialog.className = "lite-image-dialog arco-image-preview";
    dialog.setAttribute("aria-label", `${alt || "证据图片"}预览`);
    // Reuse the console's exported Arco markup/styles/icons, with native focus containment.
    dialog.innerHTML = '<div class="arco-image-preview-wrapper"><div class="arco-image-preview-img-container"><img class="arco-image-preview-img" draggable="false"></div><div class="arco-image-preview-toolbar"></div></div>';
    const wrapper = dialog.querySelector('.arco-image-preview-img-container');
    const image = dialog.querySelector('img');
    image.referrerPolicy = 'no-referrer';
    image.alt = alt || '证据图片';
    const group = trigger?.closest('.images');
    const sources = group ? [...group.querySelectorAll('[data-preview]')].map(el => allowed(el.dataset.preview)).filter(Boolean) : [source];
    let index = Math.max(0, sources.indexOf(source));
    let scale = 1, rotation = 0, x = 0, y = 0, drag;
    const scales = [.25,.33,.5,.67,.75,.8,.9,1,1.1,1.25,1.5,1.75,2,2.5,3,4,5];
    const buttons = new Map();
    function paint() {
      image.style.transform = `translate(${x}px, ${y}px) rotate(${rotation}deg) scale(${scale})`;
      for (const [name, disabled] of [['ZoomIn',scale>=5],['ZoomOut',scale<=.25],['Left',index===0],['Right',index===sources.length-1]]) {
        const button = buttons.get(name);
        if (button) {button.disabled=disabled;button.classList.toggle('arco-image-preview-toolbar-action-disabled',disabled);}
      }
    }
    function change(delta) {
      index = Math.min(sources.length-1, Math.max(0,index+delta));
      toolbar.hidden = true;
      image.src=sources[index];scale=1;rotation=0;x=0;y=0;paint();
    }
    function zoom(direction) {
      scale = direction>0 ? scales.find(v=>v>scale) || 5 : [...scales].reverse().find(v=>v<scale) || .25;
      paint();
    }
    function button(icon, label, className, action, parent=dialog) {
      const el=document.createElement('button');el.type='button';el.className=className;el.title=label;el.setAttribute('aria-label',label);
      const svg=window.InspectIcons?.[icon] || label;
      el.innerHTML=className.includes('toolbar-action') ? `<span class="arco-image-preview-toolbar-action-content">${svg}</span>` : svg;
      el.onclick=action;parent.append(el);buttons.set(icon,el);return el;
    }
    const toolbar=dialog.querySelector('.arco-image-preview-toolbar');
    toolbar.hidden = true;
    image.addEventListener('load', () => { toolbar.hidden = false; });
    image.addEventListener('error', () => { toolbar.hidden = true; });
    const action='arco-image-preview-toolbar-action';
    button('Fullscreen','适应屏幕',action,()=>{
      if (!image.complete || !image.naturalWidth || !image.naturalHeight) return;
      const rect=image.getBoundingClientRect();
      if (rect.width <= 0 || rect.height <= 0) return;
      scale*=Math.max(innerWidth/rect.width,innerHeight/rect.height);paint();
    },toolbar);
    button('RotateRight','向右旋转',action,()=>{rotation+=90;paint();},toolbar);
    button('RotateLeft','向左旋转',action,()=>{rotation-=90;paint();},toolbar);
    button('ZoomIn','放大',action,()=>zoom(1),toolbar);
    button('ZoomOut','缩小',action,()=>zoom(-1),toolbar);
    button('OriginalSize','原始尺寸',action,()=>{scale=1;x=0;y=0;paint();},toolbar);
    button('Close','关闭','arco-image-preview-close-btn',()=>dialog.close());
    if(sources.length>1) {
      button('Left','上一张','arco-image-preview-arrow-left',()=>change(-1));
      button('Right','下一张','arco-image-preview-arrow-right',()=>change(1));
    }
    wrapper.addEventListener('click',event=>{if(event.target===wrapper)dialog.close();});
    wrapper.addEventListener('wheel',event=>{event.preventDefault();zoom(event.deltaY<0?1:-1);},{passive:false});
    image.addEventListener('pointerdown',event=>{drag={x:event.clientX-x,y:event.clientY-y};image.setPointerCapture(event.pointerId);});
    image.addEventListener('pointermove',event=>{if(drag){x=event.clientX-drag.x;y=event.clientY-drag.y;paint();}});
    image.addEventListener('pointerup',()=>{drag=null;});
    image.addEventListener('pointercancel',()=>{drag=null;});
    dialog.addEventListener('keydown',event=>{
      if(event.key==='ArrowLeft'){event.preventDefault();change(-1);}
      if(event.key==='ArrowRight'){event.preventDefault();change(1);}
    });
    const previous=trigger || document.activeElement;
    dialog.addEventListener('close',()=>{dialog.remove();previous?.focus();},{once:true});
    document.body.append(dialog);change(0);dialog.showModal();buttons.get('Close').focus();
  },
  renderClarifications(data, formatTime, showUnchecked) {
    const panel = document.getElementById('clarifications');
    if (!panel) return;
    panel.hidden = !data?.checked_segments && !showUnchecked;
    if (panel.hidden) return;
    const signature = JSON.stringify(data ?? null);
    if (panel.dataset.signature === signature) return;
    panel.dataset.signature = signature;
    const update = this.domUpdate(panel), add = update.add;
    const view = panel._clarificationView ||= {status:'all', query:'', page:0};
    const labels = {pending:'待澄清', uncertain:'待核实', partial:'部分纠正', corrected:'已纠正', dismissed:'疑点已排除'};
    add(panel, 'h2', '现场澄清与纠错');
    add(panel, 'p', '帮助主播跟进说错或没讲清的内容，例如报错价格、漏讲领券条件。按同一商品和活动条件，对照原话与后续口播，记录是否已向观众说明清楚。', 'scope-note');
    if (!data?.checked_segments) {
      add(panel, 'p', '暂无已检查的口播片段。', 'scope-note');
      update.finish();
      return;
    }
    if (Array.isArray(data.items) && !data.items.length) {
      const empty=add(panel,'p','无风险 · 已检查的口播中未发现需澄清事项','clarification-empty');
      empty.setAttribute('role','status');
      update.finish();
      return;
    }
    add(panel, 'p', '待澄清：已定位需补充的说法；待核实：原话或依据不确定；部分纠正：只补充了部分信息；已纠正：后续口播已说清；疑点已排除：证据已澄清原先的疑问。', 'scope-note');
    add(panel, 'p', Object.entries(labels).map(([key,label]) => `${label} ${data.counts?.[key] || 0}`).join(' · '));
    add(panel, 'p', `已检查 ${data.checked_segments}/${data.total_segments} 段。${data.scope}`).className = 'scope-note';
    if (data.unreviewed_pairs) add(panel,'p',`收尾补查待完成：${data.unreviewed_items} 项疑点仍有 ${data.unreviewed_pairs} 个字幕范围未核对。`).className='scope-note';
    else if (data.recheck_complete) add(panel,'p','待澄清项的必要补查已完成；未找到纠正的事项仍保留原状态。').className='scope-note';
    if (data.unavailable_segments) add(panel,'p',`${data.unavailable_segments} 段无可用字幕，无法确认这些时段是否发生纠正。`).className='scope-note';
    const controls = add(panel, 'div', ''); controls.className = 'room-controls';
    const filter = add(controls, 'select', ''); filter.setAttribute('aria-label', '纠错状态');
    for (const [key,label] of [['all','全部状态'],...Object.entries(labels)]) { const option = add(filter,'option',label); option.value = key; }
    const query = add(controls,'input',''); query.type = 'search'; query.placeholder = '筛选商品或表述'; query.setAttribute('aria-label','筛选澄清记录');
    const list = add(panel,'div','','clarification-list'); update.retain(list);
    const pager = add(panel,'div',''); pager.className = 'room-controls';
    const prev = add(pager,'button','上一页'), info = add(pager,'span',''), next = add(pager,'button','下一页');
    prev.type = next.type = 'button';
    let page = view.page;
    const time = ms => formatTime ? formatTime(ms) : `${Math.floor(ms/60000)}:${String(Math.floor(ms/1000)%60).padStart(2,'0')}`;
    const draw = () => {
      const needle = query.value.trim().toLowerCase();
      const rows = (data.items || []).filter(q => (filter.value==='all' || q.status===filter.value) && `${q.object} ${q.issue} ${q.quote}`.toLowerCase().includes(needle));
      page = Math.min(page,Math.max(0,Math.ceil(rows.length/10)-1));
      const listUpdate = this.domUpdate(list), add = listUpdate.add;
      view.page = page;
      for (const q of rows.slice(page*10,page*10+10)) {
        const card = add(list, 'article', '', 'clarification-card', q.id || `${q.start_ms}:${q.object}:${q.issue}`);
        const meta = add(card, 'div', '', 'clarification-meta');
        add(meta, 'span', time(q.start_ms));
        const status = add(meta, 'span', labels[q.status] || '待核实', 'clarification-status');
        status.dataset.state = q.status;
        add(card, 'h3', q.object);
        const body = add(card, 'div', '', 'clarification-body');
        for (const [label, text] of [['需澄清内容', q.issue], ['建议', q.action]]) {
          if (!text) continue;
          const field = add(body, 'div', '', 'clarification-field', label);
          add(field, 'strong', label);
          add(field, 'p', text);
        }
        const evidence = add(card, 'dl', '', 'clarification-evidence');
        add(evidence, 'dt', '原表述');
        add(evidence, 'dd', q.quote);
        add(evidence, 'dt', '纠正记录');
        add(evidence, 'dd', q.corrections?.length
          ? q.corrections.map(c => `${time(c.start_ms)} ${c.quote}（${c.reason}）`).join('\n')
          : '尚未观察到纠正');
      }
      if (!rows.length) add(list, 'p', '本次检查范围内暂无匹配记录。');
      info.textContent = `${page+1}/${Math.max(1,Math.ceil(rows.length/10))} 页 · ${rows.length} 项`;
      prev.disabled = page===0; next.disabled = (page+1)*10>=rows.length;
      listUpdate.finish();
    };
    filter.onchange = query.oninput = () => { view.status=filter.value; view.query=query.value; page=0; draw(); };
    prev.onclick = () => { page--; draw(); }; next.onclick = () => { page++; draw(); };
    add(panel,'p',data.retention_notice).className = 'scope-note';
    // Select values only take effect after their options are attached.
    update.finish();
    filter.value = view.status; query.value = view.query;
    draw();
  },
  renderLiveRoom(snapshot, formatTime) {
    this.renderClarifications(snapshot.clarifications, formatTime, snapshot.recap !== true && snapshot.task?.kind !== 'video');
    const panel = document.getElementById("live-room");
    if (!panel) return;
    const room = snapshot.live_room;
    panel.hidden = !room || room.status === "not_collected";
    if (panel.hidden) return;
    const signature = JSON.stringify([room, snapshot.comment_summary, snapshot.sales_state?.timeline, snapshot.recap, formatTime?.(0)]);
    if (panel.dataset.signature === signature) return;
    panel.dataset.signature = signature;
    const rangeValue = panel.querySelector(".room-range")?.value || "all";
    const firstRender = !panel.querySelector("details");
    const opened = new Set(Array.from(panel.querySelectorAll("details[open]"), d => d.dataset.key));
    const update = this.domUpdate(panel), add = update.add;
    const time = formatTime || (ms => {
      const sec = Math.floor(ms / 1000);
      return [Math.floor(sec / 3600), Math.floor(sec / 60) % 60, sec % 60].map(v => String(v).padStart(2, "0")).join(":");
    });
    const labels = {connecting:"连接中", connected:"采集中", reconnecting:"重连中", stale:"数据暂未更新", stopped:"采集已停止", unavailable:"暂不可用", unsupported:"此来源暂不支持"};
    add(panel, "h3", "在线观众与评论");
    const summary = snapshot.comment_summary;
    if (summary && snapshot.recap !== true) {
      const grid = add(panel, 'div', '', 'room-comment-summary');
      const addList = (key, title) => {
        const section = add(grid, 'section', '', '', key);
        const heading = add(section, 'h4', title);
        heading.id = 'room-' + key + '-heading';
        const list = add(section, 'div', '', 'room-summary-list');
        list.tabIndex = 0;
        list.setAttribute('role', 'region');
        list.setAttribute('aria-labelledby', heading.id);
        return list;
      };
      const questions = addList('categories', '评论问题归类');
      if (Array.isArray(summary.products)) {
        for (const product of summary.products) {
          const group = add(questions, 'div', '', 'room-question-product', product.product);
          const heading = add(group, 'h5', '', 'room-product-heading');
          add(heading, 'span', product.product || '商品待确认');
          add(heading, 'small', `${product.count} 条提问`);
          for (const topic of product.topics) {
            const row = add(group, 'div', '', 'room-summary-row', JSON.stringify([topic.offer, topic.label]));
            add(row, 'span', [topic.offer, topic.label].filter(Boolean).join(' · '));
            add(row, 'strong', `${topic.count} 条`);
            for (const quote of topic.quotes) add(row, 'small', `“${quote}”`);
          }
        }
      } else {
        for (const item of summary.categories || []) {
          const row = add(questions, 'div', '', 'room-summary-row', item.label);
          add(row, 'span', item.label); add(row, 'strong', `${item.count} 个问题`);
          if (item.topics.length) add(row, 'small', item.topics.join('、'));
        }
      }
      if (!(summary.products ?? summary.categories)?.length) add(questions, 'p', '暂无已归类的问题', 'room-note');
      if (summary.purchase_requests) {
        const requests = addList('purchases', '观众点名求购');
        const relations = {current:'当前讲解商品', other:'其他商品', unknown:'商品归属待确认'};
        for (const item of summary.purchase_requests) {
          const row = add(requests, 'div', '', 'room-summary-row', JSON.stringify([item.name,item.relation]));
          add(row, 'span', item.name); add(row, 'strong', `${item.count} 条求购评论`);
          add(row, 'small', relations[item.relation] || relations.unknown);
        }
        if (!summary.purchase_requests.length) add(requests, 'p', '暂无已识别的点名求购', 'room-note');
      }
    }
    const metrics = add(panel, "div", "", "room-metrics");
    const stopped = room.status === 'stopped';
    for (const [label, value, unit] of [[stopped ? "最后采样" : "当前在线",stopped ? room.latest?.count : room.current,"人"],["采样峰值",room.peak,"人"],["已收评论",room.comment_count,"条"]]) {
      const metric = add(metrics,"div","","room-metric",label);
      add(metric,"span",label); add(metric,"strong",value ?? "未知"); add(metric,"small",value == null ? "" : unit);
      if (label === "最后采样" && room.latest) add(metric, "span", time(room.latest.start_ms), "sample-time");
    }
    add(panel,"p",labels[room.status] || "状态未知","room-note");
    if (room.latest && !stopped) add(panel, "p", `最近人数记录：${room.latest.count} 人（${time(room.latest.start_ms)}）`, "room-note");
    if (room.last_error && ["reconnecting", "stale", "unavailable"].includes(room.status)) {
      const failures = {dns_error:"域名解析失败", tls_error:"连接证书错误", network_timeout:"连接超时", protocol_error:"响应无法解析", connection_error:"连接中断", process_start_failed:"采集进程未启动"};
      add(panel, "p", `${failures[room.last_error.kind] || "评论采集异常"}${room.last_error.http_status ? `（HTTP ${room.last_error.http_status}）` : ""}；不影响字幕和画面审核。`, "room-note");
    }
    const fold = (key, label) => {
      const node = add(panel, "details", "", "", key); node.dataset.key = key;
      node.open = opened.has(key); add(node, "summary", label); return node;
    };
    const select = (parent, cls, value, options) => {
      const node = add(parent, "select", "", cls);
      for (const [key, label] of options) {
        const option = add(node, "option", label, "", key); option.value = key;
        option.selected = key === value;
      }
      node.value = value; return node;
    };
    const refresh = () => {
      panel.dataset.signature = "";
      this.renderLiveRoom(snapshot, formatTime);
    };
    const allSamples = room.samples || [], allBuckets = room.comment_buckets || [];
    if (allSamples.length || allBuckets.length) {
      const box = fold("audience", "人气与互动趋势");
      if (firstRender) box.open = true;
      const controls = add(box,"div","","room-controls room-chart-controls");
      const legend = add(controls,"div","","room-chart-legend");
      add(legend,"span","在线人数 · 左轴","room-legend-audience");
      add(legend,"span","已收评论 / 分钟 · 右轴","room-legend-comments");
      const range = select(controls,"room-range",rangeValue,[["all","全部记录"],["15m","最近15分钟"],["5m","最近5分钟"]]);
      range.setAttribute("aria-label","趋势时间范围"); range.onchange = refresh;
      const chart = add(box,"div","","room-chart");
      const tooltip = add(chart,"div","","room-chart-tooltip");
      tooltip.hidden = true; tooltip.setAttribute("role","status");
      const svg = add(chart,"svg:svg","");
      svg.setAttribute("viewBox","0 0 900 270"); svg.setAttribute("role","img");
      svg.setAttribute("aria-label","在线人数折线与每分钟已收评论柱状图；左轴人数，右轴评论条数，人数缺口不连线");
      const end = Math.max(allSamples.at(-1)?.start_ms || 0, (allBuckets.at(-1)?.start_ms ?? -60000)+60000);
      const earliest = Math.min(allSamples[0]?.start_ms ?? Infinity,allBuckets[0]?.start_ms ?? Infinity);
      const windowMs = rangeValue === "15m" ? 900000 : rangeValue === "5m" ? 300000 : null;
      const start = Math.max(earliest,windowMs ? end-windowMs : earliest);
      const samples = allSamples.filter(s=>s.start_ms>=start);
      const buckets = allBuckets.filter(s=>s.start_ms+60000>start);
      const niceMax = value => { const step=10**Math.floor(Math.log10(Math.max(1,value)/5)); return 5*Math.max(1,[1,2,2.5,5,10].find(n=>n*step>=value/5)*step); };
      const peak = niceMax(Math.max(1,...samples.map(s=>s.count)));
      const commentPeak = niceMax(Math.max(1,...buckets.map(s=>s.count)));
      const x = ms => 62+776*(ms-start)/Math.max(1000,end-start), y = count => 216-176*count/peak;
      for (let i=0;i<=5;i++) {
        const line=add(svg,"svg:line","","",`grid:${i}`), at=40+i*176/5;
        for (const [key,value] of Object.entries({x1:62,x2:838,y1:at,y2:at,stroke:"#edf1f7","stroke-dasharray":"3 5"})) line.setAttribute(key,String(value));
        for (const [side,pos,max] of [["left",50,peak],["right",850,commentPeak]]) {
          const label=add(svg,"svg:text",String(max*(5-i)/5),"",`${side}:${i}`);
          label.setAttribute("x",String(pos)); label.setAttribute("y",String(at+4));
          label.setAttribute("text-anchor",side==="left" ? "end" : "start"); label.setAttribute("class","room-axis-label");
        }
      }
      for (let i=0;i<=4;i++) {
        const tick=add(svg,"svg:text",time(start+(end-start)*i/4),"",`time:${i}`);
        tick.setAttribute("x",String(62+776*i/4)); tick.setAttribute("y","246");
        tick.setAttribute("text-anchor",i===0 ? "start" : i===4 ? "end" : "middle"); tick.setAttribute("class","room-axis-label");
      }
      const productAt = ms => {
        const period=(snapshot.sales_state?.timeline || []).find(p=>p.start_ms<=ms && ms<p.end_ms);
        return period?.status==='known' && period.product ? period.product
          : period?.scene==='chat' ? '闲聊' : period?.status==='none' ? '其他非商品内容' : '商品未确认';
      };
      const commentAt = ms => allBuckets.find(b=>b.start_ms<=ms && ms<b.start_ms+60000)?.count || 0;
      const describe = sample => `${time(sample.start_ms)}\n在线 ${sample.count} 人\n该分钟已收评论 ${room.comment_buckets ? commentAt(sample.start_ms)+' 条' : '未提供统计'}\n正在介绍：${productAt(sample.start_ms)}`;
      const show = (text,event,anchor) => {
        tooltip.textContent=text; tooltip.hidden=false;
        const bounds=chart.getBoundingClientRect(), target=anchor?.getBoundingClientRect();
        const px=Number.isFinite(event?.clientX) ? event.clientX : target.left+target.width/2;
        const py=Number.isFinite(event?.clientY) ? event.clientY : target.top;
        const size=tooltip.getBoundingClientRect(), scroll=chart.scrollLeft || 0;
        const width=chart.clientWidth || bounds.width, height=chart.clientHeight || bounds.height;
        const x=px-bounds.left+scroll, y=py-bounds.top;
        let left=x+14, top=y-size.height-14;
        if(left+size.width>scroll+width-8) left=x-size.width-14;
        if(top<8) top=y+14;
        tooltip.style.left=`${Math.max(scroll+8,Math.min(left,scroll+width-size.width-8))}px`;
        tooltip.style.top=`${Math.max(8,Math.min(top,height-size.height-8))}px`;
      };
      for (const bucket of buckets) {
        const bar=add(svg,"svg:rect","","",`comments:${bucket.start_ms}`);
        const left=x(Math.max(start,bucket.start_ms)), right=x(Math.min(end,bucket.start_ms+60000));
        const height=176*bucket.count/commentPeak, width=Math.max(1,Math.min(28,right-left-3));
        for (const [key,value] of Object.entries({x:(left+right-width)/2,y:216-height,width,height,rx:3,fill:"#9b8afb","fill-opacity":.42,tabindex:0})) bar.setAttribute(key,String(value));
        const text=`${time(bucket.start_ms)}–${time(bucket.start_ms+60000)}\n已收评论 ${bucket.count} 条`;
        bar.setAttribute("aria-label",text);
        bar.onpointerenter=bar.onpointermove=bar.onfocus=bar.onclick=event=>show(text,event,bar);
        bar.onblur=()=>{tooltip.hidden=true;};
      }
      let group=[];
      const draw=()=>{
        if (!group.length) return;
        const area=add(svg,"svg:polygon","");
        area.setAttribute("points",`${group[0].split(',')[0]},216 ${group.join(' ')} ${group.at(-1).split(',')[0]},216`);
        area.setAttribute("fill","#4080ff"); area.setAttribute("fill-opacity","0.07"); area.setAttribute("pointer-events","none");
        const line=add(svg,"svg:polyline","");
        for (const [key,value] of Object.entries({points:group.join(' '),fill:"none",stroke:"#4080ff","stroke-width":2.5,"stroke-linejoin":"round","stroke-linecap":"round","pointer-events":"none"})) line.setAttribute(key,String(value));
        group=[];
      };
      samples.forEach((sample,i)=>{
        if(i && sample.start_ms-samples[i-1].start_ms>30000) draw();
        group.push(`${x(sample.start_ms)},${y(sample.count)}`);
      }); draw();
      samples.forEach((sample,i)=>{
        const edge = !i || i===samples.length-1 || sample.start_ms-samples[i-1].start_ms>30000 || samples[i+1].start_ms-sample.start_ms>30000;
        const point=add(svg,"svg:circle","","",`sample:${sample.start_ms}`);
        for (const [key,value] of Object.entries({cx:x(sample.start_ms),cy:y(sample.count),r:edge?3:0,fill:"#4080ff",tabindex:0})) point.setAttribute(key,String(value));
        point.setAttribute("aria-label",describe(sample));
        point.onpointerenter=point.onfocus=point.onclick=event=>show(describe(sample),event,point);
        point.onblur=()=>{tooltip.hidden=true;};
      });
      svg.onpointermove=event=>{
        if(event.target?.tagName?.toLowerCase()==='rect') return;
        const rect=svg.getBoundingClientRect(); if(!rect.width || !samples.length) return;
        const pos=(event.clientX-rect.left)*900/rect.width;
        if(pos<62 || pos>838) {tooltip.hidden=true;return;}
        const ms=start+(pos-62)/776*(end-start);
        const closest=samples.reduce((best,s)=>Math.abs(s.start_ms-ms)<Math.abs(best.start_ms-ms)?s:best);
        if(Math.abs(closest.start_ms-ms)>30000){tooltip.hidden=true;return;}
        show(describe(closest),event);
      };
      chart.onscroll=svg.onpointerleave=()=>{tooltip.hidden=true;};
      add(box,"p",`展示 ${samples.length}/${allSamples.length} 个在线采样点；评论按本地接收分钟统计${stopped ? '。' : '，当前分钟持续累计。'}人数缺口不连线，未收到评论不代表无人发言。${room.comment_buckets ? '' : '此历史数据未提供评论趋势。'}`,"room-note");
    } else add(panel,"p",stopped ? "未记录到人数或评论趋势。" : "等待在线人数或评论记录。","room-note");
    update.finish();
  },
  answerMatchingEnabled: false,
  renderSalesState(snapshot, formatTime) {
    const panel = document.getElementById("sales-state");
    if (!panel) return;
    const sales = snapshot.sales_state || {};
    const optimization = snapshot.interaction_optimization;
    const hasInteraction = (optimization?.personalized?.question_count || 0) > 0;
    panel.hidden = !sales?.observed_segments && !sales?.timeline?.length && !(this.answerMatchingEnabled && (snapshot.qa?.length || hasInteraction));
    if (panel.hidden) return;
    const signature = JSON.stringify([this.answerMatchingEnabled, sales, snapshot.qa, optimization, snapshot.qa_processing, formatTime?.(0)]);
    if (panel.dataset.signature === signature) return;
    panel.dataset.signature = signature;
    const expanded = new Set(Array.from(panel.querySelectorAll("details[open]"), node => node.dataset.key));
    const update = this.domUpdate(panel), add = update.add;
    add(panel, "h3", sales.timeline?.length || sales.observed_segments ? "内容时间轴" : "互动问答记录");
    const time = formatTime || (ms => {
      const seconds = Math.floor(ms / 1000);
      return [Math.floor(seconds / 3600), Math.floor(seconds / 60) % 60, seconds % 60].map(v => String(v).padStart(2, "0")).join(":");
    });
    if (!sales.timeline?.length && sales.observed_segments) add(panel, "p", sales.current ? `最近确认主推：${sales.current.product} · ${sales.current.offer || "套餐待确认"}（截至 ${time(sales.current_at_ms)}）` : "最近已审核片段的主推商品尚未确认或未在推介商品");
    if (sales.timeline?.length) {
      add(panel, "p", "按时间顺序横向浏览；时段按已审核片段估计。").className = "sales-timeline-note";
      const rail = add(panel, "ol", "", "sales-timeline");
      rail.className = "sales-timeline";
      rail.setAttribute('tabindex', '0');
      rail.setAttribute('aria-label', '内容时间轴，可横向滚动');
      for (const period of sales.timeline) {
        const row = add(rail, "li", "", "", period.start_ms);
        row.className = `sales-period sales-period-${period.status}`;
        const label = period.status === "known" ? period.product
          : period.scene === "chat" ? "闲聊" : period.status === "none" ? "其他非商品内容" : "内容待确认";
        add(row, "div", `${time(period.start_ms)}–${time(period.end_ms)}`).className = "sales-period-time";
        const card = add(row, "div", "");
        card.className = "sales-period-card";
        add(card, "div", label).className = "sales-period-title";
      }
    }
    if (!this.answerMatchingEnabled) { update.finish(); return; }
    const section = (key, label) => {
      const node = add(panel, "section", "", "", key);
      node.dataset.key = key;
      node.className = "qa-section";
      add(node, "h4", label);
      return node;
    };
    const renderRouting = () => {
      if (!hasInteraction) return;
      const personalized = optimization.personalized || {};
      const status = {answered:'已确认解答', partial:'有回复待确认', unanswered:'已检查，暂未找到回答', reply_detected:snapshot.qa_processing ? '部分回应' : '有回复待确认', pending:'待检查', evidence_unavailable:'证据不足，无法检查'};
      const routing = section('interaction-routing', `客服个案 · ${personalized.question_count || 0} 项`);
      routing.className = 'interaction-routing';
      const service = add(routing, 'section', '', '', 'customer-service-queue');
      service.dataset.key = 'customer-service-queue'; service.className = 'interaction-queue customer-service-queue';
      add(service, 'h5', `客服跟进队列 · ${personalized.question_count || 0} 项`);
      for (const item of personalized.items || []) {
        const row = add(service, 'div', '', '', item.id || `${item.author_id}:${item.question}`); row.className = 'interaction-case';
        add(row, 'strong', `${item.category_label || '个性化问题'} · ${status[item.status] || '待客服跟进'}`);
        add(row, 'p', `${item.author_nickname || '匿名观众'}：${item.question}`);
      }
      if (!(personalized.items || []).length) add(service, 'p', '暂无已识别的个性化订单、地址或售后个案。');
      add(service, 'p', '客服按订单、地址或售后条件核对；不要求主播在公开场合逐条答复。').className = 'interaction-queue-note';
    };
    for (const [key, label, questions] of [
      ["comment-questions", "评论区问题", (snapshot.qa || []).filter(q => q.source === "viewer_comment")],
      ["qa", "主播转述问答", (snapshot.qa || []).filter(q => q.source !== "viewer_comment")],
    ]) {
      if (!questions.length) continue;
      const statusOf = q => q.status || (q.answers?.length || q.answers_omitted ? "reply_detected" : "pending");
      const names = {pending:"待检查", unanswered:"已检查暂未找到回答", reply_detected:snapshot.qa_processing ? "部分回应" : "有回复待确认", answered:"已解答", evidence_unavailable:"证据不足无法检查"};
      const counts = Object.entries(names).map(([status, name]) => `${name} ${questions.filter(q => statusOf(q) === status).length}`).join(" · ");
      const qaPanel = section(key, `${label} · ${questions.length} 个问题 · ${counts}`);
      if (key === "comment-questions") add(qaPanel, "p", this.questionerLabel(this.questionerCounts(questions))).className = "qa-meta";
      const views = panel._qaViews ||= {};
      const view = views[key] ||= {page:0, query:'', status:'all', sort:'frequency', expanded:new Set()};
      const controls = add(qaPanel, 'div', ''); controls.className = 'room-controls qa-controls';
      const search = add(controls, 'input', ''); search.className = 'qa-query'; search.type = 'search';
      search.placeholder = '搜索问题、回答、用户或商品'; search.setAttribute('aria-label', `${label}关键词`); search.value = view.query;
      const select = (className, label, options, value) => {
        const node = add(controls, 'select', ''); node.className = className; node.setAttribute('aria-label', label);
        for (const [value, text] of options) add(node, 'option', text).value = value;
        node.value = value; return node;
      };
      const statusFilter = select('qa-filter', '回答状态', [['all','全部状态'], ...Object.entries(names)], view.status);
      const sort = select('qa-sort', '问题排序', [['frequency','高频优先'],['newest','最新优先'],['oldest','最早优先']], view.sort);
      const list = add(qaPanel, 'div', '', 'qa-list'); update.retain(list);
      list.setAttribute('aria-label', `${label}列表`);
      const pager = add(qaPanel, 'div', ''); pager.className = 'qa-pager';
      const previous = add(pager, 'button', '上一页'); previous.type = 'button'; previous.className = 'qa-prev';
      const pageInfo = add(pager, 'span', ''); pageInfo.className = 'qa-page-info'; pageInfo.setAttribute('aria-live', 'polite');
      const next = add(pager, 'button', '下一页'); next.type = 'button'; next.className = 'qa-next';
      if (snapshot.qa_total > (snapshot.qa || []).length) add(qaPanel, 'p', `本页数据为已载入的 ${(snapshot.qa || []).length}/${snapshot.qa_total} 项问答，筛选不覆盖未载入记录。`).className = 'qa-meta';
      const authors = new Map();
      for (const q of questions.slice().sort((a,b) => a.start_ms-b.start_ms)) {
        if (!q.author_id) continue;
        if (!authors.has(q.author_id)) authors.set(q.author_id, []);
        authors.get(q.author_id).push(q);
      }
      const renderQuestion = (question, parent, add) => {
        const card = add(parent, "article", "", "", question.id);
        card.className = `qa-card qa-row${view.expanded.has(question.id) ? ' qa-expanded' : ''}`;
        card.dataset.key = `qa-${question.id}`;
        const questionCell = add(card, 'div', ''); questionCell.className = 'qa-question-cell';
        const answerCell = add(card, 'div', ''); answerCell.className = 'qa-answer-cell';
        const turn = (item, kind, label, content, received) => {
          const row = add(kind === "question" ? questionCell : answerCell, "div", "", "", item.id || `${item.start_ms}:${kind}:${item.source || ""}`); row.className = `qa-turn qa-turn-${kind}`;
          const clock = add(row, "div", ""); clock.className = "qa-time";
          add(clock, "span", Number.isFinite(item.start_ms) ? time(item.start_ms) : "时间未采集");
          if (received) add(clock, "small", "接收时间");
          const body = add(row, "div", ""); body.className = "qa-turn-body";
          add(body, "span", label).className = `qa-role qa-role-${kind}`;
          add(body, "p", content).className = "qa-content";
          return body;
        };
        const body = turn(question, "question", question.source === "viewer_comment" ? "问 · 观众提问" : "问 · 主播转述", question.question, question.source === "viewer_comment");
        const meta = add(body, "div", ""); meta.className = "qa-meta";
        add(meta, "span", names[statusOf(question)] || "待确认").className = `qa-status qa-status-${statusOf(question)}`;
        if (question.coverage_gap) add(answerCell, 'p', question.coverage_gap).className = 'qa-meta';
        if (question.source === "viewer_comment") {
          add(meta, "span", this.commentAuthor(question));
        }
        if (question.product) add(meta, "span", `提问时商品：${question.product} · ${question.offer || "套餐待确认"}`).className = 'qa-extra';
        if (question.group_question) add(meta, 'span', question.group_question).className = 'qa-extra';
        if (question.topic_explanation) {
          const explanation = question.topic_explanation;
          const info = add(answerCell, 'details', ''); info.className = 'qa-topic-explanation';
          add(info, 'summary', `主题已讲解 · ${time(explanation.start_ms)}${statusOf(question) === 'answered' ? '' : ' · 此提问尚未确认解答'}`);
          add(info, 'p', explanation.text);
        }
        for (const answer of question.answers || []) {
          const comment = answer.source === "room_comment";
          const label = comment ? `${answer.author_role === "host" ? "主播" : "管理员"}评论回复` : "主播口播回答";
          const answerBody = turn(answer, "answer", `答 · ${label}`, answer.text, comment);
          if (comment) add(answerBody, "div", answer.author_nickname || "昵称未采集").className = "qa-meta";
        }
        if (question.answers?.length > 1) add(answerCell, 'p', `另有 ${question.answers.length - 1} 条回答，点击详情查看。`).className = 'qa-more-answers';
        if (question.answers_omitted) add(answerCell, "p", `部分回答不在本次证据范围（${question.answers_omitted} 条），此处未展示原文。`).className = "qa-empty-answer";
        else if (!question.answers?.length) add(answerCell, "p", statusOf(question) === "answered" ? "答 · 已确认解答，本次未展示回答原文。" : statusOf(question) === "unanswered" ? `答 · 已检查${question.checked_through_ms != null ? `至 ${time(question.checked_through_ms)}` : ""}，暂未找到回答。` : "答 · 等待检查，不能据此判定主播未回答。").className = "qa-empty-answer";
        if (question.source === "viewer_comment") {
          const thread = authors.get(question.author_id) || [];
          if (thread.length > 1) {
            const related = add(questionCell, "div", ""); related.className = "qa-related qa-extra";
            add(related, "strong", `同一观众的其他提问 · ${thread.length-1} 项`);
            add(related, "p", "仅按本场身份关联；是否为同一商品的追问需核对内容，各题独立判断解答状态。");
            if (thread.length > 3) add(related, "p", "这里仅展开相邻提问，其他问题仍保留在各自分类中。");
            const index = thread.indexOf(question);
            for (const q of [thread[index-1],thread[index+1]].filter(Boolean)) {
              add(related, "p", `${time(q.start_ms)} · ${q.question} · ${names[statusOf(q)]}`);
            }
          }
        }
        const toggle = add(card, 'button', view.expanded.has(question.id) ? '收起' : '详情');
        toggle.type = 'button'; toggle.className = 'qa-expand';
        toggle.setAttribute('aria-label', `查看问答详情：${question.question}`);
        toggle.setAttribute('aria-expanded', String(view.expanded.has(question.id)));
        toggle.onclick = () => {
          if (view.expanded.has(question.id)) view.expanded.delete(question.id); else view.expanded.add(question.id);
          const open = view.expanded.has(question.id);
          card.className = `qa-card qa-row${open ? ' qa-expanded' : ''}`;
          toggle.textContent = open ? '收起' : '详情'; toggle.setAttribute('aria-expanded', String(open));
        };
      };
      const groups = new Map();
      for (const question of questions) {
        const id = question.group_id || question.id;
        if (!groups.has(id)) groups.set(id, {id, items:[], comments:new Set(), latest:0});
        const group = groups.get(id);
        group.items.push(question);
        for (const ref of question.evidence_ids || []) group.comments.add(ref);
        group.latest = Math.max(group.latest, question.start_ms || 0);
      }
      const ranked = [...groups.values()].sort((a,b) => b.comments.size-a.comments.size || b.latest-a.latest || a.id.localeCompare(b.id)).flatMap(group => group.items);
      const renderList = () => {
        const query = view.query.trim().toLocaleLowerCase();
        const filtered = ranked.filter(q => (view.status === 'all' || statusOf(q) === view.status) &&
          (!query || [q.question, q.group_question, q.author_nickname, q.product, q.offer, ...(q.answers || []).map(a => a.text)].join(' ').toLocaleLowerCase().includes(query)));
        if (view.sort !== 'frequency') filtered.sort((a,b) => view.sort === 'oldest' ? a.start_ms-b.start_ms : b.start_ms-a.start_ms);
        const visibleGroups = new Map();
        for (const q of filtered) {
          const id = q.group_id || q.id;
          if (!visibleGroups.has(id)) visibleGroups.set(id, []);
          visibleGroups.get(id).push(q);
        }
        const grouped = [...visibleGroups.entries()];
        const pages = Math.max(1, Math.ceil(grouped.length / 10));
        view.page = Math.min(view.page, pages - 1);
        const listUpdate = this.domUpdate(list), add = listUpdate.add;
        for (const [id, items] of grouped.slice(view.page * 10, (view.page + 1) * 10)) {
          if (items.length === 1) { renderQuestion(items[0], list, add); continue; }
          const group = add(list, 'details', '', '', `group:${id}`); group.className = 'qa-group';
          const groupKey = `group:${id}`;
          const answered = items.filter(q => statusOf(q) === 'answered').length;
          add(group, 'summary', `${items[0].group_question || items[0].question} · ${this.questionerLabel(this.questionerCounts(items))} · ${items.some(q => q.topic_explanation) ? '主题已讲解' : '主题未确认讲解'} · 具体提问已解答 ${answered}/${items.length} 项`);
          const body = add(group, 'div', ''); listUpdate.retain(body);
          const expand = () => {
            if (group.open) {
              view.expanded.add(groupKey);
              const bodyUpdate = this.domUpdate(body);
              for (const q of items) renderQuestion(q, body, bodyUpdate.add);
              bodyUpdate.finish();
            } else view.expanded.delete(groupKey);
          };
          group.open = view.expanded.has(groupKey); expand(); group.ontoggle = expand;
        }
        if (!filtered.length) add(list, 'p', '没有符合筛选条件的问题。');
        pageInfo.textContent = `第 ${view.page + 1}/${pages} 页 · 筛选 ${filtered.length}/${questions.length} 项 · ${grouped.length} 类 · 每页 10 类`;
        previous.disabled = view.page === 0; next.disabled = view.page >= pages - 1;
        listUpdate.finish();
      };
      search.oninput = () => { list.scrollTop = 0; view.query = search.value; view.page = 0; renderList(); };
      statusFilter.onchange = () => { list.scrollTop = 0; view.status = statusFilter.value; view.page = 0; renderList(); };
      sort.onchange = () => { list.scrollTop = 0; view.sort = sort.value; view.page = 0; renderList(); };
      previous.onclick = () => { list.scrollTop = 0; if (view.page > 0) { view.page--; renderList(); } };
      next.onclick = () => { list.scrollTop = 0; if (!next.disabled) { view.page++; renderList(); } };
      renderList();
      const note = add(qaPanel, "details", ""); note.className = "qa-note";
      note.dataset.key = `${key}-scope`; note.open = expanded.has(note.dataset.key);
      add(note, "summary", "问答识别口径");
      add(note, "p", "已解答表示找到明确对应的口播或主播、管理员评论，不代表承诺已核实或观众已满意；待检查表示处理尚未完成；已检查暂未找到回答仅描述已检查的证据范围。部分回应不计完整解答。身份未确认的评论不算助播回答，历史未采集身份的回复可能遗漏。频次不等于独立观众人数或全量评论频次。");
      if (key === "comment-questions") add(note, "p", snapshot.qa_processing ? "评论与答案独立分批处理；晚识别的问题会回查提问之后的历史字幕和已确认运营回复。已检查范围不包含采集缺失的内容。" : "历史任务仅有待答记录时，无法区分尚未检查与未找到回答；不据此计算主播漏答。");
    }
    renderRouting();
    update.finish();
  },
  mediaTime(seconds, timeline) {
    if (!timeline?.length) return seconds;
    const at = seconds * 1000;
    const span = timeline.find((s) => at >= s.start_ms && at < s.end_ms);
    return span
      ? (span.media_start_ms +
          Math.min(
            at - span.start_ms,
            span.media_end_ms - span.media_start_ms,
          )) /
          1000
      : null;
  },
};
document.addEventListener("click", (event) => {
  const trigger = event.target.closest("[data-preview]");
  if (trigger)
    window.LiteUI.preview(
      trigger.dataset.preview,
      trigger.querySelector("img")?.alt,
      trigger,
    );
});
