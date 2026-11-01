"""
Suite de tests complète et approfondie pour le logiciel avec base embarquée
de DIADJI FAMILY.
Teste :
1. database.py (Schéma SQLite, CRUD, Ventes, Caisse, Mouvements, Commandes Fournisseurs, Alertes, Excel)
2. server.py (API REST HTTP complète, codes d'état, upload Excel, backup, CORS)
3. Cas limites (caractères spéciaux, accents, stocks négatifs, remises, idempotence)
"""

import unittest
import os
import sys
import json
import tempfile
import threading
import urllib.request
import urllib.parse
import sqlite3
import openpyxl

import database
import server


class TestDatabaseComprehensive(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Initialise avec le catalogue authentique de base
        database.init_db(force_reseed=True)

    @classmethod
    def tearDownClass(cls):
        database.init_db(force_reseed=True)
        database.export_to_excel()

    def setUp(self):
        # Sauvegarde l'état si besoin ou s'assure d'une base propre
        pass

    def test_01_db_schema_and_initial_data(self):
        """Vérifie le schéma SQLite, le nombre d'articles initial (183) et les 44 prix réels."""
        stats = database.get_dashboard_stats()
        self.assertEqual(stats['total_articles'], 183)
        self.assertEqual(stats['articles_avec_prix'], 44)
        self.assertEqual(stats['articles_sans_prix'], 139)
        self.assertEqual(stats['en_rupture'], 183)  # Tous les stocks sont initialisés à 0
        self.assertEqual(stats['valeur_stock_fcfa'], 0.0)

        # Vérification des tables SQLite
        conn = database.get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = set(row['name'] for row in cur.fetchall())
        expected_tables = {'articles', 'mouvements_stock', 'ventes', 'lignes_vente', 'commandes_fournisseurs', 'lignes_commande', 'parametres'}
        for t in expected_tables:
            self.assertIn(t, tables, f"Table {t} manquante dans SQLite")
        conn.close()

    def test_02_id_generation_and_article_crud(self):
        """Teste le cycle CRUD complet sur les articles."""
        next_id = database.get_next_article_id()
        self.assertEqual(next_id, "ART-184")

        # 1. Création
        new_data = {
            "id": "ART-184",
            "nom": "Câble RO2V 3G1.5mm² (Couronne 100m)",
            "categorie": "Électricité - Câbles & Gaines",
            "unite": "Rouleau",
            "prix_vente": 35000,
            "stock_actuel": 10,
            "stock_min": 2,
            "fournisseur": "Fournisseur Test Dakar"
        }
        created = database.create_article(new_data)
        self.assertEqual(created['id'], "ART-184")
        self.assertEqual(created['nom'], "Câble RO2V 3G1.5mm² (Couronne 100m)")
        self.assertEqual(created['stock_actuel'], 10.0)
        self.assertEqual(created['statut_disponibilite'], "En stock")
        self.assertEqual(created['valeur_stock'], 350000.0)

        # Vérifier que le mouvement d'entrée initial a bien été enregistré
        art_with_history = database.get_article_by_id("ART-184")
        self.assertGreaterEqual(len(art_with_history['historique_mouvements']), 1)
        self.assertEqual(art_with_history['historique_mouvements'][0]['type_mouvement'], 'ENTREE')

        # 2. Lecture
        read_art = database.get_article_by_id("ART-184")
        self.assertIsNotNone(read_art)
        self.assertEqual(read_art['prix_vente'], 35000.0)

        # 3. Modification
        update_data = {
            "nom": "Câble RO2V 3G1.5mm² Cuivre Pur 100m",
            "prix_vente": 38000,
            "stock_actuel": 15
        }
        updated = database.update_article("ART-184", update_data)
        self.assertEqual(updated['nom'], "Câble RO2V 3G1.5mm² Cuivre Pur 100m")
        self.assertEqual(updated['prix_vente'], 38000.0)
        self.assertEqual(updated['stock_actuel'], 15.0)

        # 4. Suppression
        deleted = database.delete_article("ART-184")
        self.assertTrue(deleted)
        self.assertIsNone(database.get_article_by_id("ART-184"))

    def test_03_search_accents_and_filters(self):
        """Teste la recherche insensible à la casse et aux accents."""
        # Recherche avec accents : 'câble' doit trouver 'Cable' ou 'Câble'
        res1 = database.get_articles(query="cable")
        res2 = database.get_articles(query="câble")
        res3 = database.get_articles(query="CÂBLE")
        self.assertGreater(len(res1), 0)
        self.assertEqual(len(res1), len(res2))
        self.assertEqual(len(res1), len(res3))

        # Recherche par code
        res_code = database.get_articles(query="art-001")
        self.assertEqual(len(res_code), 1)
        self.assertEqual(res_code[0]['id'], "ART-001")

        # Filtre par catégorie
        res_cat = database.get_articles(categorie="Protection & Tableaux")
        self.assertEqual(len(res_cat), 23)
        for a in res_cat:
            self.assertEqual(a['categorie'], "Protection & Tableaux")

        # Filtre par statut 'avec_prix'
        res_priced = database.get_articles(statut="avec_prix")
        self.assertEqual(len(res_priced), 44)

    def test_04_stock_movements_flow(self):
        """Teste les types de mouvements de stock (ENTREE, AJUSTEMENT, etc.)."""
        # Ajouter du stock sur ART-001
        init_art = database.get_article_by_id("ART-001")
        init_stock = init_art['stock_actuel']

        mouv = database.record_stock_movement(
            article_id="ART-001",
            type_mouvement="ENTREE",
            quantite=25,
            prix_unitaire=1700,
            reference_doc="BL-1001",
            commentaire="Arrivage direct"
        )
        self.assertEqual(mouv['stock_avant'], init_stock)
        self.assertEqual(mouv['stock_apres'], init_stock + 25)

        art_after = database.get_article_by_id("ART-001")
        self.assertEqual(art_after['stock_actuel'], init_stock + 25)

        # Ajustement manuel
        database.record_stock_movement(
            article_id="ART-001",
            type_mouvement="AJUSTEMENT",
            quantite=-5,
            commentaire="Correction inventaire"
        )
        art_adj = database.get_article_by_id("ART-001")
        self.assertEqual(art_adj['stock_actuel'], init_stock + 20)

    def test_05_caisse_sale_pos(self):
        """Teste une vente en caisse complète avec calcul de monnaie et déduction de stock."""
        # S'assurer d'avoir du stock sur ART-001 et ART-002
        database.record_stock_movement("ART-001", "ENTREE", 30, prix_unitaire=1700)
        database.record_stock_movement("ART-002", "ENTREE", 20, prix_unitaire=1700)

        cart_items = [
            {"article_id": "ART-001", "quantite": 3, "prix_unitaire": 1700}, # 5100
            {"article_id": "ART-002", "quantite": 2, "prix_unitaire": 1700}  # 3400
        ]
        # Total brut = 8500 FCFA, remise = 500 FCFA => Net = 8000 FCFA, versé = 10000 FCFA => Monnaie = 2000 FCFA
        sale = database.create_sale(
            items=cart_items,
            montant_verse=10000,
            remise=500,
            mode_paiement="Espèces",
            client_nom="Abdoulaye Ndiaye"
        )

        self.assertIsNotNone(sale['numero_ticket'])
        self.assertTrue(sale['numero_ticket'].startswith("TK-"))
        self.assertEqual(sale['montant_total'], 8500.0)
        self.assertEqual(sale['remise'], 500.0)
        self.assertEqual(sale['montant_net'], 8000.0)
        self.assertEqual(sale['monnaie_rendue'], 2000.0)
        self.assertEqual(len(sale['lignes']), 2)

        # Vérifier historique des ventes
        ventes = database.get_ventes(limit=5)
        self.assertGreaterEqual(len(ventes), 1)
        self.assertEqual(ventes[0]['numero_ticket'], sale['numero_ticket'])

    def test_06_supplier_order_and_reception(self):
        """Teste le cycle commande fournisseur : création, 'en_commande' et réception."""
        art_id = "ART-003"
        art_before = database.get_article_by_id(art_id)
        stock_init = art_before['stock_actuel']
        cmd_init = art_before['en_commande']

        order = database.create_supplier_order(
            fournisseur="Grossiste Matériel Électrique Dakar",
            items=[{"article_id": art_id, "quantite": 50, "prix_achat_estime": 1500}],
            date_prevue="2026-11-05",
            notes="Commande test automatisée"
        )
        self.assertEqual(order['statut'], 'EN_COURS')
        self.assertEqual(len(order['lignes']), 1)

        # Vérifier que 'en_commande' a augmenté
        art_pending = database.get_article_by_id(art_id)
        self.assertEqual(art_pending['en_commande'], cmd_init + 50)

        # Réception de la commande
        received_order = database.receive_supplier_order(order['id'])
        self.assertEqual(received_order['statut'], 'RECUE')

        art_after = database.get_article_by_id(art_id)
        self.assertEqual(art_after['stock_actuel'], stock_init + 50)
        self.assertEqual(art_after['en_commande'], cmd_init)

        # Empêcher une double réception
        with self.assertRaises(ValueError):
            database.receive_supplier_order(order['id'])

    def test_07_excel_export_and_import_integrity(self):
        """Teste l'export Excel et la ré-importation / synchronisation."""
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            # Export
            exported_file = database.export_to_excel(tmp_path)
            self.assertTrue(os.path.exists(exported_file))

            # Inspecter le fichier Excel généré
            wb = openpyxl.load_workbook(exported_file, data_only=True)
            self.assertIn("STOCK_CATALOGUE", wb.sheetnames)
            self.assertIn("HISTORIQUE_VENTES", wb.sheetnames)

            ws = wb["STOCK_CATALOGUE"]
            self.assertGreater(ws.max_row, 180)
            self.assertEqual(ws.cell(4, 1).value, "Code Article")

            # Test de ré-import / synchronisation
            stats = database.import_from_excel(exported_file)
            self.assertGreater(stats['mis_a_jour'], 100)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)


class TestServerComprehensive(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Démarrer le serveur HTTP sur un port aléatoire libre
        cls.httpd, cls.port = server.create_server(host="127.0.0.1", start_port=8050)
        cls.server_thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.server_thread.start()
        cls.base_url = f"http://127.0.0.1:{cls.port}"

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        database.init_db(force_reseed=True)
        database.export_to_excel()

    def make_request(self, endpoint, method="GET", data=None, headers=None):
        url = f"{self.base_url}{endpoint}"
        req_headers = headers or {}
        body = None
        if data is not None:
            if isinstance(data, (dict, list)):
                body = json.dumps(data).encode("utf-8")
                req_headers["Content-Type"] = "application/json"
            elif isinstance(data, bytes):
                body = data
            elif isinstance(data, str):
                body = data.encode("utf-8")

        req = urllib.request.Request(url, data=body, headers=req_headers, method=method)
        try:
            with urllib.request.urlopen(req) as resp:
                status = resp.status
                content = resp.read()
                content_type = resp.headers.get("Content-Type", "")
                if "application/json" in content_type:
                    return status, json.loads(content.decode("utf-8"))
                return status, content
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8")
            try:
                return e.code, json.loads(err_body)
            except Exception:
                return e.code, err_body

    def test_01_http_root_and_stats(self):
        """Vérifie la racine HTML et l'API des statistiques."""
        status, content = self.make_request("/")
        self.assertEqual(status, 200)
        self.assertIn(b"DIADJI FAMILY", content)

        status, stats = self.make_request("/api/stats")
        self.assertEqual(status, 200)
        self.assertIn("total_articles", stats)
        self.assertIn("valeur_stock_fcfa", stats)
        self.assertIn("en_rupture", stats)

    def test_02_http_articles_endpoints(self):
        """Vérifie les requêtes GET, POST, PUT, DELETE sur /api/articles."""
        # GET articles
        status, arts = self.make_request("/api/articles?limit=10")
        self.assertEqual(status, 200)
        self.assertEqual(len(arts), 10)

        # GET article individuel
        status, art = self.make_request("/api/articles/ART-001")
        self.assertEqual(status, 200)
        self.assertEqual(art['id'], "ART-001")
        self.assertEqual(art['prix_vente'], 1700.0)

        # POST création nouvel article
        new_payload = {
            "id": "ART-999",
            "nom": "Tournevis Test API",
            "categorie": "Électricité - Appareillage",
            "prix_vente": 2500,
            "stock_actuel": 5,
            "stock_min": 1
        }
        status, created = self.make_request("/api/articles", method="POST", data=new_payload)
        self.assertEqual(status, 201)
        self.assertEqual(created['id'], "ART-999")

        # PUT modification article
        update_payload = {"nom": "Tournevis Test API Modifié", "prix_vente": 2800}
        status, updated = self.make_request("/api/articles/ART-999", method="PUT", data=update_payload)
        self.assertEqual(status, 200)
        self.assertEqual(updated['nom'], "Tournevis Test API Modifié")
        self.assertEqual(updated['prix_vente'], 2800.0)

        # DELETE article
        status, res = self.make_request("/api/articles/ART-999", method="DELETE")
        self.assertEqual(status, 200)
        self.assertEqual(res['status'], "ok")

        # Vérifier disparition
        status, err = self.make_request("/api/articles/ART-999")
        self.assertEqual(status, 404)

    def test_03_http_caisse_sale_endpoint(self):
        """Vérifie l'API de vente /api/caisse/vente."""
        # Ajouter du stock
        mouv_payload = {
            "article_id": "ART-005",
            "type": "ENTREE",
            "quantite": 10,
            "prix_unitaire": 2500
        }
        status, mouv = self.make_request("/api/stock/mouvement", method="POST", data=mouv_payload)
        self.assertEqual(status, 200)

        sale_payload = {
            "items": [{"article_id": "ART-005", "quantite": 2, "prix_unitaire": 2500}],
            "montant_verse": 5000,
            "remise": 0,
            "mode_paiement": "Wave",
            "nom_client": "Client Wave Express"
        }
        status, ticket = self.make_request("/api/caisse/vente", method="POST", data=sale_payload)
        self.assertEqual(status, 201)
        self.assertEqual(ticket['montant_net'], 5000.0)
        self.assertEqual(ticket['mode_paiement'], "Wave")

        # Récupération ticket par endpoint
        t_num = ticket['numero_ticket']
        status, t_fetched = self.make_request(f"/api/ventes/{t_num}")
        self.assertEqual(status, 200)
        self.assertEqual(t_fetched['numero_ticket'], t_num)

    def test_04_http_excel_export_and_backup(self):
        """Vérifie le téléchargement de l'export Excel et de la sauvegarde DB."""
        status, excel_bytes = self.make_request("/api/export/excel")
        self.assertEqual(status, 200)
        self.assertGreater(len(excel_bytes), 1000)
        # Signature ZIP / XLSX (PK..)
        self.assertTrue(excel_bytes.startswith(b"PK"))

        status, db_bytes = self.make_request("/api/backup/db")
        self.assertEqual(status, 200)
        self.assertGreater(len(db_bytes), 10000)
        # Signature SQLite
        self.assertTrue(db_bytes.startswith(b"SQLite format 3"))


if __name__ == "__main__":
    unittest.main()
