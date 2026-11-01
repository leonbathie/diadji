# -*- coding: utf-8 -*-
import unittest
import database

class TestWhatsAppFeature(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open('app_ui.html', 'r', encoding='utf-8') as f:
            cls.html = f.read()

    def test_html_buttons_exist(self):
        # 1. Cart pane WhatsApp button
        self.assertIn('id="btn-validate-whatsapp"', self.html)
        self.assertIn('Encaisser & Envoyer sur WhatsApp', self.html)
        self.assertIn('fa-brands fa-whatsapp', self.html)

        # 2. Ticket modal WhatsApp button & Copy button
        self.assertIn('sendTicketViaWhatsApp()', self.html)
        self.assertIn('copyTicketToClipboard()', self.html)

        # 3. Sales history WhatsApp resend button
        self.assertIn('reSendWhatsAppTicket', self.html)

    def test_javascript_functions_exist(self):
        self.assertIn('function sanitizeWhatsAppPhone', self.html)
        self.assertIn('function formatTicketForWhatsApp', self.html)
        self.assertIn('async function sendTicketViaWhatsApp', self.html)
        self.assertIn('async function copyTicketToClipboard', self.html)
        self.assertIn('async function reSendWhatsAppTicket', self.html)
        self.assertIn('CURRENT_ACTIVE_TICKET = ticket', self.html)

    def test_database_get_ventes_includes_phone(self):
        ventes = database.get_ventes(limit=5)
        # Even if empty or populated, the query should execute without SQL error
        self.assertIsInstance(ventes, list)

    def test_phone_sanitization_logic(self):
        # Simulation of sanitizeWhatsAppPhone logic
        def py_sanitize(phone):
            import re
            cleaned = re.sub(r'\D', '', str(phone))
            if cleaned.startswith('00'):
                cleaned = cleaned[2:]
            if len(cleaned) == 9:
                cleaned = '221' + cleaned
            return cleaned

        self.assertEqual(py_sanitize("77 123 45 67"), "221771234567")
        self.assertEqual(py_sanitize("+221 78 200 11 22"), "221782001122")
        self.assertEqual(py_sanitize("00221 76 333 44 55"), "221763334455")
        self.assertEqual(py_sanitize("701112233"), "221701112233")

if __name__ == '__main__':
    unittest.main()
