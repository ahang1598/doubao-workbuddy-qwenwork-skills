"use strict";
const pendingSeeks = new WeakMap();
const renderJobs = new WeakMap();
// Native dialog provides focus containment and Esc; restore focus to its trigger.
window.LiteUI = {
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
    dialog.setAttribute("aria-label", "证据图片预览");
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
