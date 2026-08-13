"""
Скрипт автогенерации новой статьи для сайта "Блок·Ноль".

Как это работает:
1. Скрипт обращается к Anthropic API с чётким промптом (тема, тон, ограничения).
2. Получает текст статьи в формате Markdown.
3. Добавляет новую запись в articles.json (со следующим номером блока).
4. Дальше нужно запустить build.py, чтобы пересобрать HTML-страницы.

Требования:
- pip install anthropic
- переменная окружения ANTHROPIC_API_KEY (свой ключ с console.anthropic.com)

Для автоматического запуска по расписанию используйте GitHub Actions
(см. workflow .github/workflows/publish.yml и инструкцию DEPLOY.md).
"""

import json
import os
import re
import hashlib
import datetime
import random
import sys

import anthropic

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ARTICLES_JSON = os.path.join(BASE_DIR, "articles.json")

# Темы для генерации — можно расширять этот список.
# Скрипт будет каждый раз выбирать случайную ещё не использованную тему.
TOPICS = [
    {
        "title": "Что такое биткоин и почему он появился первым",
        "type": "lesson",
        "tags": ["основы", "для новичков"],
    },
    {
        "title": "Что такое смарт-контракты простыми словами",
        "type": "lesson",
        "tags": ["основы", "для новичков"],
    },
    {
        "title": "Чем стейблкоин отличается от обычной криптовалюты",
        "type": "lesson",
        "tags": ["основы", "для новичков"],
    },
    {
        "title": "Частые схемы обмана в крипте и как их распознать",
        "type": "lesson",
        "tags": ["безопасность"],
    },
    {
        "title": "Комиссии за перевод: почему они бывают такими разными",
        "type": "lesson",
        "tags": ["основы"],
    },
]

SYSTEM_PROMPT = """Ты — автор образовательного сайта о криптовалютах для новичков на русском языке.
Пиши понятно, спокойно, без хайпа и без обещаний дохода.
СТРОГО ЗАПРЕЩЕНО:
- давать инвестиционные советы или рекомендации купить/продать что-либо;
- обещать или прогнозировать рост цены;
- преувеличивать доходность или называть конкретные цифры дохода;
- использовать кликбейт и агрессивный маркетинговый тон.
Формат ответа — только Markdown, без обёртки в кодовые блоки, начиная сразу с текста статьи
(без заголовка h1 — он добавляется отдельно). Используй подзаголовки ## и списки где уместно.
Объём — 350-550 слов."""


def slugify(title: str) -> str:
    translit = {
        "а":"a","б":"b","в":"v","г":"g","д":"d","е":"e","ё":"e","ж":"zh","з":"z",
        "и":"i","й":"y","к":"k","л":"l","м":"m","н":"n","о":"o","п":"p","р":"r",
        "с":"s","т":"t","у":"u","ф":"f","х":"h","ц":"ts","ч":"ch","ш":"sh","щ":"sch",
        "ъ":"","ы":"y","ь":"","э":"e","ю":"yu","я":"ya",
    }
    s = title.lower()
    s = "".join(translit.get(ch, ch) for ch in s)
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s[:60]


def next_block_num(articles):
    nums = [int(a["block_num"]) for a in articles]
    return f"{(max(nums) + 1) if nums else 1:03d}"


def make_hash(seed: str) -> str:
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:8]


def generate_article(topic: dict, client: "anthropic.Anthropic") -> dict:
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1500,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": f"Напиши статью на тему: «{topic['title']}»."}],
    )
    body_md = "".join(block.text for block in resp.content if block.type == "text").strip()

    # Простое резюме для excerpt — первая содержательная фраза
    excerpt_source = re.sub(r"^#.*$", "", body_md, flags=re.MULTILINE).strip()
    first_para = next((p for p in excerpt_source.split("\n\n") if p.strip() and not p.startswith("#")), "")
    excerpt = re.sub(r"[*_`]", "", first_para).strip()
    if len(excerpt) > 160:
        excerpt = excerpt[:157].rsplit(" ", 1)[0] + "..."

    return {
        "slug": slugify(topic["title"]),
        "type": topic["type"],
        "tags": topic["tags"],
        "title": topic["title"],
        "excerpt": excerpt,
        "body_markdown": body_md,
        "disclosure": "Статья носит образовательный характер и не является инвестиционной рекомендацией. Решения принимайте самостоятельно, оценив риски.",
        "affiliate": None,
    }


def main():
    with open(ARTICLES_JSON, encoding="utf-8") as f:
        articles = json.load(f)

    used_titles = {a["title"] for a in articles}
    available = [t for t in TOPICS if t["title"] not in used_titles]
    if not available:
        print("Все темы из списка TOPICS уже использованы — добавьте новые в TOPICS.")
        sys.exit(0)

    topic = random.choice(available)
    client = anthropic.Anthropic()  # берёт ключ из переменной окружения ANTHROPIC_API_KEY

    new_article = generate_article(topic, client)
    new_article["block_num"] = next_block_num(articles)
    new_article["date"] = datetime.date.today().isoformat()
    new_article["hash"] = make_hash(new_article["slug"] + new_article["date"])

    articles.append(new_article)
    with open(ARTICLES_JSON, "w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)

    print(f"Добавлена статья: блок {new_article['block_num']} — {new_article['title']}")


if __name__ == "__main__":
    main()
