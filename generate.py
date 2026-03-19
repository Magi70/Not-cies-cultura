#!/usr/bin/env python3
"""
Genera el HTML estàtic amb les notícies culturals del dia.
S'executa cada matí via GitHub Actions.
Estratègia: web_fetch directe a les pàgines de cultura de cada mitjà.
"""

import anthropic
import json
import sys
import time
from datetime import datetime, timezone

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

# ── URLs predefinides de seccions de cultura ──────────────────────────────────
# Afegeix o elimina URLs aquí per personalitzar les fonts
CULTURE_URLS = [
    # Catalunya
    "https://www.lavanguardia.com/cultura",
    "https://www.ara.cat/cultura",
    "https://www.nuvol.com",
    "https://www.ccma.cat/324/cultura",
    "https://www.elperiodico.com/es/ocio-y-cultura",
    "https://www.elnacional.cat/ca/cultura",
    "https://www.vilaweb.cat/categoria/cultura/",
    "https://www.timeout.cat/barcelona/ca/arts-i-cultura",
    "https://www.catorze.cat/",
    "https://www.beteve.cat/cultura/",
    "https://www.revistamirall.com/categoria/cultura/",
    "https://www.llegir.cat/",
    
    # Espanya
    "https://elpais.com/cultura",
    "https://www.elmundo.es/cultura.html",
    "https://elcultural.com",
    "https://www.rtve.es/cultura",
    "https://www.abc.es/cultura/",
    "https://www.larazon.es/cultura/",
    "https://www.publico.es/culturas/",
    "https://www.eldiario.es/cultura/",
    "https://www.20minutos.es/cultura/",
    "https://www.europapress.es/cultura/",
    "https://www.huffingtonpost.es/life/cultura/",
    
    # Regne Unit
    "https://www.theguardian.com/culture",
    "https://www.bbc.co.uk/culture",
    "https://www.telegraph.co.uk/culture/",
    "https://www.independent.co.uk/arts-entertainment",
    "https://www.thetimes.co.uk/culture",
    "https://www.ft.com/arts",
    "https://www.timeout.com/london/arts-and-culture",
    "https://www.standard.co.uk/culture",
    "https://www.nme.com",
    "https://www.classicfm.com/discover-music/",
    
    # França
    "https://www.lemonde.fr/culture",
    "https://www.lefigaro.fr/culture",
    "https://www.liberation.fr/culture/",
    "https://www.telerama.fr/",
    "https://www.franceculture.fr/",
    "https://www.francetvinfo.fr/culture/",
    "https://www.lesechos.fr/weekend/culture",
    "https://www.radiofrance.fr/franceinter/culture",
    "https://www.parismatch.com/culture",
    "https://www.lexpress.fr/culture/",
    
    # Itàlia
    "https://www.corriere.it/cultura",
    "https://www.repubblica.it/cultura",
    "https://www.ilsole24ore.com/cultura",
    "https://www.lastampa.it/cultura/",
    "https://www.ilgiornale.it/sezione/cultura.html",
    "https://www.ansa.it/cultura/",
    "https://www.artribune.com/",
    "https://www.rollingstone.it/",
    "https://www.raiplay.it/cultura",
    "https://www.ilpost.it/cultura/",
    
    # Alemanya
    "https://www.sueddeutsche.de/kultur",
    "https://www.zeit.de/kultur/index",
    "https://www.spiegel.de/kultur/",
    "https://www.faz.net/aktuell/feuilleton/",
    "https://www.welt.de/kultur/",
    "https://www.tagesspiegel.de/kultur/",
    "https://www.dw.com/de/kultur/s-9077",
    "https://www.deutschlandfunkkultur.de/",
    "https://www.berliner-zeitung.de/kultur-vergnuegen/",
    "https://www.taz.de/Kultur/!t5008/",
    
    # Portugal
    "https://www.publico.pt/culturaipsilon",
    "https://expresso.pt/cultura",
    "https://observador.pt/seccao/cultura/",
    "https://www.dn.pt/cultura/",
    "https://www.jn.pt/artes/",
    "https://www.rtp.pt/cultura",
    "https://timeout.pt/lisboa/pt/arte",
    "https://www.sabado.pt/cultura",
    "https://blitz.pt/",
    "https://www.nit.pt/cultura",
]


def fetch_news():
    client = anthropic.Anthropic()

    print("📡 Cercant notícies via web_search...")

    # Construïm un prompt curt que demana cercar a les URLs predefinides
    urls_list = "\n".join(f"- {url}" for url in CULTURE_URLS[:10])  # màx 10 per sessió
    
    search_prompt = f"""Today is {TODAY_ISO}. Search for the most recent cultural news published today or yesterday from these specific culture sections:

{urls_list}

For each source, find 1-2 recent articles. Extract: exact headline in original language, 2-line summary in original language, source name, and the exact article URL."""

    step1 = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=4000,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=[{"role": "user", "content": search_prompt}],
    )
    print(f"   stop_reason: {step1.stop_reason}, blocks: {len(step1.content)}")

    messages = [
        {"role": "user", "content": search_prompt},
        {"role": "assistant", "content": step1.content},
    ]
    while step1.stop_reason == "tool_use":
        tool_results = [
            {"type": "tool_result", "tool_use_id": b.id, "content": "done"}
            for b in step1.content if b.type == "tool_use"
        ]
        messages.append({"role": "user", "content": tool_results})
        step1 = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=4000,
            tools=[{"type": "web_search_20250305", "name": "web_search"}],
            messages=messages,
        )
        messages.append({"role": "assistant", "content": step1.content})
        print(f"   continuació stop_reason={step1.stop_reason}")

    summary = " ".join(b.text for b in step1.content if hasattr(b, "text") and b.text).strip()
    print(f"✅ Cerca OK. {len(summary)} chars")

    print("⏳ Esperant 30s...")
    time.sleep(30)

    print("📋 Formatejant JSON...")
    format_prompt = f"""Aquestes són les notícies culturals trobades avui ({TODAY_ISO}):

{summary[:6000]}

Retorna NOMÉS un objecte JSON. Sense markdown, sense text fora. Estructura:
{{"sections":[{{"theme":"TEMA","news":[{{"title":"titular en idioma original","summary":"resum 2 línies en idioma original","source":"nom del mitjà","geo":"GEO","url":"URL o null","url_exact":true,"type":"TIPUS"}}]}}]}}

Regles:
- title i summary: en l'idioma original de la notícia
- url: URL directa a l'article si la tens, si no posa null
- url_exact: true si és URL directa a l'article, false si és portada del mitjà
- theme: Música|Arts visuals|Patrimoni|Teatre i dansa|Literatura|Cinema i audiovisual|Política cultural|Festivals i esdeveniments|Opinió|Altres
- geo: Catalunya|Espanya|Europa
- type: news|opinion

Comença amb {{ acaba amb }}. Res més."""

    step2 = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=4000,
        messages=[{"role": "user", "content": format_prompt}],
    )

    raw = "".join(b.text for b in step2.content if hasattr(b, "text"))
    print(f"   Raw (first 200): {raw[:200]}")

    first = raw.find("{")
    last = raw.rfind("}")
    if first == -1 or last == -1:
        print("❌ No JSON found")
        sys.exit(1)

    data = json.loads(raw[first:last + 1])
    total = sum(len(s.get("news", [])) for s in data.get("sections", []))
    print(f"✅ JSON OK. Seccions: {len(data['sections'])}, Notícies: {total}")
    return data


def escape(text):
    if not text:
        return ""
    return (text.replace("&", "&amp;").replace("<", "&lt;")
                .replace(">", "&gt;").replace('"', "&quot;").replace("'", "&#039;"))


def render_card(n):
    is_opinion = n.get("type") == "opinion"
    opinion_class = " opinion" if is_opinion else ""
    source_html = (
        '<span class="opinion-tag">✍️ Opinió</span>'
        if is_opinion
        else f'<span class="source-tag">{escape(n.get("source",""))}</span>'
    )
    author_html = f'<div class="opinion-author">{escape(n.get("source",""))}</div>' if is_opinion else ""
    url = n.get("url") or ""
    url_exact = n.get("url_exact", True)
    if url and url.startswith("http"):
        if url_exact:
            link_html = f'<a href="{escape(url)}" target="_blank" rel="noopener" class="read-link">Llegir →</a>'
        else:
            link_html = f'<a href="{escape(url)}" target="_blank" rel="noopener" class="read-link read-link-approx">Llegir (portal) →</a>'
    else:
        link_html = '<span class="no-link">Enllaç no disponible</span>'
    return f"""
      <div class="news-card{opinion_class}">
        <div class="card-top">{source_html}<span class="geo-tag">{escape(n.get("geo",""))}</span></div>
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
    sections_html = "".join(render_section(s, i * 0.08) for i, s in enumerate(data.get("sections", [])))
    total = sum(len(s.get("news", [])) for s in data.get("sections", []))

    return f"""<!DOCTYPE html>
<html lang="ca">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Diari de Cultura — {TODAY}</title>
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,700;1,400&family=DM+Sans:wght@300;400;500&display=swap" rel="stylesheet">
<style>
  :root {{--bg:#F7F4EF;--ink:#1A1612;--accent:#C8391A;--muted:#8A7F75;--card:#FFFFFF;--border:#E2DDD6;--tag-bg:#EDE9E2;}}
  *{{margin:0;padding:0;box-sizing:border-box;}}
  body{{background:var(--bg);color:var(--ink);font-family:'DM Sans',sans-serif;font-weight:300;min-height:100vh;}}
  header{{border-bottom:2px solid var(--ink);padding:2rem 3rem 1.5rem;display:flex;justify-content:space-between;align-items:flex-end;background:var(--bg);position:sticky;top:0;z-index:10;}}
  .masthead h1{{font-family:'Playfair Display',serif;font-size:2.4rem;font-weight:700;letter-spacing:-0.02em;line-height:1;}}
  .masthead h1 span{{color:var(--accent);font-style:italic;}}
  .meta{{text-align:right;font-size:0.75rem;color:var(--muted);letter-spacing:0.08em;text-transform:uppercase;}}
  .meta strong{{display:block;font-size:1rem;color:var(--ink);font-weight:500;letter-spacing:0;margin-top:0.2rem;}}
  main{{max-width:1100px;margin:0 auto;padding:2.5rem 3rem 4rem;}}
  .summary-bar{{display:flex;gap:2rem;padding:1rem 0 2rem;border-bottom:1px solid var(--border);margin-bottom:2.5rem;font-size:0.8rem;color:var(--muted);letter-spacing:0.04em;}}
  .summary-bar strong{{color:var(--ink);font-size:1.4rem;font-family:'Playfair Display',serif;display:block;}}
  .section-block{{margin-bottom:3rem;animation:fadeUp 0.4s ease both;}}
  @keyframes fadeUp{{from{{opacity:0;transform:translateY(12px);}}to{{opacity:1;transform:translateY(0);}}}}
  .section-header{{display:flex;align-items:baseline;gap:1rem;margin-bottom:1.25rem;padding-bottom:0.6rem;border-bottom:1px solid var(--ink);}}
  .section-title{{font-family:'Playfair Display',serif;font-size:1.35rem;font-weight:700;}}
  .section-count{{font-size:0.75rem;color:var(--muted);letter-spacing:0.06em;text-transform:uppercase;}}
  .news-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:1px;background:var(--border);border:1px solid var(--border);}}
  .news-card{{background:var(--card);padding:1.25rem 1.4rem;display:flex;flex-direction:column;gap:0.6rem;transition:background 0.15s;}}
  .news-card:hover{{background:#FAFAF8;}}
  .news-card.opinion{{background:#FFFDF7;border-left:3px solid #C8A000;}}
  .news-card.opinion:hover{{background:#FFFBEE;}}
  .card-top{{display:flex;justify-content:space-between;align-items:flex-start;gap:0.5rem;}}
  .source-tag{{font-size:0.65rem;font-weight:500;letter-spacing:0.08em;text-transform:uppercase;color:var(--accent);background:#FEF0ED;padding:0.2rem 0.5rem;white-space:nowrap;}}
  .opinion-tag{{font-size:0.62rem;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;color:#7A5F00;background:#FFF3C4;padding:0.2rem 0.5rem;}}
  .geo-tag{{font-size:0.65rem;letter-spacing:0.06em;text-transform:uppercase;color:var(--muted);background:var(--tag-bg);padding:0.2rem 0.5rem;white-space:nowrap;}}
  .news-card h3{{font-family:'Playfair Display',serif;font-size:0.98rem;font-weight:700;line-height:1.35;color:var(--ink);}}
  .opinion-author{{font-size:0.72rem;color:var(--muted);}}
  .news-card p{{font-size:0.82rem;line-height:1.6;color:#4A4540;flex-grow:1;}}
  .read-link{{font-size:0.72rem;font-weight:500;letter-spacing:0.06em;text-transform:uppercase;color:var(--ink);text-decoration:none;border-bottom:1px solid var(--ink);padding-bottom:1px;align-self:flex-start;transition:color 0.15s,border-color 0.15s;}}
  .read-link:hover{{color:var(--accent);border-color:var(--accent);}}
  .read-link-approx{{color:var(--muted);border-color:var(--muted);font-style:italic;}}
  .read-link-approx:hover{{color:var(--accent);border-color:var(--accent);}}
  .no-link{{font-size:0.72rem;color:var(--muted);letter-spacing:0.04em;font-style:italic;}}
  footer{{text-align:center;padding:2rem;font-size:0.72rem;color:var(--muted);border-top:1px solid var(--border);letter-spacing:0.04em;}}
  @media(max-width:640px){{header{{padding:1.25rem 1.5rem 1rem;flex-direction:column;align-items:flex-start;gap:0.75rem;}}main{{padding:1.5rem;}}.masthead h1{{font-size:1.8rem;}}.news-grid{{grid-template-columns:1fr;}}}}
</style>
</head>
<body>
<header>
  <div class="masthead"><h1>Diari de <span>Cultura</span></h1></div>
  <div class="meta">Actualitzat el<strong>{UPDATED_AT}</strong></div>
</header>
<main>
  <div class="summary-bar">
    <div><strong>{total}</strong> notícies i articles</div>
    <div><strong>{len(data.get("sections", []))}</strong> seccions</div>
    <div>Catalunya · Espanya · Europa</div>
  </div>
  {sections_html}
</main>
<footer>Diari de Cultura · Actualitzat automàticament cada dia a les 7h · {TODAY}</footer>
</body>
</html>"""


if __name__ == "__main__":
    print(f"🗞️  Generant Diari de Cultura — {TODAY}")
    data = fetch_news()
    html = generate_html(data)
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("✅ index.html generat correctament.")
