import tkinter as tk
from tkinter import messagebox, ttk

from tkcalendar import DateEntry

from data import format_date
from .common import bind_row_menu, open_filter_dialog, show_cell_popup

COLUMNS = ("Schauspieler", "Von", "Bis", "Verpasste Proben")


class AbwesenheitenTab(tk.Frame):
    def __init__(self, parent, controller) -> None:
        super().__init__(parent)
        self.controller = controller
        self.data = controller.data
        self.actor_filter: set[str] = set()      # empty = no filter
        self.filter_von = self.filter_bis = None  # optional date range filter
        self._item_ranges: dict[str, tuple] = {}  # row id -> (actor, von, bis)

        top = tk.Frame(self)
        top.pack(fill="x", padx=8, pady=(8, 4))
        tk.Label(top, text="Schauspieler:").grid(row=0, column=0, sticky="w")
        self.cb_actor = ttk.Combobox(top, state="readonly")
        self.cb_actor.grid(row=1, column=0, sticky="we", padx=(0, 6))
        tk.Label(top, text="Von:").grid(row=0, column=1, sticky="w")
        self.cal_von = DateEntry(top, date_pattern="dd.MM.yyyy")
        self.cal_von.grid(row=1, column=1, padx=4)
        tk.Label(top, text="Bis:").grid(row=0, column=2, sticky="w")
        self.cal_bis = DateEntry(top, date_pattern="dd.MM.yyyy")
        self.cal_bis.grid(row=1, column=2, padx=4)
        tk.Button(top, text="Hinzufügen", command=self.add).grid(row=1, column=3, padx=6)
        top.columnconfigure(0, weight=1)

        self.tree = ttk.Treeview(self, columns=COLUMNS, show="headings", height=12)
        for c in COLUMNS:
            if c == "Verpasste Proben":
                self.tree.heading(c, text=c)
            else:
                self.tree.heading(c, text=f"{c} ▼", command=lambda c=c: self._open_filter(c))
            self.tree.column(c, width=150, anchor="w")
        self.tree.pack(fill="both", expand=True, padx=8, pady=8)
        self.tree.bind("<Double-1>", show_cell_popup, add="+")

        self.menu = tk.Menu(self, tearoff=0)
        self.menu.add_command(label="Löschen", command=self.delete)
        bind_row_menu(self.tree, self.menu)

    def add(self) -> None:
        actor = self.cb_actor.get().strip()
        if not actor:
            messagebox.showwarning("Fehler", "Bitte Schauspieler auswählen.")
            return
        von, bis = self.cal_von.get_date(), self.cal_bis.get_date()
        self.data.abwesenheiten.setdefault(actor, []).append((von, max(von, bis)))
        self.controller.refresh_all()

    def delete(self) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        actor, von, bis = self._item_ranges[sel[0]]
        ranges = self.data.abwesenheiten.get(actor, [])
        if (von, bis) in ranges:
            ranges.remove((von, bis))
        if not ranges:
            self.data.abwesenheiten.pop(actor, None)
        self.controller.refresh_all()

    # ---- filters ----
    def _open_filter(self, column: str) -> None:
        if column == "Schauspieler":
            open_filter_dialog(
                self, "Filter: Schauspieler", sorted(self.data.abwesenheiten), self.actor_filter,
                lambda selected: self._apply(actor_filter=selected),
            )
        else:
            self._open_date_filter()

    def _open_date_filter(self) -> None:
        win = tk.Toplevel(self)
        win.title("Datumsfilter")
        win.transient(self.winfo_toplevel())
        win.grab_set()
        frm = tk.Frame(win)
        frm.pack(padx=8, pady=8)
        entries = []
        for row, (text, value) in enumerate((("Von:", self.filter_von), ("Bis:", self.filter_bis))):
            tk.Label(frm, text=text).grid(row=row, column=0, sticky="w")
            entry = DateEntry(frm, date_pattern="dd.MM.yyyy")
            if value is not None:
                entry.set_date(value)
            entry.grid(row=row, column=1, padx=(4, 8))
            entries.append(entry)

        def apply(reset: bool) -> None:
            win.destroy()
            if reset:
                self._apply(von=None, bis=None)
            else:
                von, bis = entries[0].get_date(), entries[1].get_date()
                self._apply(von=von, bis=max(von, bis))

        buttons = tk.Frame(win)
        buttons.pack(fill="x", padx=8, pady=(4, 8))
        tk.Button(buttons, text="Zurücksetzen", command=lambda: apply(True)).pack(side="left", padx=2)
        tk.Button(buttons, text="Filter anwenden", command=lambda: apply(False)).pack(side="right", padx=2)

    def _apply(self, **kw) -> None:
        self.actor_filter = kw.get("actor_filter", self.actor_filter)
        self.filter_von = kw.get("von", self.filter_von)
        self.filter_bis = kw.get("bis", self.filter_bis)
        self.refresh()

    def refresh(self) -> None:
        self.cb_actor["values"] = sorted(self.data.schauspieler)
        self.tree.delete(*self.tree.get_children())
        self._item_ranges.clear()
        for actor, ranges in sorted(self.data.abwesenheiten.items()):
            if self.actor_filter and actor not in self.actor_filter:
                continue
            for von, bis in ranges:
                # the absence range must overlap the filter range
                if (self.filter_von and bis < self.filter_von) or (self.filter_bis and von > self.filter_bis):
                    continue
                missed = sorted({
                    p["datum"] for p in self.data.proben
                    if von <= p["datum"] <= bis and any(self.data.rollen.get(r) == actor for r in p.get("rollen", []))
                })
                item = self.tree.insert("", "end", values=(
                    actor, format_date(von), format_date(bis), ", ".join(map(format_date, missed)) or "-",
                ))
                self._item_ranges[item] = (actor, von, bis)
