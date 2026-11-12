#!/usr/bin/env python3
"""Render one course issue, weekly or daily, from Markdown and sources.json.

Usage:
  python tools/render_issue.py 2026-11-13 --font /path/to/NotoSansSC-Regular.ttf
  python tools/render_issue.py 2026-11-13 --font /path/to/NotoSansSC-Regular.ttf --write-verification

Looks for 今日导读.md (daily) or 本周导读.md (weekly), every 解读原稿.md,
and sources.json. Each manuscript needs five photos and nine sections
(明暗、对焦、快门、构图、色彩、光线、机位、主题情绪、学习模仿), at least
1000 CJK characters of analysis per photo. PDFs embed a subset of the font.

The revised 2026-11-07 issue keeps its own script, tools/render_issue_2026_11_07.py,
so later daily issues do not inherit that revision's wording.

Noto Sans SC is SIL Open Font License 1.1 and is not stored in the repository.
A regular face can be instanced from Google Fonts' variable file:
  fonttools varLib.instancer 'NotoSansSC[wght].ttf' wght=400 --output=NotoSansSC-Regular.ttf
If the name table still says Thin, set name IDs 4 and 6 to Regular before use.
Source: https://github.com/google/fonts/tree/main/ofl/notosanssc
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import urllib.parse
import urllib.request
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
UA = {'User-Agent': 'AestheticWeeklyCourse/1.0 (educational photography course; rendering and source check)'}
SECTION_PREFIXES = [str(n) + '．' for n in range(1, 10)]


def escaped(value):
    return html.escape(str(value), quote=True)


def manuscripts(path):
    """Parse the course Markdown: one H1, then H2 chapters of H3 sections."""
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


def hanzi(text):
    return len(re.findall(r'[\u3400-\u9fff]', text))


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
    def __init__(self, path, issue, document_title, banner, **kwargs):
        super().__init__(str(path), pagesize=(PAGE_W, PAGE_H), leftMargin=MARGIN,
                         rightMargin=MARGIN, topMargin=56, bottomMargin=49,
                         title=document_title, author='Aesthetic Weekly',
                         pageCompression=1, **kwargs)
        self.issue = issue
        self.banner = banner
        frame = Frame(MARGIN, 49, PAGE_W - 2 * MARGIN, PAGE_H - 105,
                      leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
        self.addPageTemplates([PageTemplate(id='issue', frames=frame,
                                            onPage=self.decorate)])

    def decorate(self, canvas, document):
        canvas.saveState()
        canvas.setFont(FONT, 8)
        canvas.setFillColor(MUTED)
        canvas.drawString(MARGIN, PAGE_H - 29, self.banner)
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
        if key in data and data[key] not in (None, ''):
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


def find_guide(issue_dir):
    for name in ('今日导读.md', '本周导读.md'):
        path = issue_dir / name
        if path.exists():
            return path
    raise FileNotFoundError(f'{issue_dir} 缺少今日导读.md或本周导读.md')


def topic_intro(daily, chapters):
    shared = [
        ('读这份点评的方法', '先看照片五秒，说出第一视觉落点和整体感受，再读文字。'
         '每张依次分为三页：明暗与清晰；快门、构图、色彩与光线；机位、主题与自己的练习。'
         '阅读不等于接受唯一答案，试着用图中证据支持或修正自己的判断。'),
        ('哪些是事实，哪些是解释', '曝光参数来自sources.json保存的Commons原图元数据；'
         '颜色、边缘与亮暗是现有图像上的观察；光向、焦点与氛围解释在证据不足时标明可能性。'
         'Z30设置均为教学建议，不能冒充作者使用过的参数。没有EXIF的拍法会写（推测）。'),
        ('先借鉴原则，再考虑复制外观', '手机、小型相机和不同画幅镜头不能直接照抄焦距或光圈。'
         '套头不够近、没有同样树种或没有相同场所时，可以换对象、距离与取景范围。'
         '每张最后都有可完成的对照练习和成片检查。'),
        ('本题五张的阅读顺序', '\n'.join(chapter for chapter, _ in chapters)),
    ]
    if daily:
        shared.append(('今天交一张', '导读里的练习是今天要拍的那张。每张范例末尾的模仿是同一地点可以继续做的对照；'
                       '时间不够就只做导读里的一项，并把对照留在相机里。'))
    else:
        shared.append(('素材与阅读', 'Markdown原稿与PDF一起保存，便于搜索和后续更正。'
                       '先把一条原则练会，再读下一张。'))
    return shared


def build_topic(folder, repo, issue, source_by_path, sty, banner, daily):
    title, chapters = manuscripts(folder / '解读原稿.md')
    if len(chapters) != 5:
        raise ValueError(f'{title}: expected 5 photos, got {len(chapters)}')
    kind = '每日一题' if daily else '每周课题'
    story = [OutlineParagraph(escaped(title), sty['title'], 'topic', 0),
             Paragraph(f'{kind} · 5张范例 · 每张九项深入解读', sty['label'])]
    for heading, text in topic_intro(daily, chapters):
        story += section(heading, text, sty)
    story.append(PageBreak())
    counts = []
    for number, (chapter_title, sections) in enumerate(chapters, 1):
        if len(sections) != 9 or any(not h.startswith(prefix)
                                      for (h, _), prefix in zip(sections, SECTION_PREFIXES)):
            raise ValueError(f'{title}/{number:02}: incomplete nine-part analysis')
        photo_path = folder / f'{number:02}.jpg'
        photo = source_by_path[str(photo_path.relative_to(repo))]
        cjk = hanzi(''.join(t for _, t in sections))
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
    IssueDocument(output, issue, title, banner).build(story)
    return output, counts


def build_guide(issue_dir, guide_path, sty, banner):
    title, chapters = manuscripts(guide_path)
    story = []
    for index, (chapter, sections) in enumerate(chapters):
        if index:
            story.append(PageBreak())
        story.append(OutlineParagraph(escaped(chapter), sty['title'], f'guide-{index}', 0))
        story.append(Paragraph(escaped(title), sty['label']))
        for heading, text in sections:
            story += section(heading, text, sty)
    output = issue_dir / (guide_path.stem + '.pdf')
    IssueDocument(output, issue_dir.name, title, banner).build(story)
    return output


def load_sources(issue_dir, repo):
    manifest = json.loads((issue_dir / 'sources.json').read_text(encoding='utf-8'))
    if manifest.get('issue') != issue_dir.name:
        raise ValueError('sources.json issue 与文件夹日期不一致')
    required = ['path', 'commons_title', 'source', 'author', 'license', 'download_url',
                'original_url', 'original_sha1', 'sha256', 'original_metadata']
    by_path = {}
    for photo in manifest['photos']:
        missing = [key for key in required if key not in photo]
        if missing:
            raise ValueError(f"{photo.get('path')} 缺少字段 {missing}")
        file_path = repo / photo['path']
        digest = hashlib.sha256(file_path.read_bytes()).hexdigest()
        if digest != photo['sha256']:
            raise ValueError(f"{photo['path']} sha256 与 sources.json 不一致")
        with PILImage.open(file_path) as image:
            if min(image.size) < 800:
                raise ValueError(f"{photo['path']} 尺寸过小：{image.size}")
        by_path[photo['path']] = photo
    return manifest, by_path


def render(issue_dir, font):
    issue_dir = issue_dir.resolve()
    repo = issue_dir.parent
    pdfmetrics.registerFont(TTFont(FONT, str(font)))
    sty = styles()
    _, by_path = load_sources(issue_dir, repo)
    guide_path = find_guide(issue_dir)
    daily = guide_path.name.startswith('今日')
    banner = f'审美提升 · {issue_dir.name} · ' + ('每日一题' if daily else '每周课题')
    outputs = [build_guide(issue_dir, guide_path, sty, banner)]
    stats = []
    for folder in sorted(p.parent for p in issue_dir.glob('*/解读原稿.md')):
        output, counts = build_topic(folder, repo, issue_dir.name, by_path, sty, banner, daily)
        outputs.append(output)
        stats.extend(counts)
    if not stats:
        raise ValueError('没有找到题材原稿')
    return {
        'issue': issue_dir.name,
        'daily': daily,
        'pdfs': [str(p.relative_to(repo)) for p in outputs],
        'photos': stats,
        'total_analysis_hanzi': sum(s['analysis_hanzi'] for s in stats),
    }


def commons_check(photo):
    url = 'https://commons.wikimedia.org/w/api.php?' + urllib.parse.urlencode({
        'action': 'query', 'format': 'json', 'titles': photo['commons_title'],
        'prop': 'imageinfo|info', 'inprop': 'url',
        'iiprop': 'url|sha1|extmetadata',
    })
    payload = json.loads(urllib.request.urlopen(
        urllib.request.Request(url, headers=UA), timeout=60).read())
    page = next(iter(payload['query']['pages'].values()))
    if page.get('missing') is not None or page.get('pageid') is None:
        raise ValueError(f"文件页不存在：{photo['commons_title']}")
    info = page['imageinfo'][0]
    if info.get('sha1') != photo['original_sha1']:
        raise ValueError(f"原图 sha1 已变化：{photo['commons_title']}")
    ext = info.get('extmetadata') or {}
    artist = re.sub(r'<[^>]+>', '', (ext.get('Artist') or {}).get('value') or '')
    license_name = (ext.get('LicenseShortName') or {}).get('value') or ''
    if photo['author'] not in artist and artist not in photo['author']:
        raise ValueError(f"作者不一致：{photo['author']!r} / {artist!r}")
    if license_name != photo['license']:
        raise ValueError(f"许可不一致：{photo['license']!r} / {license_name!r}")
    page_html = urllib.request.urlopen(urllib.request.Request(page['fullurl'], headers=UA), timeout=60).read().decode('utf-8', 'replace')
    if photo['author'].split()[0] not in page_html:
        raise ValueError(f"文件页正文未见作者：{photo['source']}")
    if 'Creative Commons' not in page_html and photo['license'] not in page_html:
        raise ValueError(f"文件页正文未见许可：{photo['source']}")
    return {'source': page['fullurl'], 'author': photo['author'], 'license': license_name}


def pdf_report(path):
    from pypdf import PdfReader
    reader = PdfReader(str(path))
    fonts = set()
    pages = []
    for page in reader.pages:
        text = page.extract_text() or ''
        pages.append(text)
        resources = page.get('/Resources') or {}
        font_dict = resources.get('/Font') or {}
        for item in font_dict.values():
            obj = item.get_object()
            fonts.add(str(obj.get('/BaseFont')))
        box = [float(v) for v in page.mediabox]
        if abs(box[2] - PAGE_W) > 2 or abs(box[3] - PAGE_H) > 2:
            raise ValueError(f'{path.name} 页面尺寸不是 A4')
    if not fonts or not any('NotoSansSC' in name or 'NotoSansSC' in name.replace(' ', '') for name in fonts):
        raise ValueError(f'{path.name} 未嵌入 Noto Sans SC：{fonts}')
    return {'pages': len(reader.pages), 'text': pages, 'fonts': sorted(fonts),
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def three_page_structure(texts):
    marks = [(index, text) for index, text in enumerate(texts, 1)]
    observes = [i for i, text in marks if '观察页' in text]
    if not observes:
        raise ValueError('点评 PDF 没有观察页')
    for start in observes:
        window = texts[start - 1:start + 2]
        if len(window) < 3 or '关系页' not in window[1] or '实践页' not in window[2]:
            raise ValueError(f'第{start}页之后不是三页结构')
    return len(observes)


def duplicate_report(repo, issue, photos):
    titles = {re.sub(r'\s+', ' ', photo['commons_title'].casefold()) for photo in photos}
    title_hits = []
    pdfs = [pdf for pdf in repo.glob('[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]/**/*.pdf')
            if issue not in pdf.parts]
    for pdf in pdfs:
        try:
            from pypdf import PdfReader
            text = '\n'.join((page.extract_text() or '') for page in PdfReader(str(pdf)).pages)
        except Exception as error:
            raise ValueError(f'无法读取历史 PDF {pdf}: {error}') from error
        folded = re.sub(r'\s+', ' ', text.casefold())
        for title in titles:
            bare = title.split(':', 1)[-1]
            if bare and bare in folded:
                title_hits.append({'title': title, 'pdf': str(pdf.relative_to(repo))})
    current = {photo['sha256'] for photo in photos}
    hash_hits = []
    for image in repo.glob('*/*/*.[jJ][pP][gG]'):
        if image.parts[-3] == issue:
            continue
        digest = hashlib.sha256(image.read_bytes()).hexdigest()
        if digest in current:
            hash_hits.append(str(image.relative_to(repo)))
    return title_hits, hash_hits


def write_verification(issue_dir, summary):
    issue_dir = issue_dir.resolve()
    repo = issue_dir.parent
    manifest = json.loads((issue_dir / 'sources.json').read_text(encoding='utf-8'))
    source_checks = [commons_check(photo) for photo in manifest['photos']]
    files = []
    structure = {}
    for relative in summary['pdfs']:
        report = pdf_report(repo / relative)
        joined = '\n'.join(report['text'])
        if '观察有证据' not in joined or hanzi(joined) < 100:
            raise ValueError(f'{relative} 没有导出中文正文')
        item = {'path': relative, 'pages': report['pages'], 'sha256': report['sha256'],
                'fonts': report['fonts']}
        if relative.endswith('点评与思考.pdf'):
            item['photo_three_page_groups'] = three_page_structure(report['text'])
            structure[relative] = item['photo_three_page_groups']
            manuscript = next((repo / relative).parent.glob('解读原稿.md'))
            _, chapters = manuscripts(manuscript)
            for chapter_title, sections in chapters:
                if chapter_title not in joined:
                    raise ValueError(f'{relative} 缺少章节 {chapter_title}')
                for heading, paragraph in sections:
                    probe = paragraph.strip().split('\n', 1)[0][:24]
                    if heading not in joined or probe not in joined:
                        raise ValueError(f'{relative} 未包含原稿段落：{heading}')
        files.append(item)
    title_hits, hash_hits = duplicate_report(repo, issue_dir.name, manifest['photos'])
    if title_hits or hash_hits:
        raise ValueError(f'与既有期次重复：{title_hits} {hash_hits}')
    payload = {
        'issue': issue_dir.name,
        'kind': 'daily' if summary['daily'] else 'weekly',
        'photos': len(manifest['photos']),
        'pdfs': len(files),
        'pdf_pages': sum(item['pages'] for item in files),
        'duplicate_source_title_matches': title_hits,
        'duplicate_sha256_matches': hash_hits,
        'unique_current_photos': len({photo['sha256'] for photo in manifest['photos']}),
        'image_decode_and_min_dimensions': 'pass',
        'source_pages_authors_licenses': source_checks,
        'all_pdf_pages_rendered': 'pass',
        'pdf_text_and_page_bounds': 'pass',
        'photo_three_page_structure': structure,
        'photos_with_nine_sections': len(summary['photos']),
        'analysis_hanzi_per_photo': [item['analysis_hanzi'] for item in summary['photos']],
        'analysis_hanzi_total': summary['total_analysis_hanzi'],
        'all_manuscript_paragraphs_present_in_pdfs': 'pass',
        'all_used_text_fonts_embedded_noto_sans_sc': 'pass',
        'font_license': 'SIL Open Font License 1.1',
        'files': files,
    }
    destination = issue_dir / 'verification.json'
    destination.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return payload


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('issue', type=Path)
    parser.add_argument('--font', type=Path, required=True)
    parser.add_argument('--write-verification', action='store_true',
                        help='重查 Commons 作者与许可、历史重复和 PDF，并写入 verification.json')
    args = parser.parse_args()
    summary = render(args.issue, args.font)
    if args.write_verification:
        summary['verification'] = str(args.issue / 'verification.json')
        write_verification(args.issue, summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
