#!/usr/bin/env python3
"""Extract on-page lesson text from issue PDFs that have no Markdown source.

Writes site-readings/<date>.json. Issues that already have 今日导读.md or
本周导读.md plus 解读原稿.md are skipped; the website build reads those
directly so later daily issues do not need this step.

Usage: python tools/extract_readings.py
"""
from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'site-readings'
# Some PDF fonts map simplified characters to CJK radicals. NFKC does not
# rewrite that block, so the reading text would show ⻓ instead of 长.
RADICALS = str.maketrans({
    '⻔': '门', '⻓': '长', '⻆': '角', '⻋': '车', '⻅': '见', '⻛': '风',
    '⻩': '黄', '⻦': '鸟', '⻜': '飞', '⻢': '马', '⻘': '青', '⻝': '食',
    '⻬': '齐', '⻰': '龙', '⺠': '民', '⻥': '鱼', '⻣': '骨', '⻉': '贝',
    '⻨': '麦', '⻮': '齿', '⻤': '鬼', '⻚': '页', '⻙': '韦',
})
HEADINGS = (
    '本题材要点', '本周主题', '为什么这周学这个', '四个题材概览', '五个题材概览',
    '本周拍摄计划', '本周练习清单', '本周交作业', '本册示例',
    '为什么这个画面好看', '大概怎么拍', '你可以怎么学', '去哪儿找类似场景',
    '本题材练习任务', '拍完自查', 'Z30 换算速查', 'Z30换算速查',
)
LABELS = ('作者', '来源', 'EXIF', 'Z30 焦段', 'Z30焦段')


def pdf_text(path: Path) -> str:
    reader = PdfReader(str(path))
    parts = [(page.extract_text() or '') for page in reader.pages]
    text = unicodedata.normalize('NFKC', '\n'.join(parts)).translate(RADICALS)
    text = text.replace('《审美提升》', '\n《审美提升》')
    if re.search(r'[\u2e80-\u2fdf]', text):
        raise ValueError(f'{path} still contains CJK radicals after cleanup')
    return text


def is_heading(line: str) -> bool:
    if re.match(r'^示例\s*\d', line):
        return True
    if line.startswith(HEADINGS) or line.startswith(LABELS):
        return True
    return False


def reflow(text: str) -> list[str]:
    paragraphs = []
    buf = ''
    for raw in text.splitlines():
        line = re.sub(r'\s+', ' ', raw).strip()
        if not line or re.fullmatch(r'\d{1,3}', line):
            if buf:
                paragraphs.append(buf)
                buf = ''
            continue
        if is_heading(line):
            if buf:
                paragraphs.append(buf)
                buf = ''
            paragraphs.append(line)
            continue
        buf = f'{buf}{line}' if buf else line
    if buf:
        paragraphs.append(buf)
    return paragraphs


def split_heading(paragraph: str):
    if re.match(r'^示例\s*\d', paragraph):
        return paragraph, ''
    for label in (*HEADINGS, *LABELS):
        if paragraph.startswith(label):
            rest = paragraph[len(label):].lstrip('：: ').strip()
            return label, rest
    return '', paragraph


def blocks_from(paragraphs: list[str]):
    blocks = []
    current = None
    for paragraph in paragraphs:
        heading, rest = split_heading(paragraph)
        if heading:
            current = {'h': heading, 'p': []}
            blocks.append(current)
            if rest:
                current['p'].append(rest)
            continue
        if current is None:
            current = {'h': '', 'p': []}
            blocks.append(current)
        if rest:
            current['p'].append(rest)
    return [block for block in blocks if block['h'] or block['p']]


def topic_reading(text: str):
    blocks = blocks_from(reflow(text))
    intro, photos, closing = [], [], []
    photo = None
    mode = 'intro'
    for block in blocks:
        if re.match(r'^示例\s*\d', block['h']):
            mode = 'photo'
            title = block['h'] if not block['p'] else f"{block['h']} {block['p'][0]}"
            photo = {'title': title.strip(), 'credit': '', 'source': '', 'blocks': []}
            photos.append(photo)
            continue
        if block['h'] in ('本题材练习任务', '拍完自查'):
            mode = 'close'
        if mode == 'intro':
            if block['h'] != '本册示例':
                intro.append(block)
        elif mode == 'photo':
            if block['h'] == '作者':
                photo['credit'] = ' '.join(block['p']).replace('许可:', ' · ').replace('许可：', ' · ')
            elif block['h'] == '来源':
                photo['source'] = ' '.join(block['p'])
            else:
                photo['blocks'].append(block)
        else:
            closing.append(block)
    return {'intro': intro, 'photos': photos, 'closing': closing}


def guide_reading(text: str):
    return {'blocks': blocks_from(reflow(text))}


def stable_chinese(text: str) -> bool:
    return unicodedata.normalize('NFKC', text) == text


def hanzi(text: str) -> int:
    return len(re.findall(r'[\u4e00-\u9fff]', text))


def issue_has_markdown(issue: Path) -> bool:
    guide = (issue / '今日导读.md').exists() or (issue / '本周导读.md').exists()
    topics = list(issue.glob('*/解读原稿.md'))
    pdf_topics = [path.parent for path in issue.glob('*/*点评与思考.pdf')]
    return guide and topics and len(topics) >= len(pdf_topics)


def main():
    OUT.mkdir(exist_ok=True)
    problems = []
    written = 0
    for issue in sorted(path for path in ROOT.iterdir() if re.fullmatch(r'\d{4}-\d{2}-\d{2}', path.name)):
        if issue_has_markdown(issue):
            stale = OUT / f'{issue.name}.json'
            if stale.exists():
                stale.unlink()
            continue
        payload = {'guide': None, 'topics': {}}
        guides = list(issue.glob('*导读.pdf'))
        if len(guides) != 1:
            problems.append(f'{issue.name}: expected one guide PDF, found {len(guides)}')
        elif guides:
            payload['guide'] = guide_reading(pdf_text(guides[0]))
            flat = json.dumps(payload['guide'], ensure_ascii=False)
            if not stable_chinese(flat) or hanzi(flat) < 200:
                problems.append(f'{issue.name}: guide text is not clean Chinese')
        for pdf in sorted(issue.glob('*/*点评与思考.pdf')):
            title = pdf.parent.name
            reading = topic_reading(pdf_text(pdf))
            payload['topics'][title] = reading
            flat = json.dumps(reading, ensure_ascii=False)
            if not stable_chinese(flat):
                problems.append(f'{pdf}: normalization left compatibility characters')
            if len(reading['photos']) != 5:
                problems.append(f'{pdf}: parsed {len(reading["photos"])} photos')
            if hanzi(flat) < 400:
                problems.append(f'{pdf}: only {hanzi(flat)} Chinese characters')
            if any(not str(photo.get('source', '')).startswith('http') for photo in reading['photos']):
                problems.append(f'{pdf}: a photo is missing its Commons source link')
            if not any(block['h'].startswith('为什么') for photo in reading['photos'] for block in photo['blocks']):
                problems.append(f'{pdf}: missing the per-photo commentary heading')
        destination = OUT / f'{issue.name}.json'
        destination.write_text(json.dumps(payload, ensure_ascii=False, separators=(',', ':')) + '\n', encoding='utf-8')
        written += 1
    if problems:
        raise SystemExit('\n'.join(problems))
    print(f'wrote {written} reading files to {OUT.relative_to(ROOT)}')


if __name__ == '__main__':
    main()
