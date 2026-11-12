# -*- coding: utf-8 -*-
"""
Script de synchronisation et d'intégration du moteur de données local autonome
pour DIADJI FAMILY.
Permet à l'application de fonctionner 100% hors-ligne et indépendante du serveur.
"""
import json
import os
import re

def build():
    # 1. Charger les articles initiaux
    with open('initial_articles_embedded.json', 'r', encoding='utf-8') as f:
        articles_data = f.read().strip()

    # 2. Lire app_ui.html source
    with open('app_ui.html', 'r', encoding='utf-8') as f:
        html = f.read()

    # Définition du Moteur de Données Local Embarqué (LocalDataEngine)
    engine_js = f"""
        // =====================================================================
        // MOTEUR DE DONNÉES LOCAL AUTONOME - DIADJI FAMILY (OFFLINE-FIRST)
        // Permet un fonctionnement 100% autonome sans aucun serveur requis.
        // =====================================================================
        const DIADJI_INITIAL_ARTICLES = {articles_data};

        const LocalDataEngine = {{
            KEY_ARTICLES: 'diadji_articles_v2',
            KEY_VENTES: 'diadji_ventes_v2',

            getArticles() {{
                const raw = localStorage.getItem(this.KEY_ARTICLES);
                if (!raw) {{
                    localStorage.setItem(this.KEY_ARTICLES, JSON.stringify(DIADJI_INITIAL_ARTICLES));
                    return JSON.parse(JSON.stringify(DIADJI_INITIAL_ARTICLES));
                }}
                try {{
                    return JSON.parse(raw);
                }} catch (e) {{
                    return JSON.parse(JSON.stringify(DIADJI_INITIAL_ARTICLES));
                }}
            }},

            saveArticles(articles) {{
                localStorage.setItem(this.KEY_ARTICLES, JSON.stringify(articles));
            }},

            getVentes() {{
                const raw = localStorage.getItem(this.KEY_VENTES);
                if (!raw) return [];
                try {{
                    return JSON.parse(raw);
                }} catch (e) {{
                    return [];
                }}
            }},

            saveVentes(ventes) {{
                localStorage.setItem(this.KEY_VENTES, JSON.stringify(ventes));
            }},

            async handleRequest(urlStr, init = {{}}) {{
                const method = (init.method || 'GET').toUpperCase();
                let pathname = urlStr;
                let searchParams = new URLSearchParams();

                try {{
                    const parsed = new URL(urlStr, 'http://localhost');
                    pathname = parsed.pathname;
                    searchParams = parsed.searchParams;
                }} catch (e) {{
                    if (urlStr.includes('?')) {{
                        const parts = urlStr.split('?');
                        pathname = parts[0];
                        searchParams = new URLSearchParams(parts[1]);
                    }}
                }}

                // 1. GET /api/stats
                if (pathname === '/api/stats') {{
                    const articles = this.getArticles();
                    const ventes = this.getVentes();

                    const todayStr = new Date().toISOString().slice(0, 10);
                    const todayVentes = ventes.filter(v => (v.date_vente || '').startsWith(todayStr));
                    const caJour = todayVentes.reduce((sum, v) => sum + (v.montant_net || 0), 0);

                    let valeurStock = 0;
                    let enRupture = 0;
                    let stockFaible = 0;
                    const catMap = {{}};

                    articles.forEach(a => {{
                        const prix = a.prix_vente || 0;
                        const stock = a.stock_actuel || 0;
                        valeurStock += (prix * stock);
                        if (stock <= 0) enRupture++;
                        else if (stock <= (a.stock_min || 0)) stockFaible++;

                        const c = a.categorie || 'Commerce Général';
                        catMap[c] = (catMap[c] || 0) + 1;
                    }});

                    const categories = Object.keys(catMap).map(c => ({{ categorie: c, total: catMap[c] }}));

                    return this.jsonResponse({{
                        total_articles: articles.length,
                        valeur_stock_fcfa: Math.round(valeurStock),
                        en_rupture: enRupture,
                        stock_faible: stockFaible,
                        commandes_en_cours: 0,
                        ventes_jour_total_fcfa: Math.round(caJour),
                        ventes_jour_count: todayVentes.length,
                        categories: categories
                    }});
                }}

                // 2. GET /api/alertes
                if (pathname === '/api/alertes') {{
                    const articles = this.getArticles();
                    const alerts = articles.filter(a => (a.stock_actuel || 0) <= (a.stock_min || 0));
                    return this.jsonResponse(alerts);
                }}

                // 3. Prochain Code Article (next-code / next-id)
                if (pathname === '/api/articles/next-code' || pathname === '/api/articles/next-id') {{
                    const articles = this.getArticles();
                    let maxId = 0;
                    articles.forEach(a => {{
                        const num = parseInt((a.id || '').replace(/\\D/g, ''), 10);
                        if (!isNaN(num) && num > maxId) maxId = num;
                    }});
                    const nextCode = 'ART-' + String(maxId + 1).padStart(3, '0');
                    return this.jsonResponse({{
                        next_code: nextCode,
                        code: nextCode,
                        id: nextCode,
                        success: true
                    }});
                }}

                // 4. GET /api/articles (Liste, recherche, filtres)
                if (pathname === '/api/articles' && method === 'GET') {{
                    let articles = this.getArticles();
                    const q = searchParams.get('q');
                    const cat = searchParams.get('cat');
                    const statut = searchParams.get('statut');

                    if (cat && cat !== 'Toutes') {{
                        articles = articles.filter(a => a.categorie === cat);
                    }}
                    if (q) {{
                        const queryLower = q.toLowerCase();
                        articles = articles.filter(a => 
                            (a.nom || '').toLowerCase().includes(queryLower) ||
                            (a.id || '').toLowerCase().includes(queryLower) ||
                            (a.categorie || '').toLowerCase().includes(queryLower) ||
                            (a.code_barre || '').toLowerCase().includes(queryLower)
                        );
                    }}
                    if (statut && statut !== 'Tous') {{
                        if (statut === 'En rupture') articles = articles.filter(a => (a.stock_actuel || 0) <= 0);
                        else if (statut === 'Stock faible') articles = articles.filter(a => (a.stock_actuel || 0) > 0 && (a.stock_actuel || 0) <= (a.stock_min || 0));
                        else if (statut === 'En stock') articles = articles.filter(a => (a.stock_actuel || 0) > (a.stock_min || 0));
                    }}

                    articles = articles.map(a => ({{
                        ...a,
                        valeur_stock: (a.stock_actuel || 0) * (a.prix_vente || 0),
                        statut_disponibilite: (a.stock_actuel || 0) <= 0 ? 'En rupture' : ((a.stock_actuel || 0) <= (a.stock_min || 0) ? 'Stock faible' : 'En stock')
                    }}));

                    return this.jsonResponse(articles);
                }}

                // 5. GET /api/articles/:id
                if (pathname.startsWith('/api/articles/') && method === 'GET') {{
                    const id = decodeURIComponent(pathname.replace('/api/articles/', '').trim());
                    const articles = this.getArticles();
                    const art = articles.find(a => a.id === id);
                    if (art) return this.jsonResponse(art);
                    return this.errorResponse(`Article ${{id}} introuvable`, 404);
                }}

                // 6. POST /api/articles (Création)
                if (pathname === '/api/articles' && method === 'POST') {{
                    const body = typeof init.body === 'string' ? JSON.parse(init.body) : (init.body || {{}});
                    const articles = this.getArticles();
                    const id = body.id || ('ART-' + String(articles.length + 1).padStart(3, '0'));
                    const newArt = {{
                        id: id,
                        code_barre: body.code_barre || id,
                        nom: body.nom || 'Nouvel Article',
                        categorie: body.categorie || 'Commerce Général',
                        unite: body.unite || 'Pièce',
                        prix_vente: parseFloat(body.prix_vente || 0),
                        source_prix: body.source_prix || 'Saisie Manuelle',
                        stock_actuel: parseFloat(body.stock_actuel || 0),
                        stock_min: parseFloat(body.stock_min || 0),
                        en_commande: 0,
                        fournisseur: body.fournisseur || 'Grossiste Général Dakar',
                        emplacement: body.emplacement || 'Magasin',
                        description: body.description || ''
                    }};
                    articles.unshift(newArt);
                    this.saveArticles(articles);
                    return this.jsonResponse(newArt, 201);
                }}

                // 7. PUT /api/articles/:id (Modification)
                if (pathname.startsWith('/api/articles/') && method === 'PUT') {{
                    const id = decodeURIComponent(pathname.replace('/api/articles/', '').trim());
                    const body = typeof init.body === 'string' ? JSON.parse(init.body) : (init.body || {{}});
                    let articles = this.getArticles();
                    const idx = articles.findIndex(a => a.id === id);
                    if (idx === -1) return this.errorResponse(`Article ${{id}} introuvable`, 404);

                    articles[idx] = {{ ...articles[idx], ...body, id: id }};
                    this.saveArticles(articles);
                    return this.jsonResponse(articles[idx]);
                }}

                // 8. DELETE /api/articles/:id (Suppression)
                if (pathname.startsWith('/api/articles/') && method === 'DELETE') {{
                    const id = decodeURIComponent(pathname.replace('/api/articles/', '').trim());
                    let articles = this.getArticles();
                    const filtered = articles.filter(a => a.id !== id);
                    this.saveArticles(filtered);
                    return this.jsonResponse({{ status: 'ok', deleted: id }});
                }}

                // 9. POST /api/caisse/vente (Vente & Encaissement Caisse)
                if (pathname === '/api/caisse/vente' && method === 'POST') {{
                    const body = typeof init.body === 'string' ? JSON.parse(init.body) : (init.body || {{}});
                    const items = body.items || [];
                    if (!items.length) return this.errorResponse("Le panier est vide.", 400);

                    const articles = this.getArticles();
                    let totalBrut = 0;
                    const processedLines = [];

                    for (const it of items) {{
                        const art = articles.find(a => a.id === it.article_id);
                        if (!art) return this.errorResponse(`Article ${{it.article_id}} introuvable.`, 400);
                        const qte = parseFloat(it.quantite || 1);
                        const prix = parseFloat(it.prix_unitaire || art.prix_vente || 0);
                        const totalLigne = qte * prix;
                        totalBrut += totalLigne;

                        // Déduction de stock
                        art.stock_actuel = Math.max(0, (art.stock_actuel || 0) - qte);

                        processedLines.push({{
                            article_id: art.id,
                            nom_article: art.nom,
                            quantite: qte,
                            prix_unitaire: prix,
                            total_ligne: totalLigne,
                            unite: art.unite || 'Pièce'
                        }});
                    }}

                    const remise = parseFloat(body.remise || 0);
                    const totalNet = Math.max(0, totalBrut - remise);
                    const montantVerse = parseFloat(body.montant_verse !== undefined && body.montant_verse !== '' ? body.montant_verse : totalNet);
                    const monnaie = Math.max(0, montantVerse - totalNet);

                    // Génération du numéro de ticket (ex: TK-20261112-0001)
                    const now = new Date();
                    const yyyy = now.getFullYear();
                    const mm = String(now.getMonth() + 1).padStart(2, '0');
                    const dd = String(now.getDate()).padStart(2, '0');
                    const dateStr = `${{yyyy}}${{mm}}${{dd}}`;

                    const ventes = this.getVentes();
                    const todayCount = ventes.filter(v => (v.numero_ticket || '').includes(dateStr)).length + 1;
                    const ticketNum = `TK-${{dateStr}}-${{String(todayCount).padStart(4, '0')}}`;

                    const dateFormatee = `${{now.getFullYear()}}-${{mm}}-${{dd}} ${{String(now.getHours()).padStart(2, '0')}}:${{String(now.getMinutes()).padStart(2, '0')}}:${{String(now.getSeconds()).padStart(2, '0')}}`;

                    const ticket = {{
                        id: ventes.length + 1,
                        numero_ticket: ticketNum,
                        date_vente: dateFormatee,
                        montant_total: totalBrut,
                        remise: remise,
                        montant_net: totalNet,
                        montant_verse: montantVerse,
                        monnaie_rendue: monnaie,
                        mode_paiement: body.mode_paiement || 'Espèces',
                        nom_client: body.nom_client || 'Client Comptant',
                        telephone_client: body.telephone_client || '',
                        statut: 'PAYE',
                        lignes: processedLines
                    }};

                    ventes.unshift(ticket);
                    this.saveVentes(ventes);
                    this.saveArticles(articles);

                    return this.jsonResponse(ticket, 201);
                }}

                // 10. GET /api/ventes (Historique)
                if (pathname === '/api/ventes' && method === 'GET') {{
                    const ventes = this.getVentes();
                    return this.jsonResponse(ventes);
                }}

                // 11. GET /api/ventes/:ticketNum
                if (pathname.startsWith('/api/ventes/') && method === 'GET') {{
                    const ticketNum = decodeURIComponent(pathname.replace('/api/ventes/', '').trim());
                    const ventes = this.getVentes();
                    const v = ventes.find(x => x.numero_ticket === ticketNum);
                    if (v) return this.jsonResponse(v);
                    return this.errorResponse(`Ticket ${{ticketNum}} introuvable`, 404);
                }}

                // 12. Backup local JSON
                if (pathname === '/api/backup/db' || pathname === '/api/backup/json') {{
                    const dump = {{
                        app: 'DIADJI FAMILY',
                        version: '2.0.0',
                        date: new Date().toISOString(),
                        articles: this.getArticles(),
                        ventes: this.getVentes()
                    }};
                    const blob = new Blob([JSON.stringify(dump, null, 2)], {{ type: 'application/json' }});
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `DIADJI_FAMILY_SAUVEGARDE_${{new Date().toISOString().slice(0, 10)}}.json`;
                    a.click();
                    return this.jsonResponse({{ success: true, message: "Sauvegarde téléchargée avec succès." }});
                }}

                return this.errorResponse(`Route ${{pathname}} non gérée localement`, 404);
            }},

            jsonResponse(data, status = 200) {{
                return new Response(JSON.stringify(data), {{
                    status: status,
                    headers: {{ 'Content-Type': 'application/json' }}
                }});
            }},

            errorResponse(message, status = 400) {{
                return new Response(JSON.stringify({{ error: message, success: false }}), {{
                    status: status,
                    headers: {{ 'Content-Type': 'application/json' }}
                }});
            }}
        }};

        window.LocalDataEngine = LocalDataEngine;
        window.DIADJI_INITIAL_ARTICLES = DIADJI_INITIAL_ARTICLES;

        // Intercepteur Transparent de Fetch pour assurer l'indépendance totale vis-à-vis du serveur
        const _origFetch = window.fetch;
        window.fetch = async function(input, init) {{
            let url = typeof input === 'string' ? input : (input && input.url ? input.url : '');
            
            // Si c'est un appel API
            if (url.includes('/api/')) {{
                // Si on tourne en local (protocole file://) ou que le serveur n'est pas utilisé :
                if (window.location.protocol === 'file:' || !window.location.origin || window.location.origin === 'null' || window.FORCE_LOCAL_MODE) {{
                    return LocalDataEngine.handleRequest(url, init);
                }}
                
                // Si sur serveur web HTTP/HTTPS : tenter le serveur d'abord, basculer automatiquement sur LocalDataEngine si hors ligne
                try {{
                    const resp = await _origFetch(input, init);
                    if (resp.ok || resp.status === 400 || resp.status === 404) {{
                        return resp;
                    }}
                    return LocalDataEngine.handleRequest(url, init);
                }} catch (networkErr) {{
                    console.warn("Serveur réseau injoignable, bascule automatique sur le moteur local embarqué :", networkErr);
                    return LocalDataEngine.handleRequest(url, init);
                }}
            }}
            
            return _origFetch(input, init);
        }};
    """

    # Remplacer la ligne problématique "new URL('/api/articles', window.location.origin)"
    html = html.replace(
        "const url = new URL('/api/articles', window.location.origin);",
        "const baseUrl = (window.location.origin && window.location.origin !== 'null') ? window.location.origin : 'http://localhost';\n            const url = new URL('/api/articles', baseUrl);"
    )

    # Injecter l'Engine juste après <script>
    if "const DIADJI_INITIAL_ARTICLES =" not in html:
        html = html.replace("<script>", f"<script>\n{engine_js}\n", 1)

    # Sauvegarder dans app_ui.html
    with open('app_ui.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print("[OK] app_ui.html mis a jour avec le moteur local autonome.")

    # 3. Créer index.html pour Android assets avec les chemins vendor locaux offline
    android_html = html
    # Utiliser les scripts locaux si disponibles
    android_html = android_html.replace(
        '<script src="https://cdn.tailwindcss.com"></script>',
        '<script src="vendor/tailwind.js"></script>'
    )
    android_html = android_html.replace(
        '<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">',
        '<link rel="stylesheet" href="vendor/fontawesome.css">'
    )
    android_html = android_html.replace(
        '<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>',
        '<script src="vendor/chart.js"></script>'
    )

    with open('android/app/src/main/assets/www/index.html', 'w', encoding='utf-8') as f:
        f.write(android_html)
    print("[OK] android/app/src/main/assets/www/index.html mis a jour avec assets locaux.")

    # 4. Synchroniser avec dist/
    for dist_path in ['dist/app_ui.html', 'dist/DIADJI_FAMILY/app_ui.html']:
        if os.path.exists(os.path.dirname(dist_path)):
            with open(dist_path, 'w', encoding='utf-8') as f:
                f.write(html)
            print(f"[OK] {dist_path} synchronise.")

if __name__ == '__main__':
    build()
