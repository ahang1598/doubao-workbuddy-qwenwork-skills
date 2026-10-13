/* Aggregate → record list → record detail → original DingTalk record interaction. */
(function(global){
  'use strict';
  const text=value=>value==null?'':typeof value==='object'?JSON.stringify(value,null,2):String(value);
  const el=(tag,className,label)=>{const node=document.createElement(tag);if(className)node.className=className;if(label!=null)node.textContent=label;return node;};

  function create(config={}){
    const mode=config.mode||'local_only';
    if(!['full','local_only','aggregate_only'].includes(mode))throw new Error('Invalid drill-down mode');
    const root=el('div',`avd-root ${config.themeClass||''}`.trim());
    root.id=config.rootId||'avd-root';root.setAttribute('role','dialog');root.setAttribute('aria-modal','true');root.setAttribute('aria-hidden','true');
    const mask=el('div','avd-mask');const dialog=el('section','avd-dialog');const header=el('header','avd-header');
    const back=el('button','avd-icon-button avd-header-back','←');back.type='button';back.hidden=true;back.setAttribute('aria-label','返回记录列表');
    const title=el('h2','avd-title','明细');const close=el('button','avd-icon-button avd-close','×');close.type='button';close.setAttribute('aria-label','关闭明细');
    header.append(back,title,close);
    const listView=el('section','avd-view avd-list-view');const toolbar=el('div','avd-toolbar');const search=el('input','avd-search');
    search.type='search';search.placeholder='搜索当前记录';search.setAttribute('aria-label','搜索当前记录');const count=el('span','avd-list-count','0 条');toolbar.append(search,count);
    const tableWrap=el('div','avd-table-wrap');const table=el('table','avd-table');const thead=el('thead');const tbody=el('tbody');table.append(thead,tbody);tableWrap.append(table);listView.append(toolbar,tableWrap);
    const detailView=el('section','avd-view avd-detail-view');const detailBody=el('div','avd-detail-body');detailView.append(detailBody);
    dialog.append(header,listView,detailView);root.append(mask,dialog);document.body.append(root);

    let allRecords=[];let visibleRecords=[];let columns=config.columns||[];let detailFields=config.detailFields||columns;let listTitle='明细';let opener=null;let fallbackTimer=null;
    const event=(name,detail={})=>global.dispatchEvent(new CustomEvent(name,{detail}));
    const value=(record,key)=>record?.[key];
    const searchable=record=>(config.searchFields||columns).map(key=>text(value(record,key))).join(' ').toLowerCase();
    function setView(name){const detail=name==='detail';listView.classList.toggle('avd-active',!detail);detailView.classList.toggle('avd-active',detail);back.hidden=!detail;root.dataset.view=name;}
    function renderList(){
      thead.replaceChildren();tbody.replaceChildren();const row=el('tr');columns.forEach(key=>row.append(el('th','',config.labels?.[key]||key)));row.append(el('th','','查看'));thead.append(row);
      if(!visibleRecords.length){const empty=el('tr');const cell=el('td','avd-empty','没有符合条件的记录');cell.colSpan=columns.length+1;empty.append(cell);tbody.append(empty);}
      visibleRecords.forEach((record,index)=>{const tr=el('tr');columns.forEach(key=>tr.append(el('td','',text(value(record,key)))));const actionCell=el('td');const button=el('button','avd-row-button','查看详情');button.type='button';button.onclick=()=>showDetail(record,index);actionCell.append(button);tr.append(actionCell);tbody.append(tr);});
      count.textContent=`${visibleRecords.length} 条`;
    }
    function renderLocalDetail(record){
      if(mode!=='full')detailBody.append(el('div','avd-notice','当前数据未包含可验证的原始记录链接，以下展示本地快照。'));
      const fields=el('dl','avd-fields');detailFields.forEach(key=>{const item=el('div','avd-field');item.append(el('dt','',config.labels?.[key]||key),el('dd','',text(value(record,key))));fields.append(item);});detailBody.append(fields);
    }
    function renderEmbed(url){
      const frameWrap=el('div','avd-frame-wrap');const iframe=el('iframe','avd-iframe');iframe.src=url;iframe.title='钉钉原始记录';iframe.referrerPolicy='no-referrer';
      const fallback=el('div','avd-embed-fallback');fallback.hidden=true;fallback.append(el('p','','原始记录无法在当前页面中加载。'));
      const link=el('a','avd-fallback-link','新窗口打开 ↗');link.href=url;link.target='_blank';link.rel='noopener';fallback.append(link);
      const fail=()=>{fallback.hidden=false;frameWrap.classList.add('avd-frame-failed');event('aitable:drilldown-embed-failed',{url});};
      iframe.addEventListener('load',()=>{if(fallbackTimer)clearTimeout(fallbackTimer);event('aitable:drilldown-embed-loaded',{url});},{once:true});
      iframe.addEventListener('error',()=>{if(fallbackTimer)clearTimeout(fallbackTimer);fail();},{once:true});
      fallbackTimer=setTimeout(fail,config.embedTimeout||10000);frameWrap.append(iframe,fallback);detailBody.append(frameWrap);
    }
    function showDetail(record,index){
      if(mode==='aggregate_only')return;if(fallbackTimer){clearTimeout(fallbackTimer);fallbackTimer=null;}detailBody.replaceChildren();
      title.textContent=text(value(record,config.titleField))||`${listTitle} · 第 ${index+1} 条`;const url=text(value(record,config.recordUrlField));
      if(mode==='full'&&url&&config.embedOriginal!==false)renderEmbed(url);else renderLocalDetail(record);
      setView('detail');back.focus();event('aitable:drilldown-detail',{record,index,mode});
    }
    function showList(){if(fallbackTimer){clearTimeout(fallbackTimer);fallbackTimer=null;}title.textContent=listTitle;setView('list');renderList();search.focus();}
    function open(options={}){
      opener=document.activeElement;listTitle=options.title||'明细';allRecords=Array.isArray(options.records)?options.records:[];visibleRecords=allRecords.slice();
      columns=options.columns||config.columns||[];detailFields=options.detailFields||config.detailFields||columns;search.value='';root.classList.add('avd-open');root.setAttribute('aria-hidden','false');document.body.dataset.drillOpen='true';showList();event('aitable:drilldown-open',{count:allRecords.length,mode});
    }
    function closeDialog(){if(fallbackTimer){clearTimeout(fallbackTimer);fallbackTimer=null;}root.classList.remove('avd-open');root.setAttribute('aria-hidden','true');delete document.body.dataset.drillOpen;if(opener&&typeof opener.focus==='function')opener.focus();event('aitable:drilldown-close');}
    search.oninput=()=>{const query=search.value.trim().toLowerCase();visibleRecords=query?allRecords.filter(record=>searchable(record).includes(query)):allRecords.slice();renderList();};
    back.onclick=showList;close.onclick=closeDialog;mask.onclick=closeDialog;
    root.addEventListener('keydown',eventObject=>{if(eventObject.key==='Escape'){eventObject.stopPropagation();if(detailView.classList.contains('avd-active'))showList();else closeDialog();}else if(['ArrowLeft','ArrowRight','PageUp','PageDown',' '].includes(eventObject.key))eventObject.stopPropagation();},true);
    return{open,close:closeDialog,showList,showDetail,root,mode};
  }
  global.AITableDrilldown={create};
})(window);
