# Dossier `vendor/` - Dépendances & Portabilité Hors-Ligne

Ce dossier contient toutes les ressources requises pour garantir une **autonomie complète (100% hors-ligne)** du logiciel DIADJI FAMILY sur n'importe quel ordinateur Windows, même sans connexion Internet ni Python installé.

---

## 📁 Contenu du Dossier

- **`wheels/`** :
  - `openpyxl-3.1.5-py2.py3-none-any.whl` : Bibliothèque de manipulation des classeurs Excel.
  - `et_xmlfile-2.0.0-py3-none-any.whl` : Moteur XML pour openpyxl.
  - Ces paquets universels (`none-any`) permettent une installation locale sans connexion via :
    ```cmd
    python -m pip install --no-index --find-links=vendor/wheels -r requirements.txt
    ```
    Ou simplement en double-cliquant sur **`INSTALLER_DEPENDANCES_HORS_LIGNE.bat`**.

- **`telecharger_python_portable.py` / `TELECHARGER_PYTHON_PORTABLE.bat`** :
  - Script permettant de télécharger et d'embarquer l'interpréteur officiel Windows **Python Embeddable** dans `vendor/python_embed/`.
  - Injecte automatiquement les packages de `wheels/` dans l'environnement embarqué.

---

## ⚡ Mode Batteries Included (Exécutable Autonome)

Si vous utilisez les fichiers exécutables compilés :
- **`DIADJI_FAMILY.exe`**
- **`INSTALLATEUR_DIADJI_FAMILY.exe`**

**Aucune étape manuelle n'est requise** : l'interpréteur Python, toutes les DLLs système Windows, openpyxl, et_xmlfile, la base SQLite (`magasin.db`), les modèles HTML (`app_ui.html`) et les icônes officielles sont **100% embarqués dans l'exécutable**.
