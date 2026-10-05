import tkinter as tk
from datetime import timedelta
from tkinter import messagebox

from tkcalendar import Calendar

from .common import RoleChecklist


class KalenderTab(tk.Frame):
    """Calendar of rehearsals plus an availability check for selected roles."""

    def __init__(self, parent, controller) -> None:
        super().__init__(parent)
        self.controller = controller
        self.data = controller.data
        self._day_proben: list[dict] = []
        self._availability_ids: list[int] = []

        top = tk.Frame(self)
        top.pack(fill="both", expand=True, padx=8, pady=8)
        left = tk.Frame(top)
        left.pack(side="left", fill="both", expand=True)
        right = tk.Frame(top)
        right.pack(side="left", fill="both", expand=True, padx=(8, 0))

        self.cal = Calendar(left, selectmode="day", date_pattern="dd.MM.yyyy")
        self.cal.pack(fill="both", expand=True)
        self.cal.bind("<<CalendarSelected>>", lambda e: self._on_select())
        self.cal.tag_config("generic", background="lightblue")
        self.cal.tag_config("scene", background="lightgreen")
        self.cal.tag_config("available", background="red", foreground="black")

        tk.Label(right, text="Proben am ausgewählten Datum:").pack(anchor="w")
        self.listbox = tk.Listbox(right, height=10)
        self.listbox.pack(fill="both", expand=True)
        self.listbox.bind("<Double-Button-1>", self._open_probe)

        lower = tk.Frame(right)
        lower.pack(fill="both", expand=True, pady=(8, 0))
        tk.Label(lower, text="Rollen auswählen (Verfügbarkeit):").pack(anchor="w")
        self.roles = RoleChecklist(
            lower, label_fn=lambda r: f"{self.data.rollen.get(r, '?')} ({r})", columns=3
        )
        self.roles.pack(fill="both", expand=True)
        buttons = tk.Frame(lower)
        buttons.pack(fill="x", pady=(4, 0))
        tk.Button(buttons, text="Go", command=self._check_availability).pack(side="left")
        tk.Button(buttons, text="Reset", command=self._reset).pack(side="left", padx=(4, 0))

    def refresh(self) -> None:
        self.roles.set_roles(self.data.rollen)
        self.cal.calevent_remove("all")  # also drops availability marks
        self._availability_ids.clear()
        for probe in self.data.proben:
            tag = "scene" if probe["szene"] else "generic"
            self.cal.calevent_create(probe["datum"], probe["szene"] or "Probe", tag)
        self._on_select()

    def _on_select(self) -> None:
        selected = self.cal.selection_get()
        self._day_proben = sorted(
            (p for p in self.data.proben if p["datum"] == selected), key=lambda p: p["szene"] or ""
        )
        self.listbox.delete(0, tk.END)
        for p in self._day_proben:
            line = f"{'[x]' if p.get('done') else '[ ]'} {p['szene'] or 'Probe'} | Rollen: {', '.join(p['rollen']) or '-'}"
            if p.get("notiz"):
                line += f" | {p['notiz']}"
            self.listbox.insert(tk.END, line)

    def _open_probe(self, _event) -> None:
        """Double click: jump to the rehearsal in the rehearsals tab."""
        sel = self.listbox.curselection()
        if sel:
            self.controller.notebook.select(self.controller.tab_proben)
            self.controller.tab_proben.focus_probe(self._day_proben[sel[0]])

    def _check_availability(self) -> None:
        """Marks every day between first and last rehearsal on which all selected roles are present."""
        selected = self.roles.selected()
        if not selected:
            messagebox.showinfo("Verfügbarkeit prüfen", "Bitte mindestens eine Rolle auswählen.")
            return
        if not self.data.proben:
            messagebox.showinfo("Verfügbarkeit prüfen", "Es sind keine Proben eingetragen.")
            return
        self._clear_marks()
        dates = [p["datum"] for p in self.data.proben]
        day = min(dates)
        while day <= max(dates):
            if not self.data.absente_for_probe(day, selected):
                self._availability_ids.append(self.cal.calevent_create(day, "", "available"))
            day += timedelta(days=1)

    def _clear_marks(self) -> None:
        for event_id in self._availability_ids:
            self.cal.calevent_remove(event_id)
        self._availability_ids.clear()

    def _reset(self) -> None:
        self._clear_marks()
        self.roles.clear()
