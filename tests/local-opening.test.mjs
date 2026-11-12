import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import vm from 'node:vm';
import {catalog} from '../scripts/catalog.mjs';
import {collectEntries} from '../scripts/build.mjs';

test('local opening renders courses without fetch or module support', async()=>{
  class Element {
    constructor(){this.children=[];this.value='';this.textContent='';}
    append(...items){this.children.push(...items);}
    replaceChildren(...items){this.children=[...items];}
    addEventListener(){}
    setAttribute(){}
    replaceWith(){}
  }
  const nodes=new Map();
  const get=s=>{if(!nodes.has(s))nodes.set(s,new Element());return nodes.get(s);};
  get('#status').value='all';get('#sort').value='new';
  get('#hero-photo').firstElementChild=new Element();
  const tree=JSON.parse(await readFile('repository-tree.json','utf8'));
  const context=vm.createContext({document:{querySelector:get,createElement:()=>new Element()},window:{PHOTOGRAPHY_CATALOG:{weeks:catalog(tree.tree)},addEventListener(){}},location:{hash:''},localStorage:{getItem:()=>null},fetch:()=>{throw Error('Local file opening must not need fetch');}});
  vm.runInContext(await readFile('app.js','utf8'),context);
  assert.equal(get('#courses').children.length,44);
  assert.equal(get('#progress-count').textContent,'0 / 44');
  assert.equal(get('#notice').textContent,'');
});
test('the published 2026-11-13 daily issue is discovered',async()=>{const weeks=catalog(await collectEntries());const day=weeks.find(w=>w.date==='2026-11-13');assert.ok(day);assert.equal(day.topics.length,1);assert.equal(day.topics[0].title,'落叶地面的方向与疏密');assert.equal(day.topics[0].photos.length,5);assert.equal(day.topics[0].documents.length,1);assert.match(day.documents[0],/今日导读\.pdf$/);});
test('opening a daily issue says today',async()=>{
  class Element {
    constructor(){this.children=[];this.value='';this.textContent='';}
    append(...items){this.children.push(...items);}
    replaceChildren(...items){this.children=[...items];}
    addEventListener(){}
    setAttribute(){}
    replaceWith(){}
    scrollIntoView(){}
    focus(){}
  }
  const nodes=new Map();
  const get=s=>{if(!nodes.has(s))nodes.set(s,new Element());return nodes.get(s);};
  get('#status').value='all';get('#sort').value='new';
  get('#hero-photo').firstElementChild=new Element();
  const day={date:'2026-11-13',documents:['2026-11-13/今日导读.pdf'],topics:[{title:'落叶地面的方向与疏密',photos:['2026-11-13/落叶地面的方向与疏密/01.jpg'],documents:['2026-11-13/落叶地面的方向与疏密/落叶地面的方向与疏密_点评与思考.pdf']}]};
  const context=vm.createContext({document:{querySelector:get,createElement:()=>new Element()},window:{PHOTOGRAPHY_CATALOG:{weeks:[day]},addEventListener(){}},location:{hash:'#week=2026-11-13'},localStorage:{getItem:()=>null},fetch:()=>{throw Error('unused');}});
  vm.runInContext(await readFile('app.js','utf8'),context);
  const heading=get('#lesson').children.flatMap(n=>n.children||[]).flatMap(n=>n.children||[]).find(n=>n.textContent.includes('看见'));
  assert.equal(heading.textContent,'今天，认真看见。');
  assert.match(get('#courses').children[0].children[0].children.at(-1).textContent,/每日一题/);
});
