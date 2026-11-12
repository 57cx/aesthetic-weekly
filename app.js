const $=s=>document.querySelector(s);
const raw='https://raw.githubusercontent.com/57cx/aesthetic-weekly/main/';
const url=path=>raw+path.split('/').map(encodeURIComponent).join('/');
const el=(tag,text,cls)=>{const n=document.createElement(tag);if(text)n.textContent=text;if(cls)n.className=cls;return n;};
const storageKey='aesthetic-weekly:completed:v1';
let completed=new Set(), weeks=[];
try{const saved=JSON.parse(localStorage.getItem(storageKey)||'[]');if(Array.isArray(saved))completed=new Set(saved.filter(x=>typeof x==='string'));}catch{}
function save(){try{localStorage.setItem(storageKey,JSON.stringify([...completed]));}catch{$('#notice').textContent='浏览器无法保存进度；本次学习仍可继续。';}}
function picture(path,alt){const img=el('img');img.src=url(path);img.alt=alt;img.loading='lazy';img.addEventListener('error',()=>{img.removeAttribute('src');img.alt=`图片暂时无法加载：${alt}`;},{once:true});return img;}
function updateProgress(){const count=weeks.filter(w=>completed.has(w.date)).length;$('#progress-count').textContent=`${count} / ${weeks.length}`;$('#progress-bar').max=weeks.length||1;$('#progress-bar').value=count;}
const isDaily=w=>w.documents.some(p=>/今日导读\.pdf$/i.test(p));
function render(){
  const query=$('#search').value.trim().toLocaleLowerCase(), state=$('#status').value;
  let filtered=weeks.filter(w=>`${w.date} ${w.topics.map(t=>t.title).join(' ')}`.toLocaleLowerCase().includes(query)&&(state==='all'||completed.has(w.date)===(state==='done')));
  if($('#sort').value==='old')filtered=[...filtered].reverse();
  $('#courses').replaceChildren();$('#count').textContent=`${filtered.length} 期课程 / 共 ${weeks.length} 期`;
  $('#notice').textContent=filtered.length?'':'没有找到课程，试试其他关键词或学习状态。';
  filtered.forEach(w=>{const article=el('article',null,'card'), button=el('button');const photo=w.topics.flatMap(t=>t.photos)[0];if(photo)button.append(picture(photo,`${w.date} 摄影范例`));const date=el('time',w.date);date.dateTime=w.date;button.append(date,el('h3',w.topics[0]?.title||(isDaily(w)?'今日摄影课':'本周摄影课')),el('p',w.topics.map(t=>t.title).join(' · ')),el('small',`${isDaily(w)?'每日一课 · ':''}${w.topics.length} 个题材 · ${w.topics.reduce((n,t)=>n+t.photos.length,0)} 张范例${completed.has(w.date)?' · 已完成 ✓':''}`));button.addEventListener('click',()=>{location.hash=`week=${w.date}`;});article.append(button);$('#courses').append(article);});updateProgress();
}
function pdf(path){const a=el('a',`下载 PDF · ${path.split('/').at(-1)}`,'pdf-link');a.href=url(path);a.target='_blank';a.rel='noopener';return a;}
function prose(parent, blocks){(blocks||[]).forEach(block=>{if(block.h)parent.append(el('h4',block.h,'read-h'));(block.p||[]).forEach(paragraph=>parent.append(el('p',paragraph)));});}
function studyCard(topic, photoPath, essay, index){const card=el('article',null,'study');const figure=el('figure');const button=el('button');button.setAttribute('aria-label',`放大 ${topic.title} 范例 ${index+1}`);button.append(picture(photoPath,`${topic.title} · 范例 ${index+1}`));button.onclick=()=>{const d=$('#lightbox');d.querySelector('img').src=url(photoPath);d.querySelector('img').alt=`${topic.title} · 范例 ${index+1}`;d.querySelector('p').textContent=essay?.credit||'作者与授权见下方说明。';d.showModal();};figure.append(button);const caption=el('figcaption');caption.append(el('span',essay?.credit||'作者与授权见点评 PDF'));if(essay?.source){const link=el('a','来源');link.href=essay.source;link.target='_blank';link.rel='noopener';caption.append(link);}figure.append(caption);const copy=el('div',null,'study-copy');if(essay?.title)copy.append(el('h4',essay.title,'study-title'));prose(copy,essay?.blocks);if(!essay)copy.append(el('p','这篇点评暂时没有抽出正文，可以下载 PDF 阅读。'));card.append(figure,copy);return card;}
function openWeek(){const date=location.hash.match(/^#week=(\d{4}-\d{2}-\d{2})$/)?.[1];const week=weeks.find(w=>w.date===date), section=$('#lesson');section.replaceChildren();section.hidden=!week;if(!week)return;
  const top=el('div',null,'lesson-top'), intro=el('div');intro.append(el('p',week.date,'eyebrow'),el('h2',isDaily(week)?'今天，认真看见。':'这一周，认真看见。'));const done=el('button',completed.has(date)?'已完成 ✓':'标记本期已完成');done.setAttribute('aria-pressed',String(completed.has(date)));done.onclick=()=>{completed.has(date)?completed.delete(date):completed.add(date);save();render();done.textContent=completed.has(date)?'已完成 ✓':'标记本期已完成';done.setAttribute('aria-pressed',String(completed.has(date)));};top.append(intro,done);section.append(top,el('p','学习顺序：在页面上读导读 → 看每张范例和它的点评 → 外出练习。PDF 仍可下载，留给离线或打印。','lesson-tip'));
  if(week.guideReading?.blocks?.length){const guide=el('article',null,'reading');guide.append(el('p','导读','eyebrow'),el('h3','先读这一课'));prose(guide,week.guideReading.blocks);const downloads=el('div',null,'downloads');week.documents.forEach(p=>downloads.append(pdf(p)));guide.append(downloads);section.append(guide);}
  week.topics.forEach((t,i)=>{const block=el('article',null,'topic');block.append(el('p',`练习 ${String(i+1).padStart(2,'0')}`,'eyebrow'),el('h3',t.title));prose(block,t.reading?.intro);t.photos.forEach((p,j)=>block.append(studyCard(t,p,t.reading?.photos?.[j],j)));prose(block,t.reading?.closing);const downloads=el('div',null,'downloads');t.documents.forEach(p=>downloads.append(pdf(p)));block.append(downloads);section.append(block);});section.scrollIntoView();section.focus({preventScroll:true});
}
$('#close-lightbox').onclick=()=>$('#lightbox').close();
$('#lightbox').addEventListener('click',e=>{if(e.target===$('#lightbox'))$('#lightbox').close();});
for(const id of ['search','status','sort'])$('#'+id).addEventListener('input',render);
window.addEventListener('hashchange',openWeek);
window.addEventListener('storage',e=>{if(e.key===storageKey){try{const v=JSON.parse(e.newValue||'[]');if(Array.isArray(v))completed=new Set(v.filter(x=>typeof x==='string'));}catch{}render();openWeek();}});
async function load(){try{let data=window.PHOTOGRAPHY_CATALOG;if(!data){const r=await fetch('catalog.json',{signal:AbortSignal.timeout(15000)});if(!r.ok)throw Error(`HTTP ${r.status}`);data=await r.json();}weeks=data.weeks;if(!Array.isArray(weeks)||!weeks.length)throw Error('课程索引为空');render();const photo=weeks[0].topics.flatMap(t=>t.photos)[0];if(photo){const img=picture(photo,'最新一期摄影作品');img.loading='eager';$('#hero-photo').firstElementChild.replaceWith(img);$('#hero-photo figcaption').textContent=`最新一期 / ${weeks[0].date} · ${weeks[0].topics[0]?.title||''}`;}openWeek();}catch{$('#notice').replaceChildren(el('span','课程暂时无法加载，请检查网络后重试。 '));const b=el('button','重新加载');b.onclick=load;$('#notice').append(b);}}
load();
