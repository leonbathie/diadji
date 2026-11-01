"""
Lanceur unifié de la suite complète de tests - DIADJI FAMILY
"""

import unittest
import sys
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

os.chdir(ROOT)

if __name__ == "__main__":
    print(f"[*] Lancement de la suite de tests DIADJI FAMILY depuis : {ROOT}")
    loader = unittest.TestLoader()
    suite = loader.discover(start_dir=os.path.join(ROOT, "tests"), pattern="test_*.py")
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
