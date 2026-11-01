"""
Tests unitaires et d'intégration pour le module de scan et réception de factures images
- Configuration et persistance de la clé API Gemini
- Détection et parsing des lignes OCR
- Moteur de correspondance floue (fuzzy matching)
- Réception en stock et création automatique de nouveaux articles
- Endpoints REST de server.py (/api/settings, /api/invoice/scan, /api/invoice/receive)
"""

import unittest
import os
import sys
import json
import base64
import time
import urllib.request
import threading
from io import BytesIO
from PIL import Image, ImageDraw

import database
import invoice_scanner
import server


class TestInvoiceScanAndReception(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Initialisation de la base SQLite
        database.init_db(force_reseed=False)

        # Lancement d'un serveur HTTP local pour tester les endpoints REST
        cls.host = "127.0.0.1"
        cls.httpd, cls.port = server.create_server(host=cls.host, start_port=8090)
        cls.server_thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.server_thread.start()
        cls.base_url = f"http://{cls.host}:{cls.port}"
        time.sleep(0.3)

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        # Réinitialisation propre à la baseline des 183 articles
        database.init_db(force_reseed=True)
        database.export_to_excel()

    def test_01_settings_persistence(self):
        """Vérifie la lecture et l'écriture de la clé API Gemini dans la base SQLite."""
        # Initialement vide ou existante
        orig_key = database.get_setting("gemini_api_key", "")

        # Enregistrement d'une clé de test
        test_key = "AIzaSyTestKey_For_UnitTesting_12345"
        database.set_setting("gemini_api_key", test_key)
        self.assertEqual(database.get_setting("gemini_api_key"), test_key)
        self.assertEqual(invoice_scanner.get_gemini_api_key(), test_key)
        self.assertTrue(invoice_scanner.has_gemini_configured())

        # Nettoyage / remise en état
        if orig_key:
            database.set_setting("gemini_api_key", orig_key)
        else:
            database.set_setting("gemini_api_key", "")

    def test_02_fuzzy_matching_hardware(self):
        """Teste l'algorithme de correspondance intelligente sur des libellés manuscrits typiques."""
        catalog = database.get_articles()
        self.assertGreater(len(catalog), 100)

        test_cases = [
            ("inter simple", "ART-001"),
            ("int va et vient", "ART-002"),
            ("inter double allumage", "ART-003"),
            ("disjoncteur 16A", "ART-018"),
            ("disj 20A", "ART-019"),
            ("fil cuivre 1.5", "ART-027"),
            ("tube pvc 40", "ART-088"),
            ("tube pvc 50", "ART-089"),
            ("coude pvc 50", "ART-098"),
            ("attache murale 10", "ART-075"),
        ]

        for query, expected_id in test_cases:
            art, score, alts = invoice_scanner.fuzzy_match_article(query, catalog)
            self.assertIsNotNone(art, f"Aucun article trouvé pour '{query}'")
            self.assertEqual(art["id"], expected_id, f"Mauvais article pour '{query}': attendu {expected_id}, obtenu {art['id']} ({art.get('nom')})")
            self.assertGreaterEqual(score, 0.40, f"Score trop bas ({score}) pour '{query}'")

    def test_03_ocr_text_parsing(self):
        """Teste le parser de texte OCR brut pour extraire fournisseur, date, quantités et prix."""
        raw_lines = [
            "ETS COMPTOIR DU BATIMENT DAKAR",
            "FACTURE N° BL-2026-904",
            "Date : 30/10/2026",
            "Ciment SOCOCIM 50kg 20 4500 90000",
            "Interrupteur simple 10 1700 17000",
            "Disjoncteur 16A x 5 2500 12500",
            "TOTAL GENERAL : 119500 FCFA"
        ]

        parsed = invoice_scanner.parse_raw_ocr_lines(raw_lines)
        self.assertIn("COMPTOIR DU BATIMENT", parsed["fournisseur"])
        self.assertEqual(parsed["numero_facture"], "BL-2026-904")
        self.assertEqual(parsed["date_facture"], "2026-10-30")
        self.assertGreaterEqual(len(parsed["articles"]), 3)

        # Vérification de l'enrichissement
        enriched = invoice_scanner.enrich_extracted_articles(parsed["articles"])
        self.assertEqual(len(enriched), len(parsed["articles"]))
        # Le deuxième article ("Interrupteur simple") doit être mappé à ART-001
        inter_item = next((x for x in enriched if "interrupteur" in x["designation_brute"].lower()), None)
        self.assertIsNotNone(inter_item)
        self.assertEqual(inter_item["article_id"], "ART-001")
        self.assertEqual(inter_item["quantite"], 10.0)
        self.assertEqual(inter_item["prix_unitaire"], 1700.0)

    def test_04_receive_invoice_batch_stock_update(self):
        """Teste la réception en stock d'articles existants et la création d'articles inédits."""
        # 1. État avant réception
        art1 = database.get_article_by_id("ART-001")
        stock_avant_1 = art1["stock_actuel"]

        items_to_receive = [
            {
                "article_id": "ART-001",
                "designation": art1["nom"],
                "quantite": 25.0,
                "prix_unitaire": 1500.0,
                "unite": "Pièce"
            },
            {
                "article_id": "NEW",
                "designation": "Brouette Renforcée Pro 100L",
                "categorie": "Gros Œuvre & Maçonnerie",
                "quantite": 4.0,
                "prix_unitaire": 28000.0,
                "prix_vente": 35000.0,
                "unite": "Pièce"
            }
        ]

        res = database.receive_invoice_batch(
            fournisseur="SOCOCIM Industries",
            numero_facture="TEST-BL-999",
            date_facture="2026-10-31",
            items=items_to_receive,
            notes="Test unitaire de réception"
        )

        self.assertEqual(res["status"], "ok")
        self.assertEqual(res["articles_recus"], 2)
        self.assertEqual(len(res["nouveaux_articles"]), 1)
        new_art_info = res["nouveaux_articles"][0]
        self.assertEqual(new_art_info["nom"], "Brouette Renforcée Pro 100L")

        # 2. Vérification que le stock de ART-001 a bien augmenté de 25
        art1_apres = database.get_article_by_id("ART-001")
        self.assertEqual(art1_apres["stock_actuel"], stock_avant_1 + 25.0)

        # 3. Vérification que le nouvel article existe en base avec stock = 4
        new_art_db = database.get_article_by_id(new_art_info["id"])
        self.assertIsNotNone(new_art_db)
        self.assertEqual(new_art_db["nom"], "Brouette Renforcée Pro 100L")
        self.assertEqual(new_art_db["stock_actuel"], 4.0)
        self.assertEqual(new_art_db["prix_vente"], 35000.0)

        # 4. Vérification de la traçabilité dans mouvements_stock
        mouvs = database.get_mouvements(limit=5, article_id="ART-001")
        self.assertGreater(len(mouvs), 0)
        last_mouv = mouvs[0]
        self.assertEqual(last_mouv["type_mouvement"], "COMMANDE_RECUE")
        self.assertEqual(last_mouv["quantite"], 25.0)

    def test_05_api_endpoints_integration(self):
        """Teste les endpoints HTTP /api/settings, /api/invoice/scan et /api/invoice/receive."""
        # A. GET /api/settings
        req = urllib.request.Request(f"{self.base_url}/api/settings")
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertIn("gemini_configured", data)
            self.assertIn("active_engine", data)
            self.assertIn("available_engines", data)

        # B. POST /api/settings
        set_payload = json.dumps({"gemini_api_key": "AIzaSy_UnitTest_RestKey"}).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}/api/settings",
            data=set_payload,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data["status"], "ok")

        # C. POST /api/invoice/scan avec une image de test
        img = Image.new("RGB", (500, 150), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        draw.text((20, 20), "ETS QUINCAILLERIE GENERALE", fill=(0, 0, 0))
        draw.text((20, 50), "FACTURE N 8820", fill=(0, 0, 0))
        draw.text((20, 80), "Interrupteur simple 15 1700", fill=(0, 0, 0))

        buf = BytesIO()
        img.save(buf, format="PNG")
        b64_img = base64.b64encode(buf.getvalue()).decode("utf-8")

        scan_payload = json.dumps({
            "image": b64_img,
            "mime_type": "image/png",
            "engine": "ocr" # Force OCR local pour tester hors ligne
        }).encode("utf-8")

        req = urllib.request.Request(
            f"{self.base_url}/api/invoice/scan",
            data=scan_payload,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            scan_data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(scan_data["status"], "ok")
            self.assertIn("articles", scan_data)
            self.assertIn("provider", scan_data)

        # D. POST /api/invoice/receive
        receive_payload = json.dumps({
            "fournisseur": "Fournisseur Test API",
            "numero_facture": "BL-API-101",
            "date_facture": "2026-10-31",
            "items": [
                {
                    "article_id": "ART-002",
                    "designation": "Interrupteur va-et-vient",
                    "quantite": 12.0,
                    "prix_unitaire": 1600.0,
                    "unite": "Pièce"
                }
            ]
        }).encode("utf-8")

        req = urllib.request.Request(
            f"{self.base_url}/api/invoice/receive",
            data=receive_payload,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            rec_res = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(rec_res["status"], "ok")
            self.assertEqual(rec_res["articles_recus"], 1)

        # Nettoyage clé de test
        database.set_setting("gemini_api_key", "")

    def test_06_gemini_api_key_check_and_test_endpoint(self):
        """Teste la fonction de validation de clé API et l'endpoint /api/settings/test."""
        # 1. Clé vide
        ok, msg = invoice_scanner.test_gemini_api_key("")
        self.assertFalse(ok)
        self.assertIn("Aucune clé", msg)

        # 2. Clé invalide via REST
        bad_payload = json.dumps({"gemini_api_key": "AIzaSyFakeKey_12345"}).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}/api/settings/test",
            data=bad_payload,
            headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(req) as resp:
                self.assertEqual(resp.status, 200)
        except urllib.error.HTTPError as e:
            # Attend une erreur 400 pour une fausse clé
            self.assertEqual(e.code, 400)
            err_data = json.loads(e.read().decode("utf-8"))
            self.assertIn("error", err_data)

    def test_07_dimensional_parsing_accuracy(self):
        """Vérifie que les calibres et diamètres (1.5, 40, 16A, 50kg) ne sont pas tronqués par l'OCR."""
        raw_lines = [
            "Fil cuivre 1.5 10 1700 17000",
            "Tube PVC 40 5 1500 7500",
            "Disjoncteur 16A x 5 2500 12500",
            "Ciment SOCOCIM 50kg 20 4500 90000",
            "10 sac Ciment SOCOCIM 4500 45000",
            "Interrupteur va-et-vient x 8"
        ]
        parsed = invoice_scanner.parse_raw_ocr_lines(raw_lines)
        items = parsed["articles"]
        self.assertEqual(len(items), 6)

        # 1. Fil cuivre 1.5
        item0 = items[0]
        self.assertIn("1.5", item0["designation_brute"])
        self.assertEqual(item0["quantite"], 10.0)
        self.assertEqual(item0["prix_unitaire"], 1700.0)
        self.assertEqual(item0["total_ligne"], 17000.0)

        # 2. Tube PVC 40
        item1 = items[1]
        self.assertIn("40", item1["designation_brute"])
        self.assertEqual(item1["quantite"], 5.0)
        self.assertEqual(item1["prix_unitaire"], 1500.0)

        # 3. Disjoncteur 16A
        item2 = items[2]
        self.assertIn("16", item2["designation_brute"])
        self.assertEqual(item2["quantite"], 5.0)
        self.assertEqual(item2["prix_unitaire"], 2500.0)

        # 4. Interrupteur va-et-vient x 8
        item5 = items[5]
        self.assertEqual(item5["quantite"], 8.0)

    def test_08_rotation_and_exif_support(self):
        """Vérifie la prise en compte de la rotation utilisateur (photo prise de côté redressée via rotation)."""
        img = Image.new("RGB", (400, 100), color=(255, 255, 255))
        d = ImageDraw.Draw(img)
        d.text((20, 20), "Interrupteur simple 10 1700", fill=(0, 0, 0))

        # Simuler une photo prise à 90° (sens anti-horaire)
        sideways = img.rotate(90, expand=True)
        buf = BytesIO()
        sideways.save(buf, format="PNG")
        sideways_bytes = buf.getvalue()

        # Analyse avec redressement horaire rotation=90
        res = invoice_scanner.scan_invoice_image(sideways_bytes, mime_type="image/png", force_engine="ocr", rotation=90)
        self.assertEqual(res["status"], "ok")
        self.assertGreaterEqual(len(res["articles"]), 1)
        self.assertEqual(res["articles"][0]["article_id"], "ART-001")

    def test_09_multiple_new_items_in_single_batch(self):
        """Vérifie que deux articles inédits dans le même bon de livraison reçoivent des IDs incrémentaux distincts."""
        items = [
            {
                "article_id": "NEW",
                "designation": "Brouette Renforcée Chantier 90L",
                "categorie": "Gros Œuvre & Maçonnerie",
                "quantite": 2.0,
                "prix_unitaire": 25000.0,
                "unite": "Pièce"
            },
            {
                "article_id": "NEW",
                "designation": "Pelle Ronde Emmanchée 110cm",
                "categorie": "Quincaillerie & Matériaux",
                "quantite": 6.0,
                "prix_unitaire": 3500.0,
                "unite": "Pièce"
            }
        ]
        res = database.receive_invoice_batch(
            fournisseur="Grossiste BTP Rufisque",
            numero_facture="BATCH-NEW-2026",
            items=items
        )
        self.assertEqual(res["status"], "ok")
        self.assertEqual(len(res["nouveaux_articles"]), 2)
        id1 = res["nouveaux_articles"][0]["id"]
        id2 = res["nouveaux_articles"][1]["id"]
        self.assertNotEqual(id1, id2, "Les deux nouveaux articles doivent avoir des IDs distincts")
        num1 = int(id1.split("-")[1])
        num2 = int(id2.split("-")[1])
        self.assertEqual(num2, num1 + 1)


if __name__ == "__main__":
    unittest.main()
