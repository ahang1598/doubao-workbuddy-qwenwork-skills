import fs from 'node:fs';
import path from 'node:path';
import {parseArgs} from 'node:util';
import {loadConfig,skillDir,writeJSON,assert,shellHTML,cli} from './common.mjs';
import {isMain} from './media-utils.mjs';

function completeResources(project) {
  const resources=[['dist/gsap.min.js','gsap.min.js'],['README.md','GSAP-README.md']];
  const missing=resources.filter(([,name])=>!fs.existsSync(path.join(project,'vendor',name)));
  for(const [source] of missing)assert(fs.existsSync(path.join(skillDir,'node_modules/gsap',source)),'Install dependencies first: npm install --prefix <skill-dir>');
  fs.mkdirSync(path.join(project,'vendor'),{recursive:true});
  for(const [source,name] of missing)fs.copyFileSync(path.join(skillDir,'node_modules/gsap',source),path.join(project,'vendor',name));
  for(const [,name] of resources)assert(fs.statSync(path.join(project,'vendor',name)).isFile()&&fs.statSync(path.join(project,'vendor',name)).size>0,`Invalid project resource: vendor/${name}`);
  const packageFile=path.join(project,'package.json');
  if(!fs.existsSync(packageFile))writeJSON(packageFile,{private:true,scripts:{check:'npx hyperframes@0.8.38 check',preview:'npx hyperframes@0.8.38 preview',render:'npx hyperframes@0.8.38 render'}});
}

if(isMain(import.meta.url))cli(()=>{
  const {positionals,values:v}=parseArgs({allowPositionals:true,options:{effect:{type:'string',multiple:true}}});
  assert(positionals.length===1,'Usage: prepare.mjs plan.json [--effect id]');
  const {config:c,base}=loadConfig(positionals[0]);
  const selected=new Set(v.effect??c.effects.map(e=>e.id));
  for(const id of selected)assert(c.effects.some(e=>e.id===id),`Unknown effect: ${id}`);
  assert(c.planInfo,'Complete plan.json is required; complete pre-add planning first');
  for(const e of c.effects.filter(e=>selected.has(e.id))) {
    if(fs.existsSync(e.project)) {
      assert(fs.existsSync(path.join(e.project,'index.html'))&&fs.statSync(path.join(e.project,'index.html')).isFile(),`Existing project incomplete: ${e.project}; inspect it manually`);
      completeResources(e.project);
      console.error(`Preserved existing project: ${e.id}`);continue;
    }
    if(e.source) {
      assert(fs.statSync(e.source).isDirectory(),'Custom source must be a directory');
      assert(e.project!==e.source&&!e.project.startsWith(e.source+path.sep),'Source cannot contain destination');
    }
    fs.mkdirSync(path.dirname(e.project),{recursive:true});
    const staging=fs.mkdtempSync(path.join(path.dirname(e.project),`.${e.id}-prepare-`));
    try {
      if(e.source)fs.cpSync(e.source,staging,{recursive:true,filter:p=>!['node_modules','.git','renders','snapshots','.hyperframes'].includes(path.basename(p))});
      else fs.writeFileSync(path.join(staging,'index.html'),shellHTML(e,c,'<!-- AUTHOR_CUSTOM_EFFECT -->','',''));
      assert(fs.existsSync(path.join(staging,'index.html'))&&fs.statSync(path.join(staging,'index.html')).isFile(),'Custom source must contain index.html');
      completeResources(staging);
      fs.renameSync(staging,e.project);
    } finally {fs.rmSync(staging,{recursive:true,force:true});}
  }
  console.log(JSON.stringify({ok:true,taskDirectory:base,customAuthoringRequired:c.effects.filter(e=>selected.has(e.id)&&!e.source&&fs.readFileSync(path.join(e.project,'index.html'),'utf8').includes('AUTHOR_CUSTOM_EFFECT')).map(e=>e.id)}));
});
