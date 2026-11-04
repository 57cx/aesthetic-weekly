import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import vm from 'node:vm';
import {catalog} from '../scripts/catalog.mjs';

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
