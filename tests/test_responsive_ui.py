# -*- coding: utf-8 -*-
import unittest
import os
import re

class TestResponsiveUI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open('app_ui.html', 'r', encoding='utf-8') as f:
            cls.html = f.read()

    def test_css_responsive_utilities(self):
        self.assertIn('.no-scrollbar', self.html)
        self.assertIn('display: none', self.html)
        self.assertIn('pos-responsive-pane', self.html)

    def test_responsive_header(self):
        self.assertIn('min-h-14 sm:min-h-16', self.html)
        self.assertIn('hidden xl:block', self.html)
        self.assertIn('hidden sm:inline', self.html)
        self.assertIn('<span class="hidden sm:inline">Caisse</span>', self.html)
        self.assertIn('<span class="hidden sm:inline">Scanner</span>', self.html)
        self.assertIn('no-scrollbar whitespace-nowrap flex-nowrap', self.html)

    def test_responsive_pos_caisse(self):
        self.assertIn('id="pos-tab-btn-catalog"', self.html)
        self.assertIn('id="pos-tab-btn-cart"', self.html)
        self.assertIn('id="pos-catalog-pane"', self.html)
        self.assertIn('id="pos-cart-pane"', self.html)
        self.assertIn('id="pos-mobile-floating-cart-bar"', self.html)
        self.assertIn('grid grid-cols-3 sm:grid-cols-6 gap-1', self.html)

    def test_responsive_pos_javascript_controller(self):
        self.assertIn('function setPOSMobileView', self.html)
        self.assertIn('function updatePOSMobileViewUI', self.html)
        self.assertIn('window.innerWidth < 1024', self.html)
        self.assertIn("window.addEventListener('resize'", self.html)
        self.assertIn('pos-mobile-floating-total', self.html)

    def test_modals_max_height_and_scroll(self):
        # Modal Article
        self.assertTrue(re.search(r'id="modal-article".+?max-h-\[92vh\] flex flex-col', self.html, re.DOTALL))
        # Modal Stockin
        self.assertTrue(re.search(r'id="modal-stockin".+?max-h-\[92vh\] flex flex-col', self.html, re.DOTALL))
        # Modal Ticket
        self.assertTrue(re.search(r'id="modal-ticket".+?max-h-\[92vh\]', self.html, re.DOTALL))
        # Modal Order
        self.assertTrue(re.search(r'id="modal-order".+?max-h-\[92vh\] flex flex-col', self.html, re.DOTALL))
        # Modal Gemini
        self.assertTrue(re.search(r'id="modal-gemini-settings".+?max-h-\[92vh\] flex flex-col', self.html, re.DOTALL))
        # Modal Camera
        self.assertTrue(re.search(r'id="modal-camera-capture".+?max-h-\[92vh\] flex flex-col', self.html, re.DOTALL))
        # Custom Dialog
        self.assertIn('id="custom-dialog-card"', self.html)
        self.assertIn('max-h-[92vh] overflow-y-auto', self.html)

    def test_tables_whitespace_nowrap(self):
        self.assertIn('whitespace-nowrap', self.html)
        self.assertIn('min-w-[200px]', self.html)

    def test_dist_sync(self):
        dist_path = os.path.join('dist', 'DIADJI_FAMILY', 'app_ui.html')
        self.assertTrue(os.path.exists(dist_path))
        with open(dist_path, 'r', encoding='utf-8') as f:
            dist_html = f.read()
        self.assertEqual(len(self.html), len(dist_html))

if __name__ == '__main__':
    unittest.main()
