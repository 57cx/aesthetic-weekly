import {readdir, readFile, mkdir, writeFile, copyFile} from 'node:fs/promises';
import {catalog} from './catalog.mjs';
async function walk(dir='', result=[]) {
  for(const item of await readdir(dir||'.',{withFileTypes:true})) {
    if(item.name.startsWith('.') || ['node_modules','dist'].includes(item.name)) continue;
    const path=dir?`${dir}/${item.name}`:item.name;
    if(item.isDirectory()) {if(dir || /^\d{4}-\d{2}-\d{2}$/.test(item.name)) await walk(path,result);}
    else result.push({path,type:'blob'});
  } return result;
}
let entries=await walk();
if(!entries.some(e=>/^\d{4}-\d{2}-\d{2}\//.test(e.path))) entries=JSON.parse(await readFile('repository-tree.json','utf8')).tree;
const weeks=catalog(entries);
if(!weeks.length) throw Error('没有发现课程目录');
await mkdir('dist',{recursive:true});
for(const name of ['style.css','app.js']) await copyFile(name,`dist/${name}`);
await writeFile('dist/catalog.json',JSON.stringify({weeks},null,2));
const dataScript='window.PHOTOGRAPHY_CATALOG='+JSON.stringify({weeks}).replaceAll('<','\\u003c')+';';
await writeFile('dist/catalog.js',dataScript);
const appScript=await readFile('app.js','utf8');
const html=(await readFile('index.html','utf8')).replace('<script src="catalog.js" defer></script><script src="app.js" defer></script>',()=>'<script defer src="catalog.js"></script><script defer src="app.js"></script>');
await writeFile('dist/index.html',html);
await writeFile('catalog.js',dataScript);
await writeFile('dist/.nojekyll','');
console.log(`Built ${weeks.length} weeks, ${weeks.reduce((n,w)=>n+w.topics.reduce((n,t)=>n+t.photos.length,0),0)} photographs`);
