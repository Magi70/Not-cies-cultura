#!/usr/bin/env python3
"""
Genera el HTML estàtic amb les notícies culturals del dia.
S'executa cada matí via GitHub Actions.
"""

import anthropic
import json
import re
import sys
import time
from datetime import datetime, timezone

# ── Constants ────────────────────────────────────────────────────────────────

ICONS = {
    "Música": "🎵",
    "Arts visuals": "🎨",
    "Patrimoni": "🏛️",
    "Teatre i dansa": "🎭",
    "Literatura": "📚",
    "Cinema i audiovisual": "🎬",
    "Política cultural": "🏛️",
    "Festivals i esdeveniments": "🎪",
    "Opinió": "✍️",
    "Altres": "📰",
}

TODAY = datetime.now(timezone.utc).strftime("%d/%m/%Y")
TODAY_ISO = datetime.now(timezone.utc).strftime("%Y-%m-%d")
UPDATED_AT = datetime.now(timezone.utc).strftime("%d/%m/%Y a les %H:%M UTC")

# ── Step 1: Search for news ───────────────────────────────────────────────────

SEARCH_PROMPT = f"""Today is {TODAY_ISO}. You are a cultural news aggregator. 
Perform MULTIPLE web searches to find as many cultural news items as possible published in the last 48 hours.

Do these searches one by one:
1. "cultura Catalunya notícies {TODAY_ISO}"
2. "cultura España noticias {TODAY_ISO}"
3. "culture Europe news {TODAY_ISO}"
4. "música concerts exposicions art España Catalunya 2025"
5. "patrimoni museus teatre literatura cinema Catalunya 2025"
6. "culture musique théâtre cinéma Europe 2025"
7. "opinión cultura España artículo 2025"
8. "opinió cultura Catalunya article 2025"
9. "arts news Spain Europe today 2025"
10. "festival cultura espectacle música 2025"

Search in: La Vanguardia, El País, El Mundo, Ara, Nació Digital, Núvol, VilaWeb, 
RTVE Cultura, CCMA/324, El Cultural, Le Monde, Le Figaro, The Guardian Culture, 
The Art Newspaper, Corriere della Sera, La Repubblica, El Periódico, Time Out Barcelona.

Collect ALL results — news articles AND opinion pieces — before responding.
Aim for 25+ items total."""

FORMAT_PROMPT = """Now take ALL the cultural news and opinion pieces you just found and format them as a single JSON object.
Return ONLY the raw JSON — no markdown, no explanation, no text before or after. Start with { and end with }.

Use this exact structure:
{"sections":[{"theme":"THEME","news":[{"title":"headline","summary":"2 line max summary","source":"media name","geo":"GEO","url":"https://url","type":"TYPE"}]}]}

Rules:
- theme must be exactly one of: Música, Arts visuals, Patrimoni, Teatre i dansa, Literatura, Cinema i audiovisual, Política cultural, Festivals i esdeveniments, Opinió, Altres
- geo must be exactly one of: Catalunya, Espanya, Europa
- type must be exactly one of: news, opinion
- Opinion articles and columns go into the "Opinió" theme with type "opinion"
- Include EVERY article you found — aim for 25+ items total
- Start with { and end with }. Nothing else."""


def fetch_news():
    client = anthropic.Anthropic()

    print("📡 Pas 1: Cercant notícies...")
    
    # Step 1: search with web_search tool
    step1 = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=5000,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=[{"role": "user", "content": SEARCH_PROMPT}],
    )

    print(f"   stop_reason: {step1.stop_reason}, blocks: {len(step1.content)}")

    # Build conversation history
    messages = [
        {"role": "user", "content": SEARCH_PROMPT},
        {"role": "assistant", "content": step1.content},
    ]

    # If stopped for tool_use, continue until end_turn
    while step1.stop_reason == "tool_use":
        tool_results = [
            {"type": "tool_result", "tool_use_id": b.id, "content": "Search completed."}
            for b in step1.content
            if b.type == "tool_use"
        ]
        messages.append({"role": "user", "content": tool_results})
        step1 = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=5000,
            tools=[{"type": "web_search_20250305", "name": "web_search"}],
            messages=messages,
        )
        messages.append({"role": "assistant", "content": step1.content})
        print(f"   continuació: stop_reason={step1.stop_reason}")

    print("✅ Pas 1 completat.")

    # Extract only the text summary from step1 (avoids sending 84 blocks to step2)
    # This prevents rate limit errors by drastically reducing input tokens
    summary_text = " ".join(
        b.text for b in step1.content if hasattr(b, "text") and b.text
    ).strip()
    print(f"   Resum extret: {len(summary_text)} caràcters")

    # Wait 30 seconds to avoid rate limit (tokens per minute)
    print("⏳ Esperant 30s per evitar rate limit...")
    time.sleep(30)

    # Step 2: fresh conversation with just the summary + format request
    print("📋 Pas 2: Formatejant com a JSON...")
    step2_messages = [
        {"role": "user", "content": f"Here is a summary of cultural news I found today ({TODAY_ISO}):\n\n{summary_text}\n\n{FORMAT_PROMPT}"}
    ]

    step2 = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=6000,
        messages=step2_messages,
    )

    raw = "".join(b.text for b in step2.content if hasattr(b, "text"))
    print(f"   Raw response (first 200): {raw[:200]}")

    # Extract JSON robustly
    first = raw.find("{")
    last = raw.rfind("}")
    if first == -1 or last == -1:
        print("❌ No s'ha trobat JSON a la resposta.")
        sys.exit(1)

    data = json.loads(raw[first : last + 1])
    total = sum(len(s.get("news", [])) for s in data.get("sections", []))
    print(f"✅ Pas 2 completat. Seccions: {len(data['sections'])}, Total notícies: {total}")
    return data


# ── HTML generation ───────────────────────────────────────────────────────────

def escape(text):
    if not text:
        return ""
    return (
        text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#039;")
    )


def render_card(n):
    is_opinion = n.get("type") == "opinion"
    opinion_class = " opinion" if is_opinion else ""
    source_html = (
        '<span class="opinion-tag">✍️ Opinió</span>'
        if is_opinion
        else f'<span class="source-tag">{escape(n.get("source",""))}</span>'
    )
    author_html = (
        f'<div class="opinion-author">{escape(n.get("source",""))}</div>'
        if is_opinion
        else ""
    )
    link_html = ""
    url = n.get("url", "")
    if url and url.startswith("http"):
        link_html = f'<a href="{escape(url)}" target="_blank" rel="noopener" class="read-link">Llegir →</a>'

    return f"""
      <div class="news-card{opinion_class}">
        <div class="card-top">
          {source_html}
          <span class="geo-tag">{escape(n.get("geo",""))}</span>
        </div>
        <h3>{escape(n.get("title",""))}</h3>
        {author_html}
        <p>{escape(n.get("summary",""))}</p>
        {link_html}
      </div>"""


def render_section(section, delay):
    theme = section.get("theme", "Altres")
    news = section.get("news", [])
    if not news:
        return ""
    icon = ICONS.get(theme, "📰")
    count = len(news)
    label = "notícia" if count == 1 else "notícies"
    cards = "".join(render_card(n) for n in news)
    return f"""
    <div class="section-block" style="animation-delay:{delay:.2f}s">
      <div class="section-header">
        <span class="section-title">{icon} {escape(theme)}</span>
        <span class="section-count">{count} {label}</span>
      </div>
      <div class="news-grid">{cards}</div>
    </div>"""


def generate_html(data):
    sections_html = "".join(
        render_section(s, i * 0.08)
        for i, s in enumerate(data.get("sections", []))
    )
    total = sum(len(s.get("news", [])) for s in data.get("sections", []))

    return f"""<!DOCTYPE html>
<html lang="ca">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Diari de Cultura — {TODAY}</title>
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,700;1,400&family=DM+Sans:wght@300;400;500&display=swap" rel="stylesheet">
<style>
  :root {{
    --bg: #F7F4EF;
    --ink: #1A1612;
    --accent: #C8391A;
    --muted: #8A7F75;
    --card: #FFFFFF;
    --border: #E2DDD6;
    --tag-bg: #EDE9E2;
  }}
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ background:var(--bg); color:var(--ink); font-family:'DM Sans',sans-serif; font-weight:300; min-height:100vh; }}

  header {{
    border-bottom: 2px solid var(--ink);
    padding: 2rem 3rem 1.5rem;
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
    background: var(--bg);
    position: sticky;
    top: 0;
    z-index: 10;
  }}
  .masthead h1 {{ font-family:'Playfair Display',serif; font-size:2.4rem; font-weight:700; letter-spacing:-0.02em; line-height:1; }}
  .masthead h1 span {{ color:var(--accent); font-style:italic; }}
  .meta {{ text-align:right; font-size:0.75rem; color:var(--muted); letter-spacing:0.08em; text-transform:uppercase; }}
  .meta strong {{ display:block; font-size:1rem; color:var(--ink); font-weight:500; letter-spacing:0; margin-top:0.2rem; }}

  main {{ max-width:1100px; margin:0 auto; padding:2.5rem 3rem 4rem; }}

  .summary-bar {{
    display: flex;
    gap: 2rem;
    padding: 1rem 0 2rem;
    border-bottom: 1px solid var(--border);
    margin-bottom: 2.5rem;
    font-size: 0.8rem;
    color: var(--muted);
    letter-spacing: 0.04em;
  }}
  .summary-bar strong {{ color: var(--ink); font-size: 1.4rem; font-family:'Playfair Display',serif; display:block; }}

  .section-block {{ margin-bottom:3rem; animation:fadeUp 0.4s ease both; }}
  @keyframes fadeUp {{ from {{ opacity:0; transform:translateY(12px); }} to {{ opacity:1; transform:translateY(0); }} }}

  .section-header {{
    display:flex; align-items:baseline; gap:1rem;
    margin-bottom:1.25rem; padding-bottom:0.6rem;
    border-bottom:1px solid var(--ink);
  }}
  .section-title {{ font-family:'Playfair Display',serif; font-size:1.35rem; font-weight:700; }}
  .section-count {{ font-size:0.75rem; color:var(--muted); letter-spacing:0.06em; text-transform:uppercase; }}

  .news-grid {{
    display:grid; grid-template-columns:repeat(auto-fill,minmax(300px,1fr));
    gap:1px; background:var(--border); border:1px solid var(--border);
  }}
  .news-card {{
    background:var(--card); padding:1.25rem 1.4rem;
    display:flex; flex-direction:column; gap:0.6rem;
    transition:background 0.15s;
  }}
  .news-card:hover {{ background:#FAFAF8; }}
  .news-card.opinion {{ background:#FFFDF7; border-left:3px solid #C8A000; }}
  .news-card.opinion:hover {{ background:#FFFBEE; }}

  .card-top {{ display:flex; justify-content:space-between; align-items:flex-start; gap:0.5rem; }}
  .source-tag {{ font-size:0.65rem; font-weight:500; letter-spacing:0.08em; text-transform:uppercase; color:var(--accent); background:#FEF0ED; padding:0.2rem 0.5rem; white-space:nowrap; }}
  .opinion-tag {{ font-size:0.62rem; font-weight:600; letter-spacing:0.08em; text-transform:uppercase; color:#7A5F00; background:#FFF3C4; padding:0.2rem 0.5rem; }}
  .geo-tag {{ font-size:0.65rem; letter-spacing:0.06em; text-transform:uppercase; color:var(--muted); background:var(--tag-bg); padding:0.2rem 0.5rem; white-space:nowrap; }}
  .news-card h3 {{ font-family:'Playfair Display',serif; font-size:0.98rem; font-weight:700; line-height:1.35; color:var(--ink); }}
  .opinion-author {{ font-size:0.72rem; color:var(--muted); }}
  .news-card p {{ font-size:0.82rem; line-height:1.6; color:#4A4540; flex-grow:1; }}
  .read-link {{
    font-size:0.72rem; font-weight:500; letter-spacing:0.06em; text-transform:uppercase;
    color:var(--ink); text-decoration:none; border-bottom:1px solid var(--ink);
    padding-bottom:1px; align-self:flex-start; transition:color 0.15s,border-color 0.15s;
  }}
  .read-link:hover {{ color:var(--accent); border-color:var(--accent); }}

  footer {{
    text-align:center; padding:2rem; font-size:0.72rem;
    color:var(--muted); border-top:1px solid var(--border); letter-spacing:0.04em;
  }}

  @media (max-width:640px) {{
    header {{ padding:1.25rem 1.5rem 1rem; flex-direction:column; align-items:flex-start; gap:0.75rem; }}
    main {{ padding:1.5rem; }}
    .masthead h1 {{ font-size:1.8rem; }}
    .news-grid {{ grid-template-columns:1fr; }}
  }}
</style>
</head>
<body>

<header>
  <div class="masthead">
    <h1>Diari de <span>Cultura</span></h1>
  </div>
  <div class="meta">
    Actualitzat el
    <strong>{UPDATED_AT}</strong>
  </div>
</header>

<main>
  <div class="summary-bar">
    <div><strong>{total}</strong> notícies i articles d'opinió</div>
    <div><strong>{len(data.get("sections", []))}</strong> seccions temàtiques</div>
    <div>Catalunya · Espanya · Europa</div>
  </div>

  {sections_html}
</main>

<footer>
  Diari de Cultura · Generat automàticament cada dia a les 7h · {TODAY}
</footer>

</body>
</html>"""


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"🗞️  Generant Diari de Cultura — {TODAY}")
    data = fetch_news()
    html = generate_html(data)
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print(f"✅ index.html generat correctament.")
