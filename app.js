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
function render(){
  const query=$('#search').value.trim().toLocaleLowerCase(), state=$('#status').value;
  let filtered=weeks.filter(w=>`${w.date} ${w.topics.map(t=>t.title).join(' ')}`.toLocaleLowerCase().includes(query)&&(state==='all'||completed.has(w.date)===(state==='done')));
  if($('#sort').value==='old')filtered=filtered.toReversed();
  $('#courses').replaceChildren();$('#count').textContent=`${filtered.length} 期课程 / 共 ${weeks.length} 期`;
  $('#notice').textContent=filtered.length?'':'没有找到课程，试试其他关键词或学习状态。';
  filtered.forEach(w=>{const article=el('article',null,'card'), button=el('button');const photo=w.topics.flatMap(t=>t.photos)[0];if(photo)button.append(picture(photo,`${w.date} 摄影范例`));const date=el('time',w.date);date.dateTime=w.date;button.append(date,el('h3',w.topics[0]?.title||'本周摄影课'),el('p',w.topics.map(t=>t.title).join(' · ')),el('small',`${w.topics.length} 个题材 · ${w.topics.reduce((n,t)=>n+t.photos.length,0)} 张范例${completed.has(w.date)?' · 已完成 ✓':''}`));button.addEventListener('click',()=>{location.hash=`week=${w.date}`;});article.append(button);$('#courses').append(article);});updateProgress();
}
function pdf(path){const a=el('a',`↗ ${path.split('/').at(-1)}`,'pdf-link');a.href=url(path);a.target='_blank';a.rel='noopener';return a;}
function openWeek(){const date=location.hash.match(/^#week=(\d{4}-\d{2}-\d{2})$/)?.[1];const week=weeks.find(w=>w.date===date), section=$('#lesson');section.replaceChildren();section.hidden=!week;if(!week)return;
  const top=el('div',null,'lesson-top'), intro=el('div');intro.append(el('p',week.date,'eyebrow'),el('h2','这一周，认真看见。'));const done=el('button',completed.has(date)?'已完成 ✓':'标记本期已完成');done.setAttribute('aria-pressed',String(completed.has(date)));done.onclick=()=>{completed.has(date)?completed.delete(date):completed.add(date);save();render();done.textContent=completed.has(date)?'已完成 ✓':'标记本期已完成';done.setAttribute('aria-pressed',String(completed.has(date)));};top.append(intro,done);section.append(top,el('p','学习顺序：阅读导读 → 观察范例 → 阅读点评 → 外出练习。照片来源与授权请查阅对应 PDF。','lesson-tip'));week.documents.forEach(p=>section.append(pdf(p)));
  week.topics.forEach((t,i)=>{const block=el('article',null,'topic');block.append(el('p',`练习 ${String(i+1).padStart(2,'0')}`,'eyebrow'),el('h3',t.title));t.documents.forEach(p=>block.append(pdf(p)));const gallery=el('div',null,'gallery');t.photos.forEach((p,j)=>{const button=el('button');button.setAttribute('aria-label',`放大 ${t.title} 范例 ${j+1}`);button.append(picture(p,`${t.title} · 范例 ${j+1}`));button.onclick=()=>{const d=$('#lightbox');d.querySelector('img').src=url(p);d.querySelector('img').alt=`${t.title} · 范例 ${j+1}`;d.querySelector('p').textContent='作者、来源及授权见本题材点评 PDF。';d.showModal();};gallery.append(button);});block.append(gallery);section.append(block);});section.scrollIntoView();section.focus({preventScroll:true});
}
$('#close-lightbox').onclick=()=>$('#lightbox').close();
$('#lightbox').addEventListener('click',e=>{if(e.target===$('#lightbox'))$('#lightbox').close();});
for(const id of ['search','status','sort'])$('#'+id).addEventListener('input',render);
window.addEventListener('hashchange',openWeek);
window.addEventListener('storage',e=>{if(e.key===storageKey){try{const v=JSON.parse(e.newValue||'[]');if(Array.isArray(v))completed=new Set(v.filter(x=>typeof x==='string'));}catch{}render();openWeek();}});
async function load(){try{const r=await fetch('catalog.json');if(!r.ok)throw Error(`HTTP ${r.status}`);const data=await r.json();weeks=data.weeks;if(!Array.isArray(weeks)||!weeks.length)throw Error('课程索引为空');render();const photo=weeks[0].topics.flatMap(t=>t.photos)[0];if(photo){const img=picture(photo,'最新一期摄影作品');img.loading='eager';$('#hero-photo').firstElementChild.replaceWith(img);$('#hero-photo figcaption').textContent=`最新一期 / ${weeks[0].date} · ${weeks[0].topics[0]?.title||''}`;}openWeek();}catch{$('#notice').replaceChildren(el('span','课程暂时无法加载，请检查网络后重试。 '));const b=el('button','重新加载');b.onclick=load;$('#notice').append(b);}}
load();
