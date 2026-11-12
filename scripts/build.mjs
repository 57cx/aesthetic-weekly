import {readdir, readFile, mkdir, writeFile, copyFile} from 'node:fs/promises';
import {pathToFileURL} from 'node:url';
import {catalog} from './catalog.mjs';
import {readingsForIssue} from './readings.mjs';
export async function collectEntries(dir='', result=[]) {
  for(const item of await readdir(dir||'.',{withFileTypes:true})) {
    if(item.name.startsWith('.') || ['node_modules','dist'].includes(item.name)) continue;
    const path=dir?`${dir}/${item.name}`:item.name;
    if(item.isDirectory()) {if(dir || /^\d{4}-\d{2}-\d{2}$/.test(item.name)) await collectEntries(path,result);}
    else result.push({path,type:'blob'});
  } return result;
}
export async function build() {
  let entries=await collectEntries();
  if(!entries.some(e=>/^\d{4}-\d{2}-\d{2}\//.test(e.path))) entries=JSON.parse(await readFile('repository-tree.json','utf8')).tree;
  const weeks=catalog(entries);
  if(!weeks.length) throw Error('没有发现课程目录');
  for(const week of weeks){
    let extracted=null;
    try{extracted=JSON.parse(await readFile(`site-readings/${week.date}.json`,'utf8'));}catch{}
    const reading=await readingsForIssue('.', week.date, extracted);
    if(!reading.guide?.blocks?.length) throw Error(`${week.date} 没有可阅读的导读`);
    week.guideReading=reading.guide;
    for(const topic of week.topics){
      const text=reading.topics?.[topic.title];
      if(!text?.photos?.length) throw Error(`${week.date}/${topic.title} 没有可阅读的点评`);
      topic.reading=text;
    }
  }
  await mkdir('dist',{recursive:true});
  for(const name of ['style.css','app.js']) await copyFile(name,`dist/${name}`);
  await writeFile('dist/catalog.json',JSON.stringify({weeks},null,2));
  const dataScript='window.PHOTOGRAPHY_CATALOG='+JSON.stringify({weeks}).replaceAll('<','\\u003c')+';';
  await writeFile('dist/catalog.js',dataScript);
  await readFile('app.js','utf8');
  const html=(await readFile('index.html','utf8')).replace('<script src="catalog.js" defer></script><script src="app.js" defer></script>',()=>'<script defer src="catalog.js"></script><script defer src="app.js"></script>');
  await writeFile('dist/index.html',html);
  await writeFile('catalog.js',dataScript);
  await writeFile('dist/.nojekyll','');
  console.log(`Built ${weeks.length} weeks, ${weeks.reduce((n,w)=>n+w.topics.reduce((n,t)=>n+t.photos.length,0),0)} photographs`);
  return weeks;
}
if(process.argv[1] && import.meta.url===pathToFileURL(process.argv[1]).href) await build();
