# -*- coding: utf-8 -*-
"""
Site builder for nadavfried.co.il
Runs on Netlify on every change (build command: python3 build.py, publish dir: dist).
- Copies the static site from site/ to dist/
- Renders every article in content/articles/*.md into its own page (existing design)
- Rebuilds the articles page (filters + grid) and the homepage articles carousel
- Writes sitemap.xml and robots.txt
No external dependencies: the Markdown converter is bundled in vendor/.
"""
import os, sys, re, json, glob, shutil, html, datetime, urllib.parse

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, 'vendor'))
import markdown  # bundled

SITE_URL = 'https://nadavfried.co.il'
SRC = os.path.join(ROOT, 'site')
DIST = os.path.join(ROOT, 'dist')
CAROUSEL_MAX = 12
DEFAULT_DISCLAIMER = 'אין לראות באמור המלצה להשקעה או תחליף לייעוץ מותאם אישית'

COLORS = {'gold': 'var(--gold)', 'brand': 'var(--brand)', 'amber': 'var(--amber)',
          'brand-strong': 'var(--brand-strong)'}


def read(p):
    with open(p, encoding='utf-8') as f:
        return f.read()


def write(p, s):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, 'w', encoding='utf-8') as f:
        f.write(s)


def esc(s):
    return html.escape(str(s or ''), quote=True)


# ---------------------------------------------------------------- data
ICONS = json.loads(read(os.path.join(ROOT, 'data', 'icons.json')))
SN = json.loads(read(os.path.join(ROOT, 'data', 'snippets.json')))
CATS = {c['name']: c for c in json.loads(read(os.path.join(ROOT, 'data', 'categories.json')))['categories']}
DEFAULT_ICON = next(iter(ICONS.values()))


def cat_color(name):
    c = CATS.get(name) or {}
    return COLORS.get(c.get('color'), 'var(--brand)')


def cat_icon(name):
    c = CATS.get(name) or {}
    return ICONS.get(c.get('icon'), DEFAULT_ICON)


def parse_article(path):
    raw = read(path).lstrip('﻿').lstrip()
    if raw.startswith('{'):
        meta, end = json.JSONDecoder().raw_decode(raw)
        body = raw[end:]
    elif raw.startswith('---'):  # simple YAML front matter fallback (key: value)
        _, fm, body = raw.split('---', 2)
        meta = {}
        for line in fm.splitlines():
            if ':' in line:
                k, v = line.split(':', 1)
                v = v.strip().strip('"').strip("'")
                meta[k.strip()] = {'true': True, 'false': False}.get(v, v)
    else:
        meta, body = {}, raw
    meta['body'] = body.strip('\n')
    if not meta.get('slug'):
        meta['slug'] = os.path.splitext(os.path.basename(path))[0]
    meta['slug'] = slugify(meta['slug'])
    meta['date'] = str(meta.get('date') or '2000-01-01')[:10]
    return meta


def slugify(s):
    s = str(s).strip().lower()
    s = re.sub(r'\.html?$', '', s)
    s = re.sub(r'[\s_]+', '-', s)
    s = re.sub(r'[^\w\-֐-׿]', '', s)
    s = re.sub(r'-{2,}', '-', s).strip('-')
    return s or 'article'


def page_url(slug):
    return slug + '.html'


def abs_url(u):
    if not u:
        return ''
    if u.startswith('http'):
        return u
    return SITE_URL + '/' + urllib.parse.quote(u.lstrip('/'))


# ---------------------------------------------------------------- markdown -> html in site style
MD_EXTS = ['markdown.extensions.' + e for e in
           ('fenced_code', 'footnotes', 'attr_list', 'def_list', 'tables', 'abbr', 'md_in_html', 'sane_lists')]


def md_to_html(md):
    h = markdown.markdown(md, extensions=MD_EXTS, output_format='html')
    h = re.sub(r'<h([23])>', r"<h\1 class='art-h'>", h)
    h = h.replace('<ul>', "<ul class='art-ul'>")
    # images: lazy + alt fallback
    h = re.sub(r'<img ', '<img loading="lazy" ', h)
    # external links open in new tab; internal links stay
    def fix_link(m):
        tag = m.group(0)
        href = re.search(r'href="([^"]*)"', tag)
        if href and href.group(1).startswith('http') and 'nadavfried.co.il' not in href.group(1):
            tag = tag[:-1] + ' target="_blank" rel="noopener">'
        return tag
    h = re.sub(r'<a [^>]*>', fix_link, h)
    return h


# ---------------------------------------------------------------- article page
def head_meta(a):
    title = (a.get('seo_title') or a.get('title') or '').strip()
    desc = (a.get('description') or a.get('subtitle') or '').strip()
    url = SITE_URL + '/' + urllib.parse.quote(page_url(a['slug']))
    img = abs_url(a.get('og_image') or a.get('image')) or SITE_URL + '/og-image.jpg'
    t = esc(title) + ' · נדב פריד'
    return '\n'.join([
        f'<title>{t}</title>',
        '<link rel="icon" href="favicon.ico" sizes="any">',
        '<link rel="icon" type="image/svg+xml" href="favicon.svg">',
        '<link rel="icon" type="image/png" sizes="32x32" href="favicon-32.png">',
        '<link rel="icon" type="image/png" sizes="192x192" href="favicon-192.png">',
        '<link rel="apple-touch-icon" href="apple-touch-icon.png">',
        f'<meta name="description" content="{esc(desc)}">',
        f'<link rel="canonical" href="{esc(url)}">',
        '<meta property="og:type" content="article">',
        '<meta property="og:site_name" content="נדב פריד · תכנון וייעוץ פיננסי">',
        f'<meta property="og:title" content="{esc(title)}">',
        f'<meta property="og:description" content="{esc(desc)}">',
        f'<meta property="og:image" content="{esc(img)}">',
        f'<meta property="og:url" content="{esc(url)}">',
        f'<meta property="article:published_time" content="{esc(a["date"])}">',
        '<meta name="twitter:card" content="summary_large_image">',
        f'<meta name="twitter:title" content="{esc(title)}">',
        f'<meta name="twitter:description" content="{esc(desc)}">',
        f'<meta name="twitter:image" content="{esc(img)}">',
        '<script type="application/ld+json">' + json.dumps({
            '@context': 'https://schema.org', '@type': 'Article',
            'headline': title, 'description': desc, 'image': img,
            'datePublished': a['date'], 'mainEntityOfPage': url,
            'author': {'@type': 'Person', 'name': 'נדב פריד'},
            'publisher': {'@type': 'Organization', 'name': 'נדב פריד · תכנון וייעוץ פיננסי'}},
            ensure_ascii=False) + '</script>',
    ])


def article_block(a):
    c = cat_color(a.get('category'))
    img = a.get('image') or ''
    body = md_to_html(a['body'])
    dtext = a.get('disclaimer', DEFAULT_DISCLAIMER)
    if dtext is True:
        dtext = DEFAULT_DISCLAIMER
    disc = f"<p class='art-disc'>{esc(dtext)}</p>" if dtext else ''
    src = ''
    if a.get('source_url'):
        src = (f'<hr class="art-hr">\n    <div class="post-source"><a href="{esc(a["source_url"])}" target="_blank" '
               f'rel="noopener">לצפייה בפוסט המקורי בפייסבוק ←</a></div>')
    postnav = re.sub(r'--c:[^;"]+', '--c:' + c, SN['postnav'])
    hero_img = f'<div class="post-hero-img" style="background-image:url({esc(img)})"></div>' if img else ''
    return f'''<!-- ARTICLE -->
<article class="post">
  <div class="post-hero" style="--c:{c}">
    {hero_img}
    <div class="post-hero-scrim"></div>
    <div class="container">
      <a class="post-crumb" href="articles.html"><span class="pc-ic">{SN['crumb']}</span>חזרה לכל המאמרים</a>
      <span class="post-cat">{cat_icon(a.get('category'))}{esc(a.get('category'))}</span>
      <h1 class="post-title">{esc(a.get('title'))}</h1>
      {f'<p class="post-sub">{esc(a.get("subtitle"))}</p>' if a.get('subtitle') else ''}
    </div>
  </div>
  <div class="container post-body" style="--c:{c}">
{body}
{disc}
    {src}
  </div>
  {postnav}
</article>'''


# ---------------------------------------------------------------- cards
def card(a):
    c = cat_color(a.get('category'))
    t = esc(a.get('title'))
    return (f'        <a class="art-card" data-topic="{esc(a.get("category"))}" style="--c:{c}" href="{esc(page_url(a["slug"]))}">\n'
            f'          <div class="art-ctop"><h3 class="art-title">{t}</h3><span class="art-more">לקריאת המאמר{SN["artmore"]}</span></div>\n'
            f'          <div class="art-cimg"><img src="{esc(a.get("image"))}" alt="{t}" loading="lazy"><span class="art-ribbon">{esc(a.get("category"))}</span></div>\n'
            f'        </a>')


# ---------------------------------------------------------------- build
def main():
    if os.path.isdir(DIST):
        shutil.rmtree(DIST)
    shutil.copytree(SRC, DIST)
    for extra in ('admin', 'uploads'):
        p = os.path.join(ROOT, extra)
        if os.path.isdir(p):
            shutil.copytree(p, os.path.join(DIST, extra), dirs_exist_ok=True)

    arts = [parse_article(p) for p in glob.glob(os.path.join(ROOT, 'content', 'articles', '*.md'))]
    arts = [a for a in arts if not a.get('draft')]
    arts.sort(key=lambda a: (a['date'], a['slug']), reverse=True)
    seen = set()
    for a in arts:
        if a['slug'] in seen:
            a['slug'] = a['slug'] + '-' + a['date'].replace('-', '')
        seen.add(a['slug'])

    tpl = read(os.path.join(ROOT, 'templates', 'article.html'))
    for a in arts:
        page = tpl.replace('{{HEAD_META}}', head_meta(a)).replace('{{ARTICLE}}', article_block(a))
        write(os.path.join(DIST, page_url(a['slug'])), page)

    # articles page
    cats_in_use = []
    for name in CATS:
        if any(a.get('category') == name for a in arts):
            cats_in_use.append(name)
    for a in arts:
        if a.get('category') and a['category'] not in cats_in_use:
            cats_in_use.append(a['category'])
    chips = '        <button class="chip active" data-filter="all">הכל</button>\n' + '\n'.join(
        f'        <button class="chip" data-filter="{esc(n)}">{esc(n)}</button>' for n in cats_in_use)
    ap = read(os.path.join(DIST, 'articles.html'))
    ap = ap.replace('<!--ARTICLES_FILTERS-->', chips).replace('<!--ARTICLES_GRID-->', '\n'.join(card(a) for a in arts))
    write(os.path.join(DIST, 'articles.html'), ap)

    # homepage carousel
    ip = read(os.path.join(DIST, 'index.html'))
    ip = ip.replace('<!--ARTICLES_CAROUSEL-->', '\n'.join(card(a) for a in arts[:CAROUSEL_MAX]))
    write(os.path.join(DIST, 'index.html'), ip)

    # sitemap + robots
    today = datetime.date.today().isoformat()
    static = [p for p in sorted(os.listdir(DIST)) if p.endswith('.html')
              and not any(p == page_url(a['slug']) for a in arts)]
    urls = []
    for p in static:
        loc = SITE_URL + '/' if p == 'index.html' else SITE_URL + '/' + urllib.parse.quote(p)
        urls.append(f'  <url><loc>{loc}</loc><lastmod>{today}</lastmod></url>')
    for a in arts:
        urls.append(f'  <url><loc>{SITE_URL}/{urllib.parse.quote(page_url(a["slug"]))}</loc><lastmod>{a["date"]}</lastmod></url>')
    write(os.path.join(DIST, 'sitemap.xml'),
          '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
          + '\n'.join(urls) + '\n</urlset>\n')
    write(os.path.join(DIST, 'robots.txt'),
          f'User-agent: *\nAllow: /\nDisallow: /admin/\n\nSitemap: {SITE_URL}/sitemap.xml\n')


    # internal links reference page for editors (noindex)
    rows = []
    names = {'index.html': 'דף הבית', 'about.html': 'מי אני', 'process.html': 'התהליך', 'articles.html': 'כל המאמרים',
             'testimonials.html': 'המלצות', 'calculator.html': 'מחשבון', 'accessibility.html': 'הצהרת נגישות',
             'privacy.html': 'מדיניות פרטיות'}
    for p in static:
        rows.append((names.get(p, p), p, 'עמוד'))
    for a in arts:
        rows.append((a.get('title', ''), page_url(a['slug']), a.get('category', '')))
    trs = '\n'.join(
        f'<tr><td>{esc(t)}</td><td>{esc(k)}</td><td><code>{esc(u)}</code></td>'
        f'<td><button onclick="navigator.clipboard.writeText(\'{esc(u)}\');this.textContent=\'הועתק ✓\'">העתקה</button></td></tr>'
        for t, u, k in rows)
    write(os.path.join(DIST, 'admin', 'links.html'), f"""<!doctype html><html lang="he" dir="rtl"><head><meta charset="utf-8">
<meta name="robots" content="noindex, nofollow"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>כתובות לקישורים פנימיים</title><style>
body{{font-family:Heebo,system-ui,sans-serif;margin:2rem auto;max-width:900px;padding:0 1rem;color:#2a1a10;background:#fffaf4}}
h1{{color:#d0672e}}p{{color:#6a5340}}table{{width:100%;border-collapse:collapse;background:#fff}}
th,td{{border:1px solid #ecdcca;padding:.55rem .7rem;text-align:right;font-size:.95rem}}th{{background:#fbeee0}}
code{{direction:ltr;display:inline-block;color:#b4521f}}button{{border:1px solid #d0672e;background:#fff;color:#d0672e;border-radius:8px;padding:.25rem .7rem;cursor:pointer;font-family:inherit}}
</style></head><body><h1>כתובות לקישורים פנימיים</h1>
<p>כדי לקשר מתוך כתבה: מסמנים מילה בעורך, לוחצים על כפתור הקישור, ומדביקים את הכתובת מהטבלה (למשל <code>article-1.html</code>). הרשימה מתעדכנת אוטומטית עם כל כתבה חדשה.</p>
<table><tr><th>שם</th><th>סוג / קטגוריה</th><th>כתובת</th><th></th></tr>
{trs}</table></body></html>""")

    print(f'Built {len(arts)} articles, {len(static)} static pages -> dist/')


if __name__ == '__main__':
    main()
