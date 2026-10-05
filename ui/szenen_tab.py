import tkinter as tk
from tkinter import messagebox, ttk

from data import format_date, format_range
from .common import RoleChecklist, bind_row_menu, cell_at, open_filter_dialog, show_cell_popup

COLUMNS = ("Szene", "Rollen", "Proben", "Geprobt", "Abwesend")
FILTER_COLUMNS = ("Szene", "Rollen", "Abwesend")
ABWESEND_COL = COLUMNS.index("Abwesend")


def parse_planned(text: str):
    """'' -> None, non-negative integer -> int, otherwise ValueError."""
    text = text.strip()
    if not text:
        return None
    value = int(text)
    if value < 0:
        raise ValueError
    return value


class SzenenTab(tk.Frame):
    def __init__(self, parent, controller) -> None:
        super().__init__(parent)
        self.controller = controller
        self.data = controller.data
        self.header_filters = {c: set() for c in FILTER_COLUMNS}  # empty set = no filter
        self._abw_details: dict[str, list[str]] = {}               # row id -> absence details

        top = tk.Frame(self)
        top.pack(fill="x", padx=8, pady=(8, 4))
        tk.Label(top, text="Name der Szene:").grid(row=0, column=0, sticky="w")
        self.e_szene = tk.Entry(top)
        self.e_szene.grid(row=1, column=0, sticky="we", padx=(0, 6))
        tk.Button(top, text="Szene hinzufügen", command=self.add).grid(row=1, column=1)
        tk.Label(top, text="Geplante Proben (optional):").grid(row=0, column=2, sticky="w")
        self.e_planned = tk.Entry(top, width=6)
        self.e_planned.grid(row=1, column=2, sticky="w", padx=(6, 0))
        top.columnconfigure(0, weight=1)

        box = tk.Frame(self)
        box.pack(fill="both", padx=8, pady=(6, 0))
        tk.Label(box, text="Rollen auswählen:").pack(anchor="w")
        self.roles = RoleChecklist(box, height=140)
        self.roles.pack(fill="both", expand=True)

        self.tree = ttk.Treeview(self, columns=COLUMNS, show="headings", height=12)
        for c in COLUMNS:
            if c in FILTER_COLUMNS:
                self.tree.heading(c, text=f"{c} ▼", command=lambda c=c: self._open_filter(c))
            else:
                self.tree.heading(c, text="Geprobt (✓)" if c == "Geprobt" else c)
            self.tree.column(c, width=150, anchor="w")
        self.tree.pack(fill="both", expand=True, padx=8, pady=(4, 8))
        self.tree.bind("<Double-1>", show_cell_popup, add="+")
        self.tree.bind("<Button-1>", self._on_click)

        self.menu = tk.Menu(self, tearoff=0)
        self.menu.add_command(label="Bearbeiten", command=self.edit)
        self.menu.add_command(label="Löschen", command=self.delete)
        bind_row_menu(self.tree, self.menu)

    # Row ids are the scene names, so selection() directly yields the scene.
    def _selected(self) -> str | None:
        sel = self.tree.selection()
        return sel[0] if sel else None

    def add(self) -> None:
        name = self.e_szene.get().strip()
        if not name:
            messagebox.showwarning("Fehler", "Bitte Namen eingeben.")
            return
        if name in self.data.szenen:
            messagebox.showwarning("Hinweis", "Szene existiert bereits (über Rechtsklick bearbeiten).")
            return
        try:
            planned = parse_planned(self.e_planned.get())
        except ValueError:
            messagebox.showwarning("Fehler", "Bitte eine nicht-negative ganze Zahl für 'Geplante Proben' eingeben.")
            return
        self.data.szenen[name] = self.roles.selected()
        if planned is not None:
            self.data.szenen_geplante_proben[name] = planned
        self.e_szene.delete(0, tk.END)
        self.e_planned.delete(0, tk.END)
        self.roles.clear()
        self.controller.refresh_all()

    def edit(self) -> None:
        old = self._selected()
        if old is None:
            return
        win = tk.Toplevel(self)
        win.title("Szene bearbeiten")
        win.transient(self.winfo_toplevel())
        win.grab_set()

        tk.Label(win, text="Szenenname:").pack(anchor="w", padx=8, pady=(8, 0))
        e_name = tk.Entry(win)
        e_name.insert(0, old)
        e_name.pack(fill="x", padx=8)
        tk.Label(win, text="Geplante Proben (optional):").pack(anchor="w", padx=8, pady=(8, 0))
        e_planned = tk.Entry(win)
        e_planned.insert(0, str(self.data.szenen_geplante_proben.get(old, "")))
        e_planned.pack(fill="x", padx=8)
        tk.Label(win, text="Rollen auswählen:").pack(anchor="w", padx=8, pady=(8, 0))
        roles = RoleChecklist(win, height=200)
        roles.set_roles(self.data.rollen, selected=self.data.szenen.get(old, []))
        roles.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        def save() -> None:
            new = e_name.get().strip()
            if not new:
                messagebox.showwarning("Fehler", "Name fehlt.", parent=win)
                return
            if new != old and new in self.data.szenen:
                messagebox.showwarning("Fehler", "Eine Szene mit diesem Namen existiert bereits.", parent=win)
                return
            try:
                planned = parse_planned(e_planned.get())
            except ValueError:
                messagebox.showwarning(
                    "Fehler", "Bitte eine nicht-negative ganze Zahl für 'Geplante Proben' eingeben.", parent=win
                )
                return
            self.data.rename_scene(old, new)
            self.data.szenen[new] = roles.selected()
            if planned is None:
                self.data.szenen_geplante_proben.pop(new, None)
            else:
                self.data.szenen_geplante_proben[new] = planned
            win.destroy()
            self.controller.refresh_all()

        tk.Button(win, text="Speichern", command=save).pack(pady=(0, 8))

    def delete(self) -> None:
        name = self._selected()
        if name is not None and messagebox.askyesno("Löschen", f"Szene '{name}' löschen?"):
            self.data.delete_scene(name)
            self.controller.refresh_all()

    # ---- filters ----
    def _filter_values(self, column: str) -> list[str]:
        if column == "Szene":
            return sorted(self.data.szenen)
        if column == "Rollen":
            return sorted({r for rollen in self.data.szenen.values() for r in rollen})
        return sorted(self.data.abwesenheiten)  # "Abwesend": actors with absences

    def _open_filter(self, column: str) -> None:
        open_filter_dialog(
            self, f"Filter: {column}", self._filter_values(column), self.header_filters[column],
            lambda selected: self._set_filter(column, selected),
        )

    def _set_filter(self, column: str, selected: set) -> None:
        self.header_filters[column] = selected
        self.refresh()

    # ---- absence details ----
    def _absence_details(self, szene: str, rollen: list[str]) -> tuple[set, list[str]]:
        """(absent actors, detail lines) for a scene.
        With rehearsals: only absences that fall on a rehearsal day of an actor in that rehearsal.
        Without rehearsals: all absence ranges of the actors in the scene."""
        actors = {self.data.rollen[r] for r in rollen if r in self.data.rollen}
        entries = set()
        scene_probes = self.data.proben_fuer_szene(szene)
        if scene_probes:
            for probe in scene_probes:
                for rolle in probe.get("rollen", []):
                    actor = self.data.rollen.get(rolle)
                    if actor in actors and self.data.is_absent(actor, probe["datum"]):
                        entries.add((actor, format_date(probe["datum"]), probe["datum"]))
        else:
            for actor in actors:
                for von, bis in self.data.abwesenheiten.get(actor, []):
                    entries.add((actor, format_range(von, bis), von))
        details = [f"{actor} ({text})" for actor, text, _ in sorted(entries, key=lambda e: (e[0], e[2]))]
        return {e[0] for e in entries}, details

    def refresh(self) -> None:
        self.roles.set_roles(self.data.rollen)
        self.tree.delete(*self.tree.get_children())
        self._abw_details.clear()
        flt = self.header_filters
        for szene, rollen in sorted(self.data.szenen.items()):
            absent_actors, details = self._absence_details(szene, rollen)
            if (flt["Szene"] and szene not in flt["Szene"]
                    or flt["Rollen"] and not set(rollen) & flt["Rollen"]
                    or flt["Abwesend"] and not absent_actors & flt["Abwesend"]):
                continue
            probe_dates = sorted({p["datum"] for p in self.data.proben_fuer_szene(szene)})
            if not details:
                abw = "-"
            elif len(details) <= 3 and sum(map(len, details)) <= 60:
                abw = ", ".join(details)
            else:
                abw = f"{len(details)} Abw. …"
            self.tree.insert("", "end", iid=szene, values=(
                szene, ", ".join(rollen) or "-", ", ".join(map(format_date, probe_dates)) or "-",
                self.data.geprobt_text(szene), abw,
            ))
            if details:
                self._abw_details[szene] = details

    def _on_click(self, event) -> None:
        """Click on the 'Abwesend' column shows all absence details of the scene."""
        hit = cell_at(self.tree, event)
        if not hit or hit[1] != ABWESEND_COL or hit[0] not in self._abw_details:
            return
        win = tk.Toplevel(self)
        win.title(f"Abwesenheiten – {hit[0]}")
        win.transient(self.winfo_toplevel())
        win.grab_set()
        box = tk.Listbox(win)
        box.pack(fill="both", expand=True, padx=8, pady=8)
        box.insert("end", *self._abw_details[hit[0]])
