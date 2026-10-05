import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from data import format_date, format_range
from .common import bind_row_menu, open_filter_dialog, show_cell_popup

FILTER_COLUMNS = ("Rolle", "Schauspieler", "Wichtigkeit")
COLUMNS = ("Rolle", "Schauspieler", "Wichtigkeit", "Szenen", "Proben", "Abwesenheiten")


class RollenTab(tk.Frame):
    """Roles with their actor, importance, scenes, rehearsals and absences."""

    def __init__(self, parent, controller) -> None:
        super().__init__(parent)
        self.controller = controller
        self.data = controller.data
        self.header_filters = {c: set() for c in FILTER_COLUMNS}  # empty set = no filter

        top = tk.Frame(self)
        top.pack(fill="x", padx=8, pady=(8, 4))
        tk.Label(top, text="Rollenname:").grid(row=0, column=0, sticky="w")
        self.e_rolle = tk.Entry(top)
        self.e_rolle.grid(row=1, column=0, sticky="we", padx=(0, 6))
        tk.Label(top, text="Schauspieler:").grid(row=0, column=1, sticky="w")
        self.cb_actor = ttk.Combobox(top, state="readonly")
        self.cb_actor.grid(row=1, column=1, sticky="we", padx=(0, 6))
        tk.Label(top, text="Wichtigkeit (1–5):").grid(row=0, column=2, sticky="w")
        self.cb_wert = ttk.Combobox(top, values=["1", "2", "3", "4", "5"], state="readonly", width=5)
        self.cb_wert.grid(row=1, column=2, sticky="w", padx=(0, 6))
        self.cb_wert.set("3")
        tk.Button(top, text="Rolle hinzufügen", command=self.add_rolle).grid(row=1, column=3, padx=(6, 0))
        top.columnconfigure((0, 1), weight=1)

        self.tree = ttk.Treeview(self, columns=COLUMNS, show="headings", height=12)
        for c in COLUMNS:
            if c in FILTER_COLUMNS:
                self.tree.heading(c, text=f"{c} ▼", command=lambda c=c: self._open_filter(c))
            else:
                self.tree.heading(c, text=c)
            self.tree.column(c, width=150, anchor="w")
        self.tree.pack(fill="both", expand=True, padx=8, pady=(4, 8))
        self.tree.bind("<Double-1>", show_cell_popup, add="+")

        self.menu = tk.Menu(self, tearoff=0)
        self.menu.add_command(label="Schauspieler ändern", command=self.edit_rolle)
        self.menu.add_command(label="Rolle löschen", command=self.delete_rolle)
        bind_row_menu(self.tree, self.menu)

    # Row ids are the role names, so selection() directly yields the role.
    def _selected_role(self) -> str | None:
        sel = self.tree.selection()
        return sel[0] if sel else None

    def add_rolle(self) -> None:
        rolle, actor = self.e_rolle.get().strip(), self.cb_actor.get().strip()
        if not rolle or not actor:
            messagebox.showwarning("Fehler", "Bitte Rolle, Schauspieler und Wert angeben.")
            return
        self.data.rollen[rolle] = actor
        self.data.rollen_wichtigkeit[rolle] = int(self.cb_wert.get() or 3)
        self.e_rolle.delete(0, tk.END)
        self.cb_actor.set("")
        self.cb_wert.set("3")
        self.controller.refresh_all()

    def edit_rolle(self) -> None:
        rolle = self._selected_role()
        if rolle is None:
            return
        new_actor = simpledialog.askstring(
            "Rolle bearbeiten", f"Schauspieler für Rolle '{rolle}':",
            initialvalue=self.data.rollen.get(rolle, ""), parent=self,
        )
        new_actor = (new_actor or "").strip()
        if not new_actor:
            return
        self.data.rollen[rolle] = new_actor
        if new_actor not in self.data.schauspieler:
            self.data.schauspieler.append(new_actor)
        self.controller.refresh_all()

    def delete_rolle(self) -> None:
        rolle = self._selected_role()
        if rolle is not None and messagebox.askyesno("Löschen", f"Rolle '{rolle}' löschen?"):
            self.data.delete_role(rolle)
            self.controller.refresh_all()

    def _filter_values(self, column: str) -> list[str]:
        if column == "Rolle":
            return sorted(self.data.rollen)
        if column == "Schauspieler":
            return sorted(set(self.data.rollen.values()))
        return sorted({str(self.data.rollenwert(r)) for r in self.data.rollen})

    def _open_filter(self, column: str) -> None:
        open_filter_dialog(
            self, f"Filter: {column}", self._filter_values(column), self.header_filters[column],
            lambda selected: self._set_filter(column, selected),
        )

    def _set_filter(self, column: str, selected: set) -> None:
        self.header_filters[column] = selected
        self.refresh()

    def refresh(self) -> None:
        self.cb_actor["values"] = sorted(self.data.schauspieler)
        self.tree.delete(*self.tree.get_children())
        flt = self.header_filters
        for rolle, actor in sorted(self.data.rollen.items()):
            wert = str(self.data.rollenwert(rolle))
            if (flt["Rolle"] and rolle not in flt["Rolle"]
                    or flt["Schauspieler"] and actor not in flt["Schauspieler"]
                    or flt["Wichtigkeit"] and wert not in flt["Wichtigkeit"]):
                continue
            szenen = ", ".join(self.data.szenen_pro_rolle(rolle)) or "-"
            proben = ", ".join(format_date(d) for d in self.data.proben_pro_rolle(rolle)) or "-"
            abw = ", ".join(format_range(v, b) for v, b in self.data.abwesenheiten_pro_rolle(rolle)) or "-"
            self.tree.insert("", "end", iid=rolle, values=(rolle, actor, wert, szenen, proben, abw))
