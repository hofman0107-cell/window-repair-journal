import os
import html
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

import requests
import markdown
import bleach

OWNER = "hofman0107-cell"
REPO = "window-repair-journal"
SITE_NAME = "Window Repair Journal"
BASE_URL = f"https://{OWNER}.github.io/{REPO}"

API_URL = f"https://api.github.com/repos/{OWNER}/{REPO}/issues"

HEADERS = {
    "Accept": "application/vnd.github+json",
    "Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}",
    "X-GitHub-Api-Version": "2022-11-28",
}

ARTICLES_DIR = Path("articles")
ARTICLES_DIR.mkdir(exist_ok=True)


def safe_html(value):
    return html.escape(str(value or ""), quote=True)


def allowed_attribute(tag, name, value):
    allowed = {
        "a": {"href", "title"},
        "img": {"src", "alt", "title", "width", "height"},
        "th": {"colspan", "rowspan"},
        "td": {"colspan", "rowspan"},
    }

    if name not in allowed.get(tag, set()):
        return False

    if name in ("href", "src"):
        url = value.strip()

        if not url:
            return False

        parsed = urlsplit(url)

        if parsed.scheme:
            return parsed.scheme.lower() in ("http", "https")

        return (
            url.startswith("/")
            and not url.startswith("//")
        ) or url.startswith("#")

    return True


def render_content(content):
    text = str(content or "").strip()

    if not text:
        return "<p>No content available.</p>"

    # Convert Markdown to HTML and preserve HTML formatting.
    rendered = markdown.markdown(
        text,
        extensions=[
            "extra",
            "sane_lists",
            "nl2br",
        ],
        output_format="html",
    )

    allowed_tags = [
        "p", "br",
        "h1", "h2", "h3", "h4", "h5", "h6",
        "strong", "b", "em", "i",
        "a", "img",
        "ul", "ol", "li",
        "blockquote",
        "code", "pre",
        "hr",
        "table", "thead", "tbody",
        "tr", "th", "td",
        "del", "s",
    ]

    cleaned = bleach.clean(
        rendered,
        tags=allowed_tags,
        attributes=allowed_attribute,
        protocols=["http", "https"],
        strip=True,
        strip_comments=True,
    )

    # Add safe attributes to links.
    cleaned = bleach.linkify(
        cleaned,
        callbacks=[
            bleach.callbacks.nofollow,
            bleach.callbacks.target_blank,
        ],
        skip_tags=["pre", "code"],
    )

    return cleaned


def page_template(title, content, date, canonical):
    title_html = safe_html(title)
    name_html = safe_html(SITE_NAME)
    canonical_html = safe_html(canonical)

    description = safe_html(title)[:155]

    year = datetime.now(timezone.utc).year

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">

<meta name="robots" content="index, follow">
<meta name="description" content="{description}">

<link rel="canonical" href="{canonical_html}">

<title>{title_html} | {name_html}</title>

<style>
* {{
  box-sizing: border-box;
}}

body {{
  margin: 0;
  background: #f7f9f7;
  color: #29352f;
  font: 16px/1.8 Arial, sans-serif;
}}

header, footer {{
  padding: 24px;
  text-align: center;
  background: #ffffff;
}}

header a {{
  color: #315b43;
  font-weight: bold;
  text-decoration: none;
  font-size: 20px;
}}

a {{
  color: #315b43;
}}

a:hover {{
  text-decoration: underline;
}}

main {{
  max-width: 850px;
  margin: 40px auto;
  padding: 32px;
  background: white;
  border-radius: 10px;
}}

h1 {{
  color: #315b43;
  line-height: 1.3;
}}

h2, h3, h4 {{
  color: #315b43;
  line-height: 1.4;
  margin-top: 28px;
}}

time {{
  color: #66756b;
  font-size: 14px;
}}

.article-content {{
  overflow-wrap: anywhere;
}}

.article-content p {{
  margin: 0 0 16px;
}}

.article-content img {{
  display: block;
  max-width: 100%;
  height: auto;
  margin: 20px 0;
  border-radius: 6px;
}}

.article-content a {{
  text-decoration: underline;
}}

.article-content ul,
.article-content ol {{
  padding-left: 24px;
}}

.article-content blockquote {{
  border-left: 4px solid #315b43;
  margin: 20px 0;
  padding: 10px 20px;
  background: #f7f9f7;
}}

.article-content pre {{
  overflow-x: auto;
  padding: 16px;
  background: #f1f3f1;
  border-radius: 6px;
}}

.article-content table {{
  border-collapse: collapse;
  width: 100%;
  display: block;
  overflow-x: auto;
}}

.article-content th,
.article-content td {{
  border: 1px solid #ddd;
  padding: 10px;
  text-align: left;
}}

.article-content hr {{
  border: 0;
  border-top: 1px solid #ddd;
  margin: 24px 0;
}}

footer {{
  color: #66756b;
}}

@media (max-width: 600px) {{
  main {{
    margin: 16px;
    padding: 20px;
  }}

  header, footer {{
    padding: 18px;
  }}

  h1 {{
    font-size: 26px;
  }}
}}
</style>
</head>

<body>

<header>
<a href="{BASE_URL}/">{name_html}</a>
</header>

<main>
<article>

<h1>{title_html}</h1>

<p>
<time datetime="{date}">{date}</time>
</p>

<div class="article-content">
{content}
</div>

</article>
</main>

<footer>
&copy; {year} {name_html}
</footer>

</body>
</html>"""


def get_issues():
    issues = []
    page = 1

    while True:
        response = requests.get(
            API_URL,
            headers=HEADERS,
            params={
                "state": "open",
                "per_page": 100,
                "page": page,
                "sort": "created",
                "direction": "desc",
            },
            timeout=30,
        )

        response.raise_for_status()
        batch = response.json()

        if not batch:
            break

        issues.extend(
            issue
            for issue in batch
            if "pull_request" not in issue
        )

        page += 1

    return issues


def publish():
    issues = get_issues()
    links = []
    active_files = set()

    for issue in issues:
        number = issue["number"]
        title = issue.get("title") or "Untitled"
        body = issue.get("body") or ""
        date = issue["created_at"][:10]

        filename = f"issue-{number}.html"
        active_files.add(filename)

        canonical = f"{BASE_URL}/articles/{filename}"

        content_html = render_content(body)

        article_html = page_template(
            title,
            content_html,
            date,
            canonical,
        )

        (ARTICLES_DIR / filename).write_text(
            article_html,
            encoding="utf-8",
        )

        links.append(
            f'<li><a href="articles/{filename}">'
            f'{safe_html(title)}</a> '
            f'<small>({date})</small></li>'
        )

    # Remove generated pages for closed or deleted Issues.
    for old_file in ARTICLES_DIR.glob("issue-*.html"):
        if old_file.name not in active_files:
            old_file.unlink()

    # Generate homepage.
    if links:
        listing = "<ul>\n" + "\n".join(links) + "\n</ul>"
    else:
        listing = "<p>No articles published yet.</p>"

    homepage = page_template(
        "Latest Articles",
        listing,
        datetime.now(timezone.utc).date().isoformat(),
        f"{BASE_URL}/",
    )

    Path("index.html").write_text(
        homepage,
        encoding="utf-8",
    )

    print(f"Published {len(issues)} articles.")


if __name__ == "__main__":
    publish()
