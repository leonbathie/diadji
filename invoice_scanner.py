"""
Module de Numérisation & Déchiffrage Intelligent de Factures et Bons de Livraison
pour le logiciel DIADJI FAMILY.

Supporte :
1. IA Multimodale Google Gemini Vision (lecture haute fidélité des écritures manuscrites difficiles)
2. OCR Local Natif Windows Media (100% hors ligne, sans installation supplémentaire)
3. Moteur de correspondance floue (Fuzzy Matching) adapté au catalogue quincaillerie & matériaux (183+ articles)
"""

import os
import sys
import json
import re
import time
import base64
import tempfile
import subprocess
import unicodedata
import urllib.request
import urllib.error
from difflib import SequenceMatcher
from io import BytesIO

try:
    from PIL import Image, ImageEnhance, ImageOps
except ImportError:
    Image = None
    ImageEnhance = None
    ImageOps = None

import database

# ==============================================================================
# CONFIGURATION ET GESTION DES CLÉS API
# ==============================================================================

def get_gemini_api_key():
    """Récupère la clé API Gemini configurée dans la base de données ou les variables d'environnement."""
    # 1. Base SQLite (table parametres)
    key = database.get_setting("gemini_api_key")
    if key and key.strip():
        return key.strip()

    # 2. Variable d'environnement
    for env_var in ("GEMINI_API_KEY", "GOOGLE_API_KEY", "GOOGLE_GENAI_API_KEY"):
        val = os.environ.get(env_var)
        if val and val.strip():
            return val.strip()

    return ""


def set_gemini_api_key(key):
    """Enregistre la clé API Gemini dans les paramètres de la base embarquée."""
    return database.set_setting("gemini_api_key", (key or "").strip())


def has_gemini_configured():
    """Indique si une clé API Gemini est actuellement utilisable."""
    return bool(get_gemini_api_key())


def test_gemini_api_key(api_key=None):
    """
    Vérifie la validité d'une clé API Google Gemini en appelant l'API REST officielle.
    Retourne (succès: bool, message: str).
    """
    if not api_key:
        api_key = get_gemini_api_key()

    if not api_key or not str(api_key).strip():
        return False, "Aucune clé API fournie."

    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key.strip()}"
    req = urllib.request.Request(url, headers={"User-Agent": "DIADJI_FAMILY/2.0"}, method="GET")

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status == 200:
                return True, "Connexion à Google Gemini réussie ! Clé valide et active."
            return False, f"Réponse inattendue de l'API (HTTP {resp.status})."
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8", errors="replace")
        if e.code in (400, 401, 403):
            return False, f"Clé API invalide ou non autorisée par Google (HTTP {e.code}). Vérifiez la clé."
        return False, f"Erreur Google Gemini HTTP {e.code} : {err_msg[:120]}"
    except Exception as e:
        return False, f"Erreur de connexion réseau vers Google Gemini : {str(e)}"


# ==============================================================================
# DICTIONNAIRE DE SYNONYMES ET ABRÉVIATIONS DU BÂTIMENT & QUINCAILLERIE SÉNÉGAL
# ==============================================================================

SYNONYMS_HARDWARE = {
    # Électricité & appareillage
    "int": "interrupteur",
    "inter": "interrupteur",
    "interupteur": "interrupteur",
    "interrup": "interrupteur",
    "vv": "va et vient",
    "vaetvient": "va et vient",
    "da": "double allumage",
    "bp": "bouton poussoir",
    "poussoir": "bouton poussoir",
    "pc": "prise",
    "dismatic": "dismatic",
    "parafoudre": "parafoudre",
    "telerupteur": "telerupteur",

    # Protection & disjoncteurs
    "disj": "disjoncteur",
    "disjonct": "disjoncteur",
    "diff": "differentiel",

    # Câbles & fils
    "fil": "fil",
    "cable": "cable",
    "gaine": "gaine",
    "icta": "icta",

    # Plomberie & PVC
    "tuyau": "tube",
    "tangit": "colle",

    # Éclairage
    "plafonnier": "hublot",

    # Visserie & Fixation
    "placo": "placo",
    "tirefond": "tirefond",

    # Matériaux lourds / Gros œuvre
    "sococim": "sococim",
    "dangote": "dangote",
    "sahel": "sahel",
    "fe": "fer",
}


def strip_accents(text):
    """Supprime les accents pour une comparaison textuelle normalisée."""
    if not text:
        return ""
    return "".join(c for c in unicodedata.normalize("NFD", str(text)) if unicodedata.category(c) != "Mn").lower()


def normalize_query(text):
    """Normalise et expanse les abréviations usuelles du bâtiment."""
    clean = strip_accents(text).lower()
    clean = clean.replace("va-et-vient", "va et vient").replace("v-et-v", "va et vient").replace("v et v", "va et vient")
    clean = clean.replace("ø", " ").replace("∅", " ").replace("°", " ").replace("²", "2")
    clean = clean.replace("+", " ").replace("-", " ")
    clean = re.sub(r'[^a-z0-9\s,\.]', ' ', clean)
    clean = clean.replace(",", ".")
    tokens = clean.split()
    expanded = []
    for t in tokens:
        expanded.append(SYNONYMS_HARDWARE.get(t, t))
    return " ".join(expanded)


# ==============================================================================
# ALGORITHME DE MATCHING FLOU (FUZZY MATCHING) AVEC LE CATALOGUE
# ==============================================================================

def fuzzy_match_article(query_label, catalog_articles):
    """
    Associe un libellé extrait d'une facture au meilleur article du catalogue.
    Retourne : (meilleur_article, score_confiance, alternatives)
    """
    if not query_label or not catalog_articles:
        return None, 0.0, []

    q_norm = normalize_query(query_label)
    q_tokens = set(q_norm.split())
    # Recherche des nombres et calibres clés (ex: 1.5, 2.5, 10, 16, 20, 25, 32, 40, 50, 100)
    q_numbers = set(re.findall(r'\b\d+(?:\.\d+)?\b', q_norm))

    scored_candidates = []

    for art in catalog_articles:
        art_name = art.get("nom") or art.get("name") or ""
        a_norm = normalize_query(art_name)
        a_tokens = set(a_norm.split())
        a_numbers = set(re.findall(r'\b\d+(?:\.\d+)?\b', a_norm))

        # 1. Correspondance exacte normalisée
        if q_norm == a_norm:
            scored_candidates.append((1.0, art))
            continue

        # 2. Similarité de Jaccard sur les jetons
        intersection = len(q_tokens & a_tokens)
        union = len(q_tokens | a_tokens)
        jaccard = intersection / max(union, 1)

        # 3. Similarité séquentielle (difflib SequenceMatcher)
        seq_ratio = SequenceMatcher(None, q_norm, a_norm).ratio()

        # 4. Cohérence des dimensions / calibres numériques
        num_modifier = 1.0
        if q_numbers:
            common_nums = q_numbers & a_numbers
            if common_nums:
                # Bonus significatif si les diamètres ou ampérages correspondent exactement
                num_modifier = 1.35
            else:
                # Pénalité si la requête précise un calibre mais que l'article en a un autre différent
                if a_numbers:
                    num_modifier = 0.35

        score = (0.50 * jaccard + 0.50 * seq_ratio) * num_modifier
        score = min(score, 1.0)

        if score > 0.20:
            scored_candidates.append((score, art))

    # Trier par score décroissant
    scored_candidates.sort(key=lambda x: x[0], reverse=True)

    if not scored_candidates:
        return None, 0.0, []

    best_score, best_art = scored_candidates[0]
    alternatives = [
        {
            "id": c[1]["id"],
            "nom": c[1].get("nom", c[1].get("name")),
            "prix": c[1].get("prix_vente", c[1].get("price", 0)),
            "unite": c[1].get("unite", c[1].get("unit", "Pièce")),
            "score": round(c[0], 2)
        }
        for c in scored_candidates[:4]
    ]

    return best_art, round(best_score, 2), alternatives


# ==============================================================================
# MOTEUR 1 : IA MULTIMODALE GEMINI VISION
# ==============================================================================

GEMINI_PROMPT_EXPERT = """
Tu es un expert comptable et gestionnaire de stock pour le magasin de quincaillerie et matériaux de construction DIADJI FAMILY (Dakar, Sénégal).
Analyse minutieusement cette photo de facture ou bon de livraison, qui peut être manuscrite, au stylo à bille, prise au smartphone avec des angles variés, parfois mal écrite ou raturée.

Objectifs d'extraction :
1. Déchiffre les écritures manuscrites même difficiles, abrégées ou imparfaites.
2. Identifie les métadonnées de l'en-tête :
   - "fournisseur": Nom de l'entreprise ou du fournisseur (ex: SOCOCIM, CDS, Comptoir du Bâtiment, Grossiste Électricité, etc.). Si non mentionné, indique "Fournisseur Général".
   - "numero_facture": Numéro du bon de livraison ou de facture (ex: "BL-1024", "FAC-2026-88"). Si non mentionné, génère un identifiant court basé sur la date ou "BL-MANUSCRIT".
   - "date_facture": Date de la livraison au format "YYYY-MM-DD". Si non mentionnée, laisse vide.
3. Extrais chaque ligne d'article commandé ou livré :
   - "designation_brute": Le texte exact tel qu'il est écrit sur la facture (ex: "ciment sococim 50kg", "interrupteur simple", "disjoncteur 16A", "fer 10", "fil 1.5 100m", "tube pvc 40", "coude 100", "colle pvc", etc.)
   - "quantite": Nombre d'unités numériques (float ou int). Défaut = 1.0 si illisible.
   - "unite": L'unité de mesure mentionnée (Sac, Barre, Rouleau, Pièce, Paquet, Boîte, Carton, Mètre, Kg, Lot, etc.). Défaut = "Pièce".
   - "prix_unitaire": Prix unitaire d'achat en Francs CFA (nombre pur sans texte). Si non indiqué, mets 0.0.
   - "total_ligne": Montant total de la ligne en FCFA (quantite * prix_unitaire). Si non indiqué, mets 0.0.
4. "total_facture": Total général de la facture en FCFA (somme des lignes ou total inscrit en bas).

Format de réponse OBLIGATOIRE :
Réponds UNIQUEMENT avec un JSON valide respectant rigoureusement la structure suivante (sans aucun texte Markdown autour) :
{
  "fournisseur": "Nom du fournisseur",
  "numero_facture": "Numéro du bon",
  "date_facture": "YYYY-MM-DD",
  "total_facture": 0.0,
  "articles": [
    {
      "designation_brute": "libellé déchiffré",
      "quantite": 10.0,
      "unite": "Sac",
      "prix_unitaire": 4500.0,
      "total_ligne": 45000.0
    }
  ]
}
"""

def call_gemini_vision(image_bytes, mime_type="image/jpeg", api_key=None):
    """
    Appelle l'API Google Gemini Vision pour extraire les articles d'une facture manuscrite.
    Supporte gemini-2.0-flash, gemini-1.5-flash et gemini-1.5-pro en séquence de repli.
    """
    if not api_key:
        api_key = get_gemini_api_key()

    if not api_key:
        raise ValueError("Aucune clé API Gemini n'est configurée.")

    b64_data = base64.b64encode(image_bytes).decode("utf-8")

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": GEMINI_PROMPT_EXPERT},
                    {
                        "inline_data": {
                            "mime_type": mime_type,
                            "data": b64_data
                        }
                    }
                ]
            }
        ],
        "generationConfig": {
            "response_mime_type": "application/json",
            "temperature": 0.1
        }
    }

    req_body = json.dumps(payload).encode("utf-8")

    # Modèles officiels Gemini valides par ordre de priorité
    candidate_models = ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"]
    last_error = None

    for model in candidate_models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        req = urllib.request.Request(
            url,
            data=req_body,
            headers={"Content-Type": "application/json", "User-Agent": "DIADJI_FAMILY/2.0"},
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                resp_text = resp.read().decode("utf-8")
                resp_json = json.loads(resp_text)
                candidates = resp_json.get("candidates", [])
                if candidates and "content" in candidates[0]:
                    parts = candidates[0]["content"].get("parts", [])
                    if parts and "text" in parts[0]:
                        raw_text = parts[0]["text"].strip()
                        # Extraction robuste du bloc JSON même si entouré de texte libre
                        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', raw_text)
                        if json_match:
                            json_str = json_match.group(1).strip()
                        else:
                            match_obj = re.search(r'(\{[\s\S]*\}|\[[\s\S]*\])', raw_text)
                            json_str = match_obj.group(1).strip() if match_obj else raw_text

                        parsed = json.loads(json_str)

                        # Normalisation : si Gemini a retourné directement une liste d'articles
                        if isinstance(parsed, list):
                            parsed = {"articles": parsed}
                        elif isinstance(parsed, dict):
                            if "articles" not in parsed:
                                for alt_key in ("items", "lignes", "produits", "facture_articles", "details"):
                                    if alt_key in parsed and isinstance(parsed[alt_key], list):
                                        parsed["articles"] = parsed[alt_key]
                                        break
                                if "articles" not in parsed:
                                    parsed["articles"] = []

                        # Normalisation des champs des articles
                        clean_articles = []
                        for art_item in parsed.get("articles", []):
                            if not isinstance(art_item, dict):
                                continue
                            desig = (art_item.get("designation_brute") or art_item.get("designation") or
                                     art_item.get("nom") or art_item.get("libelle") or art_item.get("description") or "")
                            try:
                                qty = float(art_item.get("quantite") or art_item.get("qty") or art_item.get("qte") or 1.0)
                            except (ValueError, TypeError):
                                qty = 1.0
                            try:
                                pu = float(art_item.get("prix_unitaire") or art_item.get("pu") or art_item.get("prix") or 0.0)
                            except (ValueError, TypeError):
                                pu = 0.0
                            try:
                                tot = float(art_item.get("total_ligne") or art_item.get("total") or art_item.get("montant") or (qty * pu))
                            except (ValueError, TypeError):
                                tot = qty * pu

                            clean_articles.append({
                                "designation_brute": str(desig).strip(),
                                "quantite": qty,
                                "unite": str(art_item.get("unite", "Pièce")).strip() or "Pièce",
                                "prix_unitaire": pu,
                                "total_ligne": tot
                            })
                        parsed["articles"] = clean_articles
                        parsed["provider"] = "gemini"
                        parsed["model_used"] = model
                        return parsed
        except urllib.error.HTTPError as e:
            err_msg = e.read().decode("utf-8", errors="replace")
            last_error = f"HTTP {e.code}: {err_msg[:120]}"
            # Si erreur 404/400 (modèle non disponible sur cette version), tester le suivant
            if e.code in (404, 400, 429):
                continue
            break
        except Exception as e:
            last_error = str(e)
            continue

    raise RuntimeError(f"Échec de l'appel Gemini Vision : {last_error}")


# ==============================================================================
# MOTEUR 2 : OCR LOCAL NATIF WINDOWS MEDIA (100% HORS LIGNE)
# ==============================================================================

POWERSHELL_OCR_RUNNER = """param([string]$ImagePath)
$ErrorActionPreference = 'Stop'
try {
    Add-Type -AssemblyName System.Runtime.WindowsRuntime
    $asTaskGeneric = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object { 
        $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' 
    })[0]
    function Await($WinRtTask, $ResultType) {
        $asTask = $asTaskGeneric.MakeGenericMethod($ResultType)
        $netTask = $asTask.Invoke($null, @($WinRtTask))
        $netTask.Wait(-1) | Out-Null
        $netTask.Result
    }
    [Windows.Storage.StorageFile, Windows.Storage, ContentType = WindowsRuntime] | Out-Null
    [Windows.Media.Ocr.OcrEngine, Windows.Media.Ocr, ContentType = WindowsRuntime] | Out-Null
    [Windows.Graphics.Imaging.BitmapDecoder, Windows.Graphics.Imaging, ContentType = WindowsRuntime] | Out-Null

    $fullPath = [System.IO.Path]::GetFullPath($ImagePath)
    $file = Await ([Windows.Storage.StorageFile]::GetFileFromPathAsync($fullPath)) ([Windows.Storage.StorageFile])
    $stream = Await ($file.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream])
    $decoder = Await ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])
    $bitmap = Await ($decoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])

    $engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages()
    if ($null -eq $engine) {
        $engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage([Windows.Globalization.Language]::new('fr-FR'))
    }
    if ($null -eq $engine) {
        $engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage([Windows.Globalization.Language]::new('en-US'))
    }
    if ($null -eq $engine) {
        $engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage([Windows.Globalization.Language]::AllLanguages[0])
    }
    $res = Await ($engine.RecognizeAsync($bitmap)) ([Windows.Media.Ocr.OcrResult])
    $lines = @()
    foreach ($l in $res.Lines) {
        if ($l.Text.Trim().Length -gt 0) {
            $lines += $l.Text.Trim()
        }
    }
    ConvertTo-Json -Compress -InputObject $lines
} catch {
    Write-Error $_
    exit 1
}
"""

def run_windows_media_ocr(image_bytes):
    """
    Exécute la reconnaissance optique de caractères via le moteur Windows Media OCR natif.
    Fonctionne sans aucune dépendance externe sur Windows 10 et Windows 11.
    """
    # 1. Sauvegarde temporaire de l'image
    temp_img = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    temp_img_path = temp_img.name

    # Si Pillow est disponible, s'assurer que l'image est au format PNG standard net
    if Image:
        try:
            im = Image.open(BytesIO(image_bytes))
            if ImageOps:
                try:
                    im = ImageOps.exif_transpose(im)
                except Exception:
                    pass
            # Conversion en RGB si RGBA ou palette
            if im.mode not in ("RGB", "L"):
                im = im.convert("RGB")
            # Redimensionnement si trop gigantesque (> 2800px) tout en préservant le ratio
            max_dim = max(im.size)
            if max_dim > 2800:
                scale = 2800.0 / max_dim
                new_size = (int(im.width * scale), int(im.height * scale))
                im = im.resize(new_size, Image.Resampling.LANCZOS)
            # Rehaussement du contraste pour lisibilité de l'encre manuscrite
            if ImageEnhance:
                try:
                    enh = ImageEnhance.Contrast(im)
                    im = enh.enhance(1.4)
                except Exception:
                    pass
            im.save(temp_img_path, format="PNG")
        except Exception:
            temp_img.write(image_bytes)
    else:
        temp_img.write(image_bytes)
    temp_img.close()

    # 2. Sauvegarde du script PowerShell temporaire
    temp_ps = tempfile.NamedTemporaryFile(suffix=".ps1", mode="w", encoding="utf-8", delete=False)
    temp_ps.write(POWERSHELL_OCR_RUNNER)
    temp_ps.close()
    temp_ps_path = temp_ps.name

    try:
        cmd = [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy", "Bypass",
            "-File", temp_ps_path,
            temp_img_path
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", timeout=20)
        if proc.returncode != 0:
            print(f"[WARN] Windows Media OCR failed (rc={proc.returncode}): {proc.stderr}")
            return []

        raw = proc.stdout.strip()
        if not raw:
            return []

        try:
            data = json.loads(raw)
            if isinstance(data, list):
                return [str(x).strip() for x in data if str(x).strip()]
            elif isinstance(data, str):
                return [data.strip()]
            return [str(data)]
        except Exception:
            return [l.strip() for l in raw.splitlines() if l.strip()]
    finally:
        for p in (temp_img_path, temp_ps_path):
            if os.path.exists(p):
                try:
                    os.remove(p)
                except Exception:
                    pass


# ==============================================================================
# MOTEUR 2-BIS : OCR LOCAL TESSERACT (SI PRÉSENT SUR LA MACHINE)
# ==============================================================================

def get_tesseract_cmd():
    """Détecte si l'exécutable Tesseract OCR est disponible sur le système."""
    import shutil
    cmd = shutil.which("tesseract")
    if cmd:
        return cmd
    for p in (
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe")
    ):
        if os.path.exists(p):
            return p
    return None


def run_tesseract_ocr(image_bytes):
    """
    Exécute Tesseract OCR si installé sur la machine comme moteur de repli supplémentaire.
    """
    tess_cmd = get_tesseract_cmd()
    if not tess_cmd:
        return []

    temp_img = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    temp_img_path = temp_img.name
    temp_img.write(image_bytes)
    temp_img.close()

    try:
        proc = subprocess.run(
            [tess_cmd, temp_img_path, "stdout", "-l", "fra+eng", "--psm", "6"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=20
        )
        if proc.returncode == 0 and proc.stdout:
            lines = [l.strip() for l in proc.stdout.splitlines() if l.strip()]
            return lines
        return []
    except Exception as e:
        print(f"[WARN] Tesseract OCR error: {e}")
        return []
    finally:
        if os.path.exists(temp_img_path):
            try:
                os.remove(temp_img_path)
            except Exception:
                pass


def parse_raw_ocr_lines(lines):
    """
    Analyse les lignes brutes retournées par l'OCR local pour extraire
    le fournisseur, le numéro de bon/facture et les lignes d'articles.
    """
    fournisseur = "Fournisseur Général"
    numero_facture = ""
    date_facture = ""
    articles = []

    # Unités courantes en quincaillerie
    units_regex = r'\b(sac|sacs|barre|barres|rouleau|rouleaux|pce|pces|pc|pcs|piece|pieces|u|unite|unites|crt|carton|cartons|bte|boite|boites|pqt|paquet|paquets|m|metre|metres|kg|kgs|lot|lots)\b'

    line_idx = 0
    total_lines = len(lines)

    for line in lines:
        line_idx += 1
        l_strip = line.strip()
        if not l_strip:
            continue

        l_lower = strip_accents(l_strip).lower()

        # Détection fournisseur (sur les premières lignes)
        if line_idx <= 4 and fournisseur == "Fournisseur Général":
            has_multiple_nums = len(re.findall(r'\b\d+(?:[\.,]\d+)?\b', l_strip)) >= 2
            if not has_multiple_nums and any(k in l_lower for k in ("sarl", "ets", "quincaillerie", "ste", "fournisseur", "comptoir", "cimenterie")):
                fournisseur = l_strip
                continue

        # Détection numéro de facture / BL
        if any(k in l_lower for k in ("facture", "bon de livraison", "bl n", "fac n", "fact n", "bon n")):
            match_num = re.search(r'(?:facture|livraison|bl|fac|bon)\s*(?:n[°\.]?|:)?\s*([a-zA-Z0-9_\-\/]+)', l_strip, re.IGNORECASE)
            if match_num:
                numero_facture = match_num.group(1).strip()
            continue

        # Détection date (format DD/MM/YYYY ou YYYY-MM-DD)
        match_date = re.search(r'\b(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})\b', l_strip)
        if match_date and not date_facture:
            d_raw = match_date.group(1).replace(".", "/").replace("-", "/")
            parts = d_raw.split("/")
            if len(parts) == 3:
                if len(parts[0]) == 4:
                    date_facture = f"{parts[0]}-{int(parts[1]):02d}-{int(parts[2]):02d}"
                else:
                    year = parts[2] if len(parts[2]) == 4 else f"20{parts[2]}"
                    date_facture = f"{year}-{int(parts[1]):02d}-{int(parts[0]):02d}"

        # Ignorer les lignes de total général ou pied de page
        if any(k in l_lower for k in ("total general", "net a payer", "montant total", "somme a payer", "total facture")):
            continue

        # Recherche de l'unité
        match_unit = re.search(units_regex, l_lower, re.IGNORECASE)
        unit = "Pièce"
        if match_unit:
            u_found = match_unit.group(1).capitalize()
            if u_found.startswith("Sac"): unit = "Sac"
            elif u_found.startswith("Barre"): unit = "Barre"
            elif u_found.startswith("Rouleau"): unit = "Rouleau"
            elif u_found.startswith("Pce") or u_found.startswith("Pc"): unit = "Pièce"
            elif u_found.startswith("Crt") or u_found.startswith("Carton"): unit = "Carton"
            elif u_found.startswith("Bte") or u_found.startswith("Boite"): unit = "Boîte"
            elif u_found.startswith("Pqt") or u_found.startswith("Paquet"): unit = "Paquet"
            elif u_found.startswith("M"): unit = "Mètre"
            elif u_found.startswith("Kg"): unit = "Kg"
            elif u_found.startswith("Lot"): unit = "Lot"

        # Nettoyage de la devise dans la ligne
        clean_line = re.sub(r'\s*(?:FCFA|CFA|XOF|F)\b', '', l_strip, flags=re.IGNORECASE)

        qty = 1.0
        price = 0.0
        total_line = 0.0
        desc = ""

        # Cas 1 : Trailing 3 numbers -> [desc] [qty] [price] [total] (ou avec 'x')
        m3 = re.search(r'^(.*?)\s+(?:x\s*)?(\d+(?:[\.,]\d+)?)\s+(\d+(?:[\.,]\d+)?)\s+(\d+(?:[\.,]\d+)?)$', clean_line)
        if m3:
            desc = m3.group(1).strip()
            n1 = float(m3.group(2).replace(',', '.'))
            n2 = float(m3.group(3).replace(',', '.'))
            n3 = float(m3.group(4).replace(',', '.'))
            if abs(n1 * n2 - n3) <= max(2.0, 0.05 * n3):
                qty, price, total_line = n1, n2, n3
            elif abs(n2 * n3 - n1) <= max(2.0, 0.05 * n1):
                qty, price, total_line = n2, n3, n1
            else:
                qty, price, total_line = n1, n2, n3

        # Cas 2 : Quantité en tête de ligne -> 10 sac(s) Ciment SOCOCIM 4500 45000
        if not desc:
            m_lead = re.search(r'^(\d+(?:[\.,]\d+)?)\s*(?:x\s*)?(?:(sac|sacs|barre|barres|rouleau|rouleaux|pc|pce|pcs|piece|pieces|u|unite|unites|crt|carton|cartons|bte|boite|boites|pqt|paquet|paquets|m|metre|metres|kg|kgs|lot|lots)\b)?\s*(.*?)\s+(\d+(?:[\.,]\d+)?)(?:\s+(\d+(?:[\.,]\d+)?))?$', clean_line, re.IGNORECASE)
            if m_lead and m_lead.group(3).strip():
                qty = float(m_lead.group(1).replace(',', '.'))
                if m_lead.group(2):
                    u_cand = m_lead.group(2).capitalize()
                    if u_cand.startswith("Sac"): unit = "Sac"
                    elif u_cand.startswith("Barre"): unit = "Barre"
                    elif u_cand.startswith("Rouleau"): unit = "Rouleau"
                    elif u_cand.startswith("Kg"): unit = "Kg"
                desc = m_lead.group(3).strip()
                price = float(m_lead.group(4).replace(',', '.'))
                total_line = float(m_lead.group(5).replace(',', '.')) if m_lead.group(5) else (qty * price)

        # Cas 3 : Trailing 2 numbers -> [desc] [qty] [price]
        if not desc:
            m2 = re.search(r'^(.*?)\s+(?:x\s*)?(\d+(?:[\.,]\d+)?)\s+(\d+(?:[\.,]\d+)?)$', clean_line)
            if m2:
                desc = m2.group(1).strip()
                n1 = float(m2.group(2).replace(',', '.'))
                n2 = float(m2.group(3).replace(',', '.'))
                if n1 <= 1000 and n2 >= 50:
                    qty = n1
                    price = n2
                else:
                    qty = min(n1, n2)
                    price = max(n1, n2)
                total_line = qty * price

        # Cas 4 : Trailing 1 number -> [desc] x [qty] ou [desc] [price]
        if not desc:
            m1 = re.search(r'^(.*?)\s+(?:x\s*|qte\s*:?\s*)(\d+(?:[\.,]\d+)?)$', clean_line, re.IGNORECASE)
            if m1:
                desc = m1.group(1).strip()
                qty = float(m1.group(2).replace(',', '.'))
                price = 0.0
                total_line = 0.0

        # Cas 5 : Ligne sans nombres de fin (ou sans nombres du tout)
        if not desc:
            numbers = re.findall(r'\b\d+(?:[\.,]\d+)?\b', clean_line)
            if not numbers:
                if len(l_strip) > 3 and not any(k in l_lower for k in ("merci", "signature", "page", "dakar", "senegal", "tel", "bp")):
                    articles.append({
                        "designation_brute": l_strip,
                        "quantite": 1.0,
                        "unite": unit,
                        "prix_unitaire": 0.0,
                        "total_ligne": 0.0
                    })
                continue
            desc = clean_line

        # Nettoyage des ponctuations résiduelles en fin de désignation
        desc = re.sub(r'[\sx\*=\-:]+$', '', desc).strip()
        if not desc:
            desc = l_strip

        articles.append({
            "designation_brute": desc,
            "quantite": qty if qty > 0 else 1.0,
            "unite": unit,
            "prix_unitaire": price,
            "total_ligne": total_line if total_line > 0 else (qty * price)
        })

    if not numero_facture:
        numero_facture = f"SCAN-{int(time.time()) % 10000:04d}"

    total_facture = sum(a.get("total_ligne", 0.0) for a in articles)

    return {
        "fournisseur": fournisseur,
        "numero_facture": numero_facture,
        "date_facture": date_facture or time.strftime("%Y-%m-%d"),
        "total_facture": total_facture,
        "articles": articles
    }


# ==============================================================================
# ENRICHISSEMENT & CORRESPONDANCE INTELLIGENTE DU CATALOGUE
# ==============================================================================

def enrich_extracted_articles(extracted_articles, catalog_articles=None):
    """
    Prend une liste d'articles extraits (Gemini ou OCR) et les associe
    automatiquement avec les articles du magasin DIADJI FAMILY.
    """
    if catalog_articles is None:
        catalog_articles = database.get_articles()

    enriched = []
    for item in extracted_articles:
        raw_label = item.get("designation_brute", "").strip()
        if not raw_label:
            continue

        best_art, confidence, alternatives = fuzzy_match_article(raw_label, catalog_articles)

        row = {
            "designation_brute": raw_label,
            "quantite": float(item.get("quantite", 1.0)),
            "unite": item.get("unite", "Pièce"),
            "prix_unitaire": float(item.get("prix_unitaire", 0.0)),
            "total_ligne": float(item.get("total_ligne", 0.0)),
            "match_confidence": confidence,
            "suggested_alternatives": alternatives
        }

        # Si score satisfaisant (>= 40%), présélectionner l'article du magasin
        if best_art and confidence >= 0.40:
            row["article_id"] = best_art["id"]
            row["article_nom"] = best_art.get("nom", best_art.get("name"))
            row["article_categorie"] = best_art.get("categorie", best_art.get("cat", "Quincaillerie"))
            row["article_prix_vente"] = float(best_art.get("prix_vente", best_art.get("price", 0)))
            row["stock_actuel"] = float(best_art.get("stock_actuel", best_art.get("stock", 0)))
            # Harmoniser l'unité si celle du catalogue est plus précise
            if best_art.get("unite"):
                row["unite"] = best_art["unite"]
        else:
            # Marquer comme nouvel article potentiel
            row["article_id"] = "NEW"
            row["article_nom"] = raw_label
            row["article_categorie"] = "Quincaillerie & Matériaux"
            row["article_prix_vente"] = row["prix_unitaire"] * 1.25 if row["prix_unitaire"] > 0 else 0.0
            row["stock_actuel"] = 0.0

        enriched.append(row)

    return enriched


# ==============================================================================
# FONCTION PRINCIPALE : SCAN COMPLET D'UNE IMAGE DE FACTURE
# ==============================================================================

def scan_invoice_image(image_bytes, mime_type="image/jpeg", force_engine="auto", rotation=0):
    """
    Point d'entrée principal pour l'analyse d'une image de facture :
    - Oriente correctement l'image (respect des balises EXIF smartphone et rotation manuelle utilisateur)
    - Tente d'abord l'IA Gemini Vision si une clé est présente et que l'utilisateur n'a pas forcé l'OCR
    - Bascule automatiquement vers Windows Media OCR natif (et Tesseract si présent) si aucune clé ou échec réseau
    - Enrichit tous les résultats avec l'algorithme de fuzzy matching du catalogue quincaillerie
    """
    if not image_bytes or len(image_bytes) < 100:
        raise ValueError("Données d'image invalides ou vides.")

    t0 = time.time()

    # Orientation & Rotation préalable de l'image
    if Image:
        try:
            im = Image.open(BytesIO(image_bytes))
            if ImageOps:
                try:
                    im = ImageOps.exif_transpose(im)
                except Exception:
                    pass
            if rotation % 360 != 0:
                # Dans PIL, rotate(-rotation) tourne dans le sens horaire
                im = im.rotate(-rotation, expand=True)
            buf = BytesIO()
            out_fmt = "PNG" if ("png" in str(mime_type).lower()) else "JPEG"
            if out_fmt == "JPEG" and im.mode not in ("RGB", "L"):
                im = im.convert("RGB")
            im.save(buf, format=out_fmt, quality=92)
            image_bytes = buf.getvalue()
        except Exception as rot_err:
            print(f"[WARN] Prétraitement orientation/rotation : {rot_err}")

    result = None
    engine_used = ""
    engine_label = ""
    error_notes = ""

    # Choix du moteur
    can_use_gemini = has_gemini_configured() and force_engine != "ocr"

    if force_engine == "gemini" and not has_gemini_configured():
        raise ValueError("La clé API Gemini n'est pas configurée. Veuillez renseigner votre clé dans les paramètres.")

    # 1. Tentative IA Multimodale Gemini Vision
    if can_use_gemini:
        try:
            result = call_gemini_vision(image_bytes, mime_type=mime_type)
            engine_used = "gemini"
            engine_label = f"IA Multimodale Gemini Vision ({result.get('model_used', 'flash')})"
        except Exception as e:
            error_notes = f"Repli sur OCR local suite à : {str(e)}"
            print(f"[WARN] Gemini Vision fallback : {error_notes}")
            result = None

    # 2. Repli OCR Local (Windows Media OCR natif, ou Tesseract si disponible)
    if not result:
        ocr_lines = []
        try:
            ocr_lines = run_windows_media_ocr(image_bytes)
        except Exception as e:
            error_notes += f" [OCR Windows: {e}]"

        if ocr_lines:
            result = parse_raw_ocr_lines(ocr_lines)
            engine_used = "windows_media_ocr"
            engine_label = "OCR Local Windows Media (100% Hors Ligne)"
        else:
            # Essai de Tesseract OCR si présent
            try:
                tess_lines = run_tesseract_ocr(image_bytes)
                if tess_lines:
                    result = parse_raw_ocr_lines(tess_lines)
                    engine_used = "tesseract_ocr"
                    engine_label = "OCR Local Tesseract (100% Hors Ligne)"
            except Exception as e:
                error_notes += f" [Tesseract: {e}]"

        if not result:
            msg = "Aucun texte lisible n'a pu être extrait de l'image (moteur OCR local)."
            if error_notes:
                msg += f" Note technique : {error_notes.strip()}"
            raise RuntimeError(msg)

    # 3. Enrichissement avec la correspondance catalogue DIADJI FAMILY
    extracted_items = result.get("articles", [])
    enriched_items = enrich_extracted_articles(extracted_items)

    elapsed = round(time.time() - t0, 2)

    return {
        "status": "ok",
        "provider": engine_used,
        "provider_label": engine_label,
        "execution_time_seconds": elapsed,
        "fournisseur": result.get("fournisseur") or "Fournisseur Général",
        "numero_facture": result.get("numero_facture") or f"BL-{int(time.time()) % 10000:04d}",
        "date_facture": result.get("date_facture") or time.strftime("%Y-%m-%d"),
        "total_facture": float(result.get("total_facture", 0.0)),
        "articles": enriched_items,
        "remarques": error_notes
    }
