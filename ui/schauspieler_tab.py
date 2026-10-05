import tkinter as tk
from tkinter import messagebox, simpledialog


class SchauspielerTab(tk.Frame):
    def __init__(self, parent, controller) -> None:
        super().__init__(parent)
        self.controller = controller
        self.data = controller.data

        tk.Label(self, text="Neuen Schauspieler hinzufügen:").pack(pady=(8, 4))
        row = tk.Frame(self)
        row.pack(fill="x", padx=8)
        self.entry = tk.Entry(row)
        self.entry.pack(side="left", fill="x", expand=True)
        self.entry.bind("<Return>", lambda e: self.add())
        tk.Button(row, text="Hinzufügen", command=self.add).pack(side="left", padx=6)

        frame = tk.Frame(self)
        frame.pack(fill="both", expand=True, padx=8, pady=8)
        self.listbox = tk.Listbox(frame, exportselection=False)
        self.listbox.pack(side="left", fill="both", expand=True)
        bar = tk.Scrollbar(frame, command=self.listbox.yview)
        bar.pack(side="right", fill="y")
        self.listbox.config(yscrollcommand=bar.set)

        self.menu = tk.Menu(self, tearoff=0)
        self.menu.add_command(label="Bearbeiten", command=self.edit)
        self.menu.add_command(label="Löschen", command=self.delete)
        self.listbox.bind("<Button-3>", self._open_menu)

    def _open_menu(self, event) -> None:
        if not self.listbox.size():
            return
        self.listbox.selection_clear(0, tk.END)
        self.listbox.selection_set(self.listbox.nearest(event.y))
        try:
            self.menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.menu.grab_release()

    def _selected(self) -> str | None:
        sel = self.listbox.curselection()
        return self.listbox.get(sel[0]) if sel else None

    def add(self) -> None:
        name = self.entry.get().strip()
        if not name:
            messagebox.showwarning("Fehler", "Bitte einen Namen eingeben.")
        elif name in self.data.schauspieler:
            messagebox.showwarning("Hinweis", "Schauspieler existiert bereits.")
        else:
            self.data.schauspieler.append(name)
            self.entry.delete(0, tk.END)
            self.controller.refresh_all()

    def edit(self) -> None:
        old = self._selected()
        if old is None:
            return
        new = simpledialog.askstring("Schauspieler bearbeiten", "Neuer Name:", initialvalue=old, parent=self)
        new = (new or "").strip()
        if not new or new == old:
            return
        if new in self.data.schauspieler:
            messagebox.showwarning("Hinweis", "Schauspieler existiert bereits.")
            return
        self.data.rename_actor(old, new)
        self.controller.refresh_all()

    def delete(self) -> None:
        name = self._selected()
        if name is None:
            return
        if messagebox.askyesno(
            "Löschen", f"Schauspieler '{name}' wirklich löschen?\nSeine Rollen und Abwesenheiten werden ebenfalls entfernt."
        ):
            self.data.delete_actor(name)
            self.controller.refresh_all()

    def refresh(self) -> None:
        self.listbox.delete(0, tk.END)
        for name in sorted(self.data.schauspieler):
            self.listbox.insert(tk.END, name)
