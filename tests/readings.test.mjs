import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {guideFromMarkdown, topicFromMarkdown, readableChinese, readingsForIssue} from '../scripts/readings.mjs';

test('markdown lessons become readable blocks with a credit per photo', () => {
  const guide = guideFromMarkdown('# 每日一课\n\n## 今天\n\n### 先看地面\n\n叶子朝哪边，哪里密。\n\n哪里疏。\n');
  assert.equal(guide.blocks[0].h, '先看地面');
  assert.match(guide.blocks[0].p[0], /叶子朝哪边/);
  const topic = topicFromMarkdown('# 题材\n\n## 01｜路沿\n\n### 1．明暗\n\n左侧更疏。\n', [{credit: '作者甲 · CC BY 4.0', source: 'https://commons.wikimedia.org/wiki/File:Example.jpg'}]);
  assert.equal(topic.photos.length, 1);
  assert.equal(topic.photos[0].credit, '作者甲 · CC BY 4.0');
  assert.equal(topic.photos[0].blocks[0].h, '1．明暗');
  assert.ok(readableChinese(topic));
});

test('historical PDF text is clean Chinese and tied to five photos', async () => {
  const reading = JSON.parse(await readFile('site-readings/2026-01-04.json', 'utf8'));
  const topic = reading.topics['窗光'];
  assert.equal(topic.photos.length, 5);
  assert.match(topic.photos[0].credit, /Dietmar Rabich/);
  assert.match(topic.photos[0].credit, /CC BY-SA 4.0/);
  assert.match(topic.photos[0].source, /^https:\/\/commons\.wikimedia\.org\/wiki\/File:/);
  assert.match(topic.photos[0].blocks.map(block => block.h).join(' '), /为什么这个画面好看/);
  assert.match(JSON.stringify(topic), /长椅|大理石|窗/);
  assert.ok(readableChinese(reading));
  assert.match(reading.guide.blocks.map(block => `${block.h} ${block.p.join(' ')}`).join('\n'), /光是第一主角/);
});

test('markdown issues and extracted issues both supply on-page text', async () => {
  const old = await readingsForIssue('.', '2026-01-04', JSON.parse(await readFile('site-readings/2026-01-04.json', 'utf8')));
  assert.match(old.topics['窗光'].photos[0].blocks.map(block => block.p.join('')).join(''), /窗/);
  const daily = await readingsForIssue('.', '2026-11-13', null);
  assert.match(daily.guide.blocks.map(block => block.p.join('')).join(''), /沟、箅子与横档拦住落叶/);
  assert.equal(daily.topics['落叶地面的方向与疏密'].photos.length, 5);
  assert.match(daily.topics['落叶地面的方向与疏密'].photos[0].credit, /Jules Verne Times Two/);
  assert.ok(readableChinese(daily));
});
