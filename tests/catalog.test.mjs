import {test} from 'node:test';
import assert from 'node:assert/strict';
import {catalog} from '../scripts/catalog.mjs';
import {readFile} from 'node:fs/promises';
test('discovers real repository weeks and all learning assets',async()=>{const tree=JSON.parse(await readFile('repository-tree.json'));const weeks=catalog(tree.tree);assert.equal(weeks.length,44);assert.equal(weeks[0].date,'2026-10-31');for(const w of weeks){assert.equal(w.topics.length,4);assert.equal(w.documents.length,1);for(const t of w.topics){assert.equal(t.photos.length,5);assert.equal(t.documents.length,1);}}});
test('new issues appear automatically and unrelated files are excluded',()=>{const entries=['README.md','2027-01-02/本周导读.PDF','2027-01-02/窗光/01.JPG','2027-01-02/窗光/点评.pdf','2026-12-26/街头/01.webp'].map(path=>({path,type:'blob'}));const result=catalog(entries);assert.equal(result.length,2);assert.equal(result[0].date,'2027-01-02');assert.equal(result[0].topics[0].photos.length,1);assert.equal(result[0].topics[0].documents.length,1);});
