import os
import re
import html
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

import requests

OWNER = "hofman0107-cell"
REPO = "window-repair-journal"
SITE_NAME = "Window Repair Journal"
BASE_URL = f"https://{OWNER}.github.io/{REPO}"

API_URL = (
    f"https://api.github.com/repos/{OWNER}/{REPO}/issues"
)

HEADERS = {
    "Accept": "application/vnd.github+json",
    "Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}",
    "X-GitHub-Api-Version": "2022-11-28",
}

ARTICLES_DIR = Path("articles")
ARTICLES_DIR.mkdir(exist_ok=True)


def safe_html(text):
    return html.escape(str(text or ""), quote=True)


def render_content(content):
    # Preserve ordinary text and links without allowing
    # untrusted HTML from Issues to execute scripts.
    text = safe_html(content)

    text = re.sub(
        r"(https?://[^\s&lt;&gt;]+)",
        lambda match: (
            f'<a href="{match.group(1)}" '
            f'rel="nofollow noopener noreferrer">'
            f'{match.group(1)}</a>'
        ),
        text,
    )

    paragraphs = text.split("\n\n")
    return "\n".join(
        f"<p>{p.replace(chr(10), '<br>')}</p>"
        for p in paragraphs if p.strip()
    )


def page_template(title, content, date, canonical):
    title_html = safe_html(title)
    name_html = safe_html(SITE_NAME)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="index, follow">
<meta name="description" content="{safe_html(title)[:155]}">
<link rel="canonical" href="{canonical}">
<title>{title_html} | {name_html}</title>
<style>
body {{
  margin: 0;
  background: #f7f9f7;
  color: #29352f;
  font: 16px/1.8 Arial, sans-serif;
}}
header, footer {{
  padding: 24px;
  text-align: center;
  background: white;
}}
a {{ color: #315b43; }}
header a {{
  font-weight: bold;
  text-decoration: none;
}}
main {{
  max-width: 850px;
  margin: 40px auto;
  padding: 32px;
  background: white;
  border-radius: 10px;
}}
h1 {{ color: #315b43; line-height: 1.3; }}
time {{ color: #66756b; font-size: 14px; }}
.article-content {{
  overflow-wrap: anywhere;
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
<p><time datetime="{date}">{date}</time></p>
<div class="article-content">
{content}
</div>
</article>
</main>
<footer>&copy; {datetime.now(timezone.utc).year} {name_html}</footer>
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
            issue for issue in batch
            if "pull_request" not in issue
        )
        page += 1

    return issues


def publish():
    issues = get_issues()
    links = []

    for issue in issues:
        number = issue["number"]
        title = issue.get("title") or "Untitled"
        body = issue.get("body") or ""
        date = issue["created_at"][:10]

        filename = f"issue-{number}.html"
        canonical = f"{BASE_URL}/articles/{filename}"

        article_html = page_template(
            title, render_content(body), date, canonical
        )

        (ARTICLES_DIR / filename).write_text(
            article_html, encoding="utf-8"
        )

        links.append(
            f'<li><a href="articles/{filename}">'
            f'{safe_html(title)}</a> '
            f'<small>({date})</small></li>'
        )

    # Preserve a simple homepage with all published issues.
    listing = (
        "<ul>" + "\n".join(links) + "</ul>"
        if links else "<p>No articles published yet.</p>"
    )

    homepage = page_template(
        "Latest Articles",
        listing,
        datetime.now(timezone.utc).date().isoformat(),
        f"{BASE_URL}/",
    )

    Path("index.html").write_text(
        homepage, encoding="utf-8"
    )

    print(f"Published {len(issues)} articles.")


if __name__ == "__main__":
    publish()
