"""
Tests automatisés pour la génération et le téléchargement des Factures PDF - DIADJI FAMILY.
"""

import unittest
import os
import json
import urllib.request
import threading
import time
import sqlite3
import pdf_generator
import database
import server


class TestInvoicePDF(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Initialiser un serveur de test sur le port 8092
        cls.port = 8092
        cls.server = server.ThreadingHTTPServer(("127.0.0.1", cls.port), server.MagasinRequestHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        time.sleep(0.3)

        # Créer une vente de test dans la base
        database.init_db()
        conn = database.get_db_connection()
        cur = conn.cursor()
        
        # Insérer la vente exacte du client
        cls.test_ticket = "TK-20261031-0001"
        cur.execute("DELETE FROM lignes_vente WHERE vente_id IN (SELECT id FROM ventes WHERE numero_ticket = ?)", (cls.test_ticket,))
        cur.execute("DELETE FROM ventes WHERE numero_ticket = ?", (cls.test_ticket,))
        
        cur.execute("""
        INSERT INTO ventes (numero_ticket, date_vente, montant_total, remise, montant_net, montant_verse, monnaie_rendue, mode_paiement, nom_client, telephone_client, statut)
        VALUES (?, '2026-10-31 10:48:01', 1700, 100, 1600, 1700, 100, 'Espèces', 'Ousmane', '76 128 10 65', 'VALIDE')
        """, (cls.test_ticket,))
        vente_id = cur.lastrowid

        cur.execute("""
        INSERT INTO lignes_vente (vente_id, article_id, nom_article, quantite, prix_unitaire, total_ligne)
        VALUES (?, 'ART-006', 'Interrupteur simple', 1, 1700, 1700)
        """, (vente_id,))

        conn.commit()
        conn.close()

    @classmethod
    def tearDownClass(cls):
        # Nettoyer la vente de test
        conn = database.get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM lignes_vente WHERE vente_id IN (SELECT id FROM ventes WHERE numero_ticket = ?)", (cls.test_ticket,))
        cur.execute("DELETE FROM ventes WHERE numero_ticket = ?", (cls.test_ticket,))
        conn.commit()
        conn.close()

        cls.server.shutdown()
        cls.server.server_close()

    def test_01_pdf_generator_creates_valid_pdf_bytes(self):
        sale = database.get_sale_by_ticket(self.test_ticket)
        self.assertIsNotNone(sale)
        self.assertEqual(sale['nom_client'], 'Ousmane')

        pdf_bytes = pdf_generator.generate_invoice_pdf(sale)
        self.assertIsInstance(pdf_bytes, bytes)
        self.assertGreater(len(pdf_bytes), 1000)
        self.assertTrue(pdf_bytes.startswith(b"%PDF-"))

    def test_02_api_ventes_pdf_endpoint(self):
        url = f"http://127.0.0.1:{self.port}/api/ventes/{self.test_ticket}/pdf"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            self.assertEqual(resp.headers.get("Content-Type"), "application/pdf")
            disp = resp.headers.get("Content-Disposition")
            self.assertIn("inline", disp)
            self.assertIn("Facture_DIADJI_FAMILY_TK-20261031-0001.pdf", disp)
            
            content = resp.read()
            self.assertTrue(content.startswith(b"%PDF-"))
            self.assertGreater(len(content), 2000)

    def test_03_api_ventes_pdf_404_for_unknown_ticket(self):
        url = f"http://127.0.0.1:{self.port}/api/ventes/TK-INEXISTANT-9999/pdf"
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(url)
        self.assertEqual(ctx.exception.code, 404)

    def test_04_html_contains_pdf_buttons_and_handlers(self):
        with open("app_ui.html", "r", encoding="utf-8") as f:
            html = f.read()

        # Modal ticket button
        self.assertIn("downloadActiveTicketPDF()", html)
        self.assertIn("Facture PDF", html)

        # Sales history table button
        self.assertIn("downloadTicketPDF('${s.numero_ticket}')", html)

        # JS functions
        self.assertIn("function downloadActiveTicketPDF()", html)
        self.assertIn("function downloadTicketPDF(ticketNum)", html)
        self.assertIn("function formatTicketForWhatsApp(ticket)", html)


if __name__ == "__main__":
    unittest.main()
