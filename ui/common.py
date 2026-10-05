"""Shared UI helpers used by several tabs."""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk


# ---------------------------------------------------------------- scrolling
def install_mousewheel(root: tk.Misc) -> None:
    """One global mouse-wheel handler: scrolls the scrollable_frame under the pointer."""

    def on_wheel(event):
        try:
            w = root.winfo_containing(event.x_root, event.y_root)
        except (KeyError, tk.TclError):  # e.g. open combobox popdown
            return
        while w is not None:
            if getattr(w, "_wheel_target", False):
                up = event.num == 4 or getattr(event, "delta", 0) > 0
                w.yview_scroll(-1 if up else 1, "units")
                return
            w = w.master

    for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
        root.bind_all(seq, on_wheel, add="+")


def scrollable_frame(parent, height: int | None = None) -> tuple[tk.Frame, tk.Frame]:
    """Returns (outer, inner): pack `outer`, put widgets into `inner`."""
    outer = tk.Frame(parent)
    kw = {"height": height} if height else {}
    canvas = tk.Canvas(outer, borderwidth=0, highlightthickness=0, **kw)
    inner = tk.Frame(canvas)
    bar = tk.Scrollbar(outer, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=bar.set)
    canvas.pack(side="left", fill="both", expand=True)
    bar.pack(side="right", fill="y")
    canvas.create_window((0, 0), window=inner, anchor="nw")
    inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas._wheel_target = True
    return outer, inner


# ---------------------------------------------------------------- treeview
def cell_at(tree: ttk.Treeview, event) -> tuple[str, int] | None:
    """(row id, column index) of the clicked cell, or None."""
    if tree.identify("region", event.x, event.y) != "cell":
        return None
    row, col = tree.identify_row(event.y), tree.identify_column(event.x)
    return (row, int(col[1:]) - 1) if row and col else None


def bind_row_menu(tree: ttk.Treeview, menu: tk.Menu) -> None:
    """Right click selects the row and opens `menu`."""

    def handler(event):
        item = tree.identify_row(event.y)
        if not item:
            return
        tree.selection_set(item)
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    tree.bind("<Button-3>", handler)


def show_cell_popup(event) -> None:
    """Double click on a table cell: show its full text (comma lists one per line)."""
    tree = event.widget
    hit = cell_at(tree, event)
    if hit is None:
        return
    row, col = hit
    values = tree.item(row, "values")
    if col >= len(values) or str(values[col]).strip() in ("", "-"):
        return
    text = "\n".join(p.strip() for p in str(values[col]).split(",") if p.strip())
    heading = tree.heading(tree["columns"][col]).get("text", "").replace(" ▼", "")

    top = tk.Toplevel(tree.winfo_toplevel())
    top.title(f"Zelleninhalt – {heading}" if heading else "Zelleninhalt")
    top.transient(tree.winfo_toplevel())
    top.geometry(f"+{event.x_root + 20}+{event.y_root + 20}")
    box = tk.Text(top, wrap="word", height=10, width=50)
    box.insert("1.0", text)
    box.config(state="disabled")
    box.pack(fill="both", expand=True, padx=8, pady=8)
    tk.Button(top, text="Schließen", command=top.destroy).pack(pady=(0, 8))
    top.grab_set()


# ---------------------------------------------------------------- dialogs
def open_filter_dialog(parent, title: str, values: list[str], active: set, on_apply) -> None:
    """Multi-select filter. `on_apply(selected)` gets an empty set for 'no filter'."""
    if not values:
        messagebox.showinfo("Filter", "Keine Werte zum Filtern vorhanden.")
        return
    win = tk.Toplevel(parent)
    win.title(title)
    win.transient(parent.winfo_toplevel())
    win.grab_set()

    outer, inner = scrollable_frame(win, height=200)
    outer.pack(fill="both", expand=True, padx=8, pady=8)
    checks = {v: tk.BooleanVar(value=not active or v in active) for v in values}
    for v, var in checks.items():
        tk.Checkbutton(inner, text=v, variable=var, anchor="w", justify="left").pack(fill="x", anchor="w")

    def set_all(flag: bool) -> None:
        for var in checks.values():
            var.set(flag)

    def apply() -> None:
        selected = {v for v, var in checks.items() if var.get()}
        win.destroy()
        on_apply(set() if len(selected) in (0, len(values)) else selected)

    buttons = tk.Frame(win)
    buttons.pack(fill="x", padx=8, pady=(0, 8))
    tk.Button(buttons, text="Alle", command=lambda: set_all(True)).pack(side="left", padx=2)
    tk.Button(buttons, text="Keine", command=lambda: set_all(False)).pack(side="left", padx=2)
    tk.Button(buttons, text="Filter anwenden", command=apply).pack(side="right", padx=2)


# ---------------------------------------------------------------- widgets
class RoleChecklist(tk.Frame):
    """Searchable list of role checkbuttons. The selection survives searching."""

    def __init__(self, parent, label_fn=lambda r: r, columns: int = 1, height: int | None = None):
        super().__init__(parent)
        self.label_fn, self.columns = label_fn, columns
        self.vars: dict[str, tk.BooleanVar] = {}
        self.search = tk.StringVar()
        tk.Entry(self, textvariable=self.search).pack(fill="x", pady=(0, 4))
        self.search.trace_add("write", lambda *_: self._render())
        outer, self.inner = scrollable_frame(self, height)
        outer.pack(fill="both", expand=True)

    def set_roles(self, roles, selected=()) -> None:
        """Rebuild for `roles`; keeps the current selection (plus `selected`)."""
        keep = {r for r, v in self.vars.items() if v.get()} | set(selected)
        self.vars = {r: tk.BooleanVar(value=r in keep) for r in sorted(roles)}
        self._render()

    def _render(self) -> None:
        for w in self.inner.winfo_children():
            w.destroy()
        query = self.search.get().lower().strip()
        shown = [r for r in self.vars if query in self.label_fn(r).lower()]
        for i, rolle in enumerate(shown):
            tk.Checkbutton(
                self.inner, text=self.label_fn(rolle), variable=self.vars[rolle], anchor="w", justify="left"
            ).grid(row=i // self.columns, column=i % self.columns, sticky="w", padx=4, pady=1)

    def selected(self) -> list[str]:
        return sorted(r for r, v in self.vars.items() if v.get())

    def clear(self) -> None:
        for v in self.vars.values():
            v.set(False)
        self.search.set("")
