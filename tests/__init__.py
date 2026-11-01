import sys
import os

# Toujours ajouter la racine du projet DIADJI FAMILY au sys.path
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
