import os
import json
import urllib.request
import urllib.error
from datetime import datetime, timezone

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

SOURCES = [
    {
        "name": "Reddit r/artificial",
        "url": "https://www.reddit.com/r/artificial/top.json?limit=15&t=day",
        "type": "reddit"
    },
    {
        "name": "Reddit r/PPC",
        "url": "https://www.reddit.com/r/PPC/top.json?limit=10&t=day",
        "type": "reddit"
    },
    {
        "name": "Reddit r/marketing",
        "url": "https://www.reddit.com/r/marketing/top.json?limit=10&t=day",
        "type": "reddit"
    },
    {
        "name": "Hacker News",
        "url": "https://hnrss.org/frontpage?count=20",
        "type": "rss"
    }
]

def fetch_reddit(url):
    posts = []
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "DigestBot/1.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
        for item in data.get("data", {}).get("children", []):
            p = item.get("data", {})
            title = p.get("title", "")
            link = "https://reddit.com" + p.get("permalink", "")
            score = p.get("score", 0)
            if title and score > 10:
                posts.append({"title": title, "link": link})
    except Exception as e:
        print(f"Erro ao buscar {url}: {e}")
    return posts

def fetch_rss(url):
    posts = []
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "DigestBot/1.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            content = r.read().decode("utf-8")
        import re
        items = re.findall(r"<item>(.*?)</item>", content, re.DOTALL)
        for item in items[:15]:
            title_match = re.search(r"<title><!\[CDATA\[(.*?)\]\]></title>|<title>(.*?)</title>", item)
            link_match = re.search(r"<link>(.*?)</link>", item)
            if title_match and link_match:
                title = title_match.group(1) or title_match.group(2) or ""
                link = link_match.group(1) or ""
                if title and link:
                    posts.append({"title": title.strip(), "link": link.strip()})
    except Exception as e:
        print(f"Erro ao buscar RSS {url}: {e}")
    return posts

def collect_all_posts():
    all_posts = []
    for source in SOURCES:
        print(f"Buscando {source['name']}...")
        if source["type"] == "reddit":
            posts = fetch_reddit(source["url"])
        else:
            posts = fetch_rss(source["url"])
        all_posts.extend(posts)
        print(f"  {len(posts)} posts encontrados")
    return all_posts

def analyze_with_claude(posts):
    if not posts:
        return []

    posts_text = "\n".join([f"- {p['title']} | {p['link']}" for p in posts[:50]])

    prompt = f"""Você é um curador de conteúdo especializado em IA, Marketing e Mídia Paga para profissionais brasileiros.

Analise estes posts coletados hoje de Reddit e Hacker News:

{posts_text}

Selecione os 12 mais relevantes para profissionais de marketing digital brasileiro. Foque em:
- Novidades de ferramentas de IA para marketing
- Estratégias de mídia paga (Google Ads, Meta Ads, TikTok Ads)
- Tendências de marketing digital
- Cases e dados de performance

Exclua: memes, posts de humor, conteúdo sem substância, notícias muito técnicas de programação.

Para cada post selecionado, retorne EXATAMENTE neste formato JSON (sem markdown, sem explicações, apenas o JSON):
{{
  "posts": [
    {{
      "titulo": "título traduzido para português claro e natural",
      "categoria": "IA" ou "Marketing" ou "Mídia Paga",
      "resumo": "resumo de 2 frases em português explicando o que é e por que importa para o profissional de marketing",
      "link": "url original"
    }}
  ]
}}"""

    payload = json.dumps({
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 3000,
        "messages": [{"role": "user", "content": prompt}]
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
    )

    with urllib.request.urlopen(req, timeout=60) as r:
        response = json.loads(r.read())

    text = response["content"][0]["text"].strip()
    text = text.replace("```json", "").replace("```", "").strip()
    result = json.loads(text)
    return result.get("posts", [])

def generate_html(posts):
    today = datetime.now(timezone.utc).strftime("%d/%m/%Y")

    categoria_cores = {
        "IA": {"bg": "#EEF2FF", "text": "#4338CA", "border": "#C7D2FE"},
        "Marketing": {"bg": "#F0FDF4", "text": "#15803D", "border": "#BBF7D0"},
        "Mídia Paga": {"bg": "#FFF7ED", "text": "#C2410C", "border": "#FED7AA"}
    }

    cards_html = ""
    for post in posts:
        cat = post.get("categoria", "IA")
        cores = categoria_cores.get(cat, categoria_cores["IA"])
        cards_html += f"""
        <article class="card">
            <div class="card-header">
                <span class="badge" style="background:{cores['bg']};color:{cores['text']};border:1px solid {cores['border']}">{cat}</span>
            </div>
            <h2 class="card-title">
                <a href="{post['link']}" target="_blank" rel="noopener">{post['titulo']}</a>
            </h2>
            <p class="card-summary">{post['resumo']}</p>
            <a href="{post['link']}" target="_blank" rel="noopener" class="card-link">Ver original →</a>
        </article>"""

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Marketing Daily — {today}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: #F9FAFB;
            color: #111827;
            line-height: 1.6;
        }}
        header {{
            background: #111827;
            color: white;
            padding: 2rem 1.5rem;
            text-align: center;
        }}
        header h1 {{
            font-size: 1.75rem;
            font-weight: 700;
            letter-spacing: -0.02em;
        }}
        header p {{
            color: #9CA3AF;
            margin-top: 0.5rem;
            font-size: 0.95rem;
        }}
        .container {{
            max-width: 760px;
            margin: 0 auto;
            padding: 2rem 1.5rem;
        }}
        .grid {{
            display: grid;
            gap: 1rem;
        }}
        .card {{
            background: white;
            border: 1px solid #E5E7EB;
            border-radius: 12px;
            padding: 1.25rem 1.5rem;
            transition: box-shadow 0.2s;
        }}
        .card:hover {{ box-shadow: 0 4px 12px rgba(0,0,0,0.08); }}
        .card-header {{ margin-bottom: 0.6rem; }}
        .badge {{
            display: inline-block;
            font-size: 0.75rem;
            font-weight: 600;
            padding: 0.2rem 0.65rem;
            border-radius: 999px;
        }}
        .card-title {{
            font-size: 1rem;
            font-weight: 600;
            margin-bottom: 0.5rem;
            line-height: 1.4;
        }}
        .card-title a {{
            color: #111827;
            text-decoration: none;
        }}
        .card-title a:hover {{ color: #4F46E5; }}
        .card-summary {{
            font-size: 0.9rem;
            color: #6B7280;
            margin-bottom: 0.75rem;
        }}
        .card-link {{
            font-size: 0.85rem;
            color: #4F46E5;
            text-decoration: none;
            font-weight: 500;
        }}
        .card-link:hover {{ text-decoration: underline; }}
        footer {{
            text-align: center;
            padding: 2rem;
            color: #9CA3AF;
            font-size: 0.85rem;
            border-top: 1px solid #E5E7EB;
            margin-top: 2rem;
        }}
    </style>
</head>
<body>
    <header>
        <h1>AI Marketing Daily</h1>
        <p>Os melhores conteúdos sobre IA, Marketing e Mídia Paga — {today}</p>
    </header>
    <div class="container">
        <div class="grid">
            {cards_html}
        </div>
    </div>
    <footer>
        Curado automaticamente com Claude · Atualizado em {today}
    </footer>
</body>
</html>"""
    return html

def main():
    print("=== AI Marketing Daily Digest ===")
    print(f"Data: {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M')} UTC\n")

    print("1. Coletando posts...")
    posts = collect_all_posts()
    print(f"Total coletado: {len(posts)} posts\n")

    print("2. Analisando com Claude...")
    selected = analyze_with_claude(posts)
    print(f"Posts selecionados: {len(selected)}\n")

    print("3. Gerando HTML...")
    html = generate_html(selected)

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)

    print("index.html gerado com sucesso!")
    print(f"Site disponível em: https://yanzices.github.io/ai-marketing-daily")

if __name__ == "__main__":
    main()
