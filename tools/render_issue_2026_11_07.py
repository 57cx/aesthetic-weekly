#!/usr/bin/env python3
"""Render the revised issue 45 manuscripts and sources.json into five PDFs.

Usage: python tools/render_issue_2026_11_07.py 2026-11-07 --font /path/to/CJK-Regular.ttf
Requires reportlab and Pillow. Supply a TrueType font covering simplified Chinese.
The revised edition uses Noto Sans SC (SIL OFL), embedded as PDF subsets. A regular
instance can be made from Google Fonts' NotoSansSC[wght].ttf with fontTools:
  fonttools varLib.instancer 'NotoSansSC[wght].ttf' wght=400 --output=NotoSansSC-Regular.ttf
Source: https://github.com/google/fonts/tree/main/ofl/notosanssc
The font is not copied into the repository; the PDF embeds the glyphs it uses.
"""
from __future__ import annotations
import argparse
import html
import json
import re
from fractions import Fraction
from pathlib import Path

from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate, Frame, Image, PageBreak, PageTemplate, Paragraph,
)

PAGE_W, PAGE_H = 595.28, 841.89
MARGIN = 48
INK = colors.HexColor('#20383d')
MUTED = colors.HexColor('#59696c')
TEAL = colors.HexColor('#356b70')
FONT = 'IssueChinese'


def escaped(value):
    return html.escape(str(value), quote=True)


def manuscripts(path):
    """Parse our deliberately small Markdown format: H1, H2, H3, paragraphs."""
    text = path.read_text(encoding='utf-8')
    title_match = re.search(r'^# (.+)$', text, re.M)
    if not title_match:
        raise ValueError(f'Missing title: {path}')
    chapters = []
    for chapter in re.split(r'^## ', text, flags=re.M)[1:]:
        title, body = chapter.split('\n', 1)
        sections = []
        for section in re.split(r'^### ', body, flags=re.M)[1:]:
            heading, paragraph = section.split('\n', 1)
            sections.append((heading.strip(), paragraph.strip()))
        chapters.append((title.strip(), sections))
    return title_match.group(1), chapters


def styles():
    return {
        'title': ParagraphStyle('Title', fontName=FONT, fontSize=20, leading=29,
                                textColor=INK, spaceAfter=16, wordWrap='CJK'),
        'photo_title': ParagraphStyle('PhotoTitle', fontName=FONT, fontSize=17,
                                      leading=25, textColor=INK, spaceAfter=10,
                                      wordWrap='CJK'),
        'label': ParagraphStyle('Label', fontName=FONT, fontSize=9, leading=14,
                                textColor=TEAL, spaceAfter=12, wordWrap='CJK'),
        'heading': ParagraphStyle('Heading', fontName=FONT, fontSize=12.3,
                                  leading=19, textColor=TEAL, spaceBefore=10,
                                  spaceAfter=5, keepWithNext=True, wordWrap='CJK'),
        'body': ParagraphStyle('Body', fontName=FONT, fontSize=10.5, leading=17.2,
                               textColor=INK, spaceAfter=8, wordWrap='CJK',
                               splitLongWords=True),
        'small': ParagraphStyle('Small', fontName=FONT, fontSize=8.2, leading=12.2,
                                textColor=MUTED, spaceAfter=5, wordWrap='CJK',
                                splitLongWords=True),
        'caption': ParagraphStyle('Caption', fontName=FONT, fontSize=8.2,
                                  leading=12, textColor=MUTED, alignment=TA_CENTER,
                                  spaceBefore=5, spaceAfter=9, wordWrap='CJK'),
    }


class OutlineParagraph(Paragraph):
    def __init__(self, text, style, key, level):
        super().__init__(text, style)
        self.outline_key = key
        self.outline_level = level


class IssueDocument(BaseDocTemplate):
    def __init__(self, path, issue, document_title, **kwargs):
        super().__init__(str(path), pagesize=(PAGE_W, PAGE_H), leftMargin=MARGIN,
                         rightMargin=MARGIN, topMargin=56, bottomMargin=49,
                         title=document_title, author='Aesthetic Weekly',
                         pageCompression=1, **kwargs)
        self.issue = issue
        frame = Frame(MARGIN, 49, PAGE_W - 2 * MARGIN, PAGE_H - 105,
                      leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
        self.addPageTemplates([PageTemplate(id='issue', frames=frame,
                                            onPage=self.decorate)])

    def decorate(self, canvas, document):
        canvas.saveState()
        canvas.setFont(FONT, 8)
        canvas.setFillColor(MUTED)
        canvas.drawString(MARGIN, PAGE_H - 29, f'审美提升 · {self.issue} · 深度解读更正版')
        canvas.setStrokeColor(colors.HexColor('#d5dfe0'))
        canvas.setLineWidth(.5)
        canvas.line(MARGIN, 39, PAGE_W - MARGIN, 39)
        canvas.drawString(MARGIN, 24, '观察有证据 · 推断有边界 · 练习可完成')
        canvas.drawRightString(PAGE_W - MARGIN, 24, str(document.page))
        canvas.restoreState()

    def afterFlowable(self, flowable):
        if isinstance(flowable, OutlineParagraph):
            self.canv.bookmarkPage(flowable.outline_key)
            self.canv.addOutlineEntry(flowable.getPlainText(), flowable.outline_key,
                                     level=flowable.outline_level, closed=False)


def paragraphs(text, style):
    return [Paragraph(escaped(p).replace('\n', '<br/>'), style)
            for p in re.split(r'\n\s*\n', text) if p.strip()]


def section(heading, text, sty):
    return [Paragraph(escaped(heading), sty['heading']),
            *paragraphs(text, sty['body'])]


def numeric(value):
    try:
        return f'{float(Fraction(str(value))):.6g}'
    except (ValueError, TypeError, ZeroDivisionError):
        return str(value)


def metadata_text(photo):
    data = {item['name']: item.get('value') for item in photo['original_metadata']}
    fields = []
    for key, label in [('Model', '机型'), ('FocalLength', '实焦距mm'),
                       ('FNumber', '光圈f/'), ('ExposureTime', '曝光秒'),
                       ('ISOSpeedRatings', 'ISO')]:
        if key in data:
            value = str(data[key]) if key == 'Model' else numeric(data[key])
            fields.append(f'{label}：{value}')
    return '原图EXIF（Commons来源记录）：' + ('；'.join(fields) if fields else '未提供可用曝光参数')


def attribution(photo, sty):
    rows = [Paragraph('来源与核实信息', sty['heading']),
            *paragraphs(metadata_text(photo), sty['small']),
            *paragraphs(f"作者：{photo['author']} ｜ 授权：{photo['license']}", sty['small']),
            Paragraph(f'<link href="{escaped(photo["source"])}" color="#356b70">'
                      f'Commons文件页：{escaped(photo["commons_title"])}</link>', sty['small'])]
    if photo.get('license_url'):
        rows.append(Paragraph(f'<link href="{escaped(photo["license_url"])}" color="#356b70">'
                              f'许可证：{escaped(photo["license_url"])}</link>', sty['small']))
    rows.extend(paragraphs('本期JPG为Commons缩略版本，未裁切、未调色。原图参数与教学建议分开；'
                           '未提供字段不补造。作者意图、精确焦点和处理过程未经证实的部分均按观察或推断讨论。',
                           sty['small']))
    return rows


def scaled_image(path, width, height):
    with PILImage.open(path) as image:
        w, h = image.size
    ratio = min(width / w, height / h)
    result = Image(str(path), width=w * ratio, height=h * ratio)
    result.hAlign = 'CENTER'
    return result


def build_topic(folder, repo, issue, source_by_path, sty):
    title, chapters = manuscripts(folder / '解读原稿.md')
    if len(chapters) != 5:
        raise ValueError(f'{title}: expected 5 photos, got {len(chapters)}')
    story = [OutlineParagraph(escaped(title), sty['title'], 'topic', 0),
             Paragraph('第45周 · 5张范例 · 每张九项深入解读', sty['label'])]
    introductions = [
        ('读这份点评的方法', '先看照片五秒，说出第一视觉落点和整体感受，再读文字。'
         '每张依次分为三页：明暗与清晰；快门、构图、色彩与光线；机位、主题与自己的练习。'
         '阅读不等于接受唯一答案，试着用图中证据支持或修正自己的判断。'),
        ('哪些是事实，哪些是解释', '曝光参数来自sources.json保存的Commons原图元数据；'
         '颜色、边缘与亮暗是现有图像上的观察；光向、焦点与氛围解释在证据不足时标明可能性。'
         'Z30设置均为教学建议，不能冒充作者使用过的参数。'),
        ('先借鉴原则，再考虑复制外观', '手机、小型相机和不同画幅镜头不能直接照抄焦距或光圈。'
         '套头不够微距、没有同样物候或没有相同场所时，可以换对象、距离与取景范围。'
         '每张最后都有可完成的对照练习和成片检查。'),
        ('本题五张的阅读顺序', '\n'.join(chapter for chapter, _ in chapters)),
        ('素材与修订', '照片与许可沿用原期，未新增替换照片。2026-11-10更正版重写全部九项解读，'
         '每张约1200汉字。Markdown原稿与PDF一起保存，便于搜索、引用和后续更正。'),
    ]
    for heading, text in introductions:
        story += section(heading, text, sty)
    story.append(PageBreak())
    counts = []
    for number, (chapter_title, sections) in enumerate(chapters, 1):
        expected = [str(n) + '．' for n in range(1, 10)]
        if len(sections) != 9 or any(not h.startswith(prefix)
                                      for (h, _), prefix in zip(sections, expected)):
            raise ValueError(f'{title}/{number:02}: incomplete nine-part analysis')
        photo_path = folder / f'{number:02}.jpg'
        photo = source_by_path[str(photo_path.relative_to(repo))]
        cjk = len(re.findall(r'[\u3400-\u9fff]', ''.join(t for _, t in sections)))
        if cjk < 1000:
            raise ValueError(f'{title}/{number:02}: only {cjk} Chinese characters')
        counts.append({'photo': str(photo_path.relative_to(repo)), 'analysis_hanzi': cjk,
                       'sections': len(sections)})
        story.extend([
            OutlineParagraph(escaped(chapter_title), sty['photo_title'], f'photo-{number}', 1),
            Paragraph('观察页 · 先看图，再读明暗与清晰', sty['label']),
            scaled_image(photo_path, PAGE_W - 2 * MARGIN, 255),
            Paragraph(f'{number:02}.jpg · {escaped(photo["author"])} · {escaped(photo["license"])}',
                      sty['caption']),
        ])
        for heading, text in sections[:2]:
            story += section(heading, text, sty)
        story.extend([PageBreak(), Paragraph(escaped(chapter_title), sty['photo_title']),
                      Paragraph('关系页 · 时间、构图、色彩与照明', sty['label'])])
        for heading, text in sections[2:6]:
            story += section(heading, text, sty)
        story.extend([PageBreak(), Paragraph(escaped(chapter_title), sty['photo_title']),
                      Paragraph('实践页 · 机位、解读与自己的拍摄', sty['label'])])
        for heading, text in sections[6:]:
            story += section(heading, text, sty)
        story += attribution(photo, sty)
        if number < len(chapters):
            story.append(PageBreak())
    output = folder / f'{title}_点评与思考.pdf'
    IssueDocument(output, issue, title).build(story)
    return output, counts


def build_guide(issue_dir, sty):
    title, chapters = manuscripts(issue_dir / '本周导读.md')
    story = []
    for index, (chapter, sections) in enumerate(chapters):
        if index:
            story.append(PageBreak())
        story.append(OutlineParagraph(escaped(chapter), sty['title'], f'guide-{index}', 0))
        story.append(Paragraph(escaped(title), sty['label']))
        for heading, text in sections:
            story += section(heading, text, sty)
    output = issue_dir / '本周导读.pdf'
    IssueDocument(output, issue_dir.name, title).build(story)
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('issue', type=Path)
    parser.add_argument('--font', type=Path, required=True)
    args = parser.parse_args()
    issue_dir = args.issue.resolve()
    repo = issue_dir.parent
    pdfmetrics.registerFont(TTFont(FONT, str(args.font)))
    sty = styles()
    manifest = json.loads((issue_dir / 'sources.json').read_text(encoding='utf-8'))
    by_path = {photo['path']: photo for photo in manifest['photos']}
    outputs = [build_guide(issue_dir, sty)]
    stats = []
    for folder in sorted(p.parent for p in issue_dir.glob('*/解读原稿.md')):
        output, counts = build_topic(folder, repo, issue_dir.name, by_path, sty)
        outputs.append(output)
        stats.extend(counts)
    if len(outputs) != 5 or len(stats) != 20:
        raise ValueError('Expected one guide, four topics and twenty photos')
    print(json.dumps({'pdfs': [str(p.relative_to(repo)) for p in outputs],
                      'photos': stats, 'total_analysis_hanzi': sum(s['analysis_hanzi'] for s in stats)},
                     ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
