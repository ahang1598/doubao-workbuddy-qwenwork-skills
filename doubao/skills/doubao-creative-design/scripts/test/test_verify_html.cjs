#!/usr/bin/env node
'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const os=require('node:os');
const path=require('node:path');
const {spawnSync}=require('node:child_process');
const {chromium}=require('playwright');
const launch=chromium.launch.bind(chromium);
const browserExecutable=process.env.CREATIVE_DESIGN_BROWSER||[
  '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge',
  '/Applications/Chromium.app/Contents/MacOS/Chromium',
  '/usr/bin/google-chrome',
  '/usr/bin/chromium',
  '/usr/bin/chromium-browser',
].find(candidate=>fs.existsSync(candidate));
chromium.launch=async options=>{
  const browser=await launch({...options,...(browserExecutable?{executablePath:browserExecutable}:{})}),newContext=browser.newContext.bind(browser);
  browser.newContext=async options=>{
    const context=await newContext(options);
    await context.route('**/*',route=>new URL(route.request().url()).hostname==='html-check.invalid'?route.continue():route.abort());
    return context;
  };
  return browser;
};
const {verify,parseArgs}=require('../maintenance/verify-html.cjs');
const source=fs.readFileSync(path.join(__dirname,'../../example/html-validation.html'),'utf8');
const tmp=fs.mkdtempSync(path.join(os.tmpdir(),'html-qa-tests-'));
let count=0;
function replace(s,a,b){assert.ok(s.includes(a),a);return s.replace(a,b);}
async function check(name,html,expected,longPage=false,fontContract,options={}) {
  const htmlPath=path.join(tmp,name+'.html');
  fs.writeFileSync(htmlPath,html);
  const contractPath=path.join(tmp,name+'.fonts.json');
  if(fontContract)fs.writeFileSync(contractPath,JSON.stringify(fontContract));
  const report=await verify({html:htmlPath,longPage,fontContract:fontContract?contractPath:undefined,root:'body > main',timeout:5000,tolerance:1,allowInteraction:false,...options});
  const codes=[...report.errors,...report.views.flatMap(v=>v.errors)].map(e=>e.code);
  if(expected===null)assert.equal(report.status,'pass',`${name}: ${JSON.stringify(codes)}`);
  else assert.ok(codes.includes(expected),`${name}: missing ${expected}, got ${JSON.stringify(codes)}`);
  if(!fontContract) {
    assert.equal(report.font_validation.status,'unverified');
    assert.ok(report.unverified.some(s=>s.includes('no font-contract')));
  }
  count++;console.log(`PASS ${name}`);
  return report;
}
(async()=>{
  // Regression: a complete local fixture must not fail solely due to file-origin navigation events.
  await check('valid-local-source',source,null);
  await check('mixed-text-in-safe-area',source.replace('<div data-canvas-bottom-safe-area','<p id="mixed" style="position:absolute;left:10px;top:600px;width:100px;height:20px;margin:0;font-size:16px;line-height:20px">Test<span></span></p><div data-canvas-bottom-safe-area'),'TEXT_IN_BOTTOM_SAFE_AREA');
  await check('aria-hidden-text-in-safe-area',source.replace('<div data-canvas-bottom-safe-area','<p aria-hidden="true" style="position:absolute;left:10px;top:600px;width:100px;height:20px;margin:0;font-size:16px;line-height:20px">Test<span></span></p><div data-canvas-bottom-safe-area'),'TEXT_IN_BOTTOM_SAFE_AREA');
  await check('nested-safe-area',source.replace('<div data-canvas-bottom-safe-area','<section><div data-canvas-bottom-safe-area').replace('height:72px;width:480px;"></div>','height:72px;width:480px;"></div></section>'),'HTML_BOTTOM_SAFE_AREA_MISSING');
  await check('brief-size-mismatch',source,'BRIEF_CANVAS_MISMATCH',false,undefined,{expectedWidth:480,expectedHeight:641});
  const bound=await check('brief-size-match',source,null,false,undefined,{expectedWidth:480,expectedHeight:640});
  assert.equal(bound.source_sha256,require('node:crypto').createHash('sha256').update(source).digest('hex'));
  assert.deepEqual(bound.expected_canvas,{width:480,height:640});

  await check('empty-box-over-safe-text-above',source.replace('id="headline" style="','id="headline" style="min-height:630px;'),null);
  await check('unmapped-viewport-drift',source.replace('</main>','<div style="position:fixed;left:10%;top:10px;width:60px;height:30px">A</div></main>').replace('<div data-canvas-bottom-safe-area', '<div data-canvas-bottom-safe-area'),'VIEWPORT_ELEMENT_DRIFT');
  await check('root-cropping-still-forbidden',source.replace('display:flow-root;','display:flow-root;overflow:hidden;'),'CANVAS_ROOT_CLIPPING');
  await check('clip-path-hidden-text',source.replace('id="headline" style="','id="headline" style="clip-path:inset(100%);'),'TEXT_CLIPPED');
  await check('clip-path-safe-text',source.replace('id="headline" style="','id="headline" style="clip-path:inset(0);'),null);
  await check('clip-path-transformed-text',source.replace('id="headline" style="','id="headline" style="transform:scale(.9);clip-path:inset(0);'),'TEXT_CLIP_UNVERIFIED');
  await check('safe-area-image',source.replace('height:72px;width:480px;"></div>','height:72px;width:480px;"><img alt="content" src="'+source.match(/src="([^"]+)"/)[1]+'" style="width:40px;height:40px;"></div>'),'HTML_BOTTOM_SAFE_AREA_MISSING');
  await check('image-overlaps-safe-area',source.replace('top:128px;','top:520px;').replace('height:160px;z-index:1;','height:100px;z-index:1;'),'HTML_BOTTOM_SAFE_AREA_MISSING');

  fs.writeFileSync(path.join(tmp,'local.svg'),'<svg xmlns="http://www.w3.org/2000/svg" width="160" height="160"><circle cx="80" cy="80" r="60" fill="red"/></svg>');
  await check('missing-bottom-safe-area',source.replace('data-canvas-bottom-safe-area="72"','data-missing="72"'),'HTML_BOTTOM_SAFE_AREA_MISSING');
  await check('hidden-bottom-safe-area',source.replace('height:72px;width:480px;','display:none;height:72px;width:480px;'),'HTML_BOTTOM_SAFE_AREA_MISSING');
  await check('absolute-bottom-safe-area',source.replace('height:72px;width:480px;','position:absolute;bottom:0;height:72px;width:480px;'),'HTML_BOTTOM_SAFE_AREA_MISSING');
  await check('content-after-bottom-safe-area',source.replace('</main>','<div>extra</div></main>'),'HTML_BOTTOM_SAFE_AREA_MISSING');
  await check('undersized-bottom-safe-area',source.replace('data-canvas-bottom-safe-area="72"','data-canvas-bottom-safe-area="10"'),'HTML_BOTTOM_SAFE_AREA_MISSING');
  await check('relative-local-image',source.replace(/src="[^"]+"/,'src="local.svg"'),null);
  await check('clipped-text',replace(source,'height:144px;margin:0','height:20px;overflow:hidden;margin:0'),'TEXT_CLIPPED');
  await check('broken-image',source.replace(/src="[^"]+"/,'src="missing-image.png"'),'IMAGE_NOT_LOADED');
  const legalWebFont='<style data-web-fonts>@font-face{font-family:"AuditUnused";src:url(data:font/woff2;base64,d09GMg==) format("woff2");font-weight:400;font-style:normal}</style>';
  await check('legal-web-font-style',replace(source,'</head>',legalWebFont+'</head>'),null);
  await check('multiple-web-font-styles',replace(source,'</head>',legalWebFont+legalWebFont+'</head>'),'WEB_FONT_STYLE_BLOCK_INVALID');
  await check('selector-in-web-font-style',replace(source,'</head>','<style data-web-fonts>body{color:red}</style></head>'),'WEB_FONT_STYLE_BLOCK_INVALID');
  await check('noninline-styles',replace(source,'</head>','<style>p{color:red}</style></head>'),'STYLESHEET');
  await check('viewport-dimension',replace(source,'position:relative;width:480px','position:relative;width:90vw'),'CANVAS_SIZE');
  await check('hidden-text',replace(source,'id="headline" style="','id="headline" style="opacity:0;'),'HIDDEN_TEXT');
  await check('duplicate-element',replace(source,'id="footer"','id="headline"'),'DUPLICATE_DOM_ID');
  await check('background-asset-failure',replace(source,'background:rgba(255,255,255,0.45);','background:rgba(255,255,255,0.45);background-image:url(missing-background.png);'),'CSS_OR_SVG_IMAGE_NOT_LOADED');
  await check('unauthorized-script',replace(source,'</head>','<script>window.changed=true;</script></head>'),'SCRIPT_REQUIRES_AUTHORIZATION');
  await check('root-crop',replace(source,'<main style="','<main style="overflow:hidden;'),'CANVAS_ROOT_CLIPPING');
  await check('image-outside-canvas',replace(source,'left:260px','left:460px'),'ELEMENT_OUTSIDE_CANVAS');
  await check('image-ancestor-crop',replace(source,'<img id="alpha-shape"','<div style="position:absolute;left:0;top:0;width:300px;height:300px;overflow:hidden;"><img id="alpha-shape"').replace('<section id="glass-panel"','</div><section id="glass-panel"'),null);
  await check('local-decoration-crop',replace(source,'<img id="alpha-shape"','<div aria-hidden="true" style="position:absolute;left:0;top:0;width:300px;height:300px;overflow:hidden;"><img id="alpha-shape"').replace('<section id="glass-panel"','</div><section id="glass-panel"'),null);
  const missing=replace(source,"'PingFang SC'","'DefinitelyMissingReviewFont'");
  await check('missing-font-without-contract',missing,null);
  await check('missing-font-strict-contract',missing,'FONT_FAMILY_MISMATCH',false,{families:{DefinitelyMissingReviewFont:{source:'target_environment',availability:'verified'}}});
  const diagnostic=await check('font-diagnostic',source,null);
  const family=diagnostic.views[0].actualFonts[0].fonts.find(f=>f.glyphCount>0).familyName;
  const strict=await check('installed-font-strict-contract',replace(source,"'PingFang SC'",`'${family}'`),null,false,{families:{[family]:{source:'target_environment',availability:'verified'}}});
  assert.equal(strict.font_validation.status,'pass');
  const invalidContract=path.join(tmp,'invalid-font-contract.json');
  fs.writeFileSync(invalidContract,JSON.stringify({families:{[family]:{source:'local',availability:'verified'}}}));
  await assert.rejects(()=>verify({html:path.join(tmp,'valid-local-source.html'),fontContract:invalidContract}),/FONT_CONTRACT/);
  count++;console.log('PASS invalid-font-contract');
  const render=spawnSync('python3',[path.join(__dirname,'../maintenance/render_html.py'),path.join(__dirname,'../../example/html-validation.html'),path.join(tmp,'render.png')],{encoding:'utf8'});
  assert.equal(render.status,0,render.stderr);
  const png=fs.readFileSync(path.join(tmp,'render.png'));
  assert.equal(png.readUInt32BE(16),480);assert.equal(png.readUInt32BE(20),640);
  count++;console.log('PASS render-static-main');
  const mismatch=spawnSync('python3',[path.join(__dirname,'../maintenance/render_html.py'),path.join(__dirname,'../../example/html-validation.html'),path.join(tmp,'bad-render.png'),'--width','1440'],{encoding:'utf8'});
  assert.notEqual(mismatch.status,0);assert.match(mismatch.stderr,/RENDER_DIMENSIONS/);
  assert.equal(fs.existsSync(path.join(tmp,'bad-render.png')),false);
  count++;console.log('PASS render-size-mismatch');
  const longPath=path.join(tmp,'long.html'),longPNG=path.join(tmp,'long.png');
  fs.writeFileSync(longPath,source.replaceAll('640','8200').replace('</main>','<div style="position:absolute;left:0;top:8100px;width:480px;height:100px;background:rgb(255,0,0);"></div></main>'));
  const longRender=spawnSync('python3',[path.join(__dirname,'../maintenance/render_html.py'),longPath,longPNG],{encoding:'utf8'});
  assert.equal(longRender.status,0,longRender.stderr);
  const sharp=require('sharp'),metadata=await sharp(longPNG).metadata();
  assert.equal(metadata.width,480);assert.equal(metadata.height,8200);
  const pixel=await sharp(longPNG).extract({left:10,top:8190,width:1,height:1}).raw().toBuffer();
  assert.deepEqual([...pixel].slice(0,3),[255,0,0]);
  count++;console.log('PASS render-long-canvas-tail');
  assert.throws(()=>parseArgs(['--html',path.join(tmp,'valid-local-source.html'),'--out',path.join(tmp,'valid-local-source.html')]));count++;console.log('PASS source-overwrite-guard');
  const wrap=content=>'<!DOCTYPE html><html data-canvas-width="100" data-canvas-height="200" style="width:100px;height:200px;margin:0;padding:0;"><head><meta charset="UTF-8"></head><body style="width:100px;height:200px;margin:0;padding:0;"><main style="position:relative;display:flow-root;width:100px;height:200px;">'+content+'</main></body></html>';
  const sections='<section data-section-id="top" style="height:88px;width:100px;"><p style="margin:0;font-size:12px;line-height:20px;">First content</p></section><section data-section-id="bottom" style="height:88px;width:100px;"><p style="margin:0;font-size:12px;line-height:20px;">Next content</p></section>';
  const safe='<div data-canvas-bottom-safe-area="24" style="height:24px;width:100px;"></div>';
  const longSections=wrap(sections+safe);
  const longReport=await check('long-page-sections-and-safe-area',longSections,null,true);
  assert.equal(longReport.views[0].sections.length,2);
  await check('long-page-gap',longSections.replace('data-section-id="bottom" style="','data-section-id="bottom" style="margin-top:2px;'),'LONG_PAGE_SECTION_GAP_OR_OVERLAP',true);
  const fake=wrap('<section aria-hidden="true" data-section-id="one" style="position:absolute;top:0;height:176px;width:100px;"></section><p style="margin:0;height:176px;font-size:12px;">Unmapped text</p>'+safe);
  await check('fake-section-markers',fake,'LONG_PAGE_SECTION_CONTENT',true);
  await check('unmapped-content',longSections.replace('First content','First content').replace('</main>','<span style="position:absolute;top:0;left:0;">Outside</span></main>'),'LONG_PAGE_UNMAPPED_CONTENT',true);
  await check('long-page-missing-sections',source,'LONG_PAGE_SECTIONS_REQUIRED',true);
  console.log(`${count} checks passed; temporary fixtures: ${tmp}`);
})().catch(e=>{console.error(e.stack);process.exitCode=1;});
