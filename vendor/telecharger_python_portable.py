"""
Script utilitaire pour embarquer un environnement Python portable autonome (Python Embeddable)
dans le dossier vendor/python_embed/ pour Windows 64-bit.

Ce script permet de garantir une portabilité 100% hors-ligne même pour les utilisateurs
qui ne disposent pas de Python installé sur leur système.
"""

import os
import sys

# Reconfiguration UTF-8 sécurisée pour Windows cmd/powershell
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import urllib.request
import zipfile
import shutil
import subprocess

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VENDOR_DIR = os.path.join(BASE_DIR, "vendor")
EMBED_DIR = os.path.join(VENDOR_DIR, "python_embed")
WHEELS_DIR = os.path.join(VENDOR_DIR, "wheels")

PYTHON_VERSION = "3.13.2"
PYTHON_ZIP_URL = f"https://www.python.org/ftp/python/{PYTHON_VERSION}/python-{PYTHON_VERSION}-embed-amd64.zip"
TCLTK_MSI_URL = f"https://www.python.org/ftp/python/{PYTHON_VERSION}/amd64/tcltk.msi"


def setup_portable_python():
    print("=" * 70)
    print("      CONFIGURATION DE PYTHON PORTABLE EMBARQUÉ (WINDOWS 64-BIT)")
    print("=" * 70)
    print(f"Cible : {EMBED_DIR}")
    print()

    has_python = os.path.isfile(os.path.join(EMBED_DIR, "python.exe"))
    zip_dest = os.path.join(VENDOR_DIR, f"python-{PYTHON_VERSION}-embed-amd64.zip")
    msi_dest = os.path.join(VENDOR_DIR, f"tcltk-{PYTHON_VERSION}.msi")

    try:
        if not has_python:
            os.makedirs(EMBED_DIR, exist_ok=True)
            print(f"[*] Téléchargement de Python {PYTHON_VERSION} Embeddable depuis python.org...")
            urllib.request.urlretrieve(PYTHON_ZIP_URL, zip_dest)
            print("[OK] Téléchargement terminé.")

            print(f"[*] Extraction vers {EMBED_DIR}...")
            with zipfile.ZipFile(zip_dest, "r") as zf:
                zf.extractall(EMBED_DIR)
            print("[OK] Extraction terminée.")
        else:
            print(f"[OK] Fichiers de base Python déjà présents dans {EMBED_DIR}.")

        # Configuration complète du fichier ._pth (accès Lib, site-packages, projet racine)
        for f in os.listdir(EMBED_DIR):
            if f.endswith("._pth"):
                pth_file = os.path.join(EMBED_DIR, f)
                py_zip = f.replace("._pth", ".zip")
                pth_content = f"{py_zip}\n.\nLib\nLib/site-packages\n..\n..\\..\nimport site\n"
                with open(pth_file, "w", encoding="utf-8") as pf:
                    pf.write(pth_content)
                print(f"[OK] Configuration des chemins d'importation dans {f}.")

        # Création des dossiers Lib et site-packages
        site_packages = os.path.join(EMBED_DIR, "Lib", "site-packages")
        os.makedirs(site_packages, exist_ok=True)

        # Installation des wheels locales directement dans Lib/site-packages
        if os.path.isdir(WHEELS_DIR):
            for wheel_name in os.listdir(WHEELS_DIR):
                if wheel_name.endswith(".whl"):
                    wheel_path = os.path.join(WHEELS_DIR, wheel_name)
                    print(f"[*] Extraction de la dépendance {wheel_name} dans site-packages...")
                    with zipfile.ZipFile(wheel_path, "r") as wzf:
                        wzf.extractall(site_packages)
            print("[OK] Toutes les wheels locales ont été injectées dans Python Portable.")

        # Configuration de Tkinter / Tcl/Tk si absent
        has_tkinter = os.path.isfile(os.path.join(EMBED_DIR, "_tkinter.pyd"))
        if not has_tkinter:
            try:
                print("[*] Téléchargement et intégration du support Tcl/Tk (Tkinter)...")
                urllib.request.urlretrieve(TCLTK_MSI_URL, msi_dest)
                extracted_msi = os.path.join(VENDOR_DIR, "tcltk_extracted")
                os.makedirs(extracted_msi, exist_ok=True)
                subprocess.run(
                    ["msiexec", "/a", os.path.abspath(msi_dest), "/qb", f"TARGETDIR={os.path.abspath(extracted_msi)}"],
                    check=True,
                    capture_output=True
                )
                # Copie des DLLs (_tkinter.pyd, tcl86t.dll, tk86t.dll)
                dlls_src = os.path.join(extracted_msi, "DLLs")
                if os.path.isdir(dlls_src):
                    for dll in os.listdir(dlls_src):
                        shutil.copy2(os.path.join(dlls_src, dll), EMBED_DIR)
                # Copie du module Lib/tkinter
                tk_lib_src = os.path.join(extracted_msi, "Lib", "tkinter")
                if os.path.isdir(tk_lib_src):
                    shutil.copytree(tk_lib_src, os.path.join(EMBED_DIR, "Lib", "tkinter"), dirs_exist_ok=True)
                # Copie des bibliothèques tcl/
                tcl_src = os.path.join(extracted_msi, "tcl")
                if os.path.isdir(tcl_src):
                    shutil.copytree(tcl_src, os.path.join(EMBED_DIR, "tcl"), dirs_exist_ok=True)
                # Nettoyage
                shutil.rmtree(extracted_msi, ignore_errors=True)
                if os.path.exists(msi_dest):
                    os.remove(msi_dest)
                print("[OK] Support graphique Tkinter & Tcl/Tk intégré avec succès.")
            except Exception as tk_err:
                print(f"[NOTE] Installation de Tkinter ignorée ou partielle ({tk_err}). L'interface Web reste 100% opérationnelle.")
                if os.path.exists(msi_dest):
                    try:
                        os.remove(msi_dest)
                    except Exception:
                        pass

        # Nettoyage de l'archive temporaire
        if os.path.exists(zip_dest):
            os.remove(zip_dest)

        print()
        print("=" * 70)
        print("  [OK] PYTHON PORTABLE PRÊT : vendor/python_embed/python.exe")
        print("  L'application et les lanceurs .bat fonctionnent désormais")
        print("  sur n'importe quel PC Windows sans aucune installation préalable.")
        print("=" * 70)

    except Exception as e:
        print(f"[ERREUR] Impossible de configurer Python portable : {e}")
        if os.path.exists(zip_dest):
            try:
                os.remove(zip_dest)
            except Exception:
                pass


if __name__ == "__main__":
    setup_portable_python()
