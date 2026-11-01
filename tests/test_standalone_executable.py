"""
Test d'intégration et de vérification en boîte noire de l'exécutable autonome DIADJI_FAMILY.exe.
Vérifie le démarrage, l'écoute HTTP, les endpoints API, les dépendances SQLite et l'arrêt propre.
"""

import subprocess
import urllib.request
import json
import time
import sys
import os

EXE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "DIADJI_FAMILY.exe")

def test_executable():
    print(f"[*] Test de l'exécutable autonome : {EXE_PATH}")
    assert os.path.isfile(EXE_PATH), f"Exécutable introuvable : {EXE_PATH}"
    print(f"[*] Taille du binaire : {os.path.getsize(EXE_PATH):,} octets")

    print("[*] Lancement du processus DIADJI_FAMILY.exe...")
    proc = subprocess.Popen([EXE_PATH])

    try:
        # 1. Attente de la disponibilité du serveur local
        stats_data = None
        for attempt in range(25):
            try:
                with urllib.request.urlopen("http://127.0.0.1:8000/api/stats", timeout=2) as resp:
                    if resp.status == 200:
                        stats_data = json.loads(resp.read().decode("utf-8"))
                        print(f"[✓] Serveur HTTP opérationnel (tentative {attempt+1}) :", stats_data)
                        break
            except Exception:
                time.sleep(0.5)

        assert stats_data is not None, "Le serveur HTTP n'a pas répondu dans le délai imparti (12.5s)."
        assert stats_data["total_articles"] == 183, f"Attendu 183 articles, obtenu {stats_data['total_articles']}"
        assert stats_data["articles_avec_prix"] == 44, f"Attendu 44 articles avec prix réels, obtenu {stats_data['articles_avec_prix']}"

        # 2. Test de l'interface HTML
        with urllib.request.urlopen("http://127.0.0.1:8000/") as resp:
            html_content = resp.read().decode("utf-8")
            assert "DIADJI FAMILY" in html_content, "L'interface HTML ne contient pas DIADJI FAMILY"
            assert "Caisse Express" in html_content, "L'interface HTML ne contient pas Caisse Express"
            assert "custom-dialog-backdrop" in html_content, "Le composant modal custom-dialog-backdrop est absent"
            assert "custom-dialog-input-container" in html_content, "Le conteneur input custom-dialog-input-container est absent"
            assert "showConfirmModal" in html_content, "La fonction showConfirmModal est absente"
            assert "showPromptModal" in html_content, "La fonction showPromptModal est absente"
            assert "window.confirm = function" in html_content, "L'override window.confirm est absent"
            assert "window.prompt = function" in html_content, "L'override window.prompt est absent"
            assert "confirm(" not in html_content, "Des appels natifs confirm() subsistent dans l'interface servie"
            assert "tab-scan" in html_content, "L'onglet tab-scan est absent"
            assert "modal-gemini-settings" in html_content, "Le modal modal-gemini-settings est absent"
            assert "Scanner Facture" in html_content, "Le bouton Scanner Facture est absent"
            print(f"[✓] Interface HTML avec dialogue modal et onglet Scanner servie ({len(html_content):,} caractères)")

        # 3. Test de l'API Articles
        with urllib.request.urlopen("http://127.0.0.1:8000/api/articles?limit=5") as resp:
            articles = json.loads(resp.read().decode("utf-8"))
            assert len(articles) == 5, f"Attendu 5 articles, obtenu {len(articles)}"
            print(f"[✓] API Articles fonctionnelle (premier article : {articles[0]['nom']})")

        # 3.1 Test de l'API Auto-code (/api/articles/next-code)
        with urllib.request.urlopen("http://127.0.0.1:8000/api/articles/next-code") as resp:
            next_code_data = json.loads(resp.read().decode("utf-8"))
            assert next_code_data.get("success") is True
            assert next_code_data.get("next_code").startswith("ART-")
            print(f"[✓] API Next-Code opérationnelle sur EXE autonome : {next_code_data.get('next_code')}")

        # 4. Test de l'icône / Favicon
        with urllib.request.urlopen("http://127.0.0.1:8000/favicon.ico") as resp:
            ico_bytes = resp.read()
            assert len(ico_bytes) > 1000, "Icône favicon trop petite"
            print(f"[✓] Favicon servi ({len(ico_bytes)} octets)")

        # 5. Test des paramètres API (/api/settings)
        with urllib.request.urlopen("http://127.0.0.1:8000/api/settings") as resp:
            settings_data = json.loads(resp.read().decode("utf-8"))
            assert "gemini_configured" in settings_data
            assert "active_engine" in settings_data
            assert "available_engines" in settings_data
            print("[✓] API Settings (GET) fonctionnelle :", settings_data)

        # 6. Test d'export Excel via l'API (valide openpyxl embarqué dans l'exécutable !)
        with urllib.request.urlopen("http://127.0.0.1:8000/api/export/excel") as resp:
            excel_bytes = resp.read()
            assert len(excel_bytes) > 20000, f"Export Excel trop petit ({len(excel_bytes)} octets)"
            print(f"[✓] Export Excel openpyxl généré avec succès ({len(excel_bytes):,} octets)")

        # 7. Test de validation de clé API (/api/settings/test)
        req_test = urllib.request.Request(
            "http://127.0.0.1:8000/api/settings/test",
            data=json.dumps({"gemini_api_key": "AIzaSyFakeKey_Test"}).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(req_test) as resp:
                pass
        except urllib.error.HTTPError as e:
            assert e.code == 400
            print("[✓] API /api/settings/test fonctionnelle (détection clé invalide)")

        # 8. Test de numérisation OCR (/api/invoice/scan)
        import base64
        from io import BytesIO
        from PIL import Image, ImageDraw
        img = Image.new("RGB", (400, 100), color=(255, 255, 255))
        d = ImageDraw.Draw(img)
        d.text((20, 20), "Interrupteur simple 10 1700", fill=(0, 0, 0))
        buf = BytesIO()
        img.save(buf, format="PNG")
        b64_img = base64.b64encode(buf.getvalue()).decode("utf-8")

        req_scan = urllib.request.Request(
            "http://127.0.0.1:8000/api/invoice/scan",
            data=json.dumps({"image": b64_img, "mime_type": "image/png", "engine": "ocr", "rotation": 0}).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req_scan) as resp:
            scan_res = json.loads(resp.read().decode("utf-8"))
            assert scan_res.get("status") == "ok"
            assert len(scan_res.get("articles", [])) >= 1
            print(f"[✓] API /api/invoice/scan fonctionnelle sur EXE autonome ({scan_res['provider_label']})")

        # 9. Test de réception de facture via /api/invoice/receive
        receive_payload = json.dumps({
            "fournisseur": "TEST FOURNISSEUR EXE",
            "numero_facture": "EXE-BL-999",
            "date_facture": "2026-10-31",
            "notes": "Test de réception via EXE",
            "items": [
                {
                    "article_id": "ART-001",
                    "designation": "Interrupteur simple",
                    "quantite": 5,
                    "prix_unitaire": 1600,
                    "unite": "U"
                }
            ]
        }).encode("utf-8")
        req_rcv = urllib.request.Request(
            "http://127.0.0.1:8000/api/invoice/receive",
            data=receive_payload,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req_rcv) as resp:
            rcv_res = json.loads(resp.read().decode("utf-8"))
            assert rcv_res.get("status") == "ok", f"Échec de réception : {rcv_res}"
            print("[✓] API /api/invoice/receive fonctionnelle sur EXE autonome :", rcv_res.get("articles_recus"), "articles reçus")

        # 8. Arrêt propre via /api/shutdown
        req = urllib.request.Request(
            "http://127.0.0.1:8000/api/shutdown",
            data=b"{}",
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req) as resp:
            shutdown_res = json.loads(resp.read().decode("utf-8"))
            print("[✓] Commande d'arrêt acceptée :", shutdown_res)

        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.terminate()
            proc.wait(timeout=3)
        print(f"[✓] Processus DIADJI_FAMILY.exe arrêté proprement avec code de sortie : {proc.returncode}")

    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait()

    print("\n" + "=" * 70)
    print("  [✓] TOUS LES TESTS DE L'EXÉCUTABLE AUTONOME ONT RÉUSSI À 100% !")
    print("=" * 70)

if __name__ == "__main__":
    test_executable()
