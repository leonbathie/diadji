"""
Interface Graphique Native Desktop (Tkinter) pour DIADJI FAMILY.
Permet d'utiliser le logiciel directement dans une fenêtre Windows native moderne.
Se connecte à la même base de données embarquée SQLite `magasin.db`.
"""

import sys
import os

_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if _CURRENT_DIR not in sys.path:
    sys.path.insert(0, _CURRENT_DIR)

try:
    import tkinter as tk
    from tkinter import ttk, messagebox, filedialog
except ImportError:
    print("[INFO] Tkinter n'est pas disponible dans cet environnement Python.")
    print("[INFO] Basculement automatique vers l'interface Web DIADJI FAMILY...")
    import app
    app.main()
    sys.exit(0)

import database


def bind_var_write(var, callback):
    """Liaison universelle compatible Tcl 8.6+ et Tcl 9 (trace_add vs trace)."""
    if hasattr(var, "trace_add"):
        return var.trace_add("write", callback)
    return var.trace("w", callback)


def format_qty(q):
    """Formate une quantité proprement (entier si entier, ou 2 décimales si fractionnaire)."""
    if q is None:
        return "0"
    try:
        val = float(q)
        return f"{int(val)}" if val == int(val) else f"{val:.2f}"
    except (ValueError, TypeError):
        return str(q)


def format_fcfa(val):
    """Formate un montant en FCFA avec séparateur d'espace."""
    try:
        v = float(val or 0)
        return f"{int(round(v)):,} FCFA".replace(",", " ")
    except (ValueError, TypeError):
        return "0 FCFA"


class DiadjiFamilyDesktopApp:
    def __init__(self, root):
        self.root = root
        self.root.title("DIADJI FAMILY - Logiciel de Caisse & Stock")
        self.root.geometry("1240x740")
        self.root.minsize(1020, 640)
        self.root.configure(bg="#F1F5F9")

        # Définition de l'icône de la fenêtre
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "diadji_icon.ico")
        if os.path.exists(icon_path):
            try:
                self.root.iconbitmap(icon_path)
            except Exception:
                pass

        # Assurer l'initialisation de la base SQLite
        database.init_db(force_reseed=False)

        # Style TTK moderne
        self.setup_styles()

        self.cart = [] # Panier de caisse : liste de dicts
        self.total_net = 0.0

        self.create_header()
        self.create_tabs()
        self.setup_keyboard_shortcuts()

        # Chargement initial des données
        self.load_catalogue_data()
        self.load_pos_articles()
        self.load_alerts_data()

    def setup_styles(self):
        """Configure les styles graphiques pour un rendu moderne et soigné."""
        self.style = ttk.Style()
        try:
            self.style.theme_use('clam')
        except Exception:
            pass

        # Configuration de la police globale et des Treeview
        self.style.configure(".", font=("Segoe UI", 9))
        self.style.configure(
            "Treeview",
            rowheight=26,
            font=("Segoe UI", 9),
            background="#FFFFFF",
            fieldbackground="#FFFFFF",
            bordercolor="#CBD5E1"
        )
        self.style.configure(
            "Treeview.Heading",
            font=("Segoe UI", 9, "bold"),
            background="#E2E8F0",
            foreground="#0F172A",
            relief=tk.FLAT,
            padding=4
        )
        self.style.map(
            "Treeview",
            background=[("selected", "#2563EB")],
            foreground=[("selected", "#FFFFFF")]
        )
        self.style.configure("TNotebook", background="#F1F5F9", borderwidth=0)
        self.style.configure("TNotebook.Tab", padding=[14, 7], font=("Segoe UI", 9, "bold"))
        self.style.map(
            "TNotebook.Tab",
            background=[("selected", "#FFFFFF"), ("!selected", "#E2E8F0")],
            foreground=[("selected", "#1D4ED8"), ("!selected", "#475569")]
        )

    def setup_keyboard_shortcuts(self):
        """Active les raccourcis clavier pour une utilisation ultra-rapide."""
        self.root.bind("<F1>", lambda e: self.show_shortcuts_help())
        self.root.bind("<F2>", lambda e: self.notebook.select(self.tab_caisse))
        self.root.bind("<F3>", lambda e: self.notebook.select(self.tab_catalogue))
        self.root.bind("<F4>", lambda e: self.notebook.select(self.tab_alertes))
        self.root.bind("<F5>", lambda e: self.refresh_all_data())

    def show_shortcuts_help(self):
        """Affiche la liste des raccourcis clavier disponibles."""
        msg = (
            "Raccourcis Clavier Disponibles :\n\n"
            "• F1 : Afficher cette aide\n"
            "• F2 : Ouvrir l'onglet Point de Vente / Caisse\n"
            "• F3 : Ouvrir l'onglet Catalogue & Stocks\n"
            "• F4 : Ouvrir l'onglet Alertes de Rupture & Réassort\n"
            "• F5 : Actualiser toutes les données\n"
            "• Double-Clic ou Entrée : Ajouter un article au panier\n"
        )
        messagebox.showinfo("Raccourcis Clavier - DIADJI FAMILY", msg)

    def refresh_all_data(self):
        """Rafraîchit toutes les vues de l'application."""
        self.load_catalogue_data()
        self.load_pos_articles()
        self.load_alerts_data()

    def create_header(self):
        """En-tête supérieur avec logo et informations magasin."""
        header_frame = tk.Frame(self.root, bg="#0F172A", height=60)
        header_frame.pack(fill=tk.X, side=tk.TOP)

        left_hdr = tk.Frame(header_frame, bg="#0F172A")
        left_hdr.pack(side=tk.LEFT, padx=15, pady=8)

        title_label = tk.Label(
            left_hdr,
            text="DIADJI FAMILY",
            font=("Segoe UI", 15, "bold"),
            fg="#F59E0B",
            bg="#0F172A"
        )
        title_label.pack(side=tk.LEFT)

        sub_label = tk.Label(
            left_hdr,
            text=" | Caisse Express & Gestion de Stock Embarqué (SQLite)",
            font=("Segoe UI", 10),
            fg="#94A3B8",
            bg="#0F172A"
        )
        sub_label.pack(side=tk.LEFT, padx=(5, 0))

        # Boutons d'action rapide à droite
        right_hdr = tk.Frame(header_frame, bg="#0F172A")
        right_hdr.pack(side=tk.RIGHT, padx=15, pady=8)

        btn_caisse_quick = tk.Button(
            right_hdr,
            text="🛒 Caisse [F2]",
            font=("Segoe UI", 9, "bold"),
            bg="#10B981",
            fg="#FFFFFF",
            relief=tk.FLAT,
            padx=10,
            pady=4,
            command=lambda: self.notebook.select(self.tab_caisse)
        )
        btn_caisse_quick.pack(side=tk.LEFT, padx=4)

        btn_excel = tk.Button(
            right_hdr,
            text="📥 Export Excel",
            font=("Segoe UI", 9, "bold"),
            bg="#059669",
            fg="#FFFFFF",
            relief=tk.FLAT,
            padx=10,
            pady=4,
            command=self.export_excel_action
        )
        btn_excel.pack(side=tk.LEFT, padx=4)

        btn_help = tk.Button(
            right_hdr,
            text="⌨️ Aide [F1]",
            font=("Segoe UI", 9),
            bg="#334155",
            fg="#E2E8F0",
            relief=tk.FLAT,
            padx=8,
            pady=4,
            command=self.show_shortcuts_help
        )
        btn_help.pack(side=tk.LEFT, padx=4)

    def create_tabs(self):
        """Création des onglets principaux."""
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=(6, 10))

        # Onglet 1: Caisse / Ventes (placé en 1er pour un accès direct commerçant)
        self.tab_caisse = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_caisse, text=" 🛒 Caisse Express & Ventes [F2] ")
        self.build_caisse_tab()

        # Onglet 2: Catalogue & Stocks
        self.tab_catalogue = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_catalogue, text=" 📦 Catalogue & Stocks (CRUD) [F3] ")
        self.build_catalogue_tab()

        # Onglet 3: Alertes & Réassort
        self.tab_alertes = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_alertes, text=" ⚠️ Alertes de Rupture & Réassort [F4] ")
        self.build_alertes_tab()

        # Onglet 4: Synchronisation Excel & Données
        self.tab_sync = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_sync, text=" 🔄 Synchronisation Excel & Sécurité ")
        self.build_sync_tab()

    # =========================================================================
    # ONGLET 1: POINT DE VENTE / CAISSE
    # =========================================================================
    def build_caisse_tab(self):
        caisse_paned = ttk.PanedWindow(self.tab_caisse, orient=tk.HORIZONTAL)
        caisse_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Panneau Gauche : Recherche & Sélection Articles (60%)
        left_frame = tk.Frame(caisse_paned, bg="#FFFFFF", padx=10, pady=10)
        caisse_paned.add(left_frame, weight=3)

        tk.Label(
            left_frame,
            text="Rechercher un article (ou double-cliquer pour ajouter) :",
            font=("Segoe UI", 9, "bold"),
            bg="#FFFFFF",
            fg="#0F172A"
        ).pack(anchor=tk.W)

        search_bar = tk.Frame(left_frame, bg="#FFFFFF")
        search_bar.pack(fill=tk.X, pady=(4, 8))

        self.pos_search_var = tk.StringVar()
        bind_var_write(self.pos_search_var, lambda *args: self.filter_pos_articles())
        self.ent_pos_search = ttk.Entry(search_bar, textvariable=self.pos_search_var)
        self.ent_pos_search.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.ent_pos_search.bind("<Return>", lambda e: self.add_selected_to_cart())

        btn_clear_pos = tk.Button(
            search_bar,
            text="✕",
            font=("Segoe UI", 8, "bold"),
            bg="#E2E8F0",
            relief=tk.FLAT,
            padx=6,
            command=lambda: self.pos_search_var.set("")
        )
        btn_clear_pos.pack(side=tk.LEFT, padx=(3, 0))

        # Tableau des articles disponibles
        tree_pos_frame = ttk.Frame(left_frame)
        tree_pos_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("id", "nom", "prix", "stock", "unite", "categorie")
        self.pos_tree = ttk.Treeview(tree_pos_frame, columns=columns, show="headings", selectmode="browse")
        self.pos_tree.heading("id", text="Code")
        self.pos_tree.heading("nom", text="Désignation de l'Article")
        self.pos_tree.heading("prix", text="Prix Vente")
        self.pos_tree.heading("stock", text="Stock")
        self.pos_tree.heading("unite", text="Unité")
        self.pos_tree.heading("categorie", text="Rayon")

        self.pos_tree.column("id", width=65, anchor="center")
        self.pos_tree.column("nom", width=240)
        self.pos_tree.column("prix", width=95, anchor="e")
        self.pos_tree.column("stock", width=55, anchor="center")
        self.pos_tree.column("unite", width=55, anchor="center")
        self.pos_tree.column("categorie", width=140)

        pos_scroll = ttk.Scrollbar(tree_pos_frame, orient=tk.VERTICAL, command=self.pos_tree.yview)
        self.pos_tree.configure(yscrollcommand=pos_scroll.set)
        self.pos_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        pos_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.pos_tree.bind("<Double-1>", lambda e: self.add_selected_to_cart())
        self.pos_tree.bind("<Return>", lambda e: self.add_selected_to_cart())

        # Bouton d'ajout rapide
        btn_add_to_cart = tk.Button(
            left_frame,
            text="➕ Ajouter l'Article Sélectionné au Panier [Entrée]",
            bg="#2563EB",
            fg="white",
            font=("Segoe UI", 9, "bold"),
            relief=tk.FLAT,
            pady=6,
            command=self.add_selected_to_cart
        )
        btn_add_to_cart.pack(fill=tk.X, pady=(8, 0))

        # Panneau Droit : Panier & Encaissement (40%)
        right_frame = tk.Frame(caisse_paned, bg="#FFFFFF", padx=12, pady=10)
        caisse_paned.add(right_frame, weight=2)

        # Header Panier
        cart_header = tk.Frame(right_frame, bg="#FFFFFF")
        cart_header.pack(fill=tk.X, pady=(0, 6))

        tk.Label(
            cart_header,
            text="PANIER D'ENCAISSEMENT",
            font=("Segoe UI", 11, "bold"),
            bg="#FFFFFF",
            fg="#0F172A"
        ).pack(side=tk.LEFT)

        self.lbl_cart_count = tk.Label(
            cart_header,
            text="0 article",
            font=("Segoe UI", 9),
            bg="#FFFFFF",
            fg="#64748B"
        )
        self.lbl_cart_count.pack(side=tk.RIGHT)

        # Treeview Panier
        cart_tree_frame = ttk.Frame(right_frame)
        cart_tree_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 6))

        cart_cols = ("nom", "qty", "prix", "total")
        self.cart_tree = ttk.Treeview(cart_tree_frame, columns=cart_cols, show="headings", height=6)
        self.cart_tree.heading("nom", text="Article")
        self.cart_tree.heading("qty", text="Qté")
        self.cart_tree.heading("prix", text="P.U.")
        self.cart_tree.heading("total", text="Total")

        self.cart_tree.column("nom", width=130)
        self.cart_tree.column("qty", width=40, anchor="center")
        self.cart_tree.column("prix", width=65, anchor="e")
        self.cart_tree.column("total", width=75, anchor="e")

        cart_scroll = ttk.Scrollbar(cart_tree_frame, orient=tk.VERTICAL, command=self.cart_tree.yview)
        self.cart_tree.configure(yscrollcommand=cart_scroll.set)
        self.cart_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        cart_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # Boutons de contrôle du panier (+1, -1, retirer, vider)
        cart_btns = tk.Frame(right_frame, bg="#FFFFFF")
        cart_btns.pack(fill=tk.X, pady=(0, 6))

        tk.Button(
            cart_btns, text="➕ 1", font=("Segoe UI", 8, "bold"), bg="#E2E8F0",
            relief=tk.FLAT, padx=6, command=lambda: self.change_cart_qty(1)
        ).pack(side=tk.LEFT, padx=2)

        tk.Button(
            cart_btns, text="➖ 1", font=("Segoe UI", 8, "bold"), bg="#E2E8F0",
            relief=tk.FLAT, padx=6, command=lambda: self.change_cart_qty(-1)
        ).pack(side=tk.LEFT, padx=2)

        tk.Button(
            cart_btns, text="Retirer", font=("Segoe UI", 8), bg="#FEE2E2", fg="#991B1B",
            relief=tk.FLAT, padx=6, command=self.remove_cart_item
        ).pack(side=tk.LEFT, padx=2)

        tk.Button(
            cart_btns, text="Vider Panier", font=("Segoe UI", 8), bg="#F1F5F9", fg="#475569",
            relief=tk.FLAT, padx=6, command=self.clear_cart
        ).pack(side=tk.RIGHT)

        # Bloc Encaissement & Totaux
        summary_frame = tk.Frame(right_frame, bg="#F8FAFC", relief=tk.GROOVE, bd=1, padx=10, pady=8)
        summary_frame.pack(fill=tk.X, pady=(0, 6))

        # Informations Client (Optionnel)
        client_box = tk.Frame(summary_frame, bg="#F8FAFC")
        client_box.pack(fill=tk.X, pady=(0, 6))

        tk.Label(client_box, text="Client :", font=("Segoe UI", 8, "bold"), bg="#F8FAFC").grid(row=0, column=0, sticky=tk.W)
        self.client_name_var = tk.StringVar(value="Client Comptant")
        ent_client = ttk.Entry(client_box, textvariable=self.client_name_var, width=16)
        ent_client.grid(row=0, column=1, padx=(2, 8), sticky=tk.W)

        tk.Label(client_box, text="Mode :", font=("Segoe UI", 8, "bold"), bg="#F8FAFC").grid(row=0, column=2, sticky=tk.W)
        self.payment_mode_var = tk.StringVar(value="Espèces")
        cb_mode = ttk.Combobox(client_box, textvariable=self.payment_mode_var, values=["Espèces", "Wave", "Orange Money", "Chèque"], state="readonly", width=10)
        cb_mode.grid(row=0, column=3, padx=2, sticky=tk.W)

        # Remise
        remise_box = tk.Frame(summary_frame, bg="#F8FAFC")
        remise_box.pack(fill=tk.X, pady=(0, 4))
        tk.Label(remise_box, text="Remise (FCFA) :", font=("Segoe UI", 8), bg="#F8FAFC").pack(side=tk.LEFT)
        self.remise_var = tk.StringVar(value="0")
        bind_var_write(self.remise_var, lambda *args: self.render_cart_totals())
        ent_remise = ttk.Entry(remise_box, textvariable=self.remise_var, width=10)
        ent_remise.pack(side=tk.LEFT, padx=5)

        # Net à payer en grand
        self.lbl_net_total = tk.Label(
            summary_frame,
            text="NET À PAYER : 0 FCFA",
            font=("Segoe UI", 12, "bold"),
            fg="#047857",
            bg="#F8FAFC"
        )
        self.lbl_net_total.pack(anchor=tk.W, pady=3)

        # Montant reçu & Monnaie
        pay_grid = tk.Frame(summary_frame, bg="#F8FAFC")
        pay_grid.pack(fill=tk.X, pady=3)

        tk.Label(pay_grid, text="Montant Reçu :", font=("Segoe UI", 8, "bold"), bg="#F8FAFC").grid(row=0, column=0, sticky=tk.W)
        self.received_var = tk.StringVar(value="0")
        bind_var_write(self.received_var, lambda *args: self.update_change_display())
        ent_received = ttk.Entry(pay_grid, textvariable=self.received_var, width=12)
        ent_received.grid(row=0, column=1, padx=5, sticky=tk.W)

        self.lbl_change = tk.Label(
            pay_grid,
            text="Monnaie : 0 FCFA",
            font=("Segoe UI", 9, "bold"),
            fg="#1E40AF",
            bg="#F8FAFC"
        )
        self.lbl_change.grid(row=0, column=2, padx=6, sticky=tk.W)

        # Raccourcis coupures rapides
        quick_cash_frame = tk.Frame(summary_frame, bg="#F8FAFC")
        quick_cash_frame.pack(fill=tk.X, pady=(4, 0))

        tk.Button(
            quick_cash_frame, text="Exact", font=("Segoe UI", 7, "bold"), bg="#E2E8F0",
            relief=tk.FLAT, padx=4, command=lambda: self.received_var.set(str(int(self.total_net)))
        ).pack(side=tk.LEFT, padx=1)

        for amt in [1000, 2000, 5000, 10000, 20000]:
            tk.Button(
                quick_cash_frame, text=f"{amt:,}".replace(",", " "), font=("Segoe UI", 7), bg="#E2E8F0",
                relief=tk.FLAT, padx=3, command=lambda a=amt: self.received_var.set(str(a))
            ).pack(side=tk.LEFT, padx=1)

        # Bouton Encaisser
        btn_valider_vente = tk.Button(
            right_frame,
            text="✓ VALIDER L'ENCAISSEMENT",
            bg="#059669",
            fg="white",
            font=("Segoe UI", 11, "bold"),
            relief=tk.FLAT,
            pady=8,
            command=self.valider_vente_action
        )
        btn_valider_vente.pack(fill=tk.X, pady=(4, 0))

    def load_pos_articles(self):
        """Charge la liste des articles disponibles dans la caisse."""
        self.pos_articles = database.get_articles()
        self.filter_pos_articles()

    def filter_pos_articles(self):
        query = database.strip_accents(self.pos_search_var.get().strip())
        for row in self.pos_tree.get_children():
            self.pos_tree.delete(row)

        for idx, a in enumerate(self.pos_articles):
            if query:
                blob = database.strip_accents(f"{a['id']} {a.get('code_barre') or ''} {a['nom']} {a['categorie']}")
                if query not in blob:
                    continue
            p_str = format_fcfa(a['prix_vente']) if a['prix_vente'] > 0 else "À définir"
            self.pos_tree.insert("", tk.END, values=(
                a['id'],
                a['nom'],
                p_str,
                format_qty(a['stock_actuel']),
                a['unite'],
                a['categorie']
            ), iid=a['id'])

    def add_selected_to_cart(self):
        selected = self.pos_tree.selection()
        if not selected:
            return
        art_id = selected[0]
        art = database.get_article_by_id(art_id)
        if not art:
            return

        existing = next((item for item in self.cart if item['article_id'] == art_id), None)
        if existing:
            existing['quantite'] += 1
        else:
            self.cart.append({
                "article_id": art['id'],
                "nom": art['nom'],
                "prix_unitaire": art['prix_vente'] or 0,
                "quantite": 1,
                "unite": art['unite']
            })
        self.render_cart()

    def change_cart_qty(self, delta):
        selected = self.cart_tree.selection()
        if selected:
            idx = self.cart_tree.index(selected[0])
        elif len(self.cart) == 1:
            idx = 0
        else:
            return
        self.cart[idx]['quantite'] += delta
        if self.cart[idx]['quantite'] <= 0:
            self.cart.pop(idx)
        self.render_cart()

    def remove_cart_item(self):
        selected = self.cart_tree.selection()
        if selected:
            idx = self.cart_tree.index(selected[0])
        elif len(self.cart) == 1:
            idx = 0
        else:
            return
        self.cart.pop(idx)
        self.render_cart()

    def clear_cart(self):
        self.cart.clear()
        self.render_cart()

    def render_cart(self):
        for row in self.cart_tree.get_children():
            self.cart_tree.delete(row)

        total_brut = 0.0
        last_id = None
        for idx, item in enumerate(self.cart):
            tot = item['quantite'] * item['prix_unitaire']
            total_brut += tot
            last_id = self.cart_tree.insert("", tk.END, values=(
                item['nom'],
                format_qty(item['quantite']),
                format_fcfa(item['prix_unitaire']),
                format_fcfa(tot)
            ))

        if last_id and not self.cart_tree.selection():
            try:
                self.cart_tree.selection_set(last_id)
            except Exception:
                pass

        self.total_brut = total_brut
        self.lbl_cart_count.config(text=f"{len(self.cart)} article(s)")
        self.render_cart_totals()

    def render_cart_totals(self):
        try:
            remise = float(self.remise_var.get() or 0)
        except ValueError:
            remise = 0.0

        total_brut = getattr(self, 'total_brut', 0.0)
        self.total_net = max(0.0, total_brut - remise)
        self.lbl_net_total.config(text=f"NET À PAYER : {format_fcfa(self.total_net)}")
        self.update_change_display()

    def update_change_display(self):
        try:
            received = float(self.received_var.get() or 0)
        except ValueError:
            received = 0.0
        change = max(0.0, received - getattr(self, 'total_net', 0.0))
        self.lbl_change.config(text=f"Monnaie : {format_fcfa(change)}")

    def valider_vente_action(self):
        if not self.cart:
            messagebox.showwarning("Panier vide", "Veuillez ajouter des articles avant de valider la vente.")
            return

        try:
            received = float(self.received_var.get() or 0)
        except ValueError:
            received = self.total_net

        if received < self.total_net:
            received = self.total_net

        try:
            remise = float(self.remise_var.get() or 0)
        except ValueError:
            remise = 0.0

        client_nom = self.client_name_var.get().strip() or "Client Comptant"
        mode_paiement = self.payment_mode_var.get() or "Espèces"

        try:
            ticket = database.create_sale(
                items=[{"article_id": i['article_id'], "quantite": i['quantite'], "prix_unitaire": i['prix_unitaire']} for i in self.cart],
                montant_verse=received,
                remise=remise,
                mode_paiement=mode_paiement,
                client_nom=client_nom
            )

            msg = (
                f"✓ Vente enregistrée avec succès !\n\n"
                f"• Ticket N°     : {ticket['numero_ticket']}\n"
                f"• Client        : {client_nom}\n"
                f"• Net à Payer   : {format_fcfa(ticket['montant_net'])}\n"
                f"• Reçu          : {format_fcfa(ticket['montant_verse'])}\n"
                f"• Monnaie Rendue: {format_fcfa(ticket['monnaie_rendue'])}\n"
                f"• Mode Règlement: {mode_paiement}\n"
            )
            messagebox.showinfo("Ticket de Caisse Émis", msg)

            self.clear_cart()
            self.received_var.set("0")
            self.remise_var.set("0")
            self.load_catalogue_data()
            self.load_pos_articles()
            self.load_alerts_data()
        except Exception as e:
            messagebox.showerror("Erreur de Vente", str(e))

    # =========================================================================
    # ONGLET 2: CATALOGUE & STOCKS (CRUD)
    # =========================================================================
    def build_catalogue_tab(self):
        toolbar = tk.Frame(self.tab_catalogue, bg="#FFFFFF", padx=10, pady=8)
        toolbar.pack(fill=tk.X, pady=(0, 6))

        tk.Label(toolbar, text="Recherche :", font=("Segoe UI", 9, "bold"), bg="#FFFFFF").pack(side=tk.LEFT, padx=(0, 5))
        self.cat_search_var = tk.StringVar()
        bind_var_write(self.cat_search_var, lambda *args: self.load_catalogue_data())
        ent_search = ttk.Entry(toolbar, textvariable=self.cat_search_var, width=24)
        ent_search.pack(side=tk.LEFT, padx=2)

        btn_clear_cat = tk.Button(
            toolbar, text="✕", font=("Segoe UI", 8, "bold"), bg="#E2E8F0", relief=tk.FLAT, padx=4,
            command=lambda: self.cat_search_var.set("")
        )
        btn_clear_cat.pack(side=tk.LEFT, padx=(2, 10))

        tk.Label(toolbar, text="Rayon :", font=("Segoe UI", 9, "bold"), bg="#FFFFFF").pack(side=tk.LEFT, padx=(5, 3))
        self.cat_filter_var = tk.StringVar(value="Toutes")
        cats = [
            "Toutes", "Électricité - Appareillage", "Électricité - Câbles & Gaines",
            "Plomberie & Raccords PVC", "Protection & Tableaux", "Éclairage LED & Luminaires",
            "Visserie, Boulonnerie & Fixation"
        ]
        cb_cat = ttk.Combobox(toolbar, textvariable=self.cat_filter_var, values=cats, state="readonly", width=22)
        cb_cat.pack(side=tk.LEFT, padx=3)
        cb_cat.bind("<<ComboboxSelected>>", lambda e: self.load_catalogue_data())

        tk.Label(toolbar, text="Statut :", font=("Segoe UI", 9, "bold"), bg="#FFFFFF").pack(side=tk.LEFT, padx=(10, 3))
        self.status_filter_var = tk.StringVar(value="Tous")
        cb_status = ttk.Combobox(
            toolbar, textvariable=self.status_filter_var,
            values=["Tous", "rupture", "faible", "stock", "commande", "avec_prix", "sans_prix"],
            state="readonly", width=12
        )
        cb_status.pack(side=tk.LEFT, padx=3)
        cb_status.bind("<<ComboboxSelected>>", lambda e: self.load_catalogue_data())

        # Boutons d'action catalogue
        btn_stock = tk.Button(
            toolbar, text="📥 + Entrée Stock", bg="#059669", fg="white", font=("Segoe UI", 9, "bold"),
            relief=tk.FLAT, padx=8, pady=3, command=self.open_stock_in_dialog
        )
        btn_stock.pack(side=tk.RIGHT, padx=4)

        btn_add = tk.Button(
            toolbar, text="➕ Nouvel Article", bg="#2563EB", fg="white", font=("Segoe UI", 9, "bold"),
            relief=tk.FLAT, padx=8, pady=3, command=self.open_add_article_dialog
        )
        btn_add.pack(side=tk.RIGHT, padx=4)

        # Treeview Catalogue
        tree_frame = ttk.Frame(self.tab_catalogue)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("id", "nom", "categorie", "unite", "prix", "stock", "min", "cmd", "valeur", "statut")
        self.cat_tree = ttk.Treeview(tree_frame, columns=columns, show="headings", selectmode="browse")

        self.cat_tree.heading("id", text="Code")
        self.cat_tree.heading("nom", text="Désignation de l'Article")
        self.cat_tree.heading("categorie", text="Rayon / Catégorie")
        self.cat_tree.heading("unite", text="Unité")
        self.cat_tree.heading("prix", text="Prix Vente")
        self.cat_tree.heading("stock", text="Stock")
        self.cat_tree.heading("min", text="Min")
        self.cat_tree.heading("cmd", text="En Cmd")
        self.cat_tree.heading("valeur", text="Valeur Stock")
        self.cat_tree.heading("statut", text="Statut")

        self.cat_tree.column("id", width=70, anchor="center")
        self.cat_tree.column("nom", width=280)
        self.cat_tree.column("categorie", width=170)
        self.cat_tree.column("unite", width=65, anchor="center")
        self.cat_tree.column("prix", width=95, anchor="e")
        self.cat_tree.column("stock", width=60, anchor="center")
        self.cat_tree.column("min", width=55, anchor="center")
        self.cat_tree.column("cmd", width=65, anchor="center")
        self.cat_tree.column("valeur", width=105, anchor="e")
        self.cat_tree.column("statut", width=100, anchor="center")

        # Tags de couleur pour les statuts
        self.cat_tree.tag_configure("En stock", foreground="#047857")
        self.cat_tree.tag_configure("Stock faible", foreground="#B45309")
        self.cat_tree.tag_configure("En rupture", foreground="#DC2626")
        self.cat_tree.tag_configure("En commande", foreground="#1D4ED8")
        self.cat_tree.tag_configure("odd_row", background="#F8FAFC")
        self.cat_tree.tag_configure("even_row", background="#FFFFFF")

        scroll_y = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.cat_tree.yview)
        self.cat_tree.configure(yscrollcommand=scroll_y.set)
        self.cat_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)

        # Barre d'actions en bas du tableau
        actions_bar = tk.Frame(self.tab_catalogue, bg="#FFFFFF", padx=10, pady=6)
        actions_bar.pack(fill=tk.X, pady=(4, 0))

        self.cat_count_label = tk.Label(actions_bar, text="0 article(s)", font=("Segoe UI", 9), bg="#FFFFFF", fg="#475569")
        self.cat_count_label.pack(side=tk.LEFT)

        btn_del = tk.Button(
            actions_bar, text="🗑️ Supprimer", bg="#EF4444", fg="white", font=("Segoe UI", 8, "bold"),
            relief=tk.FLAT, padx=8, pady=3, command=self.delete_selected_article
        )
        btn_del.pack(side=tk.RIGHT, padx=4)

        btn_edit = tk.Button(
            actions_bar, text="✏️ Modifier", bg="#3B82F6", fg="white", font=("Segoe UI", 8, "bold"),
            relief=tk.FLAT, padx=8, pady=3, command=self.edit_selected_article
        )
        btn_edit.pack(side=tk.RIGHT, padx=4)

    def load_catalogue_data(self):
        """Charge les articles dans le tableau du catalogue."""
        query = self.cat_search_var.get().strip()
        cat = self.cat_filter_var.get()
        statut = self.status_filter_var.get()

        articles = database.get_articles(
            query=query if query else None,
            categorie=cat if cat != "Toutes" else None,
            statut=statut if statut != "Tous" else None
        )

        for row in self.cat_tree.get_children():
            self.cat_tree.delete(row)

        for idx, a in enumerate(articles):
            p_str = format_fcfa(a['prix_vente']) if a['prix_vente'] > 0 else "À renseigner"
            v_str = format_fcfa(a['valeur_stock'])
            status_tag = a['statut_disponibilite']
            parity_tag = "even_row" if idx % 2 == 0 else "odd_row"

            self.cat_tree.insert("", tk.END, values=(
                a['id'],
                a['nom'],
                a['categorie'],
                a['unite'],
                p_str,
                format_qty(a['stock_actuel']),
                format_qty(a['stock_min']),
                format_qty(a['en_commande']),
                v_str,
                a['statut_disponibilite']
            ), tags=(status_tag, parity_tag))

        self.cat_count_label.config(text=f"{len(articles)} article(s) trouvé(s)")

    # =========================================================================
    # ONGLET 3: ALERTES & RÉASSORT
    # =========================================================================
    def build_alertes_tab(self):
        top_frame = tk.Frame(self.tab_alertes, bg="#FFFFFF", padx=12, pady=8)
        top_frame.pack(fill=tk.X, pady=(0, 6))

        tk.Label(
            top_frame,
            text="Articles en Rupture & Besoins de Réassort :",
            font=("Segoe UI", 10, "bold"),
            bg="#FFFFFF",
            fg="#0F172A"
        ).pack(side=tk.LEFT)

        self.lbl_alert_budget = tk.Label(
            top_frame,
            text="Budget estimé : 0 FCFA",
            font=("Segoe UI", 9, "bold"),
            fg="#B45309",
            bg="#FFFFFF"
        )
        self.lbl_alert_budget.pack(side=tk.RIGHT, padx=10)

        tree_frame = ttk.Frame(self.tab_alertes)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        cols = ("id", "nom", "cat", "stock", "min", "cmd", "besoin", "prix", "budget", "fournisseur")
        self.alerts_tree = ttk.Treeview(tree_frame, columns=cols, show="headings")
        self.alerts_tree.heading("id", text="Code")
        self.alerts_tree.heading("nom", text="Désignation")
        self.alerts_tree.heading("cat", text="Rayon")
        self.alerts_tree.heading("stock", text="Stock")
        self.alerts_tree.heading("min", text="Min")
        self.alerts_tree.heading("cmd", text="En Cmd")
        self.alerts_tree.heading("besoin", text="Besoin Net")
        self.alerts_tree.heading("prix", text="P.U.")
        self.alerts_tree.heading("budget", text="Budget Estimé")
        self.alerts_tree.heading("fournisseur", text="Fournisseur Recommandé")

        self.alerts_tree.column("id", width=65, anchor="center")
        self.alerts_tree.column("nom", width=240)
        self.alerts_tree.column("cat", width=160)
        self.alerts_tree.column("stock", width=50, anchor="center")
        self.alerts_tree.column("min", width=50, anchor="center")
        self.alerts_tree.column("cmd", width=60, anchor="center")
        self.alerts_tree.column("besoin", width=75, anchor="center")
        self.alerts_tree.column("prix", width=80, anchor="e")
        self.alerts_tree.column("budget", width=95, anchor="e")
        self.alerts_tree.column("fournisseur", width=180)

        self.alerts_tree.tag_configure("odd_row", background="#F8FAFC")
        self.alerts_tree.tag_configure("even_row", background="#FFFFFF")

        scroll_y = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.alerts_tree.yview)
        self.alerts_tree.configure(yscrollcommand=scroll_y.set)
        self.alerts_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)

    def load_alerts_data(self):
        alerts = database.get_alertes_reassort()
        for row in self.alerts_tree.get_children():
            self.alerts_tree.delete(row)

        total_budget = 0.0
        for idx, a in enumerate(alerts):
            b_val = float(a.get('besoin_budget_estime', 0.0))
            total_budget += b_val
            p_str = format_fcfa(a['prix_vente']) if a['prix_vente'] > 0 else "-"
            b_str = format_fcfa(b_val)
            parity_tag = "even_row" if idx % 2 == 0 else "odd_row"

            self.alerts_tree.insert("", tk.END, values=(
                a['id'],
                a['nom'],
                a['categorie'],
                format_qty(a['stock_actuel']),
                format_qty(a['stock_min']),
                format_qty(a['en_commande']),
                f"{format_qty(a['besoin_quantite'])} {a['unite']}",
                p_str,
                b_str,
                a.get('fournisseur', '')
            ), tags=(parity_tag,))

        self.lbl_alert_budget.config(text=f"Budget réassort estimé : {format_fcfa(total_budget)}")

    # =========================================================================
    # ONGLET 4: SYNCHRONISATION EXCEL & SÉCURITÉ
    # =========================================================================
    def build_sync_tab(self):
        container = tk.Frame(self.tab_sync, padx=25, pady=25, bg="#F1F5F9")
        container.pack(fill=tk.BOTH, expand=True)

        card1 = tk.LabelFrame(
            container, text=" Synchronisation avec le Classeur Excel Officiel ",
            font=("Segoe UI", 10, "bold"), fg="#1E293B", bg="#FFFFFF", padx=15, pady=15
        )
        card1.pack(fill=tk.X, pady=(0, 15))

        tk.Label(
            card1,
            text="Exportez ou importez l'intégralité du catalogue vers le classeur Excel DIADJI_FAMILY_TABLEAU_DE_BORD.xlsx.",
            font=("Segoe UI", 9), bg="#FFFFFF", fg="#475569"
        ).pack(anchor=tk.W, pady=(0, 10))

        btn_box1 = tk.Frame(card1, bg="#FFFFFF")
        btn_box1.pack(anchor=tk.W)

        btn_exp = tk.Button(
            btn_box1, text="📥 Exporter vers un nouveau fichier Excel (.xlsx)", bg="#059669", fg="white",
            font=("Segoe UI", 9, "bold"), relief=tk.FLAT, padx=12, pady=6, command=self.export_excel_action
        )
        btn_exp.pack(side=tk.LEFT, padx=(0, 10))

        btn_imp = tk.Button(
            btn_box1, text="📤 Importer / Mettre à jour depuis un fichier Excel (.xlsx)", bg="#2563EB", fg="white",
            font=("Segoe UI", 9, "bold"), relief=tk.FLAT, padx=12, pady=6, command=self.import_excel_action
        )
        btn_imp.pack(side=tk.LEFT)

        card2 = tk.LabelFrame(
            container, text=" Sauvegarde & Sécurité de la Base de Données Embarquée ",
            font=("Segoe UI", 10, "bold"), fg="#1E293B", bg="#FFFFFF", padx=15, pady=15
        )
        card2.pack(fill=tk.X)

        tk.Label(
            card2,
            text="Fichier SQLite : magasin.db (ultra-robuste, embarqué, 0 configuration serveur externe requise).",
            font=("Segoe UI", 9), bg="#FFFFFF", fg="#475569"
        ).pack(anchor=tk.W, pady=(0, 10))

        btn_backup = tk.Button(
            card2, text="💾 Sauvegarder une copie de secours de magasin.db", bg="#0F172A", fg="white",
            font=("Segoe UI", 9, "bold"), relief=tk.FLAT, padx=12, pady=6, command=self.backup_db_action
        )
        btn_backup.pack(anchor=tk.W)

    def export_excel_action(self):
        filepath = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Classeur Excel", "*.xlsx")],
            initialfile="DIADJI_FAMILY_TABLEAU_DE_BORD.xlsx"
        )
        if filepath:
            try:
                database.export_to_excel(filepath)
                messagebox.showinfo("Export Réussi", f"Classeur Excel officiel exporté avec succès :\n{filepath}")
            except Exception as e:
                messagebox.showerror("Erreur d'exportation", str(e))

    def import_excel_action(self):
        filepath = filedialog.askopenfilename(
            filetypes=[("Classeur Excel", "*.xlsx")]
        )
        if filepath:
            try:
                res = database.import_from_excel(filepath)
                msg = (
                    f"✓ Synchronisation Excel terminée avec succès !\n\n"
                    f"• Articles mis à jour   : {res['mis_a_jour']}\n"
                    f"• Nouveaux articles     : {res['ajoutes']}\n"
                    f"• Lignes ignorées       : {res['ignores']}\n"
                )
                messagebox.showinfo("Import Réussi", msg)
                self.refresh_all_data()
            except Exception as e:
                messagebox.showerror("Erreur d'importation", str(e))

    def backup_db_action(self):
        filepath = filedialog.asksaveasfilename(
            defaultextension=".db",
            filetypes=[("Base SQLite", "*.db")],
            initialfile="magasin_backup.db"
        )
        if filepath:
            try:
                import shutil
                shutil.copy2(database.DB_PATH, filepath)
                messagebox.showinfo("Sauvegarde Réussie", f"Copie de secours créée avec succès :\n{filepath}")
            except Exception as e:
                messagebox.showerror("Erreur", str(e))

    # =========================================================================
    # DIALOGUES MODAUX CRUD
    # =========================================================================
    def open_add_article_dialog(self):
        self.open_article_form_dialog(article=None)

    def edit_selected_article(self):
        selected = self.cat_tree.selection()
        if not selected:
            messagebox.showwarning("Sélection requise", "Veuillez sélectionner un article à modifier.")
            return
        art_id = self.cat_tree.item(selected[0])['values'][0]
        art = database.get_article_by_id(art_id)
        if art:
            self.open_article_form_dialog(article=art)

    def delete_selected_article(self):
        selected = self.cat_tree.selection()
        if not selected:
            messagebox.showwarning("Sélection requise", "Veuillez sélectionner un article à supprimer.")
            return
        values = self.cat_tree.item(selected[0])['values']
        art_id = values[0]
        nom = values[1]

        if messagebox.askyesno("Confirmation de suppression", f"Voulez-vous vraiment supprimer définitivement l'article :\n[{art_id}] {nom} ?"):
            try:
                database.delete_article(art_id)
                messagebox.showinfo("Supprimé", "Article supprimé du catalogue avec succès.")
                self.refresh_all_data()
            except Exception as e:
                messagebox.showerror("Suppression Impossible", str(e))

    def open_article_form_dialog(self, article=None):
        win = tk.Toplevel(self.root)
        win.title("Modifier Article" if article else "Nouvel Article")
        win.geometry("460x450")
        win.resizable(False, False)
        win.transient(self.root)
        win.grab_set()

        pad = {"padx": 15, "pady": 3}

        lbl_text = "Code Article (Identifiant fixe) :" if article else "Code Article (✨ Généré automatiquement) :"
        tk.Label(win, text=lbl_text, font=("Segoe UI", 9, "bold")).pack(anchor=tk.W, **pad)
        var_id = tk.StringVar(value=article['id'] if article else database.get_next_article_id())
        ent_id = ttk.Entry(win, textvariable=var_id, state="disabled" if article else "normal")
        ent_id.pack(fill=tk.X, **pad)

        tk.Label(win, text="Désignation de l'Article * :", font=("Segoe UI", 9, "bold")).pack(anchor=tk.W, **pad)
        var_nom = tk.StringVar(value=article['nom'] if article else "")
        ent_nom = ttk.Entry(win, textvariable=var_nom)
        ent_nom.pack(fill=tk.X, **pad)

        tk.Label(win, text="Rayon / Catégorie :", font=("Segoe UI", 9, "bold")).pack(anchor=tk.W, **pad)
        var_cat = tk.StringVar(value=article['categorie'] if article else "Électricité - Appareillage")
        cb_cat = ttk.Combobox(win, textvariable=var_cat, values=[
            "Électricité - Appareillage", "Électricité - Câbles & Gaines", "Plomberie & Raccords PVC",
            "Protection & Tableaux", "Éclairage LED & Luminaires", "Visserie, Boulonnerie & Fixation"
        ], state="readonly")
        cb_cat.pack(fill=tk.X, **pad)

        tk.Label(win, text="Prix de Vente (FCFA) :", font=("Segoe UI", 9, "bold")).pack(anchor=tk.W, **pad)
        var_prix = tk.StringVar(value=format_qty(article['prix_vente']) if article else "0")
        ent_prix = ttk.Entry(win, textvariable=var_prix)
        ent_prix.pack(fill=tk.X, **pad)

        tk.Label(win, text="Stock Actuel :", font=("Segoe UI", 9, "bold")).pack(anchor=tk.W, **pad)
        var_stock = tk.StringVar(value=format_qty(article['stock_actuel']) if article else "0")
        ent_stock = ttk.Entry(win, textvariable=var_stock)
        ent_stock.pack(fill=tk.X, **pad)

        tk.Label(win, text="Seuil Alerte Min :", font=("Segoe UI", 9, "bold")).pack(anchor=tk.W, **pad)
        var_min = tk.StringVar(value=format_qty(article['stock_min']) if article else "5")
        ent_min = ttk.Entry(win, textvariable=var_min)
        ent_min.pack(fill=tk.X, **pad)

        def save_action():
            try:
                nom = var_nom.get().strip()
                if not nom:
                    messagebox.showwarning("Validation", "Le nom de l'article est requis.", parent=win)
                    return
                prix = float(var_prix.get() or 0)
                stock = float(var_stock.get() or 0)
                s_min = float(var_min.get() or 0)

                payload = {
                    "id": var_id.get().strip() or database.get_next_article_id(),
                    "nom": nom,
                    "categorie": var_cat.get(),
                    "prix_vente": prix,
                    "stock_actuel": stock,
                    "stock_min": s_min
                }

                if article:
                    database.update_article(article['id'], payload)
                else:
                    database.create_article(payload)

                win.destroy()
                self.refresh_all_data()
                messagebox.showinfo("Enregistré", "Article enregistré avec succès dans la base DIADJI FAMILY !")
            except Exception as e:
                messagebox.showerror("Erreur", str(e), parent=win)

        btn_save = tk.Button(
            win, text="Enregistrer l'Article", bg="#2563EB", fg="white", font=("Segoe UI", 10, "bold"),
            relief=tk.FLAT, pady=7, command=save_action
        )
        btn_save.pack(fill=tk.X, padx=15, pady=(12, 10))

    def open_stock_in_dialog(self):
        selected = self.cat_tree.selection()
        if not selected:
            messagebox.showwarning("Sélection requise", "Veuillez sélectionner un article pour ajouter du stock.")
            return
        values = self.cat_tree.item(selected[0])['values']
        art_id = values[0]
        nom = values[1]

        win = tk.Toplevel(self.root)
        win.title("Entrée de Marchandise")
        win.geometry("400x270")
        win.resizable(False, False)
        win.transient(self.root)
        win.grab_set()

        pad = {"padx": 15, "pady": 4}
        tk.Label(win, text=f"Article : [{art_id}] {nom}", font=("Segoe UI", 9, "bold"), wraplength=360).pack(anchor=tk.W, padx=15, pady=(10, 5))

        tk.Label(win, text="Quantité Reçue / Ajoutée :", font=("Segoe UI", 9, "bold")).pack(anchor=tk.W, **pad)
        var_qty = tk.StringVar(value="10")
        ent_qty = ttk.Entry(win, textvariable=var_qty)
        ent_qty.pack(fill=tk.X, **pad)

        tk.Label(win, text="Référence Document / BL :", font=("Segoe UI", 9, "bold")).pack(anchor=tk.W, **pad)
        var_ref = tk.StringVar(value="BL-ARRIVAGE")
        ent_ref = ttk.Entry(win, textvariable=var_ref)
        ent_ref.pack(fill=tk.X, **pad)

        def save_in():
            try:
                qty = float(var_qty.get())
                ref = var_ref.get().strip()
                database.record_stock_movement(
                    article_id=art_id,
                    type_mouvement='ENTREE',
                    quantite=qty,
                    reference_doc=ref,
                    commentaire="Entrée rapide de marchandise"
                )
                win.destroy()
                self.refresh_all_data()
                messagebox.showinfo("Stock Mis à Jour", f"+{format_qty(qty)} unité(s) ajoutée(s) avec succès !")
            except Exception as e:
                messagebox.showerror("Erreur", str(e), parent=win)

        btn_val = tk.Button(
            win, text="Valider l'Entrée de Stock", bg="#059669", fg="white", font=("Segoe UI", 10, "bold"),
            relief=tk.FLAT, pady=7, command=save_in
        )
        btn_val.pack(fill=tk.X, padx=15, pady=(15, 10))


def main():
    root = tk.Tk()
    app = DiadjiFamilyDesktopApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
