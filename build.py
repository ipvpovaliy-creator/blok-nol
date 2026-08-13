import json
import os
import markdown
from jinja2 import Environment, FileSystemLoader

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
ARTICLES_JSON = os.path.join(BASE_DIR, "articles.json")
OUT_ARTICLES_DIR = os.path.join(BASE_DIR, "articles")

env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))

def load_articles():
    with open(ARTICLES_JSON, encoding="utf-8") as f:
        data = json.load(f)
    for a in data:
        a["body_html"] = markdown.markdown(a["body_markdown"], extensions=["extra"])
    return data

def build():
    articles = load_articles()
    articles.sort(key=lambda a: a["block_num"], reverse=True)
    lessons = [a for a in articles if a["type"] == "lesson"]
    reviews = [a for a in articles if a["type"] == "review"]

    latest_hash = articles[0]["hash"] if articles else "genesis"

    # Homepage
    index_tpl = env.get_template("index.html")
    index_html = index_tpl.render(root="", chain_hash=latest_hash, lessons=lessons, reviews=reviews)
    with open(os.path.join(BASE_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(index_html)

    # Article pages
    os.makedirs(OUT_ARTICLES_DIR, exist_ok=True)
    article_tpl = env.get_template("article.html")
    for a in articles:
        html = article_tpl.render(root="../", chain_hash=latest_hash, a=a)
        with open(os.path.join(OUT_ARTICLES_DIR, f"{a['slug']}.html"), "w", encoding="utf-8") as f:
            f.write(html)

    print(f"Собрано: главная + {len(articles)} статей ({len(lessons)} уроков, {len(reviews)} обзоров)")

if __name__ == "__main__":
    build()
