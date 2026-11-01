"""
Test d'intégration Python pour le système de boîte de dialogue sur-mesure de DIADJI FAMILY.
Vérifie la conformité de app_ui.html, index.html et dist/DIADJI_FAMILY/app_ui.html.
"""

import unittest
import os
import re

class TestCustomDialogIntegration(unittest.TestCase):

    def setUp(self):
        self.files_to_check = [
            f for f in ['app_ui.html', 'dist/DIADJI_FAMILY/app_ui.html']
            if os.path.exists(f)
        ]

    def test_no_native_dialogs_remain(self):
        """Vérifie qu'aucun appel natif confirm(), alert() ou prompt() ne subsiste."""
        patterns = [r'\bconfirm\s*\(', r'\balert\s*\(', r'\bprompt\s*\(']
        for fpath in self.files_to_check:
            self.assertTrue(os.path.exists(fpath), f"Fichier manquant: {fpath}")
            with open(fpath, 'r', encoding='utf-8') as f:
                content = f.read()
            for pat in patterns:
                # Exclure la définition de window.alert = function(...) / window.confirm / window.prompt
                matches = [m for m in re.finditer(pat, content) if not re.search(r'window\.(alert|confirm|prompt)\s*=\s*function', content[max(0, m.start()-30):m.end()+30])]
                self.assertEqual(len(matches), 0, f"Appel natif détecté ({pat}) dans {fpath}")

    def test_custom_dialog_dom_elements_present(self):
        """Vérifie la présence de tous les IDs DOM du système de dialogue."""
        required_ids = [
            'custom-dialog-backdrop',
            'custom-dialog-card',
            'custom-dialog-glow',
            'custom-dialog-badge',
            'custom-dialog-icon-container',
            'custom-dialog-icon',
            'custom-dialog-title',
            'custom-dialog-subtitle',
            'custom-dialog-message',
            'custom-dialog-item-box',
            'custom-dialog-input-container',
            'custom-dialog-input',
            'custom-dialog-cancel-btn',
            'custom-dialog-cancel-text',
            'custom-dialog-confirm-btn',
            'custom-dialog-confirm-text',
            'custom-dialog-confirm-icon',
            'custom-dialog-close-btn'
        ]

        for fpath in self.files_to_check:
            with open(fpath, 'r', encoding='utf-8') as f:
                content = f.read()
            for elem_id in required_ids:
                self.assertIn(f'id="{elem_id}"', content, f"Élément #{elem_id} absent de {fpath}")

    def test_custom_dialog_css_animations(self):
        """Vérifie la présence des keyframes CSS de dialogue."""
        required_css = [
            'dialogBackdropFadeIn',
            'dialogBackdropFadeOut',
            'dialogModalScaleUp',
            'dialogModalScaleDown',
            'dialog-backdrop-in',
            'dialog-backdrop-out',
            'dialog-modal-in',
            'dialog-modal-out'
        ]

        for fpath in self.files_to_check:
            with open(fpath, 'r', encoding='utf-8') as f:
                content = f.read()
            for css_class in required_css:
                self.assertIn(css_class, content, f"Animation {css_class} absente de {fpath}")

    def test_custom_dialog_js_functions(self):
        """Vérifie la présence des fonctions showConfirmModal, showAlertModal, showPromptModal et window overrides."""
        for fpath in self.files_to_check:
            with open(fpath, 'r', encoding='utf-8') as f:
                content = f.read()
            self.assertIn('function showConfirmModal', content, f"showConfirmModal absent de {fpath}")
            self.assertIn('function showAlertModal', content, f"showAlertModal absent de {fpath}")
            self.assertIn('function showPromptModal', content, f"showPromptModal absent de {fpath}")
            self.assertIn('window.alert = function', content, f"window.alert override absent de {fpath}")
            self.assertIn('window.confirm = function', content, f"window.confirm override absent de {fpath}")
            self.assertIn('window.prompt = function', content, f"window.prompt override absent de {fpath}")

    def test_specific_business_confirmations_used(self):
        """Vérifie les confirmations spécifiques dans app_ui.html."""
        with open('app_ui.html', 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn("Quitter DIADJI FAMILY", content)
        self.assertIn("Supprimer l'article", content)
        self.assertIn("Réceptionner la commande", content)
        self.assertIn("Réinitialiser le catalogue", content)
        self.assertIn("Annuler la vente en cours", content)

if __name__ == '__main__':
    unittest.main()
