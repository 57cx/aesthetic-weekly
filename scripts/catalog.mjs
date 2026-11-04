export function catalog(entries) {
  const weeks = new Map();
  for (const {path, type} of entries) {
    if(type !== 'blob') continue;
    const [date, ...parts] = path.split('/');
    if(!/^\d{4}-\d{2}-\d{2}$/.test(date) || !parts.length) continue;
    if(!weeks.has(date)) weeks.set(date, {date, topics:[], documents:[]});
    const week=weeks.get(date), name=parts.at(-1);
    if(parts.length===1) { if(/\.pdf$/i.test(name)) week.documents.push(path); continue; }
    const title=parts.slice(0,-1).join('/');
    let topic=week.topics.find(t=>t.title===title);
    if(!topic) {topic={title, photos:[], documents:[]};week.topics.push(topic);}
    if(/\.(jpe?g|png|webp|avif|gif)$/i.test(name)) topic.photos.push(path);
    if(/\.pdf$/i.test(name)) topic.documents.push(path);
  }
  return [...weeks.values()].sort((a,b)=>b.date.localeCompare(a.date)).map(w=>({...w,topics:w.topics.sort((a,b)=>a.title.localeCompare(b.title,'zh-CN')).map(t=>({...t,photos:t.photos.sort(),documents:t.documents.sort()}))}));
}
