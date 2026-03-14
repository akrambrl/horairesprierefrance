#!/usr/bin/env python3
"""
generate_articles.py
Génère 6 articles islamiques via l'API Claude et les injecte dans index.html
Lancé chaque nuit par GitHub Actions
"""

import anthropic
import json
import re
import os
from datetime import datetime, timezone

# ─── Config ───────────────────────────────────────────────────────────────────
CATEGORIES = [
    ("Actualités Islam France",  "🕌", "actus"),
    ("Actualités Islam France",  "📰", "actus"),
    ("Histoire des Mosquées",    "🏛️", "histoire"),
    ("Histoire des Mosquées",    "📜", "histoire"),
    ("Conseils Pratiques",       "☪️", "conseils"),
    ("Annonces Communautaires",  "📢", "annonces"),
]

SYSTEM_PROMPT = """Tu es un rédacteur spécialisé dans l'islam en France. 
Tu rédiges des articles informatifs, respectueux et accessibles pour un public francophone musulman.
Réponds UNIQUEMENT en JSON valide, sans markdown, sans backticks, sans texte autour."""

def generate_articles():
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    
    today = datetime.now(timezone.utc).strftime("%d %B %Y")
    articles = []

    for cat, icon, cat_slug in CATEGORIES:
        prompt = f"""Génère un article de blog pour la catégorie "{cat}" sur le site horairesprierefrance.fr.
Date du jour : {today}

Réponds avec ce JSON exact (pas de markdown, pas de backticks) :
{{
  "titre": "Titre accrocheur de l'article (max 70 chars)",
  "resume": "Résumé de 2 phrases pour la card (max 150 chars)",
  "contenu": "Corps de l'article en HTML simple (3-4 paragraphes avec <p> et <strong>). Min 300 mots. Informatif et optimisé SEO.",
  "categorie": "{cat}",
  "icon": "{icon}",
  "slug": "{cat_slug}"
}}

L'article doit être récent, pertinent pour la communauté musulmane en France, et utile pour le SEO."""

        try:
            msg = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}],
                system=SYSTEM_PROMPT
            )
            raw = msg.content[0].text.strip()
            # Nettoyer les backticks éventuels
            raw = re.sub(r'^```json\s*', '', raw)
            raw = re.sub(r'\s*```$', '', raw)
            article = json.loads(raw)
            article["date"] = today
            articles.append(article)
            print(f"✅ Article généré : {article['titre'][:50]}")
        except Exception as e:
            print(f"❌ Erreur pour {cat}: {e}")
            # Article de fallback
            articles.append({
                "titre": f"L'islam en France — {cat}",
                "resume": "Retrouvez toute l'actualité islamique en France sur notre site.",
                "contenu": f"<p>Bienvenue sur Horaires Prière France, votre référence pour {cat.lower()} en France.</p>",
                "categorie": cat,
                "icon": icon,
                "slug": cat_slug,
                "date": today
            })

    return articles


def build_articles_html(articles):
    """Construit le HTML des 6 cards + les modales"""
    
    cards_html = ""
    modals_html = ""

    for i, art in enumerate(articles):
        art_id = f"art-gen-{i}"
        slug = art.get("slug", "actus")
        
        # Badge couleur selon catégorie
        badge_colors = {
            "actus":    "#1a7a4a",
            "histoire": "#7a5c1a",
            "conseils": "#1a4a7a",
            "annonces": "#7a1a4a",
        }
        badge_color = badge_colors.get(slug, "#1a7a4a")

        cards_html += f"""
        <div class="ncard" onclick="openGenArt('{art_id}')">
          <div class="ncard-cat" style="background:{badge_color}">{art['icon']} {art['categorie']}</div>
          <div class="ncard-body">
            <h3>{art['titre']}</h3>
            <p>{art['resume']}</p>
          </div>
          <div class="ncard-footer">
            <span class="ncard-date">🗓 {art['date']}</span>
            <span class="ncard-read">Lire →</span>
          </div>
        </div>"""

        # Contenu sécurisé pour JS (escape quotes)
        contenu_safe = art['contenu'].replace('`', '\\`').replace('${', '\\${')
        titre_safe   = art['titre'].replace("'", "\\'")
        cat_safe     = art['categorie'].replace("'", "\\'")

        modals_html += f"""
        <div id="{art_id}" class="nmodal" style="display:none">
          <div class="nmodal-box">
            <button class="nmodal-close" onclick="closeGenArt('{art_id}')">✕</button>
            <div class="nmodal-cat" style="background:{badge_color}">{art['icon']} {art['categorie']}</div>
            <h2 class="nmodal-title">{art['titre']}</h2>
            <div class="nmodal-date">🗓 {art['date']}</div>
            <div class="nmodal-content">{art['contenu']}</div>
          </div>
        </div>"""

    return cards_html.strip(), modals_html.strip()


def inject_into_html(articles):
    """Injecte les articles dans index.html entre les marqueurs"""
    
    with open("index.html", "r", encoding="utf-8") as f:
        html = f.read()

    cards_html, modals_html = build_articles_html(articles)

    # Remplacer entre les marqueurs
    html = re.sub(
        r'<!-- GEN-ARTICLES-START -->.*?<!-- GEN-ARTICLES-END -->',
        f'<!-- GEN-ARTICLES-START -->\n{cards_html}\n<!-- GEN-ARTICLES-END -->',
        html, flags=re.DOTALL
    )
    html = re.sub(
        r'<!-- GEN-MODALS-START -->.*?<!-- GEN-MODALS-END -->',
        f'<!-- GEN-MODALS-START -->\n{modals_html}\n<!-- GEN-MODALS-END -->',
        html, flags=re.DOTALL
    )

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)
    
    print(f"✅ index.html mis à jour avec {len(articles)} articles")


if __name__ == "__main__":
    print(f"🕌 Génération articles — {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    articles = generate_articles()
    inject_into_html(articles)
    print("🎉 Terminé !")
