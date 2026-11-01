"""
Programme Principal - DIADJI FAMILY
Logiciel de Caisse & Gestion de Stock avec Base de Données Embarquée SQLite.
"""

import sys
import os

# Garantir que le dossier du script / de l'application est en tête de sys.path
_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if _CURRENT_DIR not in sys.path:
    sys.path.insert(0, _CURRENT_DIR)

# Attachement à la console parente Windows si lancée depuis un terminal (cmd / powershell)
if sys.platform == "win32":
    try:
        import ctypes
        if ctypes.windll.kernel32.AttachConsole(-1):
            if sys.stdout is None or not hasattr(sys.stdout, "write"):
                sys.stdout = open("CONOUT$", "w", encoding="utf-8", errors="replace")
            if sys.stderr is None or not hasattr(sys.stderr, "write"):
                sys.stderr = open("CONOUT$", "w", encoding="utf-8", errors="replace")
    except Exception:
        pass

# Protection si stdout/stderr est None (ex: double-clic sans console sous Windows)
if sys.stdout is None:
    sys.stdout = open(os.devnull, 'w', encoding='utf-8')
if sys.stderr is None:
    sys.stderr = open(os.devnull, 'w', encoding='utf-8')

# Reconfiguration UTF-8 sécurisée pour éviter les crashs cp1252 sur console Windows
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

import subprocess
import threading
import time
import webbrowser
import database
import server

APP_TITLE = "DIADJI FAMILY"
VERSION = "2.0.0"


def find_browser_app_executable():
    """
    Détecte si Microsoft Edge ou Google Chrome est présent sur la machine Windows
    pour ouvrir l'application en mode 'Application Dédiée' (--app) sans barre d'adresse de navigateur.
    """
    candidates = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe"),
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
    ]

    for path in candidates:
        if os.path.isfile(path):
            return path
    return None


def open_application_window(url):
    """
    Ouvre l'application dans une fenêtre de bureau dédiée (mode application)
    ou dans le navigateur par défaut de l'utilisateur.
    """
    browser_exe = find_browser_app_executable()
    if browser_exe:
        try:
            # Lancement en mode fenêtre application autonome native avec autorisations webcam
            # --use-fake-ui-for-media-stream : accorde directement l'accès à la webcam physique sans boîte de dialogue bloquante en mode --app
            # --autoplay-policy=no-user-gesture-required : autorise la lecture vidéo immédiate
            # --unsafely-treat-insecure-origin-as-secure : assure la disponibilité de navigator.mediaDevices
            cmd = [
                browser_exe,
                f"--app={url}",
                "--window-size=1280,840",
                "--window-position=50,50",
                "--use-fake-ui-for-media-stream",
                "--autoplay-policy=no-user-gesture-required",
                f"--unsafely-treat-insecure-origin-as-secure={url}",
            ]
            return subprocess.Popen(cmd)
        except Exception:
            pass

    # Fallback standard vers le navigateur par défaut
    webbrowser.open(url)
    return None


def print_banner(host, port, stats):
    """Affiche une bannière d'information claire dans la console."""
    banner = f"""
================================================================================
                    DIADJI FAMILY - LOGICIEL DE GESTION EMBARQUÉ               
================================================================================
  Version        : {VERSION}
  Entreprise     : DIADJI FAMILY (Dakar, Sénégal)
  Base de Données: SQLite Embarquée (magasin.db)
  Articles       : {stats['total_articles']} références enregistrées
  Prix Authentiq.: {stats['articles_avec_prix']} articles avec prix réels du PDF
  En Rupture     : {stats['en_rupture']} articles
  Stock Faible   : {stats['stock_faible']} articles
  Commandes Cmd. : {stats['commandes_en_cours']} en cours
  Serveur Local  : http://{host}:{port}/
================================================================================
  [OK] L'interface graphique DIADJI FAMILY démarre automatiquement...
  [!] Pour fermer l'application : Fermez la fenêtre ou appuyez sur Ctrl+C.
================================================================================
"""
    print(banner)


def main():
    # 1. Initialiser la base de données SQLite si nécessaire
    print("[1/3] Initialisation de la base de données embarquée SQLite (magasin.db)...")
    database.init_db(force_reseed=False)
    stats = database.get_dashboard_stats()

    # 2. Démarrer le serveur HTTP local
    print("[2/3] Démarrage du serveur applicatif interne...")
    host = "127.0.0.1"
    httpd, port = server.create_server(host=host, start_port=8000)
    app_url = f"http://{host}:{port}/"

    # Thread d'exécution du serveur
    server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    server_thread.start()

    # 3. Ouvrir la fenêtre du logiciel
    print(f"[3/3] Ouverture de l'interface graphique sur {app_url}...")
    print_banner(host, port, stats)

    # Lancer la fenêtre d'application après un bref délai
    time.sleep(0.5)
    open_application_window(app_url)

    # Boucle de maintien en vie avec détection d'arrêt
    try:
        while server_thread.is_alive():
            time.sleep(0.5)
        print("\nArrêt du logiciel DIADJI FAMILY. À bientôt !")
        sys.exit(0)
    except KeyboardInterrupt:
        print("\nArrêt du logiciel DIADJI FAMILY. À bientôt !")
        httpd.shutdown()
        sys.exit(0)


if __name__ == "__main__":
    if "--desktop" in sys.argv or "--tkinter" in sys.argv:
        import gui_desktop
        gui_desktop.main()
    elif "--install" in sys.argv or "--installer" in sys.argv:
        import installer
        installer.run_gui_installer()
    elif "--help" in sys.argv or "-h" in sys.argv:
        print(f"{APP_TITLE} v{VERSION} - Logiciel de Caisse & Stock Embarqué")
        print("\nOptions disponibles:")
        print("  (aucune option)       Lance l'application Caisse & Stock (Web UI dédiée)")
        print("  --desktop / --tkinter Lance l'interface graphique bureautique native Tkinter")
        print("  --install             Lance l'assistant d'installation des raccourcis Windows")
        print("  --help                Affiche cette aide")
    else:
        main()
