// Keep authoring and measurement in source coordinates; crop only the render copy.
export const CANVAS_VERSION=1;
export function renderCanvas(e,c,html) {
  const full={x:0,y:0,width:c.videoInfo.width,height:c.videoInfo.height};
  const fallback=reason=>({...full,mode:'full',reason});
  if(!['auto','full'].includes(e.canvasMode??'auto'))throw new Error('canvasMode must be auto or full');
  const padding=e.canvasPadding??32;
  if(!Number.isFinite(padding)||padding<0||padding>1024)throw new Error('canvasPadding must be between 0 and 1024');
  if(e.canvasMode==='full')return fallback('requested');
  const b=e.plan?.motionBounds;
  if(!b)return fallback('missing-motion-bounds');
  if(![b.x,b.y,b.width,b.height].every(Number.isFinite)||b.x<0||b.y<0||b.width<=0||b.height<=0||b.x+b.width>full.width||b.y+b.height>full.height)throw new Error('Invalid motionBounds for local canvas');
  // Only the canonical shell is supported. Viewport-dependent styles/scripts need the original viewport.
  if(!html.includes('id="effect-clip"')||!html.includes('id="effect-stage"')||!/<div\b[^>]*id="root"[^>]*data-composition-id=/i.test(html)||!html.includes('</head>'))return fallback('unsupported-shell');
  if(/\b(?:innerWidth|innerHeight|clientWidth|clientHeight|matchMedia|ResizeObserver)\b|\b\d*\.?\d+(?:[sld]?v(?:w|h|min|max|i|b))\b|@media|container-type\s*:|position\s*:\s*(?:fixed|sticky)\b/i.test(html))return fallback('viewport-dependent');
  // Align to 16px where possible; padding is in addition to the complete planned motion bounds.
  const x=Math.max(0,Math.floor((b.x-padding)/16)*16),y=Math.max(0,Math.floor((b.y-padding)/16)*16);
  const right=Math.min(full.width,Math.ceil((b.x+b.width+padding)/16)*16),bottom=Math.min(full.height,Math.ceil((b.y+b.height+padding)/16)*16);
  const rect={x,y,width:right-x,height:bottom-y};
  return rect.width===full.width&&rect.height===full.height?fallback('full-coverage'):{...rect,mode:'local',reason:'motion-bounds'};
}
export function localCanvasHTML(html,canvas,source) {
  if(canvas.mode==='full')return html;
  const root=/<div\b[^>]*id="root"[^>]*>/i;
  html=html.replace(root,tag=>tag.replace(/data-width=(['"])[^'"]*\1/,`data-width="${canvas.width}"`).replace(/data-height=(['"])[^'"]*\1/,`data-height="${canvas.height}"`));
  return html.replace('</head>',`<style data-render-canvas="${CANVAS_VERSION}">
html,body,#root{width:${canvas.width}px!important;height:${canvas.height}px!important;overflow:hidden!important}
#effect-clip{position:absolute!important;inset:auto!important;left:${-canvas.x}px!important;top:${-canvas.y}px!important;width:${source.width}px!important;height:${source.height}px!important}
</style></head>`);
}
