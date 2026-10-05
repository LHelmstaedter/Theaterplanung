import calendar
import tkinter as tk
from datetime import date, timedelta
from itertools import islice
from tkinter import messagebox, simpledialog, ttk

from tkcalendar import DateEntry

from data import format_date
from .common import bind_row_menu, cell_at, show_cell_popup

COLUMNS = ("Datum", "Szene / Probe", "Rollen", "Abwesenheiten", "Vorgeschlagene Probe", "Durchgeführt", "Notiz")
COL_VORSCHLAG, COL_DONE = COLUMNS.index("Vorgeschlagene Probe"), COLUMNS.index("Durchgeführt")
COLUMN_WIDTHS = {"Datum": 90, "Szene / Probe": 140, "Rollen": 160, "Abwesenheiten": 130,
                 "Vorgeschlagene Probe": 175, "Durchgeführt": 95, "Notiz": 160}  # fits ~1000 px
MAX_REPEATS = 1000


def repeat_dates(start: date, end: date, mode: str):
    """Rehearsal dates from start to end; mode: Einmalig / Wöchentlich / Monatlich."""
    if mode == "Wöchentlich":
        d = start
        while d <= end:
            yield d
            d += timedelta(weeks=1)
    elif mode == "Monatlich":
        n = 0
        while True:
            year, month = divmod(start.month - 1 + n, 12)
            year, month = start.year + year, month + 1
            d = date(year, month, min(start.day, calendar.monthrange(year, month)[1]))
            if d > end:
                return
            yield d
            n += 1
    else:
        yield start


class SzenenAuswahl(tk.Frame):
    """'Allgemeine Probe' checkbox plus multi-select list of scenes."""

    def __init__(self, parent, height: int = 5) -> None:
        super().__init__(parent)
        self.var_general = tk.BooleanVar(value=False)
        tk.Checkbutton(
            self, text="Allgemeine Probe (ohne Szenen)", variable=self.var_general, command=self._toggle
        ).pack(anchor="w")
        frame = tk.Frame(self)
        frame.pack(fill="both", expand=True)
        self.lb = tk.Listbox(frame, selectmode=tk.MULTIPLE, height=height, exportselection=False)
        bar = tk.Scrollbar(frame, orient="vertical", command=self.lb.yview)
        self.lb.configure(yscrollcommand=bar.set)
        self.lb.pack(side="left", fill="both", expand=True)
        bar.pack(side="right", fill="y")
        self.names: list[str] = []

    def _toggle(self) -> None:
        self.lb.configure(state="disabled" if self.var_general.get() else "normal")

    def set_scenes(self, names, selected=None, general=None) -> None:
        """Fill the list; keeps the current selection unless `selected` is given."""
        selected = set(self.scenes() if selected is None else selected)
        if general is not None:
            self.var_general.set(general)
        self.lb.configure(state="normal")  # a disabled Listbox ignores changes
        self.names = sorted(names)
        self.lb.delete(0, "end")
        for i, name in enumerate(self.names):
            self.lb.insert("end", name)
            if name in selected:
                self.lb.selection_set(i)
        self._toggle()

    def scenes(self) -> list[str]:
        return [self.names[i] for i in self.lb.curselection()]

    def valid(self, parent=None) -> bool:
        if self.var_general.get() or self.scenes():
            return True
        messagebox.showwarning(
            "Fehler", "Bitte mindestens eine Szene auswählen oder 'Allgemeine Probe' aktivieren.", parent=parent
        )
        return False

    def result(self) -> list[str]:
        """Selected scenes; empty list = general rehearsal."""
        return [] if self.var_general.get() else self.scenes()


class ProbenTab(tk.Frame):
    """Rehearsals: general ("Probe") or with one or more scenes, optionally repeating."""

    def __init__(self, parent, controller) -> None:
        super().__init__(parent)
        self.controller = controller
        self.data = controller.data
        self._probe_by_item: dict[str, dict] = {}

        flt = tk.Frame(self)
        flt.pack(fill="x", padx=8, pady=(8, 4))
        tk.Label(flt, text="Filter Rolle:").grid(row=0, column=0, sticky="w")
        self.var_filter = tk.StringVar()
        entry = tk.Entry(flt, textvariable=self.var_filter)
        entry.grid(row=0, column=1, sticky="we", padx=4)
        entry.bind("<Return>", lambda e: self.refresh())
        tk.Button(flt, text="Filter anwenden", command=self.refresh).grid(row=0, column=2, padx=4)
        flt.columnconfigure(1, weight=1)

        self.tree = ttk.Treeview(self, columns=COLUMNS, show="headings", height=12)
        for c in COLUMNS:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=COLUMN_WIDTHS[c], anchor="center" if c == "Durchgeführt" else "w")
        self.tree.pack(fill="both", expand=True, padx=8, pady=(4, 8))
        self.tree.bind("<Double-1>", self._on_double_click)
        self.tree.bind("<Button-1>", self._on_click)

        self.menu = tk.Menu(self, tearoff=0)
        self.menu.add_command(label="Notiz bearbeiten", command=self.edit_notiz)
        self.menu.add_command(label="Szenen / Probe ändern", command=self.edit_szenen)
        self.menu.add_command(label="Probe löschen", command=self.delete_probe)
        bind_row_menu(self.tree, self.menu)

        plan = tk.Frame(self)
        plan.pack(fill="x", padx=8, pady=(0, 8))
        tk.Label(plan, text="Datum:").grid(row=0, column=0, sticky="w")
        self.cal_datum = DateEntry(plan, date_pattern="dd.MM.yyyy")
        self.cal_datum.grid(row=1, column=0, sticky="we", padx=4)
        tk.Label(plan, text="Szenen:").grid(row=0, column=1, sticky="w")
        self.auswahl = SzenenAuswahl(plan)
        self.auswahl.grid(row=1, column=1, sticky="nsew", padx=4)
        tk.Label(plan, text="Wiederholung:").grid(row=0, column=2, sticky="w")
        self.cb_repeat = ttk.Combobox(plan, state="readonly", values=["Einmalig", "Wöchentlich", "Monatlich"])
        self.cb_repeat.grid(row=1, column=2, sticky="we", padx=4)
        self.cb_repeat.set("Einmalig")
        tk.Label(plan, text="Wiederholen bis:").grid(row=0, column=3, sticky="w")
        self.cal_end = DateEntry(plan, date_pattern="dd.MM.yyyy", state="disabled")
        self.cal_end.grid(row=1, column=3, sticky="we", padx=4)
        self.cb_repeat.bind("<<ComboboxSelected>>", self._on_repeat_change)
        tk.Label(plan, text="Notiz:").grid(row=0, column=4, sticky="w")
        self.e_notiz = tk.Entry(plan)
        self.e_notiz.grid(row=1, column=4, sticky="we", padx=4)
        tk.Button(plan, text="Probe speichern", command=self.add_probe).grid(row=1, column=5, padx=6)
        for col in range(5):
            plan.columnconfigure(col, weight=1)

    def _on_repeat_change(self, _event=None) -> None:
        once = self.cb_repeat.get() == "Einmalig"
        self.cal_end.configure(state="disabled" if once else "normal")

    # ---- create / update ----
    def _add_or_update(self, d: date, szenen: list[str], notiz: str) -> None:
        """Adds a rehearsal. Scene rehearsals replace a general one on the same day;
        a general rehearsal is not added next to scene rehearsals."""
        same_day = [p for p in self.data.proben if p["datum"] == d]
        has_scenes = any(self.data.probe_szenen(p) for p in same_day)
        if not szenen and has_scenes:
            return
        if szenen:
            self.data.proben = [p for p in self.data.proben if p["datum"] != d or self.data.probe_szenen(p)]
            same_day = [p for p in same_day if self.data.probe_szenen(p)]
        existing = next((p for p in same_day if self.data.probe_szenen(p) == szenen), None)
        if existing:
            existing["notiz"] = notiz
        else:
            probe = {"datum": d, "notiz": notiz, "done": False}
            self.data.set_probe_szenen(probe, szenen)
            self.data.proben.append(probe)

    def add_probe(self) -> None:
        mode = self.cb_repeat.get() or "Einmalig"
        start = self.cal_datum.get_date()
        end = start if mode == "Einmalig" else self.cal_end.get_date()
        if end < start:
            messagebox.showwarning("Fehler", "Enddatum liegt vor dem Startdatum.")
            return
        if not self.auswahl.valid():
            return
        szenen, notiz = self.auswahl.result(), self.e_notiz.get().strip()
        for d in islice(repeat_dates(start, end, mode), MAX_REPEATS):
            self._add_or_update(d, szenen, notiz)
        self.controller.refresh_all()

    # ---- selected row ----
    def _selected(self) -> dict | None:
        sel = self.tree.selection()
        return self._probe_by_item.get(sel[0]) if sel else None

    def edit_notiz(self) -> None:
        probe = self._selected()
        if probe is None:
            return
        note = simpledialog.askstring(
            "Notiz bearbeiten", f"Notiz für {format_date(probe['datum'])} / {probe['szene'] or 'Probe'}:",
            initialvalue=probe.get("notiz", ""), parent=self,
        )
        if note is not None:
            probe["notiz"] = note
            self.controller.refresh_all()

    def edit_szenen(self) -> None:
        probe = self._selected()
        if probe is None:
            return
        win = tk.Toplevel(self)
        win.title(f"Szenen / Probe ändern ({format_date(probe['datum'])})")
        win.transient(self.winfo_toplevel())
        win.grab_set()
        tk.Label(win, text="Szenen wählen oder allgemeine Probe:").pack(anchor="w", padx=8, pady=(8, 4))
        auswahl = SzenenAuswahl(win, height=6)
        current = self.data.probe_szenen(probe)
        auswahl.set_scenes(self.data.szenen, selected=current, general=not current)
        auswahl.pack(fill="both", expand=True, padx=8, pady=4)

        def apply() -> None:
            if not auswahl.valid(win):
                return
            szenen = auswahl.result()
            others_have_scenes = any(
                self.data.probe_szenen(p) for p in self.data.proben if p["datum"] == probe["datum"] and p is not probe
            )
            if not szenen and others_have_scenes:
                messagebox.showwarning(
                    "Nicht möglich",
                    "An diesem Datum existieren szenenspezifische Proben.\n"
                    "Eine allgemeine Probe ist daher nicht zulässig.",
                    parent=win,
                )
                return
            self.data.set_probe_szenen(probe, szenen)
            win.destroy()
            self.controller.refresh_all()

        buttons = tk.Frame(win)
        buttons.pack(fill="x", pady=8, padx=8)
        tk.Button(buttons, text="Abbrechen", command=win.destroy).pack(side="left")
        tk.Button(buttons, text="Übernehmen", command=apply).pack(side="right")

    def delete_probe(self) -> None:
        probe = self._selected()
        if probe is not None:
            self.data.proben = [p for p in self.data.proben if p is not probe]
            self.controller.refresh_all()

    # ---- table ----
    def _absent(self, probe: dict) -> list[str]:
        """General rehearsal: all absent actors; scene rehearsal: only absent actors in its roles."""
        d = probe["datum"]
        if self.data.probe_szenen(probe):
            return self.data.absente_for_probe(d, probe["rollen"])
        return sorted(a for a in self.data.abwesenheiten if self.data.is_absent(a, d))

    def refresh(self) -> None:
        self.auswahl.set_scenes(self.data.szenen)
        self.tree.delete(*self.tree.get_children())
        self._probe_by_item.clear()
        query = self.var_filter.get().lower().strip()
        for probe in sorted(self.data.proben, key=lambda p: p["datum"]):
            rollen = probe["rollen"]
            if query and rollen and query not in ", ".join(rollen).lower():
                continue  # the role filter only hides scene rehearsals
            item = self.tree.insert("", "end", values=(
                format_date(probe["datum"]), probe["szene"] or "Probe", ", ".join(rollen) or "-",
                ", ".join(self._absent(probe)) or "-", "Klicken für Vorschlag",
                "[x]" if probe.get("done") else "[ ]", probe.get("notiz", ""),
            ))
            self._probe_by_item[item] = probe

    # ---- clicks ----
    def _on_double_click(self, event) -> None:
        """Cell popup, except in the two clickable columns."""
        hit = cell_at(self.tree, event)
        if hit and hit[1] not in (COL_DONE, COL_VORSCHLAG):
            show_cell_popup(event)

    def _on_click(self, event) -> None:
        hit = cell_at(self.tree, event)
        if not hit or hit[0] not in self._probe_by_item:
            return
        probe = self._probe_by_item[hit[0]]
        if hit[1] == COL_DONE:
            probe["done"] = not probe.get("done")
            self.controller.refresh_all()
        elif hit[1] == COL_VORSCHLAG:
            self._open_suggestions(probe)

    def _open_suggestions(self, probe: dict) -> None:
        d = probe["datum"]
        vorschlaege = self.data.vorgeschlagene_proben_fuer_datum(d)
        if not vorschlaege:
            messagebox.showinfo("Vorschlag", "Keine Szenen vorhanden.")
            return
        win = tk.Toplevel(self)
        win.title(f"Vorgeschlagene Proben am {format_date(d)}")
        win.transient(self.winfo_toplevel())
        win.grab_set()
        container = tk.Frame(win)
        container.pack(fill="both", expand=True, padx=8, pady=8)

        current = self.data.probe_szenen(probe)
        checks: dict[str, tk.BooleanVar] = {}
        for v in vorschlaege:
            text = (
                f"Szene: {v['szene']}\n"
                f"Gesamtwert: {v['score']}\n"
                f"Geprobt: {self.data.geprobt_text(v['szene'])}\n"
                f"Anwesende Rollen: {', '.join(v['anwesend']) or '-'}\n"
                f"Fehlende Rollen: {', '.join(v['fehlende']) or 'keine'}"
            )
            checks[v["szene"]] = tk.BooleanVar(value=v["szene"] in current)
            tk.Checkbutton(container, text=text, justify="left", anchor="w", variable=checks[v["szene"]]).pack(
                fill="x", padx=4, pady=4, anchor="w"
            )

        def apply() -> None:
            # scenes not shown in the suggestions stay as they are
            kept = [s for s in current if s not in checks]
            self.data.set_probe_szenen(probe, kept + [s for s, var in checks.items() if var.get()])
            win.destroy()
            self.controller.refresh_all()

        def set_all(flag: bool) -> None:
            for var in checks.values():
                var.set(flag)

        buttons = tk.Frame(win)
        buttons.pack(fill="x", padx=8, pady=(0, 8))
        tk.Button(buttons, text="Alle auswählen", command=lambda: set_all(True)).pack(side="left", padx=4)
        tk.Button(buttons, text="Alle abwählen", command=lambda: set_all(False)).pack(side="left", padx=4)
        tk.Button(buttons, text="Übernehmen", command=apply).pack(side="right", padx=4)
        tk.Button(buttons, text="Abbrechen", command=win.destroy).pack(side="right", padx=4)

    # ---- called by the calendar tab ----
    def focus_probe(self, probe: dict) -> None:
        for item, p in self._probe_by_item.items():
            if p is probe:
                self.tree.selection_set(item)
                self.tree.focus(item)
                self.tree.see(item)
                return
