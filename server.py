"""
Serveur HTTP REST API et passerelle d'application embarquée
pour le logiciel DIADJI FAMILY.
Utilise la bibliothèque standard Python http.server (aucun framework lourd requis).
"""

import sys
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import json
import time
import threading
import urllib.parse
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import tempfile
import base64
import database
import invoice_scanner


def get_resource_path(filename):
    """Localise une ressource statique (HTML, icônes) en mode dev et en mode PyInstaller."""
    # 1. Vérifier dans sys._MEIPASS (si exécutable autonome PyInstaller)
    if hasattr(sys, '_MEIPASS'):
        p = os.path.join(sys._MEIPASS, filename)
        if os.path.exists(p):
            return p
    # 2. Vérifier dans le dossier de l'exécutable
    if getattr(sys, 'frozen', False):
        app_dir = os.path.dirname(os.path.abspath(sys.executable))
        p = os.path.join(app_dir, filename)
        if os.path.exists(p):
            return p
    # 3. Vérifier dans le répertoire du script source
    p = os.path.join(BASE_DIR, filename)
    if os.path.exists(p):
        return p
    # 4. Fallback répertoire courant
    return os.path.join(os.getcwd(), filename)


HTML_UI_PATH = get_resource_path("app_ui.html")


def parse_query_int(query, name, default, minimum=None, maximum=None):
    """Parse un entier de requête et rejette explicitement les valeurs invalides."""
    raw_value = query.get(name, [default])[0]
    try:
        value = int(raw_value)
    except (TypeError, ValueError):
        raise ValueError(f"Le paramètre '{name}' doit être un entier.")
    if minimum is not None and value < minimum:
        raise ValueError(f"Le paramètre '{name}' doit être supérieur ou égal à {minimum}.")
    if maximum is not None and value > maximum:
        raise ValueError(f"Le paramètre '{name}' doit être inférieur ou égal à {maximum}.")
    return value


class MagasinRequestHandler(BaseHTTPRequestHandler):
    """Gestionnaire de requêtes HTTP et API REST."""

    def log_message(self, format, *args):
        """Silencie les logs d'accès verbeux mais affiche les erreurs."""
        if args and str(args[1]) >= "400":
            super().log_message(format, *args)

    def send_json(self, data, status=200):
        """Envoie une réponse JSON avec les bons en-têtes."""
        payload = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(payload)

    def send_error_json(self, message, status=400):
        """Envoie un message d'erreur standardisé en JSON."""
        self.send_json({"error": str(message)}, status=status)

    def do_OPTIONS(self):
        """Gère les requêtes préliminaires CORS."""
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        """Routeur des requêtes GET."""
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        # 1. Page d'accueil / Interface Web
        if path in ("/", "/index.html", "/app"):
            html_file = get_resource_path("app_ui.html")
            if not os.path.exists(html_file):
                self.send_error_json("Interface HTML app_ui.html introuvable", status=404)
                return
            with open(html_file, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
            return

        # 1.1 Fichiers d'icônes et assets statiques
        if path in ("/favicon.ico", "/diadji_icon.ico"):
            ico_file = get_resource_path("diadji_icon.ico")
            if os.path.exists(ico_file):
                with open(ico_file, "rb") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "image/x-icon")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
                return

        if path in ("/diadji_icon.png", "/logo.png"):
            png_file = get_resource_path("diadji_icon.png")
            if os.path.exists(png_file):
                with open(png_file, "rb") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "image/png")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
                return

        # 1.2 Web App Manifest (PWA pour installation mobile fluide)
        if path == "/manifest.json":
            manifest = {
                "name": "DIADJI FAMILY - Caisse & Stock",
                "short_name": "DIADJI",
                "description": "Logiciel de Caisse Express, Gestion des Stocks, Facturation PDF et Scanner IA Vision",
                "start_url": "/",
                "display": "standalone",
                "background_color": "#0F172A",
                "theme_color": "#0F172A",
                "orientation": "portrait-primary",
                "icons": [
                    {
                        "src": "/diadji_icon.png",
                        "sizes": "192x192",
                        "type": "image/png",
                        "purpose": "any maskable"
                    },
                    {
                        "src": "/diadji_icon.png",
                        "sizes": "512x512",
                        "type": "image/png",
                        "purpose": "any maskable"
                    }
                ]
            }
            self.send_json(manifest)
            return

        # 2. API Statistiques Dashboard
        if path == "/api/stats":
            stats = database.get_dashboard_stats()
            self.send_json(stats)
            return

        # 3. API Articles (Liste & Recherche)
        if path == "/api/articles":
            q = query.get("q", [None])[0]
            cat = query.get("cat", [None])[0]
            statut = query.get("statut", [None])[0]
            try:
                limit = parse_query_int(query, "limit", 0, 0, 500) if "limit" in query else None
                offset = parse_query_int(query, "offset", 0, 0, None) if "offset" in query else None
            except ValueError as exc:
                self.send_error_json(str(exc), status=400)
                return
            articles = database.get_articles(query=q, categorie=cat, statut=statut, limit=limit, offset=offset)
            self.send_json(articles)
            return

        # 3.1 API Prochain Code Article Auto-généré
        if path in ("/api/articles/next-code", "/api/articles/next-id"):
            try:
                count = int(query.get("count", [1])[0])
            except (ValueError, TypeError):
                count = 1
            count = max(1, min(count, 100))
            if count == 1:
                next_code = database.get_next_article_id(1)
                self.send_json({
                    "next_code": next_code,
                    "code": next_code,
                    "id": next_code,
                    "success": True
                })
            else:
                codes = database.get_next_article_id(count)
                self.send_json({
                    "next_code": codes[0],
                    "code": codes[0],
                    "id": codes[0],
                    "codes": codes,
                    "count": len(codes),
                    "success": True
                })
            return

        # 4. API Article individuel par ID
        if path.startswith("/api/articles/"):
            art_id = urllib.parse.unquote(path.replace("/api/articles/", "").strip())
            art = database.get_article_by_id(art_id)
            if art:
                self.send_json(art)
            else:
                self.send_error_json(f"Article {art_id} introuvable", status=404)
            return

        # 5. API Ventes (Historique)
        if path == "/api/ventes":
            try:
                limit = parse_query_int(query, "limit", 50, 1, 500)
            except ValueError as exc:
                self.send_error_json(str(exc), status=400)
                return
            ventes = database.get_ventes(limit=limit)
            self.send_json(ventes)
            return

        # 6. API Vente individuelle (Ticket) et Téléchargement Facture PDF
        if path.startswith("/api/ventes/"):
            rest = urllib.parse.unquote(path.replace("/api/ventes/", "").strip())
            
            # Sous-route : Génération et téléchargement de la facture PDF
            if rest.endswith("/pdf"):
                ticket_num = rest[:-4].strip("/")
                sale = database.get_sale_by_ticket(ticket_num)
                if not sale:
                    self.send_error_json(f"Ticket {ticket_num} introuvable", status=404)
                    return
                try:
                    import pdf_generator
                    factures_dir = os.path.join(BASE_DIR, "factures_pdf")
                    os.makedirs(factures_dir, exist_ok=True)
                    clean_name = "".join(c for c in ticket_num if c.isalnum() or c in "-_")
                    pdf_filename = f"Facture_DIADJI_FAMILY_{clean_name}.pdf"
                    pdf_path = os.path.join(factures_dir, pdf_filename)
                    pdf_generator.generate_invoice_pdf(sale, output_path=pdf_path)
                    
                    with open(pdf_path, "rb") as f:
                        pdf_data = f.read()

                    self.send_response(200)
                    self.send_header("Content-Type", "application/pdf")
                    self.send_header("Content-Disposition", f'inline; filename="{pdf_filename}"')
                    self.send_header("Content-Length", str(len(pdf_data)))
                    self.send_header("Cache-Control", "no-cache")
                    self.end_headers()
                    self.wfile.write(pdf_data)
                    return
                except Exception as e:
                    self.send_error_json(f"Erreur lors de la génération du PDF: {str(e)}", status=500)
                    return

            ticket_num = rest
            sale = database.get_sale_by_ticket(ticket_num)
            if sale:
                self.send_json(sale)
            else:
                self.send_error_json(f"Ticket {ticket_num} introuvable", status=404)
            return

        # 7. API Mouvements de stock
        if path == "/api/mouvements":
            try:
                limit = parse_query_int(query, "limit", 100, 1, 500)
            except ValueError as exc:
                self.send_error_json(str(exc), status=400)
                return
            art_id = query.get("article_id", [None])[0]
            mouvs = database.get_mouvements(limit=limit, article_id=art_id)
            self.send_json(mouvs)
            return

        # 8. API Commandes Fournisseurs
        if path == "/api/commandes":
            statut = query.get("statut", [None])[0]
            commandes = database.get_commandes(statut=statut)
            self.send_json(commandes)
            return

        # 9. API Alertes de Rupture & Réassort
        if path == "/api/alertes":
            alertes = database.get_alertes_reassort()
            self.send_json(alertes)
            return

        # 10. Téléchargement Export Excel
        if path == "/api/export/excel":
            temp_path = None
            try:
                temp_excel = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
                temp_path = temp_excel.name
                temp_excel.close()
                database.export_to_excel(temp_path)
                with open(temp_path, "rb") as f:
                    content = f.read()

                self.send_response(200)
                self.send_header("Content-Type", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                self.send_header("Content-Disposition", 'attachment; filename="DIADJI_FAMILY_TABLEAU_DE_BORD.xlsx"')
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
                return
            except Exception as e:
                self.send_error_json(f"Erreur d'exportation Excel : {str(e)}", status=500)
                return
            finally:
                if temp_path and os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                    except Exception:
                        pass

        # 11. Téléchargement Sauvegarde Base SQLite (magasin.db)
        if path == "/api/backup/db":
            if not os.path.exists(database.DB_PATH):
                self.send_error_json("Fichier magasin.db inexistant", status=404)
                return
            with open(database.DB_PATH, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Disposition", 'attachment; filename="magasin_backup.db"')
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
            return

        # 12. API Paramètres & État IA/OCR
        if path == "/api/settings":
            raw_key = invoice_scanner.get_gemini_api_key()
            masked = f"{raw_key[:6]}...{raw_key[-4:]}" if len(raw_key) > 10 else ("Configurée" if raw_key else "")
            data = {
                "gemini_configured": bool(raw_key),
                "gemini_masked_key": masked,
                "active_engine": "gemini" if bool(raw_key) else "windows_media_ocr",
                "available_engines": [
                    {"id": "auto", "label": "Automatique (IA Gemini si dispo, sinon OCR Windows)"},
                    {"id": "gemini", "label": "IA Multimodale Google Gemini Vision"},
                    {"id": "ocr", "label": "OCR Local Windows Media (100% Hors Ligne)"}
                ]
            }
            self.send_json(data)
            return

        # Route non reconnue
        self.send_error_json("Route introuvable", status=404)

    def do_POST(self):
        """Routeur des requêtes POST."""
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        length = int(self.headers.get("Content-Length", 0))

        # 1. API Création Article
        if path == "/api/articles":
            try:
                body = self.rfile.read(length).decode("utf-8")
                data = json.loads(body)
                new_art = database.create_article(data)
                self.send_json(new_art, status=201)
                return
            except Exception as e:
                self.send_error_json(str(e), status=400)
                return

        # 2. API Mouvement de Stock (Entrée rapide, ajustement)
        if path == "/api/stock/mouvement":
            try:
                body = self.rfile.read(length).decode("utf-8")
                data = json.loads(body)
                art_id = data.get("article_id")
                type_mouv = data.get("type", "ENTREE")
                qty = float(data.get("quantite", 0))
                prix = float(data.get("prix_unitaire", 0))
                ref = data.get("reference_doc", "")
                comm = data.get("commentaire", "")

                res = database.record_stock_movement(
                    article_id=art_id,
                    type_mouvement=type_mouv,
                    quantite=qty,
                    prix_unitaire=prix,
                    reference_doc=ref,
                    commentaire=comm
                )
                self.send_json(res, status=200)
                return
            except Exception as e:
                self.send_error_json(str(e), status=400)
                return

        # 3. API Vente / Caisse
        if path == "/api/caisse/vente":
            try:
                body = self.rfile.read(length).decode("utf-8")
                data = json.loads(body)
                items = data.get("items", [])
                montant_verse = float(data.get("montant_verse", 0))
                remise = float(data.get("remise", 0))
                mode = data.get("mode_paiement", "Espèces")
                client = data.get("nom_client", "Client Comptant")
                tel = data.get("telephone_client", "")

                ticket = database.create_sale(
                    items=items,
                    montant_verse=montant_verse,
                    remise=remise,
                    mode_paiement=mode,
                    client_nom=client,
                    client_tel=tel
                )
                self.send_json(ticket, status=201)
                return
            except Exception as e:
                self.send_error_json(str(e), status=400)
                return

        # 4. API Commande Fournisseur - Création
        if path == "/api/commandes":
            try:
                body = self.rfile.read(length).decode("utf-8")
                data = json.loads(body)
                fournisseur = data.get("fournisseur")
                items = data.get("items", [])
                date_prev = data.get("date_livraison_prevue", "")
                notes = data.get("notes", "")

                cmd = database.create_supplier_order(
                    fournisseur=fournisseur,
                    items=items,
                    date_prevue=date_prev,
                    notes=notes
                )
                self.send_json(cmd, status=201)
                return
            except Exception as e:
                self.send_error_json(str(e), status=400)
                return

        # 5. API Réception de commande fournisseur
        if path.startswith("/api/commandes/") and path.endswith("/recevoir"):
            try:
                parts = path.strip("/").split("/")
                cmd_id = int(parts[2])
                cmd = database.receive_supplier_order(cmd_id)
                self.send_json(cmd, status=200)
                return
            except Exception as e:
                self.send_error_json(str(e), status=400)
                return

        # 6. API Importation / Synchronisation depuis Excel
        if path == "/api/import/excel":
            try:
                file_bytes = self.rfile.read(length)
                temp_in = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
                temp_in.write(file_bytes)
                temp_in.close()

                stats = database.import_from_excel(temp_in.name)
                os.remove(temp_in.name)
                self.send_json(stats, status=200)
                return
            except Exception as e:
                self.send_error_json(f"Erreur import Excel: {str(e)}", status=400)
                return

        # 7. API Réinitialisation complète de la base
        if path == "/api/reset/db":
            try:
                database.init_db(force_reseed=True)
                stats = database.get_dashboard_stats()
                self.send_json({"status": "ok", "message": "Base réinitialisée", "stats": stats})
                return
            except Exception as e:
                self.send_error_json(str(e), status=500)
                return

        # 8. API Arrêt propre du logiciel
        if path == "/api/shutdown":
            self.send_json({"status": "ok", "message": "Arrêt du logiciel DIADJI FAMILY..."})
            def do_stop():
                time.sleep(0.5)
                self.server.shutdown()
            threading.Thread(target=do_stop, daemon=True).start()
            return

        # 9. API Configuration Paramètres (Clé Gemini API, etc.)
        if path == "/api/settings":
            try:
                body = self.rfile.read(length).decode("utf-8")
                data = json.loads(body)
                if "gemini_api_key" in data:
                    key = str(data["gemini_api_key"]).strip()
                    invoice_scanner.set_gemini_api_key(key)
                self.send_json({"status": "ok", "message": "Paramètres enregistrés avec succès."})
                return
            except Exception as e:
                self.send_error_json(str(e), status=400)
                return

        # 9-bis. API Test de connexion Clé Gemini API
        if path == "/api/settings/test":
            try:
                body = self.rfile.read(length).decode("utf-8")
                data = json.loads(body) if body else {}
                key = str(data.get("gemini_api_key", "")).strip() or invoice_scanner.get_gemini_api_key()
                if not key:
                    self.send_error_json("Aucune clé API Gemini fournie à tester.", status=400)
                    return
                ok, msg = invoice_scanner.test_gemini_api_key(key)
                if ok:
                    self.send_json({"status": "ok", "message": msg}, status=200)
                else:
                    self.send_error_json(msg, status=400)
                return
            except Exception as e:
                self.send_error_json(str(e), status=400)
                return

        # 10. API Numérisation & Analyse de Facture Image (IA & OCR)
        if path == "/api/invoice/scan":
            try:
                body = self.rfile.read(length).decode("utf-8")
                data = json.loads(body)
                b64_img = data.get("image", "")
                if not b64_img:
                    self.send_error_json("Aucune image de facture fournie.", status=400)
                    return

                mime_type = data.get("mime_type", "image/jpeg")
                if "base64," in b64_img:
                    header, b64_part = b64_img.split("base64,", 1)
                    b64_img = b64_part
                    if "image/png" in header:
                        mime_type = "image/png"
                    elif "image/webp" in header:
                        mime_type = "image/webp"

                image_bytes = base64.b64decode(b64_img)
                engine = data.get("engine", "auto")
                rotation = int(data.get("rotation", 0))
                scan_res = invoice_scanner.scan_invoice_image(image_bytes, mime_type=mime_type, force_engine=engine, rotation=rotation)
                self.send_json(scan_res, status=200)
                return
            except Exception as e:
                self.send_error_json(f"Erreur d'analyse de la facture : {str(e)}", status=400)
                return

        # 11. API Validation de Réception et Mise à Jour du Stock en 1 Clic
        if path == "/api/invoice/receive":
            try:
                body = self.rfile.read(length).decode("utf-8")
                data = json.loads(body)
                fournisseur = data.get("fournisseur", "Fournisseur Général")
                num_facture = data.get("numero_facture", "")
                date_facture = data.get("date_facture", "")
                items = data.get("items", [])
                notes = data.get("notes", "")

                reception = database.receive_invoice_batch(
                    fournisseur=fournisseur,
                    numero_facture=num_facture,
                    date_facture=date_facture,
                    items=items,
                    notes=notes
                )
                self.send_json(reception, status=200)
                return
            except Exception as e:
                self.send_error_json(f"Erreur lors de la mise à jour des stocks : {str(e)}", status=400)
                return

        self.send_error_json("Route POST introuvable", status=404)

    def do_PUT(self):
        """Routeur des requêtes PUT."""
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        length = int(self.headers.get("Content-Length", 0))

        if path.startswith("/api/articles/"):
            art_id = urllib.parse.unquote(path.replace("/api/articles/", "").strip())
            try:
                body = self.rfile.read(length).decode("utf-8")
                data = json.loads(body)
                updated = database.update_article(art_id, data)
                self.send_json(updated, status=200)
                return
            except Exception as e:
                self.send_error_json(str(e), status=400)
                return

        self.send_error_json("Route PUT introuvable", status=404)

    def do_DELETE(self):
        """Routeur des requêtes DELETE."""
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path.startswith("/api/articles/"):
            art_id = urllib.parse.unquote(path.replace("/api/articles/", "").strip())
            try:
                deleted = database.delete_article(art_id)
                if deleted:
                    self.send_json({"status": "ok", "deleted": art_id})
                else:
                    self.send_error_json(f"Article {art_id} introuvable", status=404)
                return
            except Exception as e:
                self.send_error_json(str(e), status=400)
                return

        self.send_error_json("Route DELETE introuvable", status=404)


def create_server(host="127.0.0.1", start_port=8000, max_attempts=20):
    """Crée et retourne une instance du serveur HTTP sur le premier port disponible."""
    ThreadingHTTPServer.allow_reuse_address = True
    for p in range(start_port, start_port + max_attempts):
        try:
            server = ThreadingHTTPServer((host, p), MagasinRequestHandler)
            return server, p
        except OSError:
            continue
    raise RuntimeError(f"Impossible de lier un port HTTP libre entre {start_port} et {start_port + max_attempts}.")
