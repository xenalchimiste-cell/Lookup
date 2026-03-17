#!/usr/bin/env python3
"""
ZSearcher – Générateur de fiche contact depuis le terminal.
Usage : python3 fiche.py <nom> <prenom>
Exemple : python3 fiche.py Dupont Jean
"""

import sys
import ssl
import os
import subprocess
import urllib.request
import urllib.parse
import urllib.error
import json
import time
import argparse
from datetime import datetime

# ── COULEURS HACKER (MEDIUM GREEN) ──
G  = "\033[32m"         # Vert standard
DG = "\033[1;32m"       # Vert gras
B  = "\033[1m"          # Gras
R  = "\033[0m"          # Reset

def print_logo():
    """Affiche le logo ASCII de ZSearcher."""
    logo = f"""
    {DG}      ▄████████  ▄████████  ▄████████  ▄████████  ▄████████  ▄████████  ▄████████    ▄████████    ▄████████ 
    {DG}     ███    ███ ███    ███ ███    ███ ███    ███ ███    ███ ███    ███ ███    ███   ███    ███   ███    ███ 
    {DG}     ╚══███══╝  ███    █▀  ███    █▀  ███    ███ ███    ███ ███    █▀  ███    ███   ███    █▀    ███    ███ 
    {DG}        ███     ███        ███        ███    ███ ███    ███ ███        ███    ███  ▄███▄▄▄       ███    ███ 
    {DG}        ███   ▀███████████ ████████▀  ███████████ ████████▀  ███        ███████████ ▀▀███▀▀▀     ▀███████████ 
    {DG}        ███            ███ ███        ███    ███ ███  ██▄    ███    █▄  ███    ███   ███    █▄    ███    ███ 
    {DG}        ███      ▄█    ███ ███    █▄  ███    ███ ███  ▀██▄   ███    ███ ███    ███   ███    ███   ███    ███ 
    {DG}        ███    ▄████████▀  ████████▀  ███    █▀  ███    ██▄  ████████▀  ███    █▀    ██████████   ███    █▀  
    
    {G}                        [  EYE OF THE NET : MODE OSINT ACTIVÉ  ]
    {DG}                      .---.        .---.
    {DG}                     /     \  _   /     \\
    {DG}                     \_.._.._( )_.._.._./
    {DG}                      .---./( )\.---.
    {DG}                     /     \     /     \\
    {DG}                     \_.._.._.._.._.._./
    {G}                       [ HACKER EDITION ]
    """
    print(logo)

def make_link(url, text):
    """Crée un lien hypertexte pour le terminal (compatible OSC 8)."""
    # \033]8;;URL\033\\TEXT\033]8;;\033\\
    return f"\033]8;;{url}\033\\\033[4m{text}\033[24m\033]8;;\033\\"

def strip_ansi(text):
    """Supprime tous les codes ANSI pour l'export fichier texte."""
    import re
    ansi_escape = re.compile(r'(\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])|\x1b]8;;.*?\x1b\\)')
    return ansi_escape.sub('', text)

# ── CONFIGURATION & COOKIES ──
COOKIE_FILE = os.path.expanduser("~/.zsearcher_cookie")

def save_login_cookie(cookie_str):
    """Sauvegarde le cookie dans un fichier pour les futures sessions."""
    # Nettoyage si l'utilisateur met 'session=' en trop
    if "session=" in cookie_str and not cookie_str.startswith("session="):
        # On garde tout tel quel si c'est déjà complexe, sinon on nettoie
        pass
    with open(COOKIE_FILE, "w", encoding="utf-8") as f:
        f.write(cookie_str.strip())
    print(f"  {G}✅  Session sauvegardée ! Tu peux maintenant faire tes recherches sans --login.{R}")

def load_login_cookie():
    """Charge le cookie sauvegardé."""
    if os.path.exists(COOKIE_FILE):
        with open(COOKIE_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    return os.environ.get("ZSEARCHER_COOKIE", "")

def visible_len(text):
    """Calcule la longueur réelle affichée à l'écran (ignore les codes ANSI et liens)."""
    import re
    # Supprime les codes ANSI classiques et les hyperliens OSC 8
    clean = re.sub(r'\x1b\[[0-9;]*[mK]', '', text)
    clean = re.sub(r'\x1b]8;;.*?\x1b\\', '', clean)
    clean = re.sub(r'\x1b]8;;\x1b\\', '', clean)
    return len(clean)


# ── EFFETS VISUELS ──
def progress_bar(duration=1.5):
    """Barre de progression stylée."""
    width = 40
    for i in range(width + 1):
        percent = int((i / width) * 100)
        bar = "█" * i + "░" * (width - i)
        sys.stdout.write(f"\r  {G}⚡ Lancement du scan... [{bar}] {percent}%{R}")
        sys.stdout.flush()
        time.sleep(duration / width)
    print("\n")
EXPORT_BASE_URL = "https://zsearcher.fr/search/export"
W = 90  # Largeur augmentée pour éviter les coupures

def pad(s, length):
    return s + " " * max(0, length - visible_len(s))

def center(s, length):
    v = visible_len(s)
    left = (length - v) // 2
    right = length - v - left
    return " " * max(0, left) + s + " " * max(0, right)

box_top   = "╔" + "═" * W + "╗"
box_bot   = "╚" + "═" * W + "╝"
box_mid   = "╠" + "═" * W + "╣"
thin_sep  = "╟" + "─" * W + "╢"

def box_line(txt):
    """Ligne de boîte increvable."""
    return f"║ {pad(txt, W-2)} ║"

def box_center(txt):
    """Ligne centrée increvable."""
    return f"║{center(txt, W)}║"



def box_line(txt):
    """Ligne de boîte standard avec padding intelligent qui ignore les codes ANSI."""
    return "║ " + pad(txt, W - 4) + " ║"


def box_center(txt):
    """Ligne de boîte centrée avec padding intelligent qui ignore les codes ANSI."""
    return "║" + center(txt, W) + "║"


def box_empty():
    return "║" + " " * W + "║"


# ═══════════════════════════════════════════════════════════
#  APPEL API
# ═══════════════════════════════════════════════════════════
def fetch_results(nom, prenom):
    """Appelle l'API ZSearcher et retourne la liste de résultats."""
    params = {"nom": nom, "prenom": prenom}
    url = EXPORT_BASE_URL + "?" + urllib.parse.urlencode(params)
    
    print(f"\n  {DG}🔗  Scan en cours...{R}")
    progress_bar(0.6)

    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        req = urllib.request.Request(url)
        req.add_header("User-Agent", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
        req.add_header("Referer", "https://zsearcher.fr/")
        req.add_header("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8")
        req.add_header("Accept-Language", "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7")

        # Gestion du cookie de session
        cookie = load_login_cookie()
        if cookie:
            # S'assurer du format 'session=...'
            if not cookie.startswith("session="):
                cookie = f"session={cookie}"
            req.add_header("Cookie", cookie)
            print(f"  {DG}🔑  Session active chargée.{R}")
        else:
            print(f"  {R}[!] Attention : Aucun cookie de session trouvé. Recherche limitée.{R}")

        with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:
            raw = resp.read().decode("utf-8")

        # Détecter si l'API renvoie du HTML au lieu de données
        stripped = raw.strip()
        if stripped.lower().startswith("<!doctype") or stripped.lower().startswith("<html"):
            print(f"  {G}⚠️  L'API a renvoyé une page HTML (pas de données CSV/JSON).{R}")
            print(f"  {G}⚠️  Cela peut indiquer un problème d'authentification.{R}")
            print(f"  {G}💡  Essaie avec ton cookie de session :{R}")
            print(f'  {DG}💡  ZSEARCHER_COOKIE="ton_cookie" python3 fiche.py Nom Prenom{R}')
            return []

        # Sauvegarder la réponse brute pour debug
        debug_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_debug_response.txt")
        with open(debug_path, "w", encoding="utf-8") as dbg:
            dbg.write(raw)
        print(f"  {DG}🔧  Réponse brute sauvegardée → {debug_path}{R}")

        # Essayer de parser en JSON
        try:
            data = json.loads(raw)
            if isinstance(data, list):
                return data
            if isinstance(data, dict):
                return data.get("results", data.get("data", [data]))
            return [data]
        except json.JSONDecodeError:
            # Si c'est du CSV, parser avec le module csv
            return parse_csv(raw)

    except urllib.error.HTTPError as e:
        print(f"  ❌  Erreur HTTP {e.code}: {e.reason}")
        return []
    except urllib.error.URLError as e:
        print(f"  ❌  Erreur de connexion: {e.reason}")
        return []
    except Exception as e:
        print(f"  ❌  Erreur: {e}")
        return []


def parse_csv(raw):
    """Parse le format CSV de ZSearcher : chaque ligne est  numéro,"JSON"."""
    lines = raw.strip().replace("\r\n", "\n").replace("\r", "\n").split("\n")

    results = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        # Format attendu : numéro,"{ JSON }"
        # Trouver la première virgule pour séparer le numéro du JSON
        comma_idx = stripped.find(",")
        if comma_idx < 0:
            continue

        json_part = stripped[comma_idx + 1:].strip()

        # Enlever les guillemets extérieurs si présents
        if json_part.startswith('"') and json_part.endswith('"'):
            json_part = json_part[1:-1]

        # Remplacer les doubles guillemets ("") par des simples (") — échappement CSV
        json_part = json_part.replace('""', '"')

        # Essayer de parser comme JSON
        try:
            obj = json.loads(json_part)
            if isinstance(obj, dict):
                # Aplatir les sous-objets (ex: adresse imbriquée)
                flat = {}
                for k, v in obj.items():
                    if isinstance(v, dict):
                        # Aplatir : adresse.ville → Ville (adresse), etc.
                        for sk, sv in v.items():
                            if sv:
                                flat_key = f"{sk}"
                                flat[flat_key] = str(sv)
                    elif isinstance(v, list):
                        flat[k] = ", ".join(str(x) for x in v)
                    else:
                        if v is not None and str(v).strip():
                            flat[k] = str(v)
                results.append(flat)
            else:
                # C'est peut-être un format CSV classique (pas de JSON)
                results.append({"raw": json_part})
        except json.JSONDecodeError:
            # Pas du JSON, essayer comme CSV classique
            if "," in json_part:
                parts = [p.strip() for p in json_part.split(",")]
                # Format type: "308416,GIACOMELLO,Andreas,2007-03-08,,,,Basket,FFBasket.jsonl"
                if len(parts) >= 3:
                    entry = {}
                    # Essayer de mapper les champs connus
                    field_map = ["id", "nom", "prenom", "date_naissance", "field4", "field5", "field6", "activite", "source"]
                    for i, val in enumerate(parts):
                        if val and i < len(field_map):
                            entry[field_map[i]] = val
                        elif val:
                            entry[f"champ_{i+1}"] = val
                    if entry:
                        results.append(entry)

    return results


# ═══════════════════════════════════════════════════════════
#  NORMALISATION DES DONNÉES
# ═══════════════════════════════════════════════════════════
def normalize(item):
    """Normalise un résultat brut en dict propre."""
    d: dict = dict(item)

    # Allocataire imbriqué
    alloc = d.get("allocataire")
    if isinstance(alloc, dict):
        parts = [alloc.get("qualite", ""), alloc.get("nom", ""), alloc.get("prenom", "")]
        ident = " ".join(p for p in parts if p).strip()
        if ident:
            d["allocataire"] = ident
        if alloc.get("telephone") and not d.get("telephone"):
            d["telephone"] = alloc["telephone"]
        if alloc.get("courriel") and not d.get("Email"):
            d["Email"] = alloc["courriel"]

    # Adresse imbriquée
    addr = d.get("adresse")
    if isinstance(addr, dict):
        segs = [
            addr.get("voie") or addr.get("ligne", ""),
            " ".join(filter(None, [addr.get("code_postal", ""), addr.get("ville", "")])),
            addr.get("pays", ""),
        ]
        d["adresse"] = " · ".join(s for s in segs if s) or json.dumps(addr)

    # Date de naissance
    dn = d.get("date_naissance", "")
    if dn and "T" in str(dn):
        d["date_naissance"] = str(dn).split("T")[0]

    return d


# ═══════════════════════════════════════════════════════════
#  GÉNÉRATION DU TXT
# ═══════════════════════════════════════════════════════════
FIELD_ORDER = [
    ("nom", "Nom"),
    ("prenom", "Prénom"),
    ("date_naissance", "Date de naissance"),
    ("ville_naiss", "Ville de naissance"),
    ("genre", "Genre"),
    ("telephone", "Téléphone"),
    ("tel", "Téléphone"),
    ("Phone", "Téléphone"),
    ("Phone1", "Téléphone"),
    ("tel_fixe", "Téléphone fixe"),
    ("Email", "Email"),
    ("email", "Email"),
    ("adresse", "Adresse"),
    ("ville", "Ville"),
    ("postal", "Code postal"),
    ("pays", "Pays"),
    ("nationalite", "Nationalité"),
    ("organisme", "Organisme"),
    ("situation", "Situation"),
    ("profession", "Profession"),
    ("employeur", "Employeur"),
    ("ip", "Adresse IP"),
    ("iban", "IBAN"),
    ("plaque", "Plaque"),
    ("discord_id", "Discord ID"),
    ("twitter", "Twitter"),
    ("snapchat", "Snapchat"),
    ("steam", "Steam"),
    ("minecraft", "Minecraft"),
    ("fivem", "FiveM"),
    ("username", "Username"),
    ("id", "Identifiant"),
    ("id_psp", "ID PSP"),
]


def generate_dorks(nom, prenom):
    """Génère des liens Google Dorks pour la cible."""
    target = f'"{prenom} {nom}"'
    dorks = [
        ("LinkedIn", f"site:linkedin.com/in/ {target}"),
        ("Facebook", f"site:facebook.com {target}"),
        ("Instagram", f"site:instagram.com {target}"),
        ("Documents", f"{target} filetype:pdf OR filetype:doc OR filetype:docx"),
        ("News", f"{target} news")
    ]
    links = []
    for label, query in dorks:
        q = urllib.parse.quote(query)
        links.append((label, f"https://www.google.com/search?q={q}"))
    return links


def generate_fiche_txt(nom, prenom, results, date_str):
    """Génère le contenu TXT complet de la fiche."""
    L = []

    # ── LOGO ──
    L: list = []
    L.append("")
    L.append("     ╔════════════════════════════════════════════╗")
    L.append("     ║            ┌──────────────────┐            ║")
    L.append("     ║            │   ╱╱╱╱╱╱╱╱╱╱╱╱   │            ║")
    L.append("     ║            │          ╱╱╱╱     │            ║")
    L.append("     ║            │       ╱╱╱╱        │            ║")
    L.append("     ║            │    ╱╱╱╱           │            ║")
    L.append("     ║            │   ╱╱╱╱╱╱╱╱╱╱╱╱   │            ║")
    L.append("     ║            └──────────────────┘            ║")
    L.append("     ║                                            ║")
    L.append("     ║    ███████ ███████  █████  ██████   ██████ ║")
    L.append("     ║       ██  ██      ██   ██ ██   ██ ██      ║")
    L.append("     ║      ██  ███████ ███████  ██████  ██      ║")
    L.append("     ║     ██       ██ ██   ██ ██   ██ ██      ║")
    L.append("     ║    ███████ ███████ ██   ██ ██   ██  ██████ ║")
    L.append("     ║          ──── Z S E A R C H E R ────       ║")
    L.append("     ╚════════════════════════════════════════════╝")
    L.append("")

    # ── EN-TÊTE ──
    title = f"{prenom} {nom}".strip()
    L.append(box_top)
    L.append(box_center("F I C H E   C O N T A C T"))
    L.append(box_mid)
    L.append(box_line(f"Recherche        : {title}"))
    L.append(box_line(f"Date             : {date_str}"))
    L.append(box_line(f"Résultats trouvés: {len(results)}"))
    L.append(box_bot)
    L.append("")

    if not results:
        L.append(box_top)
        L.append(box_center("AUCUN RÉSULTAT"))
        L.append(box_mid)
        L.append(box_line("La recherche n'a retourné aucun résultat."))
        L.append(box_bot)
        L.append("")
    else:
        for idx, raw_item in enumerate(results):
            item = normalize(raw_item)

            # Trouver les champs disponibles
            seen_labels = set()
            entries = []
            for key, label in FIELD_ORDER:
                val = item.get(key, "")
                if val and label not in seen_labels:
                    entries.append((label, str(val)))
                    seen_labels.add(label)

            # Ajouter les champs non mappés
            mapped_keys = {k for k, _ in FIELD_ORDER}
            for k, v in item.items():
                if k not in mapped_keys and v and not isinstance(v, (dict, list)):
                    lbl = k.replace("_", " ").title()
                    if lbl not in seen_labels:
                        entries.append((lbl, str(v)))
                        seen_labels.add(lbl)

            # Titre du résultat
            r_nom = item.get("nom", item.get("Nom", ""))
            r_prenom = item.get("prenom", item.get("Prénom", ""))
            r_title = f"{r_prenom} {r_nom}".strip() or f"Résultat {idx + 1}"

            L.append(box_top)
            L.append(box_center(f"RÉSULTAT {idx + 1} / {len(results)}  —  {r_title}"))
            L.append(box_mid)

            if not entries:
                L.append(box_line("Aucune donnée exploitable."))
            else:
                max_label = max(len(lbl) for lbl, _ in entries)
                for i, (lbl, val) in enumerate(entries):
                    padded = pad(lbl, max_label)
                    
                    # Logique de lien cliquable
                    display_val = val
                    link = None
                    lbl_low = lbl.lower()
                    
                    if "adresse" in lbl_low or "voie" in lbl_low or "rue" in lbl_low or "ville" in lbl_low:
                        q = urllib.parse.quote(val)
                        link = f"https://www.google.com/maps/search/?api=1&query={q}"
                    elif "email" in lbl_low and "@" in val:
                        link = f"mailto:{val}"
                    elif ("téléphone" in lbl_low or "phone" in lbl_low or "numéro" in lbl_low) and any(c.isdigit() for c in val):
                        link = f"tel:{val.replace(' ', '')}"
                    
                    if link:
                        display_val = f"{G}{make_link(link, val)}{R}{G}"

                    L.append(box_line(f"  {padded}  │  {display_val}"))
                    if i < len(entries) - 1:
                        L.append(thin_sep)

            L.append(box_bot)
            L.append("")

    # ── GOOGLE DORKS (OSINT) ──
    dorks = generate_dorks(nom, prenom)
    L.append(box_top)
    L.append(box_center("🔬  GOOGLE DORKS (OSINT BOOST)"))
    L.append(box_mid)
    for label, link in dorks:
        link_text = f"[ Ouvrir {label} ]"
        display_link = f"{G}{make_link(link, link_text)}{R}{G}"
        L.append(box_line(f"  {pad(label, 12)}  │  {display_link}"))
    L.append(box_bot)
    L.append("")

    # ── PIED DE PAGE ──
    footer = f"Généré par ZSearcher  •  {date_str}"
    L.append("─" * (W + 2))
    L.append(center(footer, W + 2))
    L.append("─" * (W + 2))
    L.append("")

    return "\n".join(L)


def update_index_dashboard():
    """Génère ou met à jour l'index central des dossiers dans le dossier 'archives'."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    archives_dir = os.path.join(script_dir, "archives")
    index_path = os.path.join(archives_dir, "index.html")
    
    if not os.path.exists(archives_dir):
        return

    # Scan des fichiers HTML
    files = [f for f in os.listdir(archives_dir) if f.endswith(".html") and f != "index.html"]
    dossiers = []
    
    for f in files:
        path = os.path.join(archives_dir, f)
        mtime = os.path.getmtime(path)
        date_str = datetime.fromtimestamp(mtime).strftime("%d/%m/%Y %H:%M")
        
        # Extraction du nom du sujet (simple via filename pour la rapidité)
        # Format attendu : Fiche_Prenom_Nom.html
        name_part = f.replace("Fiche_", "").replace(".html", "").replace("_", " ")
        dossiers.append({
            "name": name_part,
            "filename": f,
            "date": date_str,
            "timestamp": mtime
        })

    # Tri par date décroissante
    dossiers.sort(key=lambda x: x["timestamp"], reverse=True)

    # Statistiques
    total = len(dossiers)
    
    # HTML Dashboard
    html = f"""
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>ZSearcher Dashboard</title>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
            :root {{
                --bg: #0f172a;
                --surface: #1e293b;
                --primary: #3b82f6;
                --text: #f8fafc;
                --text-muted: #94a3b8;
                --accent: #10b981;
            }}
            body {{
                background: var(--bg);
                color: var(--text);
                font-family: 'Inter', sans-serif;
                margin: 0;
                padding: 40px;
                display: flex;
                flex-direction: column;
                align-items: center;
            }}
            .container {{ width: 100%; max-width: 1000px; }}
            header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 40px;
                border-bottom: 1px solid #334155;
                padding-bottom: 20px;
            }}
            h1 {{ font-size: 28px; font-weight: 700; margin: 0; color: var(--primary); }}
            .stats {{ font-size: 13px; color: var(--text-muted); }}
            .search-bar {{
                width: 100%;
                padding: 12px 20px;
                background: var(--surface);
                border: 1px solid #334155;
                border-radius: 8px;
                color: white;
                margin-bottom: 30px;
                font-size: 15px;
            }}
            .grid {{
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
                gap: 20px;
            }}
            .folder-card {{
                background: var(--surface);
                border: 1px solid #334155;
                border-radius: 12px;
                padding: 20px;
                transition: transform 0.2s, border-color 0.2s;
                text-decoration: none;
                color: inherit;
                position: relative;
                overflow: hidden;
            }}
            .folder-card:hover {{
                transform: translateY(-5px);
                border-color: var(--primary);
                background: #25334a;
            }}
            .card-icon {{
                font-size: 40px;
                margin-bottom: 15px;
                opacity: 0.2;
                position: absolute;
                right: -10px;
                bottom: -10px;
            }}
            .folder-name {{ font-weight: 700; font-size: 18px; margin-bottom: 5px; }}
            .folder-date {{ font-size: 12px; color: var(--text-muted); }}
            .badge {{
                display: inline-block;
                padding: 3px 8px;
                background: rgba(59, 130, 246, 0.2);
                color: var(--primary);
                border-radius: 4px;
                font-size: 10px;
                font-weight: 700;
                margin-top: 10px;
                text-transform: uppercase;
            }}
            footer {{ margin-top: 50px; font-size: 12px; color: var(--text-muted); text-align: center; }}
            #no-results {{ display: none; text-align: center; padding: 40px; opacity: 0.5; }}
        </style>
    </head>
    <body>
        <div class="container">
            <header>
                <div>
                    <h1>ZSearcher Intelligence</h1>
                    <div class="stats">TOTAL DOSSIERS: {total}</div>
                </div>
                <div style="text-align: right">
                    <div style="font-weight: 700; color: var(--accent);">STATION_ACTIVE</div>
                    <div style="font-size: 10px; color: var(--text-muted);">HOST: LOCALHOST:8000</div>
                </div>
            </header>

            <input type="text" class="search-bar" placeholder="Rechercher un dossier par nom..." id="search">

            <div class="grid" id="dossier-grid">
    """
    
    for d in dossiers:
        html += f"""
                <a href="{d['filename']}" class="folder-card" data-name="{d['name'].lower()}">
                    <div class="folder-name">{d['name']}</div>
                    <div class="folder-date">Dernière mise à jour : {d['date']}</div>
                    <div class="badge">DOSSIER_CONFIDENTIEL</div>
                    <div class="card-icon">📁</div>
                </a>
        """
        
    html += """
            </div>
            <div id="no-results">Aucun dossier correspondant trouvé.</div>

            <footer>
                ZSEARCHER CASE MANAGEMENT SYSTEM &copy; 2026<br>
                Généré automatiquement par le moteur ZSearcher.
            </footer>
        </div>

        <script>
            const search = document.getElementById('search');
            const grid = document.getElementById('dossier-grid');
            const cards = document.querySelectorAll('.folder-card');
            const noResults = document.getElementById('no-results');

            search.addEventListener('input', (e) => {
                const term = e.target.value.toLowerCase();
                let found = 0;
                cards.forEach(card => {
                    if (card.getAttribute('data-name').includes(term)) {
                        card.style.display = 'block';
                        found++;
                    } else {
                        card.style.display = 'none';
                    }
                });
                noResults.style.display = found === 0 ? 'block' : 'none';
            });
        </script>
    </body>
    </html>
    """
    
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(html)

def save_fiche(nom, prenom, content, results=None):
    """Sauvegarde la fiche en TXT et génère un rapport HTML Premium."""
    clean_content = strip_ansi(content)
    
    # Dossiers
    script_dir = os.path.dirname(os.path.abspath(__file__))
    archives_dir = os.path.join(script_dir, "archives")
    if not os.path.exists(archives_dir):
        os.makedirs(archives_dir)
        
    # Nommage
    safe_nom = nom.replace(" ", "_").strip()
    safe_prenom = prenom.replace(" ", "_").strip()
    if not safe_prenom: safe_prenom = "Search"
    
    base_name = f"Fiche_{safe_prenom}_{safe_nom}"
    txt_path = os.path.join(archives_dir, f"{base_name}.txt")
    html_path = os.path.join(archives_dir, f"{base_name}.html")
    
    try:
        # 1. Sauvegarde TXT
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(clean_content)
        with open("derniere_recherche.txt", "w", encoding="utf-8") as f:
            f.write(clean_content)
            
        # 2. Sauvegarde HTML (Rapport Pro)
        if results:
            html_content = generate_html_report(nom, prenom, results)
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html_content)
            print(f"  {G}✅  Rapport Pro généré → {B}{base_name}.html{R}")
            
        print(f"  {G}✅  Fiche TXT exportée → {B}{base_name}.txt{R}")
        
        # 3. Mettre à jour le Dashboard Case Management
        update_index_dashboard()
        print(f"  {G}🖥️   Dashboard mis à jour → {B}http://localhost:8000/archives/index.html{R}")
        
        return html_path if results else txt_path
    except Exception as e:
        print(f"  {R}[!] Erreur export : {e}{R}")
        return None

def generate_html_report(nom: str, prenom: str, results: list):
    """Génère un rapport HTML avec un design 'OSINT Dossier' élégant et pro."""
    date_now = datetime.now().strftime("%d/%m/%Y %H:%M")
    full_name = f"{prenom.title()} {nom.upper()}"
    
    # Calcul du Score d'Exposition (Threat Assessment)
    score = 0
    exposure_factors = []
    pii_found = set()
    
    for res_item in results:
        res: dict = dict(res_item)
        for k, v in res.items():
            if not v: continue
            kl = k.lower()
            if "email" in kl or "@" in str(v): pii_found.add("EMAIL")
            if "tel" in kl or "phone" in kl: pii_found.add("PHONE")
            if "adresse" in kl or "voie" in kl or "rue" in kl: pii_found.add("ADDRESS")
            if "iban" in kl or "rib" in kl: pii_found.add("FINANCIAL")
            if "naissance" in kl: pii_found.add("BIRTHDATE")

    # Calcul
    if "EMAIL" in pii_found: score += 15; exposure_factors.append("Courriel identifié")
    if "PHONE" in pii_found: score += 25; exposure_factors.append("Contact téléphonique direct")
    if "ADDRESS" in pii_found: score += 20; exposure_factors.append("Localisation résidentielle")
    if "FINANCIAL" in pii_found: score += 30; exposure_factors.append("Données bancaires/RIB")
    if "BIRTHDATE" in pii_found: score += 10; exposure_factors.append("Date de naissance")
    
    score = min(score, 100)
    threat_level = "FAIBLE"
    threat_color = "#10b981"
    if score > 40: threat_level = "MODÉRÉ"; threat_color = "#f59e0b"
    if score > 70: threat_level = "CRITIQUE"; threat_color = "#ef4444"

    # Construction des lignes de résultats
    cards_html = ""
    for i, res_item in enumerate(results):
        res_dict: dict = dict(res_item)
        r_nom = res_dict.get("nom", "").upper()
        r_prenom = res_dict.get("prenom", "").title()
        
        items_html = ""
        for key, val in res_dict.items():
            if val and key not in ["nom", "prenom"]:
                label = key.replace("_", " ").upper()
                
                # Actions contextuelles
                action_btn = ""
                val_low = str(val).lower()
                if "@" in val_low:
                    action_btn = f'<a href="https://epieos.com/?q={val}" target="_blank" class="action-tag">CHECK_EPIEOS</a>'
                elif any(c.isdigit() for c in str(val)) and ("tel" in key.lower() or "phone" in key.lower()):
                    clean_phone = "".join(filter(str.isdigit, str(val)))
                    action_btn = f'<a href="https://wa.me/{clean_phone}" target="_blank" class="action-tag">WHATSAPP</a>'

                items_html += f"""
                <div class="data-row">
                    <span class="data-label">{label}</span>
                    <span class="data-value">{val} {action_btn}</span>
                </div>"""
        
        cards_html += f"""
        <div class="profile-section">
            <div class="section-badge">IDENTIFICATION_DATA_{i+1:02d}</div>
            <div class="section-name">{r_prenom} {r_nom}</div>
            <div class="data-grid">
                {items_html}
            </div>
        </div>
        """

    # Section Liens de découverte
    dorks = generate_dorks(nom, prenom)
    dorks_html = ""
    for label, link in dorks:
        dorks_html += f'<a href="{link}" target="_blank" class="discovery-btn">{label.upper()}</a>'

    return f"""
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>OSINT_PROFILE_{nom.upper()}</title>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&family=JetBrains+Mono:wght@400;700&display=swap');
            
            :root {{
                --primary: #3b82f6;
                --bg: #0f172a;
                --surface: #1e293b;
                --text: #f8fafc;
                --text-muted: #94a3b8;
                --border: #334155;
            }}
            
            body {{
                background-color: var(--bg);
                color: var(--text);
                font-family: 'Inter', sans-serif;
                margin: 0;
                padding: 30px;
                line-height: 1.5;
            }}
            
            .dossier-container {{
                max-width: 900px;
                margin: auto;
                background: var(--surface);
                border: 1px solid var(--border);
                border-radius: 12px;
                overflow: hidden;
                box-shadow: 0 10px 30px rgba(0,0,0,0.5);
            }}
            
            .dossier-header {{
                background: linear-gradient(135deg, #1e293b, #0f172a);
                padding: 40px;
                border-bottom: 1px solid var(--border);
                position: relative;
            }}

            .back-link {{
                position: absolute;
                top: 20px;
                right: 40px;
                color: var(--text-muted);
                text-decoration: none;
                font-size: 11px;
                font-weight: 600;
                display: flex;
                align-items: center;
                gap: 5px;
                transition: color 0.2s;
            }}
            .back-link:hover {{ color: var(--primary); }}
            
            .dossier-header h1 {{
                margin: 0;
                font-size: 32px;
                font-weight: 700;
                letter-spacing: -1px;
                color: var(--text);
            }}
            
            .doc-status {{
                display: inline-block;
                background: rgba(59, 130, 246, 0.1);
                color: var(--primary);
                padding: 4px 12px;
                border: 1px solid var(--primary);
                border-radius: 6px;
                font-size: 11px;
                font-weight: 700;
                margin-top: 15px;
                text-transform: uppercase;
                letter-spacing: 1px;
            }}
            
            .metadata-bar {{
                display: flex;
                gap: 30px;
                padding: 15px 40px;
                background: rgba(0,0,0,0.2);
                font-size: 12px;
                color: var(--text-muted);
                border-bottom: 1px solid var(--border);
            }}
            
            .meta-item b {{ color: var(--text); }}
            
            .profile-section {{
                margin: 20px 40px;
                padding: 25px;
                background: rgba(15, 23, 42, 0.5);
                border: 1px solid var(--border);
                border-radius: 8px;
                display: none; /* Hidden by default for pagination */
            }}
            .profile-section.active {{ display: block; }}
            
            .section-badge {{
                font-family: 'JetBrains Mono', monospace;
                font-size: 10px;
                color: var(--primary);
                margin-bottom: 10px;
                opacity: 0.8;
            }}
            
            .section-name {{
                font-size: 20px;
                font-weight: 600;
                margin-bottom: 20px;
                border-bottom: 1px solid var(--border);
                padding-bottom: 10px;
            }}
            
            .data-grid {{
                display: grid;
                gap: 12px;
            }}
            
            .data-row {{
                display: flex;
                align-items: center;
                font-size: 14px;
            }}
            
            .data-label {{
                width: 180px;
                color: var(--text-muted);
                font-size: 11px;
                font-weight: 700;
                text-transform: uppercase;
                flex-shrink: 0;
            }}
            
            .data-value {{
                color: var(--text);
                display: flex;
                align-items: center;
                gap: 10px;
                flex-wrap: wrap;
            }}

            .action-tag {{
                text-decoration: none;
                font-size: 9px;
                font-weight: 700;
                background: rgba(16, 185, 129, 0.1);
                color: #10b981;
                border: 1px solid rgba(16, 185, 129, 0.3);
                padding: 2px 6px;
                border-radius: 4px;
                transition: all 0.2s;
            }}

            .action-tag:hover {{
                background: #10b981;
                color: white;
            }}
            
            .discovery-section {{
                margin: 40px;
                padding: 25px;
                border: 1px solid rgba(59, 130, 246, 0.3);
                border-radius: 8px;
                background: rgba(59, 130, 246, 0.03);
            }}
            
            .discovery-section h3 {{
                margin-top: 0;
                font-size: 14px;
                text-transform: uppercase;
                color: var(--primary);
                margin-bottom: 20px;
            }}
            
            .discovery-grid {{
                display: flex;
                flex-wrap: wrap;
                gap: 10px;
            }}
            
            .discovery-btn {{
                text-decoration: none;
                background: var(--surface);
                border: 1px solid var(--border);
                color: var(--text);
                padding: 8px 16px;
                border-radius: 6px;
                font-size: 11px;
                font-weight: 600;
                transition: all 0.2s;
            }}
            
            .discovery-btn:hover {{
                border-color: var(--primary);
                background: var(--primary);
                color: white;
            }}
            
            .dossier-footer {{
                padding: 30px;
                text-align: center;
                font-size: 11px;
                color: var(--text-muted);
                border-top: 1px solid var(--border);
                background: rgba(0,0,0,0.1);
            }}
            
            .exposure-gauge {{
                margin: 40px;
                padding: 25px;
                background: rgba(0,0,0,0.2);
                border: 1px solid var(--border);
                border-radius: 8px;
                display: flex;
                align-items: center;
                gap: 30px;
            }}
            
            .gauge-circle {{
                width: 80px;
                height: 80px;
                border-radius: 50%;
                border: 8px solid #334155;
                display: flex;
                align-items: center;
                justify-content: center;
                font-weight: 700;
                font-size: 20px;
                color: {threat_color};
                position: relative;
            }}
            
            .gauge-info h4 {{ margin: 0 0 5px 0; font-size: 11px; text-transform: uppercase; color: var(--text-muted); }}
            .gauge-status {{ font-size: 24px; font-weight: 700; color: {threat_color}; }}
            .exposure-list {{ margin-top: 10px; font-size: 11px; color: var(--text-muted); }}

            /* Pagination */
            .pagination-container {{
                display: flex;
                justify-content: center;
                gap: 10px;
                margin: 20px 0;
                padding: 0 40px;
            }}
            .page-btn {{
                background: var(--surface);
                border: 1px solid var(--border);
                color: var(--text);
                padding: 8px 15px;
                border-radius: 6px;
                cursor: pointer;
                font-size: 12px;
                font-weight: 600;
                transition: all 0.2s;
            }}
            .page-btn.active {{
                background: var(--primary);
                border-color: var(--primary);
                color: white;
            }}
            .page-btn:hover:not(.active) {{
                border-color: var(--primary);
                color: var(--primary);
            }}

            @media print {{
                body {{ background: white; color: black; padding: 0; }}
                .dossier-container {{ border: none; box-shadow: none; }}
                .discovery-btn {{ border: 1px solid #ccc; }}
                .profile-section {{ display: block !important; }}
                .pagination-container {{ display: none; }}
            }}
        </style>
    </head>
    <body>
        <div class="dossier-container">
            <header class="dossier-header">
                <a href="index.html" class="back-link">← DASHBOARD ARCHIVES</a>
                <h1>Dossier d'Identification</h1>
                <div class="doc-status" style="border-color: {threat_color}; color: {threat_color};">
                    RISQUE : {threat_level} ({score}%)
                </div>
                <div class="doc-status">Profil OSINT : {full_name}</div>
            </header>
            
            <div class="metadata-bar">
                <div class="meta-item">GÉNÉRÉ LE : <b>{date_now}</b></div>
                <div class="meta-item">ID_LOG : <b>{int(time.time() % 100000)}</b></div>
                <div class="meta-item">SOURCE : <b>ZSEARCHER_IDENTITY</b></div>
            </div>

            <div class="exposure-gauge">
                <div class="gauge-circle" style="border-top-color: {threat_color}">
                    {score}%
                </div>
                <div class="gauge-info">
                    <h4>Analyse d'Exposition Numérique</h4>
                    <div class="gauge-status">{threat_level}</div>
                    <div class="exposure-list">
                        Facteurs d'exposition : {', '.join(exposure_factors) if exposure_factors else 'Aucun facteur critique détecté'}
                    </div>
                </div>
            </div>

            <div id="results-wrapper">
                {cards_html}
            </div>

            <div class="pagination-container" id="pagination-controls"></div>

            <div class="discovery-section">
                <h3>Vérifications étendues (liens externes)</h3>
                <div class="discovery-grid">
                    {dorks_html}
                </div>
            </div>

            <div class="dossier-footer">
                ZSEARCHER IDENTITY SYSTEMS - DOCUMENT D'INTELLIGENCE <br>
                Usage confidentiel uniquement. Source : Données publiques agrégées.
            </div>
        </div>

        <script>
            const resultsPerPage = 10;
            const sections = document.querySelectorAll('.profile-section');
            const totalPages = Math.ceil(sections.length / resultsPerPage);
            const paginationControls = document.getElementById('pagination-controls');
            let currentPage = 1;

            function showPage(page) {{
                currentPage = page;
                const start = (page - 1) * resultsPerPage;
                const end = start + resultsPerPage;

                sections.forEach((section, index) => {{
                    if (index >= start && index < end) {{
                        section.classList.add('active');
                    }} else {{
                        section.classList.remove('active');
                    }}
                }});

                updatePagination();
            }}

            function updatePagination() {{
                if (totalPages <= 1) {{
                    paginationControls.style.display = 'none';
                    return;
                }}

                paginationControls.innerHTML = '';
                for (let i = 1; i <= totalPages; i++) {{
                    const btn = document.createElement('button');
                    btn.innerText = i;
                    btn.classList.add('page-btn');
                    if (i === currentPage) btn.classList.add('active');
                    btn.onclick = () => showPage(i);
                    paginationControls.appendChild(btn);
                }}
            }}

            showPage(1);
        </script>
    </body>
    </html>
    """


# ═══════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════
def main():
    parser = argparse.ArgumentParser(description="ZSearcher Hacker Edition")
    parser.add_argument("nom", nargs="?", help="Nom de famille")
    parser.add_argument("prenom", nargs="?", help="Prénom")
    parser.add_argument("--interactive", "-i", action="store_true", help="Mode interactif Ghost")
    parser.add_argument("--file", "-f", help="Mode Batch : fichier contenant une liste de noms")
    parser.add_argument("--login", help="Sauvegarder ton cookie de session (ex: search --login 'session=...')")

    args = parser.parse_args()

    # Si login demandé
    if args.login:
        save_login_cookie(args.login)
        sys.exit(0)

    # Si on n'a rien du tout, aide
    if not args.nom and not args.interactive and not args.file:
        parser.print_help()
        sys.exit(0)

    # Mode Interactif Ghost
    if args.interactive:
        print_logo()
        print(f"  {G}👻 MODE GHOST ACTIVÉ{R}")
        print(f"  {DG}Commandes : 'clear', 'stats', 'history', '-export', 'exit'{R}")
        last_search: dict = {}
        
        while True:
            try:
                line = input(f"\n  {G}root@zsearcher:{R} ").strip()
                if not line: continue
                if line.lower() in ["exit", "quit", "q"]: break
                
                # Option Export manuel
                if line.lower() == "-export":
                    if last_search and 'res' in last_search:
                        path = save_fiche(str(last_search.get('nom', '')), 
                                         str(last_search.get('prenom', '')), 
                                         str(last_search.get('content', '')), 
                                         last_search.get('res'))
                        if path:
                            try:
                                subprocess.Popen(["open", path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                                print(f"  {DG}📂  Rapport professionnel ouvert.{R}")
                            except: pass
                    else:
                        print(f"  {R}[!] Aucune recherche en mémoire à exporter.{R}")
                    continue

                parts = line.split()
                if not parts: continue
                
                p_nom = parts[0]
                p_prenom = " ".join(parts[1:]) if len(parts) > 1 else ""
                
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                res_fetched = fetch_results(p_nom, p_prenom)
                res: list = res_fetched if isinstance(res_fetched, list) else []
                
                print(f"  {G}📊  {len(res)} résultat(s) trouvé(s).{R}")
                if res:
                    content = generate_fiche_txt(p_nom, p_prenom, res, now_str)
                    # On stocke pour l'export futur
                    last_search = {'nom': p_nom, 'prenom': p_prenom, 'content': content, 'res': res}
                    print(f"{G}{content}{R}")
                    print(f"  {DG}💡 Taper '-export' pour générer le rapport PDF/HTML.{R}")
            except KeyboardInterrupt:
                break
        print(f"\n  {DG}Sortie du mode Ghost.{R}\n")
        sys.exit(0)

    # Mode Batch (Multiples recherches)
    if args.file:
        if not os.path.exists(args.file):
            print(f"  {R}[!] Fichier introuvable : {args.file}{R}")
            sys.exit(1)
            
        with open(args.file, "r") as f:
            lines = [l.strip() for l in f if l.strip()]
            
        print(f"\n  {G}🚀 Lancement du SCAN BATCH ({len(lines)} cibles){R}")
        for i, line in enumerate(lines):
            parts = line.split()
            nom = parts[0]
            prenom = " ".join(parts[1:]) if len(parts) > 1 else ""
            
            print(f"\n  {B}[{i+1}/{len(lines)}] Scan de {prenom} {nom}...{R}")
            now = datetime.now()
            date_str = now.strftime("%H:%M:%S")
            
            results = fetch_results(nom, prenom)
            if results:
                content = generate_fiche_txt(nom, prenom, results, date_str)
                save_fiche(nom, prenom, content, results)
        
        print(f"\n  {G}🏁 SCAN BATCH TERMINÉ.{R}")
        sys.exit(0)

    # Mode normal (Une seule recherche)
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d %H:%M:%S")
    nom = args.nom
    prenom = args.prenom or ""

    print_logo()
    print(f"  {B}Recherche{R} : {prenom} {nom}")
    print(f"  {B}Date     {R} : {date_str}")
    print(f"  {DG}──────────────────────────────────────────{R}")

    # Appel API
    results = fetch_results(nom, prenom)

    print(f"  {G}📊  {B}{len(results)}{R}{G} résultat(s) trouvé(s).{R}")

    # Export et Affichage
    content = generate_fiche_txt(nom, prenom, results, date_str)
    filepath = save_fiche(nom, prenom, content, results)
    
    if filepath:
        try:
            subprocess.Popen(["open", filepath], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print(f"  {DG}📂  Ouverture automatique du rapport.{R}")
        except: pass

    print()
    print(f"{G}{content}{R}")
    print()


if __name__ == "__main__":
    main()
