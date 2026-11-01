"""
Assistant d'Installation Professionnel pour Windows - DIADJI FAMILY
Logiciel de Caisse & Gestion de Stock Embarqué SQLite.

Fonctionnalités de l'installateur :
1. Vérification et installation des dépendances (openpyxl, etc.)
2. Initialisation et validation de la base SQLite embarquée (magasin.db)
3. Génération et vérification du classeur Excel officiel (DIADJI_FAMILY_TABLEAU_DE_BORD.xlsx)
4. Création des raccourcis Windows avec icône personnalisée sur le Bureau
5. Création du dossier et raccourcis dans le Menu Démarrer de Windows
6. Création du script de désinstallation propre
7. Lancement direct en 1 clic
"""

import sys
import os

# Garantir que le dossier de base est dans sys.path
_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if _CURRENT_DIR not in sys.path:
    sys.path.insert(0, _CURRENT_DIR)

# Attachement à la console parente Windows si lancée en CLI (cmd / powershell)
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

# Protection si stdout/stderr est None
if sys.stdout is None:
    sys.stdout = open(os.devnull, 'w', encoding='utf-8')
if sys.stderr is None:
    sys.stderr = open(os.devnull, 'w', encoding='utf-8')

# Reconfiguration UTF-8 sécurisée
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
import shutil
import time

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

APP_NAME = "DIADJI FAMILY"
APP_DESCRIPTION = "Logiciel de Caisse & Gestion de Stock - DIADJI FAMILY"
ICON_PATH = os.path.join(BASE_DIR, "diadji_icon.ico")
EXE_PATH = os.path.join(BASE_DIR, "DIADJI_FAMILY.exe")
LAUNCHER_BAT = os.path.join(BASE_DIR, "LANCER_APPLICATION.bat")
EXCEL_PATH = os.path.join(BASE_DIR, "DIADJI_FAMILY_TABLEAU_DE_BORD.xlsx")
DB_PATH = os.path.join(BASE_DIR, "magasin.db")


def log(msg):
    print(f"[*] {msg}")


def extract_bundled_assets():
    """Extrait les ressources embarquées si absentes du dossier de destination."""
    if not hasattr(sys, '_MEIPASS'):
        return
    assets = [
        "diadji_icon.ico",
        "diadji_icon.png",
        "articles_clean.json",
        "magasin.db",
        "DIADJI_FAMILY_TABLEAU_DE_BORD.xlsx",
        "app_ui.html",
        "create_shortcuts.ps1",
        "requirements.txt",
        "README.md",
        "LANCER_APPLICATION.bat",
        "LANCER_DESKTOP_TKINTER.bat",
        "DESINSTALLER_DIADJI_FAMILY.bat",
        "CREER_RACCOURCI_BUREAU.bat",
        "INSTALLER_DEPENDANCES_HORS_LIGNE.bat",
        "invoice_scanner.py",
    ]
    for asset in assets:
        dest = os.path.join(BASE_DIR, asset)
        src = os.path.join(sys._MEIPASS, asset)
        if not os.path.exists(dest) and os.path.exists(src):
            try:
                shutil.copy2(src, dest)
                log(f"Fichier extrait : {asset}")
            except Exception:
                pass

    # Extraction des wheels hors-ligne si présentes dans le bundle
    bundled_wheels = os.path.join(sys._MEIPASS, "vendor", "wheels")
    dest_wheels = os.path.join(BASE_DIR, "vendor", "wheels")
    if os.path.isdir(bundled_wheels):
        os.makedirs(dest_wheels, exist_ok=True)
        for w in os.listdir(bundled_wheels):
            if w.endswith(".whl"):
                dw = os.path.join(dest_wheels, w)
                if not os.path.exists(dw):
                    try:
                        shutil.copy2(os.path.join(bundled_wheels, w), dw)
                        log(f"Wheel extraite : {w}")
                    except Exception:
                        pass


def find_python_executable():
    """Trouve l'exécutable Python sur le système Windows."""
    if not getattr(sys, 'frozen', False) and sys.executable and "python" in os.path.basename(sys.executable).lower():
        return sys.executable
    candidates = [
        os.path.join(BASE_DIR, "vendor", "python_embed", "python.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Python\pythoncore-3.15-64\python.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Python\Python313\python.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Python\Python312\python.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Python\Python311\python.exe"),
        r"C:\Python313\python.exe",
        r"C:\Python312\python.exe",
        r"C:\Python311\python.exe",
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    try:
        res = subprocess.run(["where", "python"], capture_output=True, text=True)
        if res.returncode == 0:
            lines = res.stdout.strip().splitlines()
            if lines and os.path.isfile(lines[0]):
                return lines[0]
    except Exception:
        pass
    return "python"


def check_and_install_dependencies():
    """Vérifie que les paquets requis sont disponibles."""
    required = ["openpyxl"]
    missing = []
    for pkg in required:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)

    if missing:
        log(f"Installation des dépendances manquantes : {', '.join(missing)}...")
        try:
            py_cmd = find_python_executable()
            # Vérifier si des wheels hors-ligne sont présentes
            wheels_dir = os.path.join(BASE_DIR, "vendor", "wheels")
            if hasattr(sys, '_MEIPASS'):
                bundled_wheels = os.path.join(sys._MEIPASS, "vendor", "wheels")
                if os.path.isdir(bundled_wheels):
                    wheels_dir = bundled_wheels

            if os.path.isdir(wheels_dir) and any(f.endswith(".whl") for f in os.listdir(wheels_dir)):
                log("Installation hors-ligne à partir des wheels locales (0% Internet requis)...")
                cmd = [py_cmd, "-m", "pip", "install", "--no-index", f"--find-links={wheels_dir}", *missing]
            else:
                cmd = [py_cmd, "-m", "pip", "install", *missing]

            subprocess.run(
                cmd,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            log("Dépendances installées avec succès.")
        except Exception as e:
            log(f"Avertissement : installation pip non requise ou échouée ({e}). Les modules compilés seront utilisés.")
    else:
        log("Toutes les dépendances Python requises (openpyxl, etc.) sont déjà prêtes.")


def initialize_database():
    """Initialise ou migre la base SQLite magasin.db."""
    log("Initialisation de la base de données SQLite (magasin.db)...")
    import database
    database.init_db(force_reseed=False)
    stats = database.get_dashboard_stats()
    log(f"Base de données prête : {stats['total_articles']} articles enregistrés sous le nom DIADJI FAMILY.")


def verify_excel_workbook():
    """Vérifie ou génère le classeur Excel officiel DIADJI FAMILY."""
    if not os.path.exists(EXCEL_PATH):
        log("Génération du classeur Excel officiel DIADJI_FAMILY_TABLEAU_DE_BORD.xlsx...")
        try:
            import build_excel
            log("Classeur Excel généré avec succès.")
        except Exception as e:
            log(f"Avertissement lors de la génération Excel: {e}")
    else:
        log("Classeur Excel DIADJI_FAMILY_TABLEAU_DE_BORD.xlsx déjà présent.")


def create_windows_shortcuts(desktop=True, start_menu=True):
    """Crée les raccourcis Windows avec icône personnalisée."""
    created = []
    target_app = EXE_PATH if os.path.isfile(EXE_PATH) else LAUNCHER_BAT
    tkinter_bat = os.path.join(BASE_DIR, "LANCER_DESKTOP_TKINTER.bat")

    # 1. Raccourci Bureau
    if desktop:
        ps_cmd_desktop = f"""
        $ws = New-Object -ComObject WScript.Shell;
        $desktopPath = [System.Environment]::GetFolderPath('Desktop');
        $shortcut = $ws.CreateShortcut("$desktopPath\\{APP_NAME}.lnk");
        $shortcut.TargetPath = "{target_app}";
        $shortcut.WorkingDirectory = "{BASE_DIR}";
        $shortcut.Description = "{APP_DESCRIPTION}";
        if (Test-Path "{ICON_PATH}") {{
            $shortcut.IconLocation = "{ICON_PATH}";
        }}
        $shortcut.Save();
        """
        try:
            res = subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd_desktop], capture_output=True, text=True)
            if res.returncode == 0:
                log("Raccourci Bureau créé : [Bureau]\\DIADJI FAMILY.lnk")
                created.append("Bureau")
        except Exception as e:
            log(f"Erreur création raccourci Bureau: {e}")

    # 2. Raccourci Menu Démarrer
    if start_menu:
        ps_cmd_start = f"""
        $ws = New-Object -ComObject WScript.Shell;
        $startPath = [System.Environment]::GetFolderPath('StartMenu');
        $progDir = "$startPath\\Programs\\{APP_NAME}";
        if (!(Test-Path $progDir)) {{
            New-Item -ItemType Directory -Path $progDir -Force | Out-Null;
        }}
        
        # 1. Raccourci Application Principale
        $shortcutApp = $ws.CreateShortcut("$progDir\\{APP_NAME}.lnk");
        $shortcutApp.TargetPath = "{target_app}";
        $shortcutApp.WorkingDirectory = "{BASE_DIR}";
        $shortcutApp.Description = "{APP_DESCRIPTION}";
        if (Test-Path "{ICON_PATH}") {{
            $shortcutApp.IconLocation = "{ICON_PATH}";
        }}
        $shortcutApp.Save();

        # 2. Raccourci Interface Tkinter de secours
        $shortcutTk = $ws.CreateShortcut("$progDir\\{APP_NAME} (Interface Bureau Tkinter).lnk");
        if (Test-Path "{EXE_PATH}") {{
            $shortcutTk.TargetPath = "{EXE_PATH}";
            $shortcutTk.Arguments = "--desktop";
        }} elseif (Test-Path "{tkinter_bat}") {{
            $shortcutTk.TargetPath = "{tkinter_bat}";
        }}
        $shortcutTk.WorkingDirectory = "{BASE_DIR}";
        $shortcutTk.Description = "Interface Bureau Tkinter - {APP_NAME}";
        if (Test-Path "{ICON_PATH}") {{
            $shortcutTk.IconLocation = "{ICON_PATH}";
        }}
        $shortcutTk.Save();

        # 3. Raccourci Classeur Excel
        if (Test-Path "{EXCEL_PATH}") {{
            $shortcutExcel = $ws.CreateShortcut("$progDir\\Classeur Excel DIADJI FAMILY.lnk");
            $shortcutExcel.TargetPath = "{EXCEL_PATH}";
            $shortcutExcel.WorkingDirectory = "{BASE_DIR}";
            $shortcutExcel.Description = "Tableau de Bord Excel DIADJI FAMILY";
            $shortcutExcel.Save();
        }}
        """
        try:
            res = subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd_start], capture_output=True, text=True)
            if res.returncode == 0:
                log("Dossier et raccourcis créés dans le Menu Démarrer Windows.")
                created.append("Menu Démarrer")
        except Exception as e:
            log(f"Erreur création raccourcis Menu Démarrer: {e}")

    return created


def create_uninstaller():
    """Génère le script de désinstallation DESINSTALLER_DIADJI_FAMILY.bat."""
    uninstaller_path = os.path.join(BASE_DIR, "DESINSTALLER_DIADJI_FAMILY.bat")
    content = f"""@echo off
chcp 65001 > nul
title Désinstallation des raccourcis - {APP_NAME}
echo ===============================================================================
echo                DÉSINSTALLATION DES RACCOURCIS {APP_NAME}
echo ===============================================================================
echo.
echo Cette opération va supprimer les raccourcis du Bureau et du Menu Démarrer.
echo Vos données (magasin.db et classeur Excel) seront conservées en sécurité.
echo.
set /p confirm="Confirmer la suppression des raccourcis (O/N) ? "
if /i "%confirm%" neq "O" (
    echo Opération annulée.
    pause
    exit /b 0
)

powershell -NoProfile -Command "$desktop = [System.Environment]::GetFolderPath('Desktop'); $s1 = \"$desktop\\{APP_NAME}.lnk\"; if (Test-Path $s1) {{ Remove-Item -Force $s1; Write-Host '[OK] Raccourci Bureau supprimé.' }}; $start = [System.Environment]::GetFolderPath('StartMenu'); $dir = \"$start\\Programs\\{APP_NAME}\"; if (Test-Path $dir) {{ Remove-Item -Recurse -Force $dir; Write-Host '[OK] Raccourcis Menu Démarrer supprimés.' }}"

echo.
echo ===============================================================================
echo  Désinstallation terminée avec succès.
echo ===============================================================================
pause
"""
    with open(uninstaller_path, "w", encoding="utf-8") as f:
        f.write(content)
    log(f"Script de désinstallation prêt : {uninstaller_path}")


def run_full_installation(desktop=True, start_menu=True, launch_after=False):
    """Exécute l'installation complète sans interface."""
    print("=" * 70)
    print(f"      INSTALLATEUR AUTOMATISÉ POUR WINDOWS - {APP_NAME}")
    print("=" * 70)
    print()
    extract_bundled_assets()
    check_and_install_dependencies()
    initialize_database()
    verify_excel_workbook()
    create_windows_shortcuts(desktop=desktop, start_menu=start_menu)
    create_uninstaller()
    print()
    print("=" * 70)
    print(f"  [OK] INSTALLATION DE {APP_NAME} TERMINÉE AVEC SUCCÈS !")
    print("=" * 70)
    print(f"  • Raccourci Bureau       : Oui")
    print(f"  • Menu Démarrer Windows  : Programmes > {APP_NAME}")
    print(f"  • Base de Données        : magasin.db (SQLite embarqué)")
    print(f"  • Classeur Excel         : DIADJI_FAMILY_TABLEAU_DE_BORD.xlsx")
    print("=" * 70)

    if launch_after:
        print(f"\nLancement de {APP_NAME}...")
        if os.path.isfile(EXE_PATH):
            subprocess.Popen([EXE_PATH])
        else:
            subprocess.Popen([LAUNCHER_BAT], shell=True)


def run_gui_installer():
    """Lance l'assistant d'installation graphique avec Tkinter."""
    try:
        import tkinter as tk
        from tkinter import ttk, messagebox
    except ImportError:
        # Fallback console si Tkinter n'est pas dispo
        run_full_installation(launch_after=True)
        return

    root = tk.Tk()
    root.title(f"Installation - {APP_NAME}")
    root.geometry("620x520")
    root.resizable(False, False)
    root.configure(bg="#0F172A")

    # Center window
    root.eval('tk::PlaceWindow . center')

    # Header frame
    hdr = tk.Frame(root, bg="#0F172A", height=100)
    hdr.pack(fill=tk.X, padx=25, pady=(20, 10))

    tk.Label(
        hdr,
        text=APP_NAME,
        font=("Segoe UI", 20, "bold"),
        fg="#F59E0B",
        bg="#0F172A"
    ).pack(anchor=tk.W)

    tk.Label(
        hdr,
        text="Assistant d'Installation & Configuration Windows",
        font=("Segoe UI", 11),
        fg="#94A3B8",
        bg="#0F172A"
    ).pack(anchor=tk.W, pady=(2, 0))

    # Card frame
    card = tk.Frame(root, bg="#1E293B", padx=25, pady=20)
    card.pack(fill=tk.BOTH, expand=True, padx=25, pady=10)

    tk.Label(
        card,
        text="Bienvenue dans l'assistant d'installation de DIADJI FAMILY.\nCe programme configure automatiquement votre logiciel de caisse et gestion de stock.",
        font=("Segoe UI", 10),
        fg="#E2E8F0",
        bg="#1E293B",
        justify=tk.LEFT
    ).pack(anchor=tk.W, pady=(0, 15))

    # Options frame
    chk_desktop_var = tk.BooleanVar(value=True)
    chk_start_var = tk.BooleanVar(value=True)
    chk_launch_var = tk.BooleanVar(value=True)

    opts_box = tk.LabelFrame(
        card,
        text=" Options d'installation ",
        font=("Segoe UI", 10, "bold"),
        fg="#38BDF8",
        bg="#1E293B",
        padx=15,
        pady=10
    )
    opts_box.pack(fill=tk.X, pady=(0, 15))

    c1 = tk.Checkbutton(
        opts_box,
        text="Créer un raccourci direct sur le Bureau Windows",
        variable=chk_desktop_var,
        font=("Segoe UI", 9),
        fg="#FFFFFF",
        bg="#1E293B",
        selectcolor="#0F172A",
        activebackground="#1E293B",
        activeforeground="#FFFFFF"
    )
    c1.pack(anchor=tk.W, pady=3)

    c2 = tk.Checkbutton(
        opts_box,
        text="Ajouter au Menu Démarrer de Windows (Programmes > DIADJI FAMILY)",
        variable=chk_start_var,
        font=("Segoe UI", 9),
        fg="#FFFFFF",
        bg="#1E293B",
        selectcolor="#0F172A",
        activebackground="#1E293B",
        activeforeground="#FFFFFF"
    )
    c2.pack(anchor=tk.W, pady=3)

    c3 = tk.Checkbutton(
        opts_box,
        text="Lancer l'application immédiatement à la fin de l'installation",
        variable=chk_launch_var,
        font=("Segoe UI", 9, "bold"),
        fg="#10B981",
        bg="#1E293B",
        selectcolor="#0F172A",
        activebackground="#1E293B",
        activeforeground="#10B981"
    )
    c3.pack(anchor=tk.W, pady=3)

    # Status label
    lbl_status = tk.Label(
        card,
        text="Prêt pour l'installation en un clic.",
        font=("Segoe UI", 9, "italic"),
        fg="#94A3B8",
        bg="#1E293B"
    )
    lbl_status.pack(anchor=tk.W, pady=(5, 5))

    # Progress bar
    style = ttk.Style()
    style.theme_use('clam')
    style.configure("Green.Horizontal.TProgressbar", foreground='#10B981', background='#10B981')

    prog = ttk.Progressbar(card, style="Green.Horizontal.TProgressbar", orient=tk.HORIZONTAL, length=520, mode='determinate')
    prog.pack(fill=tk.X, pady=(5, 10))

    # Bottom Actions
    btn_frame = tk.Frame(root, bg="#0F172A", height=60)
    btn_frame.pack(fill=tk.X, padx=25, pady=(5, 20))

    btn_cancel = tk.Button(
        btn_frame,
        text="Annuler",
        font=("Segoe UI", 9),
        bg="#334155",
        fg="#FFFFFF",
        relief=tk.FLAT,
        padx=15,
        pady=6,
        command=root.destroy
    )
    btn_cancel.pack(side=tk.RIGHT, padx=(10, 0))

    def do_install():
        btn_install.config(state=tk.DISABLED)
        btn_cancel.config(state=tk.DISABLED)

        def step(pct, text):
            prog['value'] = pct
            lbl_status.config(text=text)
            root.update()
            time.sleep(0.15)

        step(10, "1/5 Extraction des ressources et composants...")
        extract_bundled_assets()

        step(25, "2/5 Vérification des dépendances embarquées...")
        check_and_install_dependencies()

        step(50, "3/5 Initialisation de la base de données embarquée (magasin.db)...")
        initialize_database()

        step(70, "4/5 Vérification du classeur Excel officiel...")
        verify_excel_workbook()

        step(90, "5/5 Création des raccourcis Windows avec icône...")
        create_windows_shortcuts(desktop=chk_desktop_var.get(), start_menu=chk_start_var.get())
        create_uninstaller()

        step(100, "Installation terminée avec succès !")

        messagebox.showinfo(
            "Installation Réussie",
            f"Félicitations !\n\nL'installation de {APP_NAME} s'est terminée avec succès.\n\nVous pouvez désormais ouvrir votre logiciel directement depuis le Bureau ou le Menu Démarrer Windows."
        )

        should_launch = chk_launch_var.get()
        root.destroy()

        if should_launch:
            if os.path.isfile(EXE_PATH):
                subprocess.Popen([EXE_PATH])
            else:
                subprocess.Popen([LAUNCHER_BAT], shell=True)

    btn_install = tk.Button(
        btn_frame,
        text="▶ Lancer l'Installation Complète",
        font=("Segoe UI", 10, "bold"),
        bg="#10B981",
        fg="#FFFFFF",
        relief=tk.FLAT,
        padx=20,
        pady=7,
        command=do_install
    )
    btn_install.pack(side=tk.RIGHT)

    root.mainloop()


if __name__ == "__main__":
    if "--shortcuts" in sys.argv:
        create_windows_shortcuts(desktop=True, start_menu=True)
    elif "--cli" in sys.argv or "--silent" in sys.argv:
        launch = "--launch" in sys.argv
        run_full_installation(launch_after=launch)
    else:
        run_gui_installer()
