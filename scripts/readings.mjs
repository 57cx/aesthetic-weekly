import {readFile} from 'node:fs/promises';

export function parseCourseMarkdown(text) {
  const lines = text.replace(/\r\n/g, '\n').split('\n');
  let title = '';
  const chapters = [];
  let chapter = null;
  let section = null;
  let buf = [];
  const flush = () => {
    const body = buf.join('\n').trim();
    buf = [];
    if (!body || !section) return;
    section.p.push(...body.split(/\n\s*\n/).map(part => part.trim()).filter(Boolean));
  };
  for (const line of lines) {
    if (line.startsWith('# ')) { title = line.slice(2).trim(); continue; }
    if (line.startsWith('## ')) {
      flush();
      chapter = {h: line.slice(3).trim(), sections: []};
      chapters.push(chapter);
      section = {h: '', p: []};
      chapter.sections.push(section);
      continue;
    }
    if (line.startsWith('### ')) {
      flush();
      if (!chapter) { chapter = {h: '', sections: []}; chapters.push(chapter); }
      section = {h: line.slice(4).trim(), p: []};
      chapter.sections.push(section);
      continue;
    }
    buf.push(line);
  }
  flush();
  return {title, chapters};
}

function chapterBlocks(chapter) {
  const blocks = [];
  for (const section of chapter.sections) {
    if (!section.h && !section.p.length) continue;
    blocks.push({h: section.h || chapter.h, p: section.p});
  }
  return blocks;
}

export function guideFromMarkdown(text) {
  const parsed = parseCourseMarkdown(text);
  return {title: parsed.title, blocks: parsed.chapters.flatMap(chapterBlocks)};
}

export function topicFromMarkdown(text, credits = []) {
  const parsed = parseCourseMarkdown(text);
  return {
    intro: [],
    photos: parsed.chapters.map((chapter, index) => ({
      title: chapter.h,
      credit: credits[index]?.credit || '',
      source: credits[index]?.source || '',
      blocks: chapter.sections.filter(section => section.h || section.p.length).map(section => ({h: section.h, p: section.p})),
    })),
    closing: [],
  };
}

export async function creditsByTopic(root, date) {
  const byTopic = new Map();
  try {
    const manifest = JSON.parse(await readFile(`${root}/${date}/sources.json`, 'utf8'));
    for (const photo of manifest.photos || []) {
      const parts = photo.path.split('/');
      const topic = parts.slice(1, -1).join('/');
      if (!byTopic.has(topic)) byTopic.set(topic, []);
      byTopic.get(topic).push(photo);
    }
  } catch { /* older issues keep the credit parsed from the PDF */ }
  for (const photos of byTopic.values()) {
    photos.sort((a, b) => a.path.localeCompare(b.path, 'en'));
  }
  return byTopic;
}

export function creditLine(photo) {
  if (!photo) return {credit: '', source: ''};
  return {credit: [photo.author, photo.license].filter(Boolean).join(' · '), source: photo.source || ''};
}

export async function readingsForIssue(root, date, extracted) {
  const reading = extracted ? structuredClone(extracted) : {guide: null, topics: {}};
  const credits = await creditsByTopic(root, date);
  for (const name of ['今日导读.md', '本周导读.md']) {
    try {
      reading.guide = guideFromMarkdown(await readFile(`${root}/${date}/${name}`, 'utf8'));
      break;
    } catch { /* use the extracted guide */ }
  }
  const {readdir} = await import('node:fs/promises');
  let topics = [];
  try { topics = await readdir(root ? `${root}/${date}` : date, {withFileTypes: true}); } catch { topics = []; }
  for (const topic of topics) {
    if (!topic.isDirectory()) continue;
    try {
      const markdown = await readFile(`${root}/${date}/${topic.name}/解读原稿.md`, 'utf8');
      const lines = (credits.get(topic.name) || []).map(creditLine);
      reading.topics[topic.name] = topicFromMarkdown(markdown, lines);
    } catch { /* extracted topic text remains */ }
  }
  return reading;
}

export function readableChinese(value) {
  const text = JSON.stringify(value);
  return /[\u4e00-\u9fff]/.test(text) && !/[\u2f00-\u2fd5\u2e80-\u2eff]/.test(text);
}
