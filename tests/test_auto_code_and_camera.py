"""
Tests unitaires et d'intégration pour :
1. La génération automatique des codes d'articles (ART-XXX).
2. L'interface et les correctifs de flux vidéo de la caméra scanner.
"""

import unittest
import json
import urllib.request
import threading
import time
import os
import re

import database
import server


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if os.path.basename(os.path.dirname(os.path.abspath(__file__))) == "tests" else os.path.dirname(os.path.abspath(__file__))


class TestAutoCodeAndCamera(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Initialiser la base si nécessaire
        database.init_db()

        # Démarrer le serveur HTTP de test sur un port dédié
        cls.port = 8092
        cls.server = server.ThreadingHTTPServer(("127.0.0.1", cls.port), server.MagasinRequestHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        time.sleep(0.5)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_01_database_get_next_article_id_single(self):
        next_id = database.get_next_article_id()
        self.assertTrue(bool(re.match(r"^ART-\d{3,}$", next_id)), f"Format de code invalide : {next_id}")

        # Vérifier que ce code n'existe pas déjà dans la base
        conn = database.get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id FROM articles WHERE id = ?", (next_id,))
        row = cur.fetchone()
        conn.close()
        self.assertIsNone(row, f"Le code calculé {next_id} existe déjà dans la base !")

    def test_02_database_get_next_article_id_batch(self):
        codes = database.get_next_article_id(count=5)
        self.assertIsInstance(codes, list)
        self.assertEqual(len(codes), 5)
        self.assertEqual(len(set(codes)), 5, "Les codes générés doivent être strictement uniques !")

        # Vérifier la séquence consécutive
        nums = [int(c.split("-")[1]) for c in codes]
        for i in range(len(nums) - 1):
            self.assertEqual(nums[i + 1], nums[i] + 1, "La séquence de codes doit être consécutive")

    def test_03_create_article_with_auto_id(self):
        # 1. Test avec id None / vide
        data1 = {
            "id": "",
            "nom": "Disjoncteur Test Auto Code 1",
            "categorie": "Protection & Tableaux",
            "prix_vente": 4500
        }
        res1 = database.create_article(data1)
        next_code1 = database.get_next_article_id()
        # Le dernier inséré doit être préfixé par ART-
        conn = database.get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, nom FROM articles WHERE nom = ?", (data1["nom"],))
        art1 = cur.fetchone()
        self.assertIsNotNone(art1)
        self.assertTrue(art1["id"].startswith("ART-"))

        # 2. Test avec id = 'AUTO'
        data2 = {
            "id": "AUTO",
            "nom": "Disjoncteur Test Auto Code 2",
            "categorie": "Protection & Tableaux",
            "prix_vente": 5500
        }
        database.create_article(data2)
        cur.execute("SELECT id, nom FROM articles WHERE nom = ?", (data2["nom"],))
        art2 = cur.fetchone()
        self.assertIsNotNone(art2)
        self.assertTrue(art2["id"].startswith("ART-"))
        self.assertNotEqual(art1["id"], art2["id"])

        # Nettoyage des articles de test
        cur.execute("DELETE FROM mouvements_stock WHERE article_id IN (?, ?)", (art1["id"], art2["id"]))
        cur.execute("DELETE FROM articles WHERE id IN (?, ?)", (art1["id"], art2["id"]))
        conn.commit()
        conn.close()

    def test_04_http_api_next_code(self):
        url = f"http://127.0.0.1:{self.port}/api/articles/next-code"
        with urllib.request.urlopen(url) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertTrue(data.get("success"))
            self.assertTrue(data.get("next_code").startswith("ART-"))
            self.assertEqual(data.get("code"), data.get("next_code"))

    def test_05_http_api_next_code_batch(self):
        url = f"http://127.0.0.1:{self.port}/api/articles/next-code?count=3"
        with urllib.request.urlopen(url) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertTrue(data.get("success"))
            self.assertEqual(data.get("count"), 3)
            self.assertEqual(len(data.get("codes")), 3)

    def test_06_http_api_next_id_alias(self):
        url = f"http://127.0.0.1:{self.port}/api/articles/next-id"
        with urllib.request.urlopen(url) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertTrue(data.get("next_code").startswith("ART-"))

    def test_07_http_api_single_article_regression(self):
        # Vérifier que /api/articles/{id} fonctionne toujours correctement
        url = f"http://127.0.0.1:{self.port}/api/articles/ART-001"
        with urllib.request.urlopen(url) as resp:
            self.assertEqual(resp.status, 200)
            art = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(art.get("id"), "ART-001")

        # Vérifier 404 pour un id inexistant
        url_404 = f"http://127.0.0.1:{self.port}/api/articles/ART-999999"
        with self.assertRaises(urllib.error.HTTPError) as cm:
            urllib.request.urlopen(url_404)
        self.assertEqual(cm.exception.code, 404)

    def test_08_receive_invoice_batch_with_auto_codes(self):
        # Tester l'entrée d'articles inédits avec génération automatique de codes
        items = [
            {
                "article_id": "NEW",
                "designation": "Interrupteur Inédit Test 1",
                "categorie": "Électricité - Appareillage",
                "unite": "Pièce",
                "quantite": 5,
                "prix_unitaire": 1200,
                "prix_vente": 1500
            },
            {
                "article_id": "NEW",
                "designation": "Interrupteur Inédit Test 2",
                "categorie": "Électricité - Appareillage",
                "unite": "Pièce",
                "quantite": 10,
                "prix_unitaire": 2000,
                "prix_vente": 2600
            }
        ]
        res = database.receive_invoice_batch(
            fournisseur="Fournisseur Test Auto Code",
            numero_facture="TEST-AUTO-CODE-01",
            items=items
        )
        self.assertEqual(res["articles_recus"], 2)
        self.assertEqual(len(res["nouveaux_articles"]), 2)
        id1 = res["nouveaux_articles"][0]["id"]
        id2 = res["nouveaux_articles"][1]["id"]
        self.assertTrue(id1.startswith("ART-"))
        self.assertTrue(id2.startswith("ART-"))
        self.assertNotEqual(id1, id2)

        # Nettoyage
        conn = database.get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM lignes_commande WHERE commande_id = ?", (res["commande_id"],))
        cur.execute("DELETE FROM commandes_fournisseurs WHERE id = ?", (res["commande_id"],))
        cur.execute("DELETE FROM mouvements_stock WHERE article_id IN (?, ?)", (id1, id2))
        cur.execute("DELETE FROM articles WHERE id IN (?, ?)", (id1, id2))
        conn.commit()
        conn.close()

    def test_09_app_ui_html_camera_and_autocode_elements(self):
        ui_path = os.path.join(ROOT_DIR, "app_ui.html")
        self.assertTrue(os.path.isfile(ui_path))
        with open(ui_path, "r", encoding="utf-8") as f:
            html = f.read()

        # 1. Vérification des attributs indispensables de l'élément video
        self.assertIn('id="camera-video-feed"', html)
        self.assertIn("autoplay", html)
        self.assertIn("playsinline", html)
        self.assertIn("muted", html)

        # 2. Vérification des overlays d'état
        self.assertIn('id="camera-loading-overlay"', html)
        self.assertIn("Connexion à la caméra en cours...", html)
        self.assertIn('id="camera-error-overlay"', html)
        self.assertIn('id="camera-select-container"', html)
        self.assertIn('id="camera-device-select"', html)

        # 3. Vérification des fonctions JavaScript de caméra
        self.assertIn("video.play()", html)
        self.assertIn("video.onloadedmetadata", html)
        self.assertIn("facingMode", html)
        self.assertIn("enumerateDevices", html)
        self.assertIn("populateCameraDevices", html)
        self.assertIn("changeCameraDevice", html)
        self.assertIn("handleCameraError", html)

        # 4. Vérification de l'auto-génération des codes d'articles
        self.assertIn('id="form-art-id-badge"', html)
        self.assertIn("/api/articles/next-code", html)
        self.assertIn("assignAutoCodesToScanArticles", html)
        print("✓ Tous les éléments HTML et scripts JS caméra et auto-code sont présents et conformes !")

    def test_10_database_boundary_count_zero_and_negative(self):
        # Vérifier que count=0 ou négatif ne provoque pas d'IndexError
        res0 = database.get_next_article_id(count=0)
        self.assertEqual(res0, [])
        res_neg = database.get_next_article_id(count=-5)
        self.assertEqual(res_neg, [])

    def test_11_create_article_collision_retry(self):
        # Simuler un scénario de concurrence où le code suggéré a déjà été pris
        next_code = database.get_next_article_id()
        # 1. Créer le premier article avec ce code
        art1 = database.create_article({
            "id": next_code,
            "nom": "Article Concurrence 1",
            "prix_vente": 1000
        })
        self.assertEqual(art1["id"], next_code)

        # 2. Créer le deuxième article en tentant d'insérer le même next_code (collision)
        art2 = database.create_article({
            "id": next_code,
            "nom": "Article Concurrence 2",
            "prix_vente": 2000
        })
        # L'insertion doit réussir en ayant régénéré un ID sans crash sqlite3.IntegrityError
        self.assertNotEqual(art2["id"], art1["id"])
        self.assertTrue(art2["id"].startswith("ART-"))

        # Nettoyage
        conn = database.get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM mouvements_stock WHERE article_id IN (?, ?)", (art1["id"], art2["id"]))
        cur.execute("DELETE FROM articles WHERE id IN (?, ?)", (art1["id"], art2["id"]))
        conn.commit()
        conn.close()

    def test_12_camera_pc_friendly_constraints_and_recovery(self):
        ui_path = os.path.join(ROOT_DIR, "app_ui.html")
        with open(ui_path, "r", encoding="utf-8") as f:
            html = f.read()

        # Vérifier l'adaptation PC vs Mobile (ne pas forcer facingMode environment sur PC)
        self.assertIn("isMobileDevice", html)
        self.assertIn("getCameraConstraints", html)
        self.assertIn("getUserMediaWithTimeout", html)

        # Vérifier la présence de l'overlay de reprise et des classes de dimensionnement
        self.assertIn('id="camera-clicktoplay-overlay"', html)
        self.assertIn("resumeCameraPlayback", html)
        self.assertIn("min-h-[260px]", html)

        # Vérifier la mémorisation de l'ID réel de la caméra active
        self.assertIn("CURRENT_CAMERA_DEVICE_ID", html)

    def test_13_app_launcher_browser_flags(self):
        app_path = os.path.join(ROOT_DIR, "app.py")
        with open(app_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Vérifier que les flags essentiels pour la webcam sous Windows en mode application sont présents
        self.assertIn("--use-fake-ui-for-media-stream", content)
        self.assertIn("--autoplay-policy=no-user-gesture-required", content)
        self.assertIn("--unsafely-treat-insecure-origin-as-secure", content)

    def test_14_ajouter_ligne_manuelle_auto_code(self):
        ui_path = os.path.join(ROOT_DIR, "app_ui.html")
        with open(ui_path, "r", encoding="utf-8") as f:
            html = f.read()

        # Vérifier que la fonction manuelle déclenche l'attribution auto de codes
        self.assertIn("async function ajouterLigneManuelleScan()", html)
        self.assertIn("await assignAutoCodesToScanArticles()", html)
        # Vérifier le bouton de rafraîchissement manuel
        self.assertIn("refreshNextArticleCode", html)


if __name__ == "__main__":
    unittest.main()
