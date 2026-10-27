"""Offline inventory manager for individually tracked electronic assets."""

from __future__ import annotations

import tkinter as tk
import sqlite3
from datetime import date
from decimal import Decimal, InvalidOperation
from tkinter import filedialog, messagebox, ttk

from app_resources import resource_path
from history_export import (
    HISTORY_HEADERS,
    export_history_png,
    export_history_xlsx,
    export_inventory_png,
    export_inventory_xlsx,
)
from inventory_store import InventoryStore


PAPER = "#FFFAFA"
INK = "#111111"
SURFACE = "#FFFFFF"
MUTED = "#686868"


class TrackRightApp:
    def __init__(self, root: tk.Tk, store: InventoryStore) -> None:
        self.root = root
        self.store = store
        root.title("TrackRight - Offline Electronic Inventory")
        root.geometry("1180x760")
        root.minsize(900, 620)
        self._configure_style()

        self.brand_image = tk.PhotoImage(
            file=str(resource_path("assets/trackright_logo.png"))
        )
        header = ttk.Frame(root, style="Hero.TFrame", padding=(22, 10))
        header.pack(fill="x")
        ttk.Label(
            header,
            image=self.brand_image,
            style="BrandLogo.TLabel",
        ).pack(side="left", padx=(0, 18))
        brand_copy = ttk.Frame(header, style="Hero.TFrame")
        brand_copy.pack(side="left", fill="y", pady=(9, 0))
        ttk.Label(
            brand_copy, text="KPMTECH SOLUTIONS", style="CompanyBrand.TLabel"
        ).pack(anchor="w")
        ttk.Label(
            brand_copy, text="TRACKRIGHT  /  INVENTORY", style="ProductBrand.TLabel"
        ).pack(anchor="w", pady=(4, 2))
        ttk.Label(
            brand_copy,
            text="Crafting seamless digital experiences",
            style="Tagline.TLabel",
        ).pack(anchor="w")
        ttk.Label(
            header,
            text="OFFLINE  |  LOCAL DATABASE",
            style="Status.TLabel",
            padding=(10, 5),
        ).pack(side="right")
        ttk.Label(
            root,
            text="Track purchased electronics, transfers, and asset condition.",
            style="Subtitle.TLabel",
            padding=(22, 8),
        ).pack(fill="x")

        notebook = ttk.Notebook(root)
        notebook.pack(fill="both", expand=True, padx=16, pady=(0, 12))
        self.notebook = notebook
        self.dashboard_tab = ttk.Frame(notebook, padding=16)
        self.purchase_tab = ttk.Frame(notebook)
        self.movement_tab = ttk.Frame(notebook)
        self.history_tab = ttk.Frame(notebook)
        notebook.add(self.dashboard_tab, text="Inventory")
        notebook.add(self.purchase_tab, text="1. Purchase Intake")
        notebook.add(self.movement_tab, text="2. Movement & Transfer")
        notebook.add(self.history_tab, text="3. History")

        self._build_dashboard()
        self._build_purchase_tab()
        self._build_movement_tab()
        self._build_history_tab()
        notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)

        footer = ttk.Frame(root, padding=(16, 0, 16, 10))
        footer.pack(fill="x")
        ttk.Label(
            footer,
            text=f"Saved on this computer: {store.database_path}",
            style="Footer.TLabel",
        ).pack(side="left")
        ttk.Button(
            footer, text="Refresh inventory", command=self.refresh_inventory
        ).pack(side="right")
        self.refresh_inventory()

    def _configure_style(self) -> None:
        style = ttk.Style(self.root)
        if "clam" in style.theme_names():
            style.theme_use("clam")
        self.root.configure(background=PAPER)
        style.configure("TFrame", background=PAPER)
        style.configure("Hero.TFrame", background=PAPER)
        style.configure("BrandLogo.TLabel", background=PAPER)
        style.configure(
            "CompanyBrand.TLabel",
            background=PAPER,
            foreground=INK,
            font=("TkDefaultFont", 17, "bold"),
        )
        style.configure(
            "ProductBrand.TLabel",
            background=PAPER,
            foreground=INK,
            font=("TkDefaultFont", 10, "bold"),
        )
        style.configure(
            "Tagline.TLabel",
            background=PAPER,
            foreground=MUTED,
            font=("TkDefaultFont", 9),
        )
        style.configure(
            "Status.TLabel",
            background=INK,
            foreground=SURFACE,
            font=("TkDefaultFont", 9, "bold"),
        )
        style.configure(
            "Subtitle.TLabel",
            background=PAPER,
            foreground=MUTED,
            font=("TkDefaultFont", 10),
        )
        style.configure("TNotebook", background=PAPER, tabmargins=(3, 4, 3, 0))
        style.configure(
            "TNotebook.Tab",
            background="#F0ECEC",
            foreground=INK,
            padding=(16, 9),
            font=("TkDefaultFont", 10),
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", INK)],
            foreground=[("selected", SURFACE)],
        )
        style.configure("TLabel", background=PAPER, foreground=INK)
        style.configure("TLabelFrame", background=PAPER, foreground=INK)
        style.configure("TLabelFrame.Label", background=PAPER, foreground=INK)
        style.configure(
            "TEntry",
            fieldbackground=SURFACE,
            foreground=INK,
            insertcolor=INK,
        )
        style.configure(
            "TCombobox",
            fieldbackground=SURFACE,
            foreground=INK,
            selectbackground=INK,
            selectforeground=SURFACE,
        )
        style.configure(
            "Treeview",
            rowheight=28,
            background=SURFACE,
            fieldbackground=SURFACE,
            foreground=INK,
            font=("TkDefaultFont", 10),
        )
        style.configure(
            "Treeview.Heading",
            background="#E9E5E5",
            foreground=INK,
            font=("TkDefaultFont", 9, "bold"),
            padding=(7, 8),
        )
        style.map(
            "Treeview",
            background=[("selected", "#D9D3D3")],
            foreground=[("selected", INK)],
        )
        style.configure(
            "Primary.TButton",
            background=INK,
            foreground=SURFACE,
            font=("TkDefaultFont", 10, "bold"),
            padding=(12, 8),
        )
        style.map(
            "Primary.TButton",
            background=[("active", "#333333"), ("pressed", "#000000")],
            foreground=[("active", SURFACE), ("pressed", SURFACE)],
        )
        style.configure("Footer.TLabel", background=PAPER, foreground=MUTED)

    def _build_dashboard(self) -> None:
        title_row = ttk.Frame(self.dashboard_tab)
        title_row.pack(fill="x")
        ttk.Label(
            title_row, text="Inventory overview", font=("TkDefaultFont", 17, "bold")
        ).pack(side="left")
        ttk.Button(
            title_row,
            text="+  Record purchase",
            style="Primary.TButton",
            command=lambda: self.notebook.select(self.purchase_tab),
        ).pack(side="right")
        ttk.Label(
            self.dashboard_tab,
            text="Search by asset tag, model, location, company, or condition.",
            style="Footer.TLabel",
        ).pack(anchor="w", pady=(4, 12))

        summary = ttk.Frame(self.dashboard_tab)
        summary.pack(fill="x", pady=(0, 14))
        self.total_assets_value = self._summary_card(summary, 0, "ASSETS TRACKED")
        self.in_storage_value = self._summary_card(summary, 1, "IN SAMAR")
        self.companies_value = self._summary_card(summary, 2, "COMPANIES")

        search_row = ttk.Frame(self.dashboard_tab)
        search_row.pack(fill="x", pady=(0, 8))
        ttk.Label(search_row, text="Find an asset").pack(side="left", padx=(0, 8))
        self.inventory_search = ttk.Entry(search_row)
        self.inventory_search.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.inventory_search.bind("<Return>", self._search_inventory_return)
        ttk.Button(
            search_row, text="Search", command=self.refresh_inventory
        ).pack(side="left")
        ttk.Button(
            search_row, text="Clear", command=self.clear_inventory_search
        ).pack(side="left", padx=(6, 0))

        filter_row = ttk.Frame(self.dashboard_tab)
        filter_row.pack(fill="x", pady=(0, 8))
        ttk.Label(filter_row, text="Product").pack(side="left", padx=(0, 5))
        self.inventory_product_filter = ttk.Combobox(
            filter_row, state="readonly", width=18
        )
        self.inventory_product_filter.pack(side="left", padx=(0, 12))
        ttk.Label(filter_row, text="Company").pack(side="left", padx=(0, 5))
        self.inventory_company_filter = ttk.Combobox(
            filter_row, state="readonly", width=22
        )
        self.inventory_company_filter.pack(side="left", padx=(0, 8))
        ttk.Label(filter_row, text="Location").pack(side="left", padx=(0, 5))
        self.inventory_location_filter = ttk.Combobox(
            filter_row, state="readonly", width=16
        )
        self.inventory_location_filter.pack(side="left", padx=(0, 8))
        ttk.Button(
            filter_row, text="Apply filters", command=self.refresh_inventory
        ).pack(side="left")

        download_row = ttk.Frame(self.dashboard_tab)
        download_row.pack(fill="x", pady=(0, 8))
        ttk.Label(
            download_row,
            text="Download the filtered current inventory:",
            style="Footer.TLabel",
        ).pack(side="left")
        ttk.Button(
            download_row,
            text="Download Excel",
            command=self.export_inventory_excel,
        ).pack(side="right", padx=(8, 0))
        ttk.Button(
            download_row,
            text="Download PNG",
            command=self.export_inventory_image,
        ).pack(side="right")

        columns = (
            "Asset tag",
            "Model / variety",
            "Condition",
            "Current location",
            "Company",
            "Purchase date",
            "Cost",
        )
        self.inventory_result_label = ttk.Label(
            self.dashboard_tab, text="", style="Footer.TLabel"
        )
        self.inventory_result_label.pack(anchor="w", pady=(0, 4))
        table_frame = ttk.Frame(self.dashboard_tab)
        table_frame.pack(fill="both", expand=True)
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)
        self.inventory_tree = ttk.Treeview(
            table_frame, columns=columns, show="headings", height=12
        )
        widths = (140, 190, 115, 160, 160, 115, 100)
        for column, width in zip(columns, widths):
            self.inventory_tree.heading(column, text=column)
            self.inventory_tree.column(
                column, width=width, minwidth=75, stretch=True
            )
        self.inventory_tree.tag_configure("alternate", background="#F5F8FB")
        self.inventory_tree.bind("<Double-1>", self._open_selected_asset)
        y_scroll = ttk.Scrollbar(
            table_frame, orient="vertical", command=self.inventory_tree.yview
        )
        x_scroll = ttk.Scrollbar(
            table_frame, orient="horizontal", command=self.inventory_tree.xview
        )
        self.inventory_tree.configure(
            yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set
        )
        self.inventory_tree.grid(row=0, column=0, sticky="nsew")
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll.grid(row=1, column=0, sticky="ew")

        actions = ttk.Frame(self.dashboard_tab)
        actions.pack(fill="x", pady=(10, 0))
        ttk.Label(
            actions, text="Tip: double-click an asset to record a movement."
        ).pack(side="left")
        ttk.Button(
            actions,
            text="View selected history",
            command=self._view_selected_history,
        ).pack(side="right")
        ttk.Button(
            actions,
            text="Record movement",
            command=self._move_selected_asset,
        ).pack(side="right", padx=(0, 8))

    @staticmethod
    def _summary_card(parent: ttk.Frame, column: int, title: str) -> ttk.Label:
        card = ttk.LabelFrame(parent, text=title, padding=(14, 8))
        card.grid(row=0, column=column, sticky="ew", padx=(0, 10))
        parent.columnconfigure(column, weight=1)
        value = ttk.Label(card, text="0", font=("TkDefaultFont", 19, "bold"))
        value.pack(anchor="w", pady=(2, 4))
        return value

    def _on_tab_changed(self, event: tk.Event) -> None:
        if (
            event.widget is self.notebook
            and self.notebook.select() == str(self.dashboard_tab)
        ):
            self.refresh_inventory()

    def _search_inventory_return(self, event: tk.Event) -> None:
        if event.widget is self.inventory_search:
            self.refresh_inventory()

    def _search_history_return(self, event: tk.Event) -> None:
        if event.widget is self.history_serial:
            self.fetch_history()

    def clear_inventory_search(self) -> None:
        self.inventory_search.delete(0, tk.END)
        self.inventory_product_filter.set("All products")
        self.inventory_company_filter.set("All companies")
        self.inventory_location_filter.set("All locations")
        self.refresh_inventory()

    @staticmethod
    def _update_filter(
        control: ttk.Combobox, label: str, options: list[str]
    ) -> None:
        current = control.get()
        values = [label, *options]
        control.configure(values=values)
        control.set(current if current in values else label)

    def refresh_inventory(self) -> None:
        try:
            self._update_filter(
                self.inventory_product_filter,
                "All products",
                sorted(
                    {
                        str(row["variety_name"])
                        for row in self.store.list_inventory()
                        if row["variety_name"]
                    },
                    key=str.casefold,
                ),
            )
            self._update_filter(
                self.inventory_company_filter,
                "All companies",
                self.store.list_companies(),
            )
            all_rows = self.store.list_inventory()
            self._update_filter(
                self.inventory_location_filter,
                "All locations",
                sorted(
                    {
                        str(row["to_location"])
                        for row in all_rows
                        if row["to_location"]
                    },
                    key=str.casefold,
                ),
            )
            product = self.inventory_product_filter.get()
            company = self.inventory_company_filter.get()
            location = self.inventory_location_filter.get()
            rows = self.store.list_inventory(
                self.inventory_search.get(),
                "" if product == "All products" else product,
                "" if company == "All companies" else company,
                "" if location == "All locations" else location,
            )
        except sqlite3.Error as error:
            messagebox.showerror(
                "Database error", f"Could not load inventory:\n{error}", parent=self.root
            )
            return

        for item in self.inventory_tree.get_children():
            self.inventory_tree.delete(item)
        if not rows:
            self.inventory_result_label.configure(
                text=(
                    "No assets yet. Record your first purchase."
                    if not self.inventory_search.get().strip()
                    else "No matching assets. Try a different search."
                )
            )
        else:
            self.inventory_result_label.configure(
                text=f"{len(rows)} asset(s) shown"
            )
        for index, row in enumerate(rows):
            self.inventory_tree.insert(
                "",
                "end",
                values=(
                    row["serial_number"],
                    row["variety_name"],
                    row["item_condition"] or "—",
                    row["to_location"] or "—",
                    row["destination_company"] or "—",
                    str(row["purchase_date"])[:10],
                    f"{float(row['purchase_cost']):,.2f}",
                ),
                tags=("alternate",) if index % 2 else (),
            )

        self.total_assets_value.configure(text=str(len(all_rows)))
        self.in_storage_value.configure(
            text=str(
                sum(row["to_location"] == "Samar" for row in all_rows)
            )
        )
        self.companies_value.configure(
            text=str(
                len(
                    {
                        row["destination_company"]
                        for row in all_rows
                        if row["destination_company"]
                        and row["destination_company"] != "Internal Store"
                    }
                )
            )
        )

    def _selected_serial(self) -> str | None:
        selected = self.inventory_tree.selection()
        if not selected:
            messagebox.showinfo(
                "Select an asset",
                "Select an asset in the inventory list first.",
                parent=self.root,
            )
            return None
        return str(self.inventory_tree.item(selected[0], "values")[0])

    def _move_selected_asset(self) -> None:
        serial = self._selected_serial()
        if serial is None:
            return
        self.movement_serial.delete(0, tk.END)
        self.movement_serial.insert(0, serial)
        self.load_asset()
        self.notebook.select(self.movement_tab)

    def _open_selected_asset(self, event: tk.Event) -> None:
        if event.widget is self.inventory_tree:
            item = self.inventory_tree.identify_row(event.y)
            if item:
                self.inventory_tree.selection_set(item)
                self._move_selected_asset()

    def _view_selected_history(self) -> None:
        serial = self._selected_serial()
        if serial is None:
            return
        self.history_serial.set(serial)
        self.notebook.select(self.history_tab)
        self.fetch_history()

    @staticmethod
    def _add_entry(
        parent: ttk.LabelFrame, row: int, label: str, width: int = 34
    ) -> ttk.Entry:
        ttk.Label(parent, text=label).grid(
            row=row, column=0, sticky="w", padx=10, pady=5
        )
        entry = ttk.Entry(parent, width=width)
        entry.grid(row=row, column=1, sticky="w", padx=10, pady=5)
        return entry

    def _build_purchase_tab(self) -> None:
        ttk.Label(
            self.purchase_tab,
            text="Record a new electronic asset when it is purchased",
            font=("TkDefaultFont", 12, "bold"),
        ).pack(pady=12)
        form = ttk.LabelFrame(self.purchase_tab, text="Purchase details")
        form.pack(fill="x", padx=24, pady=10, ipadx=8, ipady=8)
        self.purchase_serial = self._add_entry(form, 0, "Serial number / asset tag:")
        ttk.Label(form, text="Device model:").grid(
            row=1, column=0, sticky="w", padx=10, pady=5
        )
        self.purchase_variety = ttk.Combobox(
            form, state="readonly", width=32, values=self.store.list_models()
        )
        self.purchase_variety.grid(row=1, column=1, sticky="w", padx=10, pady=5)
        self.purchase_variety.current(0)
        self.purchase_cost = self._add_entry(form, 2, "Purchase cost:")
        self.purchase_condition = self._add_entry(form, 3, "Initial condition:")
        self.purchase_handler = self._add_entry(form, 4, "Purchased by:")
        self.purchase_date = self._add_entry(form, 5, "Purchase date (YYYY-MM-DD):")
        self.purchase_date.insert(0, date.today().isoformat())
        self.purchase_condition.insert(0, "Brand New")
        ttk.Button(
            self.purchase_tab,
            text="Save Purchase",
            style="Primary.TButton",
            command=self.save_purchase,
        ).pack(pady=12)

    def _build_movement_tab(self) -> None:
        ttk.Label(
            self.movement_tab,
            text="Log a transfer, location change, company assignment, or condition",
            font=("TkDefaultFont", 12, "bold"),
        ).pack(pady=12)
        form = ttk.LabelFrame(self.movement_tab, text="Movement details")
        form.pack(fill="x", padx=24, pady=10, ipadx=8, ipady=8)
        self.movement_serial = self._add_entry(form, 0, "Serial number:")
        ttk.Button(
            form, text="Load current asset", command=self.load_asset
        ).grid(row=0, column=2, padx=8, pady=5)
        self.current_asset_label = ttk.Label(form, text="Current: not loaded")
        self.current_asset_label.grid(
            row=1, column=0, columnspan=3, sticky="w", padx=10, pady=5
        )
        self.movement_to = self._add_entry(form, 2, "New location:")
        self.movement_company = self._add_entry(form, 3, "Destination company:")
        self.movement_handler = self._add_entry(form, 4, "Moved by:")
        self.movement_condition = self._add_entry(form, 5, "Current condition:")
        self.movement_notes = self._add_entry(form, 6, "Notes:")
        self.movement_vehicle = self._add_entry(form, 7, "Vehicle registration:")
        self.movement_condition.insert(0, "Good")
        ttk.Button(
            self.movement_tab,
            text="Log Asset Movement",
            style="Primary.TButton",
            command=self.log_movement,
        ).pack(pady=12)

    def _build_history_tab(self) -> None:
        ttk.Label(
            self.history_tab,
            text="Filter asset history by device, product, company, and location; "
            "scroll the filter bar to see all options.",
            font=("TkDefaultFont", 12, "bold"),
        ).pack(pady=12)
        filter_bar = ttk.Frame(self.history_tab)
        filter_bar.pack(fill="x", padx=20, pady=5)
        filter_canvas = tk.Canvas(
            filter_bar,
            height=40,
            background=PAPER,
            borderwidth=0,
            highlightthickness=0,
        )
        filter_scrollbar = ttk.Scrollbar(
            filter_bar, orient="horizontal", command=filter_canvas.xview
        )
        filter_canvas.configure(xscrollcommand=filter_scrollbar.set)
        filter_canvas.pack(fill="x")
        filter_scrollbar.pack(fill="x")
        search_frame = ttk.Frame(filter_canvas)
        filter_window = filter_canvas.create_window(
            (0, 0), window=search_frame, anchor="nw"
        )
        search_frame.bind(
            "<Configure>",
            lambda _: filter_canvas.configure(scrollregion=filter_canvas.bbox("all")),
        )
        filter_canvas.bind(
            "<Configure>",
            lambda event: filter_canvas.itemconfigure(
                filter_window, height=event.height
            ),
        )
        ttk.Label(search_frame, text="Device / serial:").pack(side="left", padx=5)
        self.history_serial = ttk.Combobox(
            search_frame, state="readonly", width=24, values=["All devices"]
        )
        self.history_serial.set("All devices")
        self.history_serial.pack(side="left", padx=5)
        ttk.Label(search_frame, text="Product:").pack(side="left", padx=5)
        self.history_product_filter = ttk.Combobox(
            search_frame, state="readonly", width=17, values=["All products"]
        )
        self.history_product_filter.set("All products")
        self.history_product_filter.pack(side="left", padx=5)
        ttk.Label(search_frame, text="Company:").pack(side="left", padx=5)
        self.history_company_filter = ttk.Combobox(
            search_frame, state="readonly", width=18, values=["All companies"]
        )
        self.history_company_filter.set("All companies")
        self.history_company_filter.pack(side="left", padx=5)
        ttk.Label(search_frame, text="Location:").pack(side="left", padx=5)
        self.history_location_filter = ttk.Combobox(
            search_frame, state="readonly", width=16, values=["All locations"]
        )
        self.history_location_filter.set("All locations")
        self.history_location_filter.pack(side="left", padx=5)
        ttk.Button(
            search_frame, text="Search / filter", command=self.fetch_history
        ).pack(side="left", padx=5)

        columns = HISTORY_HEADERS
        table_frame = ttk.Frame(self.history_tab)
        table_frame.pack(fill="both", expand=True, padx=20, pady=10)
        self.history_tree = ttk.Treeview(
            table_frame, columns=columns, show="headings", height=15
        )
        widths = (155, 115, 115, 135, 125, 125, 140, 145, 110, 110, 220)
        for column, width in zip(columns, widths):
            self.history_tree.heading(column, text=column)
            self.history_tree.column(column, width=width, minwidth=70)
        scrollbar = ttk.Scrollbar(
            table_frame, orient="vertical", command=self.history_tree.yview
        )
        self.history_tree.configure(yscrollcommand=scrollbar.set)
        self.history_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        export_frame = ttk.Frame(self.history_tab)
        export_frame.pack(fill="x", padx=20, pady=(0, 12))
        ttk.Button(
            export_frame, text="Download filtered history (Excel)",
            command=self.export_history_excel,
        ).pack(side="right", padx=(8, 0))
        ttk.Button(
            export_frame, text="Download filtered history (PNG)",
            command=self.export_history_image,
        ).pack(side="right")

    def save_purchase(self) -> None:
        serial = self.purchase_serial.get().strip()
        variety = self.purchase_variety.get().strip()
        cost_text = self.purchase_cost.get().strip()
        condition = self.purchase_condition.get().strip()
        purchased_by = self.purchase_handler.get().strip()
        purchase_date = self.purchase_date.get().strip()
        if not all((serial, variety, cost_text, condition, purchased_by, purchase_date)):
            messagebox.showerror("Missing details", "Complete all purchase fields.")
            return
        try:
            date.fromisoformat(purchase_date)
        except ValueError:
            messagebox.showerror(
                "Invalid purchase date",
                "Enter a valid purchase date in YYYY-MM-DD format.",
            )
            return
        try:
            cost = Decimal(cost_text)
            if not cost.is_finite() or cost < 0:
                raise InvalidOperation
        except InvalidOperation:
            messagebox.showerror(
                "Invalid cost", "Purchase cost must be a non-negative number."
            )
            return
        try:
            self.store.create_purchase(
                serial, variety, cost, condition, purchased_by, purchase_date
            )
        except sqlite3.IntegrityError:
            messagebox.showerror(
                "Duplicate asset",
                f"Serial number '{serial}' already exists in inventory.",
            )
            return
        except sqlite3.Error as error:
            messagebox.showerror("Database error", f"Could not save purchase:\n{error}")
            return

        messagebox.showinfo("Saved", f"Asset {serial} was recorded.")
        for entry in (
            self.purchase_serial,
            self.purchase_cost,
            self.purchase_handler,
            self.purchase_date,
        ):
            entry.delete(0, tk.END)
        self.purchase_variety.current(0)
        self.purchase_date.insert(0, date.today().isoformat())
        self.purchase_condition.delete(0, tk.END)
        self.purchase_condition.insert(0, "Brand New")
        self.refresh_inventory()

    def load_asset(self) -> None:
        serial = self.movement_serial.get().strip()
        if not serial:
            messagebox.showerror("Missing serial", "Enter an asset serial number.")
            return
        try:
            state = self.store.current_state(serial)
        except sqlite3.Error as error:
            messagebox.showerror("Database error", f"Could not load asset:\n{error}")
            return
        if state is None:
            self.current_asset_label.configure(text="Current: asset not found")
            messagebox.showerror("Not found", f"Asset '{serial}' was not found.")
            return
        self.current_asset_label.configure(
            text=(
                f"Current: {state['variety_name']} | {state['to_location']} | "
                f"{state['destination_company']} | {state['item_condition']}"
            )
        )

    def log_movement(self) -> None:
        serial = self.movement_serial.get().strip()
        to_location = self.movement_to.get().strip()
        company = self.movement_company.get().strip()
        handler = self.movement_handler.get().strip()
        condition = self.movement_condition.get().strip()
        if not all((serial, to_location, company, handler, condition)):
            messagebox.showerror(
                "Missing details",
                "Serial number, new location, destination company, moved by, "
                "and condition are required.",
            )
            return
        try:
            self.store.record_movement(
                serial,
                to_location,
                company,
                handler,
                condition,
                self.movement_notes.get().strip(),
                self.movement_vehicle.get().strip(),
            )
        except ValueError as error:
            messagebox.showerror("Asset not found", str(error))
            return
        except sqlite3.Error as error:
            messagebox.showerror("Database error", f"Could not log movement:\n{error}")
            return

        messagebox.showinfo("Saved", f"Movement for asset {serial} was logged.")
        for entry in (
            self.movement_serial,
            self.movement_to,
            self.movement_company,
            self.movement_handler,
            self.movement_notes,
            self.movement_vehicle,
        ):
            entry.delete(0, tk.END)
        self.movement_condition.delete(0, tk.END)
        self.movement_condition.insert(0, "Good")
        self.current_asset_label.configure(text="Current: not loaded")
        self.refresh_inventory()

    def fetch_history(self) -> None:
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
        try:
            self._update_filter(
                self.history_serial, "All devices", self.store.list_devices()
            )
            self._update_filter(
                self.history_product_filter,
                "All products",
                sorted(
                    {
                        str(row["variety_name"])
                        for row in self.store.list_inventory()
                        if row["variety_name"]
                    },
                    key=str.casefold,
                ),
            )
            self._update_filter(
                self.history_company_filter,
                "All companies",
                self.store.list_companies(history=True),
            )
            self._update_filter(
                self.history_location_filter,
                "All locations",
                self.store.list_locations(),
            )
            serial = self.history_serial.get()
            product = self.history_product_filter.get()
            company = self.history_company_filter.get()
            location = self.history_location_filter.get()
            rows = self.store.history_records(
                "" if serial == "All devices" else serial,
                "" if product == "All products" else product,
                "" if company == "All companies" else company,
                "" if location == "All locations" else location,
            )
        except sqlite3.Error as error:
            messagebox.showerror("Database error", f"Could not retrieve history:\n{error}")
            return
        if not rows:
            return
        for row in rows:
            self.history_tree.insert(
                "",
                "end",
                values=tuple(
                    row[key]
                    for key in (
                        "movement_date", "purchase_date", "serial_number",
                        "variety_name", "from_location", "to_location",
                        "destination_company", "vehicle_registration", "moved_by",
                        "item_condition", "notes",
                    )
                ),
            )

    def _filtered_history_records(self) -> list[dict[str, object]]:
        serial = self.history_serial.get()
        product = self.history_product_filter.get()
        company = self.history_company_filter.get()
        location = self.history_location_filter.get()
        return self.store.history_records(
            "" if serial == "All devices" else serial,
            "" if product == "All products" else product,
            "" if company == "All companies" else company,
            "" if location == "All locations" else location,
        )

    def _export_history(self, file_type: str) -> None:
        try:
            rows = self._filtered_history_records()
        except sqlite3.Error as error:
            messagebox.showerror(
                "Database error", f"Could not retrieve history:\n{error}",
                parent=self.root,
            )
            return
        if not rows:
            messagebox.showinfo(
                "No history", "There is no history matching the selected filters.",
                parent=self.root,
            )
            return

        if file_type == "xlsx":
            path = filedialog.asksaveasfilename(
                parent=self.root,
                title="Download history as Excel",
                defaultextension=".xlsx",
                filetypes=[("Excel workbook", "*.xlsx")],
            )
        else:
            path = filedialog.asksaveasfilename(
                parent=self.root,
                title="Download history as PNG",
                defaultextension=".png",
                filetypes=[("PNG image", "*.png")],
            )
        if not path:
            return

        try:
            exporter = export_history_xlsx if file_type == "xlsx" else export_history_png
            exporter(path, rows)
        except (OSError, ValueError) as error:
            messagebox.showerror(
                "Export failed", f"Could not export history:\n{error}",
                parent=self.root,
            )
            return
        messagebox.showinfo(
            "Download complete", f"History downloaded to:\n{path}", parent=self.root
        )

    def _export_inventory(self, file_type: str) -> None:
        try:
            search = self.inventory_search.get()
            product = self.inventory_product_filter.get()
            company = self.inventory_company_filter.get()
            location = self.inventory_location_filter.get()
            rows = self.store.list_inventory(
                search,
                "" if product == "All products" else product,
                "" if company == "All companies" else company,
                "" if location == "All locations" else location,
            )
        except sqlite3.Error as error:
            messagebox.showerror(
                "Database error", f"Could not retrieve inventory:\n{error}",
                parent=self.root,
            )
            return
        if not rows:
            messagebox.showinfo(
                "No inventory",
                "There is no inventory matching the selected filters.",
                parent=self.root,
            )
            return

        extension, file_type_label = (
            ("xlsx", "Excel workbook") if file_type == "xlsx" else ("png", "PNG image")
        )
        path = filedialog.asksaveasfilename(
            parent=self.root,
            title=f"Download inventory as {file_type_label}",
            defaultextension=f".{extension}",
            filetypes=[(file_type_label, f"*.{extension}")],
        )
        if not path:
            return

        try:
            exporter = export_inventory_xlsx if file_type == "xlsx" else export_inventory_png
            exporter(path, rows)
        except (OSError, ValueError) as error:
            messagebox.showerror(
                "Download failed", f"Could not download inventory:\n{error}",
                parent=self.root,
            )
            return
        messagebox.showinfo(
            "Download complete", f"Inventory downloaded to:\n{path}", parent=self.root
        )

    def export_history_excel(self) -> None:
        self._export_history("xlsx")

    def export_history_image(self) -> None:
        self._export_history("png")

    def export_inventory_excel(self) -> None:
        self._export_inventory("xlsx")

    def export_inventory_image(self) -> None:
        self._export_inventory("png")


def main() -> None:
    store = InventoryStore()
    root = tk.Tk()
    TrackRightApp(root, store)
    root.mainloop()


if __name__ == "__main__":
    main()
