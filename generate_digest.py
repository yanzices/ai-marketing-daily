import os
import json
import urllib.request
import urllib.error
import re
from datetime import datetime, timezone

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

SOURCES = [
    {
        "name": "Google News - IA Marketing",
        "url": "https://news.google.com/rss/search?q=inteligencia+artificial+marketing&hl=pt-BR&gl=BR&ceid=BR:pt-419",
        "type": "rss"
    },
    {
        "name": "Google News - Mídia Paga",
        "url": "https://news.google.com/rss/search?q=midia+paga+google+ads+meta+ads&hl=pt-BR&gl=BR&ceid=BR:pt-419",
        "type": "rss"
    },
    {
        "name": "Google News - AI Advertising",
        "url": "https://news.google.com/rss/search?q=AI+advertising+paid+media&hl=en-US&gl=US&ceid=US:en",
        "type": "rss"
    },
    {
        "name": "Hacker News",
        "url": "https://hnrss.org/frontpage?count=20",
        "type": "rss"
    },
    {
        "name": "Marketing Land",
        "url": "https://martech.org/feed/",
        "type": "rss"
    }
]

def fetch_rss(url, name):
    posts = []
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; DigestBot/1.0)"}
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            content = r.read().decode("utf-8", errors="ignore")

        items = re.findall(r"<item>(.*?)</item>", content, re.DOTALL)
        for item in items[:20]:
            title_match = re.search(r"<title><!\[CDATA\[(.*?)\]\]></title>|<title>(.*?)</title>", item, re.DOTALL)
            link_match = re.search(r"<link>(.*?)</link>|<feedburner:origLink>(.*?)</feedburner:origLink>", item, re.DOTALL)

            if title_match and link_match:
                title = (title_match.group(1) or title_match.group(2) or "").strip()
                link = (link_match.group(1) or link_match.group(2) or "").strip()
                title = re.sub(r"<[^>]+>", "", title).strip()
                link = re.sub(r"<[^>]+>", "", link).strip()
                if title and link and len(title) > 10:
                    posts.append({"title": title, "link": link, "source": name})

        print(f"  {len(posts)} posts de {name}")
    except Exception as e:
        print(f"  Erro em {name}: {e}")
    return posts

def collect_all_posts():
    all_posts = []
    for source in SOURCES:
        posts = fetch_rss(source["url"], source["name"])
        all_posts.extend(posts)
    return all_posts

def analyze_with_claude(posts):
    if not posts:
        print("Nenhum post para analisar.")
        return []

    print(f"Chave API presente: {'Sim' if ANTHROPIC_API_KEY else 'NAO - CHAVE VAZIA'}")
    print(f"Primeiros 8 chars da chave: {ANTHROPIC_API_KEY[:8] if ANTHROPIC_API_KEY else 'VAZIO'}")

    posts_text = "\n".join([f"- {p['title']} | {p['link']}" for p in posts[:60]])

    prompt = f"""Você é um curador de conteúdo especializado em IA, Marketing e Mídia Paga para profissionais brasileiros.

Analise estes artigos coletados hoje:

{posts_text}

Selecione os 12 mais relevantes para profissionais de marketing digital. Foque em:
- Novidades de ferramentas de IA para marketing
- Estratégias de mídia paga (Google Ads, Meta Ads, TikTok Ads)
- Tendências de marketing digital
- Cases e dados de performance

Exclua: conteúdo político, entretenimento, esportes, notícias sem relação com marketing.

Retorne APENAS um JSON válido, sem markdown, sem texto antes ou depois:
{{"posts": [{{"titulo": "título em português claro", "categoria": "IA", "resumo": "2 frases explicando o que é e por que importa", "link": "url original"}}]}}

Categorias válidas: IA, Marketing, Mídia Paga"""

    payload = json.dumps({
        "model": "claude-sonnet-4-6",
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
    text = re.sub(r"```json|```", "", text).strip()
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
        titulo = post.get("titulo", "")
        resumo = post.get("resumo", "")
        link = post.get("link", "#")
        cards_html += f"""
        <article class="card">
            <div class="card-header">
                <span class="badge" style="background:{cores['bg']};color:{cores['text']};border:1px solid {cores['border']}">{cat}</span>
            </div>
            <h2 class="card-title">
                <a href="{link}" target="_blank" rel="noopener">{titulo}</a>
            </h2>
            <p class="card-summary">{resumo}</p>
            <a href="{link}" target="_blank" rel="noopener" class="card-link">Ver original →</a>
        </article>"""

    if not cards_html:
        cards_html = '<p style="text-align:center;color:#6B7280;padding:2rem">Nenhum conteúdo encontrado hoje.</p>'

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Marketing Daily — {today}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #F9FAFB; color: #111827; line-height: 1.6; }}
        header {{ background: #111827; color: white; padding: 2rem 1.5rem; text-align: center; }}
        header h1 {{ font-size: 1.75rem; font-weight: 700; letter-spacing: -0.02em; }}
        header p {{ color: #9CA3AF; margin-top: 0.5rem; font-size: 0.95rem; }}
        .container {{ max-width: 760px; margin: 0 auto; padding: 2rem 1.5rem; }}
        .grid {{ display: grid; gap: 1rem; }}
        .card {{ background: white; border: 1px solid #E5E7EB; border-radius: 12px; padding: 1.25rem 1.5rem; transition: box-shadow 0.2s; }}
        .card:hover {{ box-shadow: 0 4px 12px rgba(0,0,0,0.08); }}
        .badge {{ display: inline-block; font-size: 0.75rem; font-weight: 600; padding: 0.2rem 0.65rem; border-radius: 999px; margin-bottom: 0.6rem; }}
        .card-title {{ font-size: 1rem; font-weight: 600; margin-bottom: 0.5rem; line-height: 1.4; }}
        .card-title a {{ color: #111827; text-decoration: none; }}
        .card-title a:hover {{ color: #4F46E5; }}
        .card-summary {{ font-size: 0.9rem; color: #6B7280; margin-bottom: 0.75rem; }}
        .card-link {{ font-size: 0.85rem; color: #4F46E5; text-decoration: none; font-weight: 500; }}
        .card-link:hover {{ text-decoration: underline; }}
        footer {{ text-align: center; padding: 2rem; color: #9CA3AF; font-size: 0.85rem; border-top: 1px solid #E5E7EB; margin-top: 2rem; }}
    </style>
</head>
<body>
    <header>
        <h1>AI Marketing Daily</h1>
        <p>Os melhores conteúdos sobre IA, Marketing e Mídia Paga — {today}</p>
    </header>
    <div class="container">
        <div class="grid">{cards_html}</div>
    </div>
    <footer>Curado automaticamente com Claude · Atualizado em {today}</footer>
</body>
</html>"""

def main():
    print("=== AI Marketing Daily Digest ===")
    print(f"Data: {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M')} UTC\n")

    print("1. Coletando posts...")
    posts = collect_all_posts()
    print(f"Total coletado: {len(posts)} posts\n")

    if not posts:
        print("Nenhum post coletado. Gerando página vazia.")
        html = generate_html([])
    else:
        print("2. Analisando com Claude...")
        selected = analyze_with_claude(posts)
        print(f"Posts selecionados: {len(selected)}\n")
        print("3. Gerando HTML...")
        html = generate_html(selected)

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)

    print("index.html gerado com sucesso!")

if __name__ == "__main__":
    main()
