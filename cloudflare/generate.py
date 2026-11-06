from pathlib import Path
from datetime import datetime, timezone
from html import escape
from html.parser import HTMLParser
from urllib.parse import quote
import re
import shutil
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / 'articles'
OUTPUT = ROOT / 'cloudflare' / 'site'
SITE_URL = 'https://window-repair-journal.pages.dev'
SITE_NAME = 'Window Repair Journal'
DESCRIPTION = 'Practical window repair, glass care, and maintenance guides for homeowners.'

class ArticleParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title = ''
        self.date = ''
        self.content = []
        self.capture = None
        self.depth = 0
    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if tag == 'h1' and not self.title:
            self.capture = 'title'
        elif tag == 'time' and not self.date:
            self.capture = 'date'
            self.date = attrs_dict.get('datetime', '')
        elif tag == 'div' and 'article-content' in attrs_dict.get('class', '').split() and self.depth == 0:
            self.depth = 1
            return
        if self.depth:
            if tag == 'div': self.depth += 1
            self.content.append(self.get_starttag_text())
    def handle_startendtag(self, tag, attrs):
        if self.depth: self.content.append(self.get_starttag_text())
    def handle_endtag(self, tag):
        if self.depth:
            if tag == 'div':
                self.depth -= 1
                if self.depth == 0: return
            self.content.append(f'</{tag}>')
        if tag in ('h1', 'time') and self.capture:
            self.capture = None
    def handle_data(self, data):
        if self.capture == 'title': self.title += data
        elif self.capture == 'date' and not self.date: self.date += data
        if self.depth: self.content.append(escape(data))
    def handle_entityref(self, name):
        if self.depth: self.content.append(f'&{name};')
    def handle_charref(self, name):
        if self.depth: self.content.append(f'&#{name};')

CSS = '''
:root{--navy:#203b56;--sand:#d7b98c;--cream:#f5f3ee;--ink:#253443;--muted:#63707b}
*{box-sizing:border-box}body{margin:0;background:var(--cream);color:var(--ink);font:16px/1.75 system-ui,-apple-system,Segoe UI,Arial,sans-serif}
a{color:var(--navy)}.top{background:var(--navy);color:white}.wrap{max-width:1120px;margin:auto;padding:0 24px}
.nav{display:flex;align-items:center;justify-content:space-between;gap:24px;padding:22px 0}.brand{font-size:21px;font-weight:750;color:white;text-decoration:none}.nav nav{display:flex;gap:20px}.nav nav a{color:#fff;text-decoration:none;font-size:14px}
.hero{padding:64px 0 72px}.eyebrow{text-transform:uppercase;letter-spacing:.15em;color:var(--sand);font-size:12px;font-weight:700}.hero h1{font-size:clamp(32px,5vw,52px);max-width:740px;line-height:1.15;margin:12px 0}.hero p{max-width:650px;color:#dce5ed}
main{padding:46px 0 70px}.section-title{font-size:28px;color:var(--navy);margin:0 0 25px}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:22px}.card{background:white;border:1px solid #e8e3db;border-radius:12px;padding:27px;box-shadow:0 5px 22px #203b5609}.card:before{content:'';display:block;background:var(--sand);width:45px;height:4px;border-radius:8px;margin-bottom:18px}.card h2{font-size:21px;line-height:1.35;margin:8px 0}.card h2 a{text-decoration:none}.card p{color:var(--muted);font-size:14px}.date{font-size:13px;color:var(--muted)}.read{font-weight:650;text-decoration:none}
.paper{max-width:850px;margin:0 auto;background:white;border-radius:12px;padding:clamp(24px,5vw,56px)}.paper h1{font-size:clamp(29px,4vw,43px);line-height:1.2;color:var(--navy)}.article-content{overflow-wrap:anywhere}.article-content img{max-width:100%;height:auto}.article-content a{text-decoration:underline}.article-content pre,.article-content table{max-width:100%;overflow-x:auto}.article-content table{display:block;border-collapse:collapse}.article-content td,.article-content th{border:1px solid #ddd;padding:9px}.article-content blockquote{border-left:4px solid var(--sand);padding-left:20px;margin-left:0}.article-content h2,.article-content h3{color:var(--navy)}
.footer{background:var(--navy);color:#dce5ed;padding:30px 0;text-align:center;font-size:14px}.footer a{color:white}
@media(max-width:650px){.grid{grid-template-columns:1fr}.nav{align-items:flex-start;flex-direction:column;gap:8px}.hero{padding:35px 0 45px}}
'''

def layout(title, description, canonical, body, kind='website'):
    title = title.strip() or SITE_NAME
    desc = description.strip()[:155] or DESCRIPTION
    year = datetime.now(timezone.utc).year
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(title)}</title><meta name="description" content="{escape(desc,quote=True)}">
<meta name="robots" content="index,follow"><link rel="canonical" href="{escape(canonical,quote=True)}">
<meta property="og:type" content="{kind}"><meta property="og:site_name" content="{escape(SITE_NAME,quote=True)}">
<meta property="og:title" content="{escape(title,quote=True)}"><meta property="og:description" content="{escape(desc,quote=True)}"><meta property="og:url" content="{escape(canonical,quote=True)}">
<meta name="twitter:card" content="summary"><meta name="twitter:title" content="{escape(title,quote=True)}"><meta name="twitter:description" content="{escape(desc,quote=True)}">
<link rel="stylesheet" href="/style.css"></head><body>
<header class="top"><div class="wrap nav"><a class="brand" href="/">{escape(SITE_NAME)}</a><nav aria-label="Main navigation"><a href="/">Home</a><a href="/#articles">Articles</a></nav></div></header>
{body}
<footer class="footer"><div class="wrap">&copy; {year} {escape(SITE_NAME)} &middot; Practical guides for homeowners</div></footer></body></html>'''

def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / 'articles').mkdir(exist_ok=True)
    (OUTPUT / 'style.css').write_text(CSS, encoding='utf-8')
    cards = []
    urls = [SITE_URL + '/']
    for file in sorted(SOURCE.glob('issue-*.html'), key=lambda p: int(re.search(r'issue-(\d+)',p.name).group(1)), reverse=True) if SOURCE.exists() else []:
        parser = ArticleParser()
        parser.feed(file.read_text(encoding='utf-8'))
        title = parser.title.strip() or 'Untitled article'
        date = parser.date.strip()
        content = ''.join(parser.content)
        url = f'{SITE_URL}/articles/{quote(file.name)}'
        desc = re.sub(r'\s+', ' ', re.sub(r'<[^>]*>', ' ', content)).strip()[:155] or DESCRIPTION
        body = f'<main class="wrap"><article class="paper"><p class="date">{escape(date)}</p><h1>{escape(title)}</h1><div class="article-content">{content}</div></article></main>'
        (OUTPUT / 'articles' / file.name).write_text(layout(f'{title} | {SITE_NAME}', desc, url, body, 'article'), encoding='utf-8')
        cards.append(f'<article class="card"><p class="date">{escape(date)}</p><h2><a href="/articles/{quote(file.name)}">{escape(title)}</a></h2><p>{escape(desc)}</p><a class="read" href="/articles/{quote(file.name)}">Read article &rarr;</a></article>')
        urls.append(url)
    for old in (OUTPUT / 'articles').glob('issue-*.html'):
        if old.name not in {u.rsplit('/',1)[-1] for u in urls}: old.unlink()
    listing = '<div class="grid">' + ''.join(cards) + '</div>' if cards else '<p>No articles published yet.</p>'
    body = '<section class="top"><div class="wrap hero"><span class="eyebrow">Window care & maintenance</span><h1>Practical Window Care & Repair Guides</h1><p>Clear, useful articles on window repair, glass maintenance, and everyday home comfort.</p></div></section><main class="wrap" id="articles"><h2 class="section-title">Latest Articles</h2>' + listing + '</main>'
    (OUTPUT / 'index.html').write_text(layout(f'{SITE_NAME} | Window Repair & Maintenance Guides', DESCRIPTION, SITE_URL+'/', body),encoding='utf-8')
    (OUTPUT / 'robots.txt').write_text('User-agent: *\nAllow: /\nSitemap: '+SITE_URL+'/sitemap.xml\n',encoding='utf-8')
    sitemap = ET.Element('urlset', xmlns='http://www.sitemaps.org/schemas/sitemap/0.9')
    for url in urls:
        node = ET.SubElement(sitemap,'url')
        ET.SubElement(node,'loc').text=url
    ET.ElementTree(sitemap).write(OUTPUT/'sitemap.xml',encoding='utf-8',xml_declaration=True)
    print(f'Cloudflare site generated: {len(cards)} articles')

if __name__ == '__main__': main()
