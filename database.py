"""
Module de gestion de la base de données embarquée SQLite pour DIADJI FAMILY.
Nom de la base : magasin.db
"""

import sqlite3
import json
import os
import sys
import datetime
import unicodedata
import shutil
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

if getattr(sys, 'frozen', False):
    _APP_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    _APP_DIR = os.path.dirname(os.path.abspath(__file__))

if _APP_DIR not in sys.path:
    sys.path.insert(0, _APP_DIR)

DB_PATH = os.path.join(_APP_DIR, "magasin.db")

# Si magasin.db est absent du dossier de l'application mais embarqué dans l'exécutable
if not os.path.exists(DB_PATH) and hasattr(sys, '_MEIPASS'):
    _bundled_db = os.path.join(sys._MEIPASS, "magasin.db")
    if os.path.exists(_bundled_db):
        try:
            shutil.copy2(_bundled_db, DB_PATH)
        except Exception:
            pass

JSON_CLEAN_PATH = os.path.join(_APP_DIR, "articles_clean.json")
if not os.path.exists(JSON_CLEAN_PATH):
    # Vérification dans sys._MEIPASS (exécutable PyInstaller)
    if hasattr(sys, '_MEIPASS'):
        _meipass_json = os.path.join(sys._MEIPASS, "articles_clean.json")
        if os.path.exists(_meipass_json):
            JSON_CLEAN_PATH = _meipass_json
    # Fallback vers le dossier du module source
    if not os.path.exists(JSON_CLEAN_PATH):
        _bundled_json = os.path.join(os.path.dirname(os.path.abspath(__file__)), "articles_clean.json")
        if os.path.exists(_bundled_json):
            JSON_CLEAN_PATH = _bundled_json

EXCEL_PATH = os.path.join(_APP_DIR, "DIADJI_FAMILY_TABLEAU_DE_BORD.xlsx")
if not os.path.exists(EXCEL_PATH) and hasattr(sys, '_MEIPASS'):
    _bundled_excel = os.path.join(sys._MEIPASS, "DIADJI_FAMILY_TABLEAU_DE_BORD.xlsx")
    if os.path.exists(_bundled_excel):
        try:
            shutil.copy2(_bundled_excel, EXCEL_PATH)
        except Exception:
            pass

LEGACY_EXCEL_PATH = os.path.join(_APP_DIR, "QUINCAILLERIE_DIADJI_GNINGUE_TABLEAU_DE_BORD.xlsx")

# Extraction automatique des icônes et fichiers d'accompagnement si absents
for _asset_name in ("diadji_icon.ico", "diadji_icon.png", "articles_clean.json", "create_shortcuts.ps1", "CREER_RACCOURCI_BUREAU.bat", "LANCER_APPLICATION.bat", "DESINSTALLER_DIADJI_FAMILY.bat", "invoice_scanner.py"):
    _dest_asset = os.path.join(_APP_DIR, _asset_name)
    if not os.path.exists(_dest_asset) and hasattr(sys, '_MEIPASS'):
        _src_asset = os.path.join(sys._MEIPASS, _asset_name)
        if os.path.exists(_src_asset):
            try:
                shutil.copy2(_src_asset, _dest_asset)
            except Exception:
                pass



def strip_accents(s):
    """Supprime les accents et met en minuscule pour une recherche insensible aux accents."""
    if not s:
        return ""
    return ''.join(c for c in unicodedata.normalize('NFD', str(s)) if unicodedata.category(c) != 'Mn').lower()


def get_db_connection():
    """Crée une connexion SQLite avec support des dictionnaires et activation des clés étrangères."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn


def init_db(force_reseed=False):
    """
    Initialise la base de données SQLite : création des tables, index et amorçage avec articles_clean.json.
    """
    conn = get_db_connection()
    cur = conn.cursor()

    # Table des paramètres généraux du magasin
    cur.execute("""
    CREATE TABLE IF NOT EXISTS parametres (
        cle TEXT PRIMARY KEY,
        valeur TEXT NOT NULL
    );
    """)

    # Table du catalogue d'articles
    cur.execute("""
    CREATE TABLE IF NOT EXISTS articles (
        id TEXT PRIMARY KEY,
        code_barre TEXT,
        nom TEXT NOT NULL,
        categorie TEXT NOT NULL,
        unite TEXT NOT NULL DEFAULT 'Pièce',
        prix_vente REAL NOT NULL DEFAULT 0.0,
        source_prix TEXT DEFAULT 'À renseigner',
        stock_actuel REAL NOT NULL DEFAULT 0.0,
        stock_min REAL NOT NULL DEFAULT 0.0,
        en_commande REAL NOT NULL DEFAULT 0.0,
        fournisseur TEXT DEFAULT 'Grossiste Général Dakar',
        emplacement TEXT DEFAULT '',
        description TEXT DEFAULT '',
        date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        date_modification TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Table du journal des mouvements de stock (audit trail complet)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS mouvements_stock (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date_mouvement TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        article_id TEXT NOT NULL,
        type_mouvement TEXT NOT NULL, -- 'VENTE', 'ENTREE', 'AJUSTEMENT', 'RETOUR', 'COMMANDE_RECUE'
        quantite REAL NOT NULL,
        stock_avant REAL NOT NULL,
        stock_apres REAL NOT NULL,
        prix_unitaire REAL DEFAULT 0.0,
        montant_total REAL DEFAULT 0.0,
        reference_doc TEXT DEFAULT '',
        commentaire TEXT DEFAULT '',
        FOREIGN KEY (article_id) REFERENCES articles(id) ON DELETE CASCADE
    );
    """)

    # Table des ventes / caisse (en-têtes de tickets)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS ventes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero_ticket TEXT UNIQUE NOT NULL,
        date_vente TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        montant_total REAL NOT NULL,
        remise REAL DEFAULT 0.0,
        montant_net REAL NOT NULL,
        montant_verse REAL NOT NULL,
        monnaie_rendue REAL NOT NULL,
        mode_paiement TEXT DEFAULT 'Espèces', -- 'Espèces', 'Wave', 'Orange Money', 'Chèque', 'Virement'
        nom_client TEXT DEFAULT 'Client Comptant',
        telephone_client TEXT DEFAULT '',
        statut TEXT DEFAULT 'PAYE'
    );
    """)

    # Table des lignes de tickets de caisse
    cur.execute("""
    CREATE TABLE IF NOT EXISTS lignes_vente (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        vente_id INTEGER NOT NULL,
        article_id TEXT NOT NULL,
        nom_article TEXT NOT NULL,
        quantite REAL NOT NULL,
        prix_unitaire REAL NOT NULL,
        total_ligne REAL NOT NULL,
        FOREIGN KEY (vente_id) REFERENCES ventes(id) ON DELETE CASCADE,
        FOREIGN KEY (article_id) REFERENCES articles(id)
    );
    """)

    # Table des commandes fournisseurs
    cur.execute("""
    CREATE TABLE IF NOT EXISTS commandes_fournisseurs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero_commande TEXT UNIQUE NOT NULL,
        fournisseur TEXT NOT NULL,
        date_commande TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        date_livraison_prevue TEXT DEFAULT '',
        statut TEXT DEFAULT 'EN_COURS', -- 'EN_COURS', 'RECUE', 'ANNULEE'
        montant_total REAL DEFAULT 0.0,
        notes TEXT DEFAULT ''
    );
    """)

    # Table des lignes de commande fournisseur
    cur.execute("""
    CREATE TABLE IF NOT EXISTS lignes_commande (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        commande_id INTEGER NOT NULL,
        article_id TEXT NOT NULL,
        nom_article TEXT NOT NULL,
        quantite_commandee REAL NOT NULL,
        quantite_recue REAL DEFAULT 0.0,
        prix_achat_estime REAL DEFAULT 0.0,
        FOREIGN KEY (commande_id) REFERENCES commandes_fournisseurs(id) ON DELETE CASCADE,
        FOREIGN KEY (article_id) REFERENCES articles(id)
    );
    """)

    # Création des index pour des requêtes instantanées
    cur.execute("CREATE INDEX IF NOT EXISTS idx_articles_nom ON articles(nom);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_articles_cat ON articles(categorie);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_mouv_art ON mouvements_stock(article_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_mouv_date ON mouvements_stock(date_mouvement);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_ventes_date ON ventes(date_vente);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_lignes_vente ON lignes_vente(vente_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_cmd_statut ON commandes_fournisseurs(statut);")

    # Paramètres initiaux par défaut
    cur.execute("""
    INSERT INTO parametres (cle, valeur) VALUES
    ('magasin_nom', 'DIADJI FAMILY'),
    ('magasin_adresse', 'Dakar, Sénégal'),
    ('magasin_telephone', '+221 77 000 00 00'),
    ('devise', 'FCFA'),
    ('version', '2.0.0')
    ON CONFLICT(cle) DO UPDATE SET valeur = excluded.valeur WHERE cle IN ('magasin_nom', 'version');
    """)
    cur.execute("UPDATE parametres SET valeur = 'DIADJI FAMILY' WHERE cle = 'magasin_nom';")
    cur.execute("UPDATE parametres SET valeur = '2.0.0' WHERE cle = 'version';")

    conn.commit()

    # Vérification du contenu actuel des articles
    cur.execute("SELECT COUNT(*) AS total FROM articles")
    row_count = cur.fetchone()['total']

    # Si la base est vide ou si force_reseed est demandé, injecter les 183 articles de base
    if row_count == 0 or force_reseed:
        if force_reseed and row_count > 0:
            cur.execute("DELETE FROM lignes_vente;")
            cur.execute("DELETE FROM ventes;")
            cur.execute("DELETE FROM mouvements_stock;")
            cur.execute("DELETE FROM lignes_commande;")
            cur.execute("DELETE FROM commandes_fournisseurs;")
            cur.execute("DELETE FROM articles;")

        if os.path.exists(JSON_CLEAN_PATH):
            with open(JSON_CLEAN_PATH, 'r', encoding='utf-8') as f:
                articles_data = json.load(f)

            for item in articles_data:
                source = item.get('source', 'À renseigner')
                fournisseur = "Grossiste Matériel Électrique Dakar" if "Électricité" in item.get('cat', '') else "Fournisseur Matériaux Dakar"
                cur.execute("""
                INSERT OR REPLACE INTO articles (
                    id, nom, categorie, unite, prix_vente, source_prix,
                    stock_actuel, stock_min, en_commande, fournisseur, description
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    item['id'],
                    item['name'],
                    item['cat'],
                    item.get('unit', 'Pièce'),
                    float(item.get('price', 0)),
                    source,
                    float(item.get('stock', 0)),
                    float(item.get('min_stock', 0)),
                    float(item.get('on_order', 0)),
                    fournisseur,
                    item.get('raw', '')
                ))
            conn.commit()
            print(f"[DB] Initialisation réussie : {len(articles_data)} articles injectés dans magasin.db.")
        else:
            print("[DB] Avertissement : fichier articles_clean.json introuvable.")

    conn.close()


# ==============================================================================
# GESTION DU CATALOGUE ARTICLES (CRUD)
# ==============================================================================

def get_next_article_id(count=1):
    """
    Génère le prochain identifiant d'article unique (ex: ART-184)
    ou une liste séquentielle d'identifiants uniques si count > 1.
    """
    if count <= 0:
        return []

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM articles WHERE id LIKE 'ART-%'")
    rows = cur.fetchall()
    conn.close()

    existing_ids = {str(r['id']).strip().upper() for r in rows if r['id']}
    import re
    max_num = 0
    for r in rows:
        val = str(r['id']).strip()
        m = re.match(r'^ART-(\d+)$', val, re.IGNORECASE)
        if m:
            try:
                num = int(m.group(1))
                if num > max_num:
                    max_num = num
            except ValueError:
                pass

    generated = []
    cand = max_num + 1 if max_num > 0 else 1
    while len(generated) < count:
        cand_id = f"ART-{cand:03d}"
        if cand_id.upper() not in existing_ids:
            generated.append(cand_id)
            existing_ids.add(cand_id.upper())
        cand += 1

    return generated[0] if count == 1 else generated


def get_articles(query=None, categorie=None, statut=None, limit=None, offset=None):
    """
    Récupère la liste des articles avec calcul dynamique des statuts, filtres et pagination.
    """
    conn = get_db_connection()
    cur = conn.cursor()

    sql = """
    SELECT 
        id, code_barre, nom, categorie, unite, prix_vente, source_prix,
        stock_actuel, stock_min, en_commande, fournisseur, emplacement, description,
        date_creation, date_modification,
        (stock_actuel * prix_vente) AS valeur_stock,
        CASE 
            WHEN (stock_min - stock_actuel - en_commande) > 0 THEN (stock_min - stock_actuel - en_commande)
            ELSE 0 
        END AS besoin_reassort,
        CASE
            WHEN stock_actuel = 0 AND en_commande > 0 THEN 'En commande'
            WHEN stock_actuel = 0 THEN 'En rupture'
            WHEN stock_actuel <= stock_min THEN 'Stock faible'
            ELSE 'En stock'
        END AS statut_disponibilite
    FROM articles
    WHERE 1=1
    """
    params = []

    if categorie and categorie != "Toutes":
        sql += " AND categorie = ?"
        params.append(categorie)

    # Récupérer les articles
    cur.execute(sql + " ORDER BY id ASC", params)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()

    # Filtrage en mémoire pour la recherche insensible aux accents et le statut calculé
    result = []
    norm_query = strip_accents(query) if query else None

    for art in rows:
        # Filtre de recherche
        if norm_query:
            search_blob = strip_accents(f"{art['id']} {art.get('code_barre') or ''} {art['nom']} {art['categorie']} {art.get('emplacement') or ''} {art.get('description') or ''} {art.get('fournisseur') or ''}")
            if norm_query not in search_blob:
                continue

        # Filtre de statut calculé
        if statut and statut != "Tous":
            if statut == "rupture" and art['statut_disponibilite'] != "En rupture":
                continue
            elif statut == "faible" and art['statut_disponibilite'] != "Stock faible":
                continue
            elif statut == "commande" and art['statut_disponibilite'] != "En commande":
                continue
            elif statut == "stock" and art['statut_disponibilite'] != "En stock":
                continue
            elif statut == "avec_prix" and art['prix_vente'] <= 0:
                continue
            elif statut == "sans_prix" and art['prix_vente'] > 0:
                continue

        result.append(art)

    # Pagination optionnelle
    if offset is not None:
        result = result[offset:]
    if limit is not None:
        result = result[:limit]

    return result


def get_article_by_id(article_id):
    """Récupère un article individuel par son ID avec son historique récent."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
    SELECT 
        id, code_barre, nom, categorie, unite, prix_vente, source_prix,
        stock_actuel, stock_min, en_commande, fournisseur, emplacement, description,
        date_creation, date_modification,
        (stock_actuel * prix_vente) AS valeur_stock,
        CASE 
            WHEN (stock_min - stock_actuel - en_commande) > 0 THEN (stock_min - stock_actuel - en_commande)
            ELSE 0 
        END AS besoin_reassort,
        CASE
            WHEN stock_actuel = 0 AND en_commande > 0 THEN 'En commande'
            WHEN stock_actuel = 0 THEN 'En rupture'
            WHEN stock_actuel <= stock_min THEN 'Stock faible'
            ELSE 'En stock'
        END AS statut_disponibilite
    FROM articles
    WHERE id = ?
    """, (article_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return None

    article = dict(row)

    # Récupérer les 10 derniers mouvements de stock de cet article
    cur.execute("""
    SELECT id, date_mouvement, type_mouvement, quantite, stock_avant, stock_apres, prix_unitaire, reference_doc, commentaire
    FROM mouvements_stock
    WHERE article_id = ?
    ORDER BY date_mouvement DESC, id DESC
    LIMIT 10
    """, (article_id,))
    article['historique_mouvements'] = [dict(m) for m in cur.fetchall()]

    conn.close()
    return article


def create_article(data):
    """Crée un nouvel article dans la base de données."""
    art_id = data.get('id')
    art_id_is_auto = (not art_id or not str(art_id).strip() or str(art_id).strip().upper() in ('AUTO', 'NEW'))
    if art_id_is_auto:
        art_id = get_next_article_id()
    else:
        art_id = str(art_id).strip()

    nom = str(data.get('nom') or '').strip()
    if not nom:
        raise ValueError("Le nom de l'article est obligatoire.")

    categorie = str(data.get('categorie') or 'Général').strip() or 'Général'
    unite = str(data.get('unite') or 'Pièce').strip() or 'Pièce'
    prix_vente = float(data.get('prix_vente', 0.0) or 0.0)
    stock_actuel = float(data.get('stock_actuel', 0.0) or 0.0)
    stock_min = float(data.get('stock_min', 0.0) or 0.0)
    en_commande = float(data.get('en_commande', 0.0) or 0.0)
    source_prix = data.get('source_prix', 'Saisi manuellement' if prix_vente > 0 else 'À renseigner')
    fournisseur = data.get('fournisseur', 'Fournisseur Général Dakar')
    code_barre = data.get('code_barre', '')
    emplacement = data.get('emplacement', '')
    description = data.get('description', '')

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
        INSERT INTO articles (
            id, code_barre, nom, categorie, unite, prix_vente, source_prix,
            stock_actuel, stock_min, en_commande, fournisseur, emplacement, description
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            art_id, code_barre, nom, categorie, unite, prix_vente, source_prix,
            stock_actuel, stock_min, en_commande, fournisseur, emplacement, description
        ))
    except sqlite3.IntegrityError as err:
        if art_id_is_auto or art_id.upper().startswith("ART-"):
            art_id = get_next_article_id()
            cur.execute("""
            INSERT INTO articles (
                id, code_barre, nom, categorie, unite, prix_vente, source_prix,
                stock_actuel, stock_min, en_commande, fournisseur, emplacement, description
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                art_id, code_barre, nom, categorie, unite, prix_vente, source_prix,
                stock_actuel, stock_min, en_commande, fournisseur, emplacement, description
            ))
        else:
            conn.close()
            raise err

    # Si un stock initial positif est spécifié, consigner le mouvement initial
    if stock_actuel > 0:
        cur.execute("""
        INSERT INTO mouvements_stock (
            article_id, type_mouvement, quantite, stock_avant, stock_apres,
            prix_unitaire, montant_total, reference_doc, commentaire
        ) VALUES (?, 'ENTREE', ?, 0, ?, ?, ?, 'STOCK_INIT', 'Stock initial à la création')
        """, (art_id, stock_actuel, stock_actuel, prix_vente, stock_actuel * prix_vente))

    conn.commit()
    conn.close()

    return get_article_by_id(art_id)


def update_article(art_id, data):
    """Met à jour les informations d'un article existant."""
    existing = get_article_by_id(art_id)
    if not existing:
        raise ValueError(f"Article {art_id} introuvable.")

    nom = str(data.get('nom') if data.get('nom') is not None else existing['nom']).strip()
    if not nom:
        nom = existing['nom']
    categorie = str(data.get('categorie') if data.get('categorie') is not None else existing['categorie']).strip() or 'Général'
    unite = str(data.get('unite') if data.get('unite') is not None else existing['unite']).strip() or 'Pièce'
    prix_vente = float(data.get('prix_vente', existing['prix_vente']) or 0.0)
    stock_actuel = float(data.get('stock_actuel', existing['stock_actuel']) or 0.0)
    stock_min = float(data.get('stock_min', existing['stock_min']) or 0.0)
    en_commande = float(data.get('en_commande', existing['en_commande']) or 0.0)
    source_prix = data.get('source_prix', existing['source_prix'])
    if prix_vente > 0 and source_prix == 'À renseigner':
        source_prix = 'Prix Commerçant'
    fournisseur = data.get('fournisseur', existing['fournisseur'])
    code_barre = data.get('code_barre', existing['code_barre'])
    emplacement = data.get('emplacement', existing['emplacement'])
    description = data.get('description', existing['description'])

    conn = get_db_connection()
    cur = conn.cursor()

    # Si le stock a été modifié directement dans la fiche, enregistrer un ajustement
    ancien_stock = existing['stock_actuel']
    if abs(stock_actuel - ancien_stock) > 0.0001:
        delta = stock_actuel - ancien_stock
        type_mouv = 'AJUSTEMENT'
        cur.execute("""
        INSERT INTO mouvements_stock (
            article_id, type_mouvement, quantite, stock_avant, stock_apres,
            prix_unitaire, montant_total, reference_doc, commentaire
        ) VALUES (?, ?, ?, ?, ?, ?, ?, 'FICHE_ARTICLE', 'Ajustement manuel depuis la fiche article')
        """, (art_id, type_mouv, delta, ancien_stock, stock_actuel, prix_vente, abs(delta) * prix_vente))

    cur.execute("""
    UPDATE articles SET
        code_barre = ?, nom = ?, categorie = ?, unite = ?, prix_vente = ?,
        source_prix = ?, stock_actuel = ?, stock_min = ?, en_commande = ?,
        fournisseur = ?, emplacement = ?, description = ?,
        date_modification = CURRENT_TIMESTAMP
    WHERE id = ?
    """, (
        code_barre, nom, categorie, unite, prix_vente, source_prix,
        stock_actuel, stock_min, en_commande, fournisseur, emplacement, description, art_id
    ))

    conn.commit()
    conn.close()

    return get_article_by_id(art_id)


def delete_article(art_id):
    """Supprime un article du catalogue."""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM articles WHERE id = ?", (art_id,))
        deleted = cur.rowcount > 0
        conn.commit()
        return deleted
    except sqlite3.IntegrityError:
        raise ValueError(f"L'article {art_id} ne peut pas être supprimé car il figure déjà dans des ventes ou commandes enregistrées.")
    finally:
        conn.close()


# ==============================================================================
# GESTION DES MOUVEMENTS DE STOCK
# ==============================================================================

def record_stock_movement(article_id, type_mouvement, quantite, prix_unitaire=0.0, reference_doc='', commentaire=''):
    """
    Enregistre un mouvement de stock avec mise à jour transactionnelle du stock actuel de l'article.
    type_mouvement : 'ENTREE', 'VENTE', 'AJUSTEMENT', 'RETOUR', 'COMMANDE_RECUE'
    """
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT id, stock_actuel, prix_vente FROM articles WHERE id = ?", (article_id,))
    art = cur.fetchone()
    if not art:
        conn.close()
        raise ValueError(f"Article {article_id} inexistant.")

    stock_avant = art['stock_actuel']
    if not prix_unitaire:
        prix_unitaire = art['prix_vente']

    # Déterminer le nouveau stock selon le mouvement
    if type_mouvement in ('ENTREE', 'RETOUR', 'COMMANDE_RECUE'):
        qty_change = abs(quantite)
        stock_apres = stock_avant + qty_change
    elif type_mouvement == 'VENTE':
        qty_change = -abs(quantite)
        stock_apres = stock_avant + qty_change
    elif type_mouvement == 'AJUSTEMENT':
        # Pour un ajustement direct, la quantité transmise est le delta ou la nouvelle valeur
        qty_change = quantite
        stock_apres = stock_avant + qty_change
    else:
        qty_change = quantite
        stock_apres = stock_avant + qty_change

    montant_total = abs(qty_change) * prix_unitaire

    # Insertion mouvement
    cur.execute("""
    INSERT INTO mouvements_stock (
        article_id, type_mouvement, quantite, stock_avant, stock_apres,
        prix_unitaire, montant_total, reference_doc, commentaire
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        article_id, type_mouvement, qty_change, stock_avant, stock_apres,
        prix_unitaire, montant_total, reference_doc, commentaire
    ))

    # Mise à jour du stock dans la table articles
    cur.execute("""
    UPDATE articles SET 
        stock_actuel = ?,
        date_modification = CURRENT_TIMESTAMP
    WHERE id = ?
    """, (stock_apres, article_id))

    conn.commit()
    conn.close()

    return {
        "article_id": article_id,
        "stock_avant": stock_avant,
        "quantite": qty_change,
        "stock_apres": stock_apres,
        "type": type_mouvement
    }


def get_mouvements(limit=100, article_id=None):
    """Récupère le journal chronologique des mouvements de stock."""
    conn = get_db_connection()
    cur = conn.cursor()
    sql = """
    SELECT 
        m.id, m.date_mouvement, m.article_id, a.nom AS article_nom, a.unite,
        m.type_mouvement, m.quantite, m.stock_avant, m.stock_apres,
        m.prix_unitaire, m.montant_total, m.reference_doc, m.commentaire
    FROM mouvements_stock m
    LEFT JOIN articles a ON m.article_id = a.id
    WHERE 1=1
    """
    params = []
    if article_id:
        sql += " AND m.article_id = ?"
        params.append(article_id)

    sql += " ORDER BY m.date_mouvement DESC, m.id DESC LIMIT ?"
    params.append(limit)

    cur.execute(sql, params)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


# ==============================================================================
# GESTION DE LA CAISSE ET DES VENTES (POINT DE VENTE)
# ==============================================================================

def create_sale(items, montant_verse, remise=0.0, mode_paiement='Espèces', client_nom='Client Comptant', client_tel=''):
    """
    Enregistre une vente complète :
    - Calcul des totaux et de la monnaie
    - Génération du numéro de ticket
    - Déduction des stocks
    - Enregistrement des mouvements de stock
    - Émission des lignes de ticket
    """
    if not items or len(items) == 0:
        raise ValueError("Le panier est vide. Veuillez ajouter au moins un article.")

    conn = get_db_connection()
    cur = conn.cursor()

    today_str = datetime.datetime.now().strftime("%Y%m%d")
    # Trouver le dernier numéro de ticket du jour
    cur.execute("SELECT numero_ticket FROM ventes WHERE numero_ticket LIKE ? ORDER BY id DESC LIMIT 1", (f"TK-{today_str}-%",))
    last_ticket = cur.fetchone()
    if last_ticket and last_ticket['numero_ticket']:
        try:
            seq = int(last_ticket['numero_ticket'].split('-')[-1]) + 1
        except ValueError:
            seq = 1
    else:
        seq = 1
    ticket_num = f"TK-{today_str}-{seq:04d}"

    # Calcul des totaux
    total_brut = 0.0
    processed_items = []

    for item in items:
        art_id = item['article_id']
        cur.execute("SELECT id, nom, prix_vente, stock_actuel, unite FROM articles WHERE id = ?", (art_id,))
        art = cur.fetchone()
        if not art:
            conn.close()
            raise ValueError(f"Article {art_id} introuvable.")

        qty = float(item.get('quantite', 1))
        if qty <= 0:
            continue

        unit_price = float(item.get('prix_unitaire', art['prix_vente']))
        line_total = qty * unit_price
        total_brut += line_total

        processed_items.append({
            "article_id": art_id,
            "nom_article": art['nom'],
            "quantite": qty,
            "prix_unitaire": unit_price,
            "total_ligne": line_total,
            "stock_avant": art['stock_actuel'],
            "unite": art['unite']
        })

    if not processed_items:
        conn.close()
        raise ValueError("Aucun article valide dans la commande.")

    remise = float(remise or 0.0)
    total_net = max(0.0, total_brut - remise)
    montant_verse = float(total_net if montant_verse is None or str(montant_verse).strip() == '' else montant_verse)
    monnaie = max(0.0, montant_verse - total_net)

    # 1. Insertion dans la table ventes
    cur.execute("""
    INSERT INTO ventes (
        numero_ticket, montant_total, remise, montant_net,
        montant_verse, monnaie_rendue, mode_paiement, nom_client, telephone_client
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        ticket_num, total_brut, remise, total_net,
        montant_verse, monnaie, mode_paiement, client_nom, client_tel
    ))
    vente_id = cur.lastrowid

    # 2. Insertion des lignes de vente et mise à jour des stocks
    for p_item in processed_items:
        cur.execute("""
        INSERT INTO lignes_vente (
            vente_id, article_id, nom_article, quantite, prix_unitaire, total_ligne
        ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            vente_id, p_item['article_id'], p_item['nom_article'],
            p_item['quantite'], p_item['prix_unitaire'], p_item['total_ligne']
        ))

        # Déduire le stock
        stock_apres = p_item['stock_avant'] - p_item['quantite']
        cur.execute("""
        UPDATE articles SET
            stock_actuel = ?,
            date_modification = CURRENT_TIMESTAMP
        WHERE id = ?
        """, (stock_apres, p_item['article_id']))

        # Consigner le mouvement dans mouvements_stock
        cur.execute("""
        INSERT INTO mouvements_stock (
            article_id, type_mouvement, quantite, stock_avant, stock_apres,
            prix_unitaire, montant_total, reference_doc, commentaire
        ) VALUES (?, 'VENTE', ?, ?, ?, ?, ?, ?, ?)
        """, (
            p_item['article_id'], -p_item['quantite'], p_item['stock_avant'],
            stock_apres, p_item['prix_unitaire'], p_item['total_ligne'],
            ticket_num, f"Vente au comptant - {client_nom}"
        ))

    conn.commit()
    conn.close()

    return get_sale_by_ticket(ticket_num)


def get_sale_by_ticket(ticket_num):
    """Récupère une vente complète avec ses lignes pour impression ou consultation."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
    SELECT id, numero_ticket, date_vente, montant_total, remise, montant_net,
           montant_verse, monnaie_rendue, mode_paiement, nom_client, telephone_client, statut
    FROM ventes
    WHERE numero_ticket = ?
    """, (ticket_num,))
    v_row = cur.fetchone()
    if not v_row:
        conn.close()
        return None

    sale = dict(v_row)
    cur.execute("""
    SELECT lv.id, lv.article_id, lv.nom_article, lv.quantite, lv.prix_unitaire, lv.total_ligne, a.unite
    FROM lignes_vente lv
    LEFT JOIN articles a ON lv.article_id = a.id
    WHERE lv.vente_id = ?
    ORDER BY lv.id ASC
    """, (sale['id'],))
    sale['lignes'] = [dict(l) for l in cur.fetchall()]

    conn.close()
    return sale


def get_ventes(limit=50):
    """Récupère les dernières ventes effectuées avec le nombre d'articles vendus."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
    SELECT 
        v.id, v.numero_ticket, v.date_vente, v.montant_total, v.remise, v.montant_net,
        v.montant_verse, v.monnaie_rendue, v.mode_paiement, v.nom_client, v.telephone_client, v.statut,
        COUNT(lv.id) AS total_lignes,
        SUM(lv.quantite) AS total_quantite
    FROM ventes v
    LEFT JOIN lignes_vente lv ON v.id = lv.vente_id
    GROUP BY v.id
    ORDER BY v.date_vente DESC, v.id DESC
    LIMIT ?
    """, (limit,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


# ==============================================================================
# GESTION DES COMMANDES FOURNISSEURS & RÉAPPROVISIONNEMENT
# ==============================================================================

def get_alertes_reassort():
    """
    Calcule la liste des articles nécessitant un réapprovisionnement urgent ou critique :
    - Rupture (stock == 0)
    - Stock faible (stock <= min_stock)
    - Quantité manquante et budget estimé
    """
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
    SELECT 
        id, nom, categorie, unite, prix_vente, stock_actuel, stock_min, en_commande, fournisseur,
        CASE
            WHEN stock_actuel = 0 AND en_commande > 0 THEN 'En commande'
            WHEN stock_actuel = 0 THEN 'En rupture'
            WHEN stock_actuel <= stock_min THEN 'Stock faible'
            ELSE 'En stock'
        END AS statut,
        CASE 
            WHEN (stock_min - stock_actuel - en_commande) > 0 THEN (stock_min - stock_actuel - en_commande)
            ELSE 0 
        END AS besoin_quantite,
        CASE 
            WHEN (stock_min - stock_actuel - en_commande) > 0 THEN (stock_min - stock_actuel - en_commande) * prix_vente
            ELSE 0 
        END AS besoin_budget_estime
    FROM articles
    WHERE (stock_actuel <= stock_min OR stock_actuel = 0)
    ORDER BY 
        (stock_actuel = 0) DESC,
        (stock_actuel / CASE WHEN stock_min=0 THEN 1 ELSE stock_min END) ASC,
        id ASC
    """)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def create_supplier_order(fournisseur, items, date_prevue='', notes=''):
    """
    Crée une commande fournisseur et incrémente 'en_commande' sur les articles concernés.
    """
    if not items:
        raise ValueError("La commande fournisseur doit contenir au moins un article.")

    conn = get_db_connection()
    cur = conn.cursor()

    today_str = datetime.datetime.now().strftime("%Y%m%d")
    cur.execute("SELECT numero_commande FROM commandes_fournisseurs WHERE numero_commande LIKE ? ORDER BY id DESC LIMIT 1", (f"CMD-{today_str}-%",))
    last_cmd = cur.fetchone()
    if last_cmd and last_cmd['numero_commande']:
        try:
            seq = int(last_cmd['numero_commande'].split('-')[-1]) + 1
        except ValueError:
            seq = 1
    else:
        seq = 1
    cmd_num = f"CMD-{today_str}-{seq:03d}"

    montant_total = 0.0
    for item in items:
        qty = float(item.get('quantite', 0))
        price = float(item.get('prix_achat_estime', 0))
        montant_total += qty * price

    cur.execute("""
    INSERT INTO commandes_fournisseurs (
        numero_commande, fournisseur, date_livraison_prevue, montant_total, notes
    ) VALUES (?, ?, ?, ?, ?)
    """, (cmd_num, fournisseur, date_prevue, montant_total, notes))
    cmd_id = cur.lastrowid

    for item in items:
        art_id = item['article_id']
        cur.execute("SELECT id, nom, en_commande FROM articles WHERE id = ?", (art_id,))
        art = cur.fetchone()
        if not art:
            continue

        qty = float(item.get('quantite', 0))
        price = float(item.get('prix_achat_estime', 0))

        cur.execute("""
        INSERT INTO lignes_commande (
            commande_id, article_id, nom_article, quantite_commandee, prix_achat_estime
        ) VALUES (?, ?, ?, ?, ?)
        """, (cmd_id, art_id, art['nom'], qty, price))

        # Incrémenter en_commande
        cur.execute("""
        UPDATE articles SET
            en_commande = en_commande + ?,
            date_modification = CURRENT_TIMESTAMP
        WHERE id = ?
        """, (qty, art_id))

    conn.commit()
    conn.close()

    return get_supplier_order(cmd_id)


def receive_supplier_order(cmd_id):
    """
    Valide la réception d'une commande fournisseur :
    - Incrémente le stock actuel des articles
    - Décrémente en_commande
    - Enregistre les mouvements de stock 'COMMANDE_RECUE'
    - Marque la commande comme 'RECUE'
    """
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM commandes_fournisseurs WHERE id = ?", (cmd_id,))
    cmd = cur.fetchone()
    if not cmd:
        conn.close()
        raise ValueError(f"Commande {cmd_id} introuvable.")

    if cmd['statut'] == 'RECUE':
        conn.close()
        raise ValueError("Cette commande a déjà été réceptionnée.")

    cur.execute("SELECT * FROM lignes_commande WHERE commande_id = ?", (cmd_id,))
    lignes = cur.fetchall()

    for ligne in lignes:
        art_id = ligne['article_id']
        qty = ligne['quantite_commandee']

        cur.execute("SELECT stock_actuel, en_commande, prix_vente FROM articles WHERE id = ?", (art_id,))
        art = cur.fetchone()
        if not art:
            continue

        stock_avant = art['stock_actuel']
        stock_apres = stock_avant + qty
        nouveau_en_commande = max(0.0, art['en_commande'] - qty)

        cur.execute("""
        UPDATE articles SET
            stock_actuel = ?,
            en_commande = ?,
            date_modification = CURRENT_TIMESTAMP
        WHERE id = ?
        """, (stock_apres, nouveau_en_commande, art_id))

        cur.execute("""
        UPDATE lignes_commande SET
            quantite_recue = quantite_commandee
        WHERE id = ?
        """, (ligne['id'],))

        cur.execute("""
        INSERT INTO mouvements_stock (
            article_id, type_mouvement, quantite, stock_avant, stock_apres,
            prix_unitaire, montant_total, reference_doc, commentaire
        ) VALUES (?, 'COMMANDE_RECUE', ?, ?, ?, ?, ?, ?, ?)
        """, (
            art_id, qty, stock_avant, stock_apres,
            ligne['prix_achat_estime'] or art['prix_vente'],
            qty * (ligne['prix_achat_estime'] or art['prix_vente']),
            cmd['numero_commande'], f"Réception commande fournisseur {cmd['fournisseur']}"
        ))

    cur.execute("UPDATE commandes_fournisseurs SET statut = 'RECUE' WHERE id = ?", (cmd_id,))

    conn.commit()
    conn.close()

    return get_supplier_order(cmd_id)


def get_supplier_order(cmd_id):
    """Récupère le détail d'une commande fournisseur."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM commandes_fournisseurs WHERE id = ?", (cmd_id,))
    cmd = cur.fetchone()
    if not cmd:
        conn.close()
        return None

    res = dict(cmd)
    cur.execute("SELECT * FROM lignes_commande WHERE commande_id = ?", (cmd_id,))
    res['lignes'] = [dict(l) for l in cur.fetchall()]
    conn.close()
    return res


def get_commandes(statut=None):
    """Récupère la liste des commandes fournisseurs."""
    conn = get_db_connection()
    cur = conn.cursor()
    sql = """
    SELECT 
        c.id, c.numero_commande, c.fournisseur, c.date_commande, c.date_livraison_prevue,
        c.statut, c.montant_total, c.notes,
        COUNT(lc.id) AS nb_articles,
        SUM(lc.quantite_commandee) AS quantite_totale
    FROM commandes_fournisseurs c
    LEFT JOIN lignes_commande lc ON c.id = lc.commande_id
    WHERE 1=1
    """
    params = []
    if statut:
        sql += " AND c.statut = ?"
        params.append(statut)

    sql += " GROUP BY c.id ORDER BY c.date_commande DESC, c.id DESC"

    cur.execute(sql, params)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


# ==============================================================================
# STATISTIQUES GLOBALES & TABLEAU DE BORD
# ==============================================================================

def get_dashboard_stats():
    """Calcule tous les indicateurs clés pour le tableau de bord en temps réel."""
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) AS total FROM articles")
    total_articles = cur.fetchone()['total']

    cur.execute("SELECT COUNT(*) AS en_rupture FROM articles WHERE stock_actuel = 0 AND en_commande = 0")
    en_rupture = cur.fetchone()['en_rupture']

    cur.execute("SELECT COUNT(*) AS en_commande FROM articles WHERE stock_actuel = 0 AND en_commande > 0")
    en_commande_rupture = cur.fetchone()['en_commande']

    cur.execute("SELECT COUNT(*) AS stock_faible FROM articles WHERE stock_actuel > 0 AND stock_actuel <= stock_min")
    stock_faible = cur.fetchone()['stock_faible']

    cur.execute("SELECT COUNT(*) AS en_stock FROM articles WHERE stock_actuel > stock_min")
    en_stock_normal = cur.fetchone()['en_stock']

    cur.execute("SELECT SUM(stock_actuel * prix_vente) AS valeur_totale FROM articles")
    valeur_stock = cur.fetchone()['valeur_totale'] or 0.0

    cur.execute("SELECT COUNT(*) AS avec_prix FROM articles WHERE prix_vente > 0")
    articles_avec_prix = cur.fetchone()['avec_prix']

    # Ventes du jour
    today_str = datetime.datetime.now().strftime("%Y-%m-%d")
    cur.execute("SELECT COUNT(*) AS nb_ventes, SUM(montant_net) AS total_ventes FROM ventes WHERE date_vente LIKE ?", (f"{today_str}%",))
    v_today = cur.fetchone()
    ventes_jour_count = v_today['nb_ventes'] or 0
    ventes_jour_total = v_today['total_ventes'] or 0.0

    # Commandes fournisseurs en cours
    cur.execute("SELECT COUNT(*) AS total_cmd FROM commandes_fournisseurs WHERE statut = 'EN_COURS'")
    commandes_en_cours = cur.fetchone()['total_cmd'] or 0

    # Répartition par catégorie
    cur.execute("""
    SELECT 
        categorie,
        COUNT(*) AS total,
        SUM(stock_actuel) AS stock_total,
        SUM(stock_actuel * prix_vente) AS valeur_totale
    FROM articles
    GROUP BY categorie
    ORDER BY total DESC
    """)
    categories_stats = [dict(r) for r in cur.fetchall()]

    conn.close()

    return {
        "total_articles": total_articles,
        "en_rupture": en_rupture,
        "en_commande_rupture": en_commande_rupture,
        "stock_faible": stock_faible,
        "en_stock_normal": en_stock_normal,
        "valeur_stock_fcfa": valeur_stock,
        "articles_avec_prix": articles_avec_prix,
        "articles_sans_prix": total_articles - articles_avec_prix,
        "ventes_jour_count": ventes_jour_count,
        "ventes_jour_total_fcfa": ventes_jour_total,
        "commandes_en_cours": commandes_en_cours,
        "categories": categories_stats
    }


# ==============================================================================
# EXPORT ET SYNCHRONISATION EXCEL
# ==============================================================================

def export_to_excel(output_path=None):
    """
    Exporte le contenu actuel de la base de données vers un classeur Excel complet et professionnel.
    Si le classeur maître existe, met à jour les données tout en préservant le tableau de bord et les formules.
    """
    if not output_path:
        output_path = EXCEL_PATH

    articles = get_articles()
    articles_map = {a['id']: a for a in articles}

    # Styles
    font_title = Font(name="Segoe UI", size=16, bold=True, color="0F172A")
    font_subtitle = Font(name="Segoe UI", size=9.5, color="64748B")
    font_hdr = Font(name="Segoe UI", size=9.5, bold=True, color="FFFFFF")
    font_body = Font(name="Segoe UI", size=9.5, color="1E293B")
    font_bold = Font(name="Segoe UI", size=9.5, bold=True, color="1E293B")

    fill_hdr = PatternFill(start_color="0F172A", end_color="0F172A", fill_type="solid")
    fill_zebra = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
    thin_border = Border(
        left=Side(style='thin', color="E2E8F0"),
        right=Side(style='thin', color="E2E8F0"),
        top=Side(style='thin', color="E2E8F0"),
        bottom=Side(style='thin', color="E2E8F0")
    )

    master_path = EXCEL_PATH if os.path.exists(EXCEL_PATH) else (LEGACY_EXCEL_PATH if os.path.exists(LEGACY_EXCEL_PATH) else None)
    if master_path:
        try:
            wb = openpyxl.load_workbook(master_path, data_only=False)
            if "STOCK_CATALOGUE" in wb.sheetnames:
                ws = wb["STOCK_CATALOGUE"]
                ws['A2'] = "CATALOGUE OFFICIEL & ÉTAT DES STOCKS - DIADJI FAMILY"
                existing_codes = set()
                total_row_idx = None
                for r in range(5, ws.max_row + 1):
                    c_val = str(ws.cell(r, 1).value or '').strip()
                    if c_val.upper() == 'TOTAL' or str(ws.cell(r, 3).value or '').strip().upper() == 'TOTAL':
                        total_row_idx = r
                        break
                    if c_val in articles_map:
                        existing_codes.add(c_val)
                        art = articles_map[c_val]
                        ws.cell(r, 5).value = art['prix_vente']
                        ws.cell(r, 6).value = art['stock_actuel']
                        ws.cell(r, 7).value = art['stock_min']
                        ws.cell(r, 8).value = art['en_commande']
                        if art.get('fournisseur'):
                            ws.cell(r, 13).value = art['fournisseur']

                # Insérer les articles inédits dans STOCK_CATALOGUE
                new_codes = [a['id'] for a in articles if a['id'] not in existing_codes]
                if new_codes and total_row_idx:
                    for ncode in new_codes:
                        nart = articles_map[ncode]
                        ws.insert_rows(total_row_idx)
                        r = total_row_idx
                        ws.cell(r, 1, nart['id']).font = font_bold
                        ws.cell(r, 2, nart.get('categorie', 'Quincaillerie')).font = font_body
                        ws.cell(r, 3, nart.get('nom', '')).font = font_body
                        ws.cell(r, 4, nart.get('unite', 'Pièce')).font = font_body
                        ws.cell(r, 5, nart.get('prix_vente', 0)).font = font_bold
                        ws.cell(r, 6, nart.get('stock_actuel', 0)).font = font_bold
                        ws.cell(r, 7, nart.get('stock_min', 5)).font = font_body
                        ws.cell(r, 8, nart.get('en_commande', 0)).font = font_body
                        ws.cell(r, 9, f'=IF(F{r}=0, IF(H{r}>0, "En commande", "En rupture"), IF(F{r}<=G{r}, "Stock faible", "En stock"))')
                        ws.cell(r, 10, f'=F{r}*E{r}')
                        ws.cell(r, 11, f'=MAX(0, G{r}-F{r}-H{r})')
                        ws.cell(r, 12, nart.get('source_prix', 'Ajouté')).font = font_body
                        ws.cell(r, 13, nart.get('fournisseur', '')).font = font_body
                        norm_kw = f"{nart['id']} {nart.get('nom', '')} {nart.get('categorie', '')} {nart.get('unite', '')}".lower()
                        ws.cell(r, 14, norm_kw)
                        ws.cell(r, 15, f'=IF(I{r}="En stock", "", 999)')
                        total_row_idx += 1

                    if "CatalogueStock" in ws.tables:
                        ws.tables["CatalogueStock"].ref = f"A4:O{total_row_idx}"

            if "TABLEAU DE BORD" in wb.sheetnames:
                ws_dash = wb["TABLEAU DE BORD"]
                ws_dash['B2'] = "DIADJI FAMILY"

            if "HISTORIQUE_VENTES" in wb.sheetnames:
                del wb["HISTORIQUE_VENTES"]
            ws_v = wb.create_sheet(title="HISTORIQUE_VENTES")
            ws_v.views.sheetView[0].showGridLines = True
            ws_v['A2'] = "HISTORIQUE RÉCENT DES ENCAISSEMENTS ET VENTES - DIADJI FAMILY"
            ws_v['A2'].font = font_title

            v_headers = ["Numéro Ticket", "Date / Heure", "Client", "Mode Paiement", "Total Brut", "Remise", "Net Payé", "Monnaie Rendue", "Statut"]
            for c_idx, h in enumerate(v_headers, 1):
                c = ws_v.cell(row=4, column=c_idx, value=h)
                c.font = font_hdr
                c.fill = fill_hdr
                c.alignment = Alignment(horizontal="center", vertical="center")

            ventes = get_ventes(limit=500)
            v_row = 5
            for v in ventes:
                ws_v.cell(row=v_row, column=1, value=v['numero_ticket']).font = font_bold
                ws_v.cell(row=v_row, column=2, value=v['date_vente']).font = font_body
                ws_v.cell(row=v_row, column=3, value=v['nom_client']).font = font_body
                ws_v.cell(row=v_row, column=4, value=v['mode_paiement']).font = font_body
                
                c1 = ws_v.cell(row=v_row, column=5, value=v['montant_total'])
                c1.number_format = '#,##0 "FCFA"'
                c2 = ws_v.cell(row=v_row, column=6, value=v['remise'])
                c2.number_format = '#,##0 "FCFA"'
                c3 = ws_v.cell(row=v_row, column=7, value=v['montant_net'])
                c3.number_format = '#,##0 "FCFA"'
                c3.font = font_bold
                c4 = ws_v.cell(row=v_row, column=8, value=v['monnaie_rendue'])
                c4.number_format = '#,##0 "FCFA"'
                ws_v.cell(row=v_row, column=9, value=v['statut']).font = font_body

                for c_idx in range(1, 10):
                    ws_v.cell(row=v_row, column=c_idx).border = thin_border
                v_row += 1

            for c_idx, w in enumerate([18, 22, 25, 18, 16, 14, 16, 16, 12], 1):
                ws_v.column_dimensions[get_column_letter(c_idx)].width = w

            wb.save(output_path)
            return output_path
        except Exception:
            pass

    # Fallback si le classeur maître n'existe pas : création nouveau classeur
    wb = openpyxl.Workbook()
    wb.remove(wb.active)

    ws = wb.create_sheet(title="STOCK_CATALOGUE")
    ws.views.sheetView[0].showGridLines = True
    ws['A2'] = "CATALOGUE OFFICIEL & ÉTAT DES STOCKS - DIADJI FAMILY"
    ws['A2'].font = font_title
    ws['A3'] = f"Généré automatiquement depuis le logiciel le {datetime.datetime.now().strftime('%d/%m/%Y à %H:%M')}"
    ws['A3'].font = font_subtitle

    headers = [
        "Code Article", "Rayon / Catégorie", "Désignation de l'Article", "Unité",
        "Prix Unitaire (FCFA)", "Stock Actuel", "Stock Min (Alerte)", "En Commande",
        "Statut Disponibilité", "Valeur Stock (FCFA)", "Besoin Net Réassort",
        "Source Prix", "Fournisseur Recommandé", "Recherche Normalisée"
    ]

    for col_idx, h in enumerate(headers, 1):
        cell = ws.cell(row=4, column=col_idx, value=h)
        cell.font = font_hdr
        cell.fill = fill_hdr
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    ws.row_dimensions[4].height = 28

    current_row = 5
    for art in articles:
        norm_search = strip_accents(f"{art['id']} {art['nom']} {art['categorie']} {art['unite']}")
        ws.cell(row=current_row, column=1, value=art['id']).font = font_bold
        ws.cell(row=current_row, column=2, value=art['categorie']).font = font_body
        ws.cell(row=current_row, column=3, value=art['nom']).font = font_body
        ws.cell(row=current_row, column=4, value=art['unite']).font = font_body
        
        c_price = ws.cell(row=current_row, column=5, value=art['prix_vente'])
        c_price.font = font_body
        c_price.number_format = '#,##0 "FCFA"'

        c_stock = ws.cell(row=current_row, column=6, value=art['stock_actuel'])
        c_stock.font = font_bold
        c_stock.number_format = '#,##0'

        c_min = ws.cell(row=current_row, column=7, value=art['stock_min'])
        c_min.font = font_body
        c_min.number_format = '#,##0'

        c_cmd = ws.cell(row=current_row, column=8, value=art['en_commande'])
        c_cmd.font = font_body
        c_cmd.number_format = '#,##0'

        ws.cell(row=current_row, column=9, value=f'=IF(F{current_row}=0, IF(H{current_row}>0, "En commande", "En rupture"), IF(F{current_row}<=G{current_row}, "Stock faible", "En stock"))').font = font_bold
        c_val = ws.cell(row=current_row, column=10, value=f'=F{current_row}*E{current_row}')
        c_val.font = font_bold
        c_val.number_format = '#,##0 "FCFA"'

        c_reap = ws.cell(row=current_row, column=11, value=f'=MAX(0, G{current_row}-F{current_row}-H{current_row})')
        c_reap.font = font_bold
        c_reap.number_format = '#,##0'

        ws.cell(row=current_row, column=12, value=art['source_prix']).font = font_body
        ws.cell(row=current_row, column=13, value=art['fournisseur']).font = font_body
        ws.cell(row=current_row, column=14, value=norm_search).font = font_subtitle

        for col_idx in range(1, 15):
            c = ws.cell(row=current_row, column=col_idx)
            c.border = thin_border
            if current_row % 2 == 0:
                c.fill = fill_zebra

        current_row += 1

    ws.cell(row=current_row, column=3, value="TOTAUX GÉNÉRAUX").font = font_title
    c_tot_stock = ws.cell(row=current_row, column=6, value=f'=SUM(F5:F{current_row-1})')
    c_tot_stock.font = font_title
    c_tot_stock.number_format = '#,##0'

    c_tot_val = ws.cell(row=current_row, column=10, value=f'=SUM(J5:J{current_row-1})')
    c_tot_val.font = font_title
    c_tot_val.number_format = '#,##0 "FCFA"'

    col_widths = {1: 12, 2: 28, 3: 40, 4: 12, 5: 18, 6: 14, 7: 16, 8: 14, 9: 20, 10: 20, 11: 20, 12: 18, 13: 30, 14: 30}
    for col_idx, width in col_widths.items():
        ws.column_dimensions[get_column_letter(col_idx)].width = width

    ws_v = wb.create_sheet(title="HISTORIQUE_VENTES")
    ws_v.views.sheetView[0].showGridLines = True
    ws_v['A2'] = "HISTORIQUE RÉCENT DES ENCAISSEMENTS ET VENTES"
    ws_v['A2'].font = font_title

    v_headers = ["Numéro Ticket", "Date / Heure", "Client", "Mode Paiement", "Total Brut", "Remise", "Net Payé", "Monnaie Rendue", "Statut"]
    for c_idx, h in enumerate(v_headers, 1):
        c = ws_v.cell(row=4, column=c_idx, value=h)
        c.font = font_hdr
        c.fill = fill_hdr
        c.alignment = Alignment(horizontal="center", vertical="center")

    ventes = get_ventes(limit=500)
    v_row = 5
    for v in ventes:
        ws_v.cell(row=v_row, column=1, value=v['numero_ticket']).font = font_bold
        ws_v.cell(row=v_row, column=2, value=v['date_vente']).font = font_body
        ws_v.cell(row=v_row, column=3, value=v['nom_client']).font = font_body
        ws_v.cell(row=v_row, column=4, value=v['mode_paiement']).font = font_body
        
        c1 = ws_v.cell(row=v_row, column=5, value=v['montant_total'])
        c1.number_format = '#,##0 "FCFA"'
        c2 = ws_v.cell(row=v_row, column=6, value=v['remise'])
        c2.number_format = '#,##0 "FCFA"'
        c3 = ws_v.cell(row=v_row, column=7, value=v['montant_net'])
        c3.number_format = '#,##0 "FCFA"'
        c3.font = font_bold
        c4 = ws_v.cell(row=v_row, column=8, value=v['monnaie_rendue'])
        c4.number_format = '#,##0 "FCFA"'
        ws_v.cell(row=v_row, column=9, value=v['statut']).font = font_body

        for c_idx in range(1, 10):
            ws_v.cell(row=v_row, column=c_idx).border = thin_border
        v_row += 1

    for c_idx, w in enumerate([18, 22, 25, 18, 16, 14, 16, 16, 12], 1):
        ws_v.column_dimensions[get_column_letter(c_idx)].width = w

    wb.save(output_path)
    return output_path


def import_from_excel(excel_path):
    """
    Importe ou synchronise des articles depuis un classeur Excel dans la base SQLite.
    Met à jour les prix, stocks, stocks minimums et ajoute les nouveaux articles.
    """
    if not os.path.exists(excel_path):
        raise FileNotFoundError(f"Fichier Excel introuvable : {excel_path}")

    wb = openpyxl.load_workbook(excel_path, data_only=True)
    
    # Chercher la feuille STOCK_CATALOGUE ou la première feuille
    sheet_name = 'STOCK_CATALOGUE' if 'STOCK_CATALOGUE' in wb.sheetnames else wb.sheetnames[0]
    ws = wb[sheet_name]

    # Trouver la ligne d'en-tête (cherche 'Code Article' ou 'Code')
    header_row = None
    for r in range(1, 10):
        val = ws.cell(r, 1).value
        if val and "Code" in str(val):
            header_row = r
            break

    if not header_row:
        header_row = 4  # Valeur standard

    headers = [str(ws.cell(header_row, col).value or '').strip() for col in range(1, ws.max_column + 1)]

    # Mapping des colonnes
    col_map = {}
    for idx, h in enumerate(headers, 1):
        h_lower = h.lower()
        if "source" in h_lower:
            col_map['source_prix'] = idx
        elif "valeur" in h_lower:
            col_map['valeur_stock'] = idx
        elif "code" in h_lower:
            col_map['id'] = idx
        elif "rayon" in h_lower or "catégorie" in h_lower or "categorie" in h_lower:
            col_map['categorie'] = idx
        elif "désignation" in h_lower or "designation" in h_lower or "nom" in h_lower or "article" in h_lower:
            col_map['nom'] = idx
        elif "unité" in h_lower or "unite" in h_lower:
            col_map['unite'] = idx
        elif "prix" in h_lower and "source" not in h_lower:
            col_map['prix_vente'] = idx
        elif "stock actuel" in h_lower or (h_lower == "stock") or ("stock" in h_lower and "min" not in h_lower and "valeur" not in h_lower):
            col_map['stock_actuel'] = idx
        elif "min" in h_lower:
            col_map['stock_min'] = idx
        elif "commande" in h_lower:
            col_map['en_commande'] = idx
        elif "fournisseur" in h_lower:
            col_map['fournisseur'] = idx

    stats = {"ajoutes": 0, "mis_a_jour": 0, "ignores": 0}

    conn = get_db_connection()
    cur = conn.cursor()

    for r in range(header_row + 1, ws.max_row + 1):
        art_id = str(ws.cell(r, col_map.get('id', 1)).value or '').strip()
        if not art_id or art_id.startswith("TOTAL") or art_id == "None":
            continue

        nom = str(ws.cell(r, col_map.get('nom', 3)).value or '').strip()
        if not nom:
            stats["ignores"] += 1
            continue

        cat = str(ws.cell(r, col_map.get('categorie', 2)).value or 'Général').strip()
        unite = str(ws.cell(r, col_map.get('unite', 4)).value or 'Pièce').strip()
        
        try:
            prix = float(ws.cell(r, col_map.get('prix_vente', 5)).value or 0.0)
        except (ValueError, TypeError):
            prix = 0.0

        try:
            stock = float(ws.cell(r, col_map.get('stock_actuel', 6)).value or 0.0)
        except (ValueError, TypeError):
            stock = 0.0

        try:
            s_min = float(ws.cell(r, col_map.get('stock_min', 7)).value or 0.0)
        except (ValueError, TypeError):
            s_min = 0.0

        try:
            en_cmd = float(ws.cell(r, col_map.get('en_commande', 8)).value or 0.0)
        except (ValueError, TypeError):
            en_cmd = 0.0

        fournisseur = str(ws.cell(r, col_map.get('fournisseur', 13)).value or 'Fournisseur Général Dakar').strip()

        # Vérifier si l'article existe déjà
        cur.execute("SELECT id, stock_actuel, prix_vente FROM articles WHERE id = ?", (art_id,))
        existing = cur.fetchone()

        if existing:
            # Enregistrer mouvement si le stock change
            ancien_stock = existing['stock_actuel']
            if abs(stock - ancien_stock) > 0.001:
                delta = stock - ancien_stock
                cur.execute("""
                INSERT INTO mouvements_stock (
                    article_id, type_mouvement, quantite, stock_avant, stock_apres,
                    prix_unitaire, montant_total, reference_doc, commentaire
                ) VALUES (?, 'AJUSTEMENT', ?, ?, ?, ?, ?, 'IMPORT_EXCEL', 'Synchronisation depuis fichier Excel')
                """, (art_id, delta, ancien_stock, stock, prix, abs(delta) * prix))

            cur.execute("""
            UPDATE articles SET
                nom = ?, categorie = ?, unite = ?, prix_vente = ?,
                stock_actuel = ?, stock_min = ?, en_commande = ?, fournisseur = ?,
                date_modification = CURRENT_TIMESTAMP
            WHERE id = ?
            """, (nom, cat, unite, prix, stock, s_min, en_cmd, fournisseur, art_id))
            stats["mis_a_jour"] += 1
        else:
            cur.execute("""
            INSERT INTO articles (
                id, nom, categorie, unite, prix_vente, stock_actuel, stock_min, en_commande, fournisseur, source_prix
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'Import Excel')
            """, (art_id, nom, cat, unite, prix, stock, s_min, en_cmd, fournisseur))
            if stock > 0:
                cur.execute("""
                INSERT INTO mouvements_stock (
                    article_id, type_mouvement, quantite, stock_avant, stock_apres,
                    prix_unitaire, montant_total, reference_doc, commentaire
                ) VALUES (?, 'ENTREE', ?, 0, ?, ?, ?, 'IMPORT_EXCEL', 'Création via import Excel')
                """, (art_id, stock, stock, prix, stock * prix))
            stats["ajoutes"] += 1

    conn.commit()
    conn.close()

    return stats


# ==============================================================================
# GESTION DES PARAMÈTRES ET CONFIGURATION (CLÉ API GEMINI, ETC.)
# ==============================================================================

def get_setting(cle, default=None):
    """Récupère la valeur d'un paramètre stocké dans la table parametres."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT valeur FROM parametres WHERE cle = ?", (cle,))
    row = cur.fetchone()
    conn.close()
    if row:
        return row['valeur']
    return default


def set_setting(cle, valeur):
    """Enregistre ou met à jour un paramètre dans la base embarquée."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
    INSERT INTO parametres (cle, valeur) VALUES (?, ?)
    ON CONFLICT(cle) DO UPDATE SET valeur = excluded.valeur
    """, (cle, str(valeur)))
    conn.commit()
    conn.close()
    return True


# ==============================================================================
# RÉCEPTION GROUPÉE DE FACTURES / BONS DE LIVRAISON IMAGE
# ==============================================================================

def receive_invoice_batch(fournisseur, numero_facture, date_facture=None, items=None, notes=""):
    """
    Enregistre la réception d'un bon de livraison ou d'une facture numérisée :
    - Crée les articles inédits si le commerçant les a ajoutés
    - Met à jour immédiatement le stock_actuel de chaque référence dans magasin.db
    - Enregistre chaque mouvement d'entrée dans mouvements_stock ('COMMANDE_RECUE')
    - Conserve l'historique de livraison dans commandes_fournisseurs (statut 'RECUE')
    - Synchronise automatiquement le classeur officiel DIADJI_FAMILY_TABLEAU_DE_BORD.xlsx
    """
    import re
    import time
    import datetime

    if not items or len(items) == 0:
        raise ValueError("Aucun article à réceptionner.")

    if not date_facture:
        date_facture = datetime.datetime.now().strftime("%Y-%m-%d")

    if not fournisseur or not str(fournisseur).strip():
        fournisseur = "Fournisseur Général"

    today_str = datetime.datetime.now().strftime("%Y%m%d")
    clean_num = re.sub(r'[^a-zA-Z0-9_\-]', '', str(numero_facture or '')).strip()
    if clean_num:
        cmd_num = f"BL-{clean_num}" if not clean_num.upper().startswith("BL-") else clean_num
    else:
        cmd_num = f"BL-{today_str}-{int(time.time()) % 10000:04d}"

    conn = get_db_connection()
    cur = conn.cursor()

    # Si le numéro de BL existe déjà dans la base, ajouter un suffixe unique
    cur.execute("SELECT id FROM commandes_fournisseurs WHERE numero_commande = ?", (cmd_num,))
    if cur.fetchone():
        cmd_num = f"{cmd_num}-{int(time.time()) % 1000:03d}"

    # Validation et filtrage des articles
    valid_items = []
    montant_total = 0.0
    for it in items:
        try:
            qty = float(it.get('quantite', 0))
        except (ValueError, TypeError):
            qty = 0.0
        if qty <= 0:
            continue
        try:
            price = float(it.get('prix_unitaire', 0))
        except (ValueError, TypeError):
            price = 0.0
        montant_total += (qty * price)
        valid_items.append(it)

    if not valid_items:
        conn.close()
        raise ValueError("Tous les articles ont une quantité nulle ou invalide.")

    # 1. Enregistrement de l'en-tête dans commandes_fournisseurs
    cur.execute("""
    INSERT INTO commandes_fournisseurs (
        numero_commande, fournisseur, date_commande, date_livraison_prevue, statut, montant_total, notes
    ) VALUES (?, ?, ?, ?, 'RECUE', ?, ?)
    """, (cmd_num, fournisseur, date_facture, date_facture, montant_total, notes or "Réception Facture Image (IA & OCR)"))
    cmd_id = cur.lastrowid

    nouveaux_articles = []
    articles_traites = []

    for it in valid_items:
        art_id = str(it.get('article_id', '')).strip()
        designation = str(it.get('designation', '')).strip() or str(it.get('designation_brute', '')).strip()
        qty = float(it.get('quantite', 1))
        unit_price = float(it.get('prix_unitaire', 0))
        unit = str(it.get('unite', 'Pièce')).strip() or 'Pièce'
        cat = str(it.get('categorie', 'Quincaillerie & Matériaux')).strip() or 'Quincaillerie & Matériaux'
        pv = float(it.get('prix_vente', 0))
        if pv <= 0:
            pv = (unit_price * 1.25) if unit_price > 0 else 0.0

        existing_art = None
        if art_id and art_id.upper() != 'NEW':
            cur.execute("SELECT id, nom, stock_actuel, unite, prix_vente FROM articles WHERE id = ?", (art_id,))
            existing_art = cur.fetchone()

        # Si l'article n'existe pas ou s'il est marqué NEW : création
        if not existing_art:
            cur.execute("SELECT id FROM articles WHERE id LIKE 'ART-%'")
            ids = [r['id'] for r in cur.fetchall()]
            existing_art_ids = {str(aid).strip().upper() for aid in ids if aid}

            # Si un ID commençant par ART- a été proposé et qu'il est libre, l'utiliser
            cand_id = art_id if (art_id and art_id.upper() != 'NEW' and art_id.upper().startswith('ART-')) else None
            if cand_id and cand_id.upper() not in existing_art_ids:
                new_id = cand_id
            else:
                max_num = 0
                import re
                for aid in ids:
                    m = re.match(r'^ART-(\d+)$', str(aid).strip(), re.IGNORECASE)
                    if m:
                        try:
                            num = int(m.group(1))
                            if num > max_num:
                                max_num = num
                        except ValueError:
                            pass
                n_cand = max_num + 1 if max_num > 0 else 1
                new_id = f"ART-{n_cand:03d}"
                while new_id.upper() in existing_art_ids:
                    n_cand += 1
                    new_id = f"ART-{n_cand:03d}"

            art_name = designation if designation else f"Article Inédit {new_id}"

            cur.execute("""
            INSERT INTO articles (
                id, nom, categorie, unite, prix_vente, source_prix, stock_actuel, stock_min, en_commande, fournisseur
            ) VALUES (?, ?, ?, ?, ?, 'Facture Fournisseur', 0.0, 5.0, 0.0, ?)
            """, (new_id, art_name, cat, unit, pv, fournisseur))

            art_id = new_id
            stock_avant = 0.0
            article_nom = art_name
            nouveaux_articles.append({"id": new_id, "nom": art_name, "categorie": cat, "prix": pv})
        else:
            stock_avant = float(existing_art['stock_actuel'])
            article_nom = existing_art['nom']
            # Mise à jour du prix de vente si auparavant 0
            if float(existing_art['prix_vente']) == 0 and pv > 0:
                cur.execute("UPDATE articles SET prix_vente = ?, source_prix = 'Facture Fournisseur' WHERE id = ?", (pv, art_id))

        stock_apres = stock_avant + qty

        # 2. Mise à jour immédiate du stock
        cur.execute("""
        UPDATE articles SET
            stock_actuel = stock_actuel + ?,
            date_modification = CURRENT_TIMESTAMP
        WHERE id = ?
        """, (qty, art_id))

        # 3. Traçabilité dans mouvements_stock
        cur.execute("""
        INSERT INTO mouvements_stock (
            article_id, type_mouvement, quantite, stock_avant, stock_apres,
            prix_unitaire, montant_total, reference_doc, commentaire
        ) VALUES (?, 'COMMANDE_RECUE', ?, ?, ?, ?, ?, ?, ?)
        """, (art_id, qty, stock_avant, stock_apres, unit_price, qty * unit_price, cmd_num, f"Facture {cmd_num} ({fournisseur})"))

        # 4. Enregistrement de la ligne de commande fournisseur
        cur.execute("""
        INSERT INTO lignes_commande (
            commande_id, article_id, nom_article, quantite_commandee, quantite_recue, prix_achat_estime
        ) VALUES (?, ?, ?, ?, ?, ?)
        """, (cmd_id, art_id, article_nom, qty, qty, unit_price))

        articles_traites.append({
            "article_id": art_id,
            "nom": article_nom,
            "quantite": qty,
            "stock_avant": stock_avant,
            "stock_apres": stock_apres,
            "prix_unitaire": unit_price,
            "total_ligne": qty * unit_price
        })

    conn.commit()
    conn.close()

    # Synchronisation immédiate du classeur Excel DIADJI_FAMILY_TABLEAU_DE_BORD.xlsx
    try:
        export_to_excel(EXCEL_PATH)
    except Exception as exc:
        print(f"[WARN] Erreur synchronisation Excel automatique: {exc}")

    return {
        "status": "ok",
        "commande_id": cmd_id,
        "numero_commande": cmd_num,
        "fournisseur": fournisseur,
        "date_facture": date_facture,
        "articles_recus": len(articles_traites),
        "montant_total": montant_total,
        "nouveaux_articles": nouveaux_articles,
        "details": articles_traites
    }

