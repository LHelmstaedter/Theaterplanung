import json
import tkinter as tk
import traceback
from tkinter import filedialog, messagebox, ttk

import exporter
from data import TheaterData
from ui.abwesenheiten_tab import AbwesenheitenTab
from ui.common import install_mousewheel
from ui.kalender_tab import KalenderTab
from ui.proben_tab import ProbenTab
from ui.rollen_tab import RollenTab
from ui.schauspieler_tab import SchauspielerTab
from ui.szenen_tab import SzenenTab

JSON_TYPES = [("JSON Dateien", "*.json")]


class TheaterProbenplaner:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        root.title("Theaterplanung")
        root.report_callback_exception = self._report_error
        install_mousewheel(root)
        self.data = TheaterData()

        menubar = tk.Menu(root)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Exportieren...", command=self.open_export_dialog)
        file_menu.add_command(label="Speichern...", command=self.save_data)
        file_menu.add_command(label="Laden...", command=self.load_data)
        file_menu.add_separator()
        file_menu.add_command(label="Beenden", command=root.quit)
        menubar.add_cascade(label="Datei", menu=file_menu)
        root.config(menu=menubar)

        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill="both", expand=True)
        self.tab_schauspieler = SchauspielerTab(self.notebook, self)
        self.tab_rollen = RollenTab(self.notebook, self)
        self.tab_szenen = SzenenTab(self.notebook, self)
        self.tab_abwesenheiten = AbwesenheitenTab(self.notebook, self)
        self.tab_proben = ProbenTab(self.notebook, self)
        self.tab_kalender = KalenderTab(self.notebook, self)
        for tab, title in (
            (self.tab_schauspieler, "Schauspieler"), (self.tab_rollen, "Rollen"), (self.tab_szenen, "Szenen"),
            (self.tab_abwesenheiten, "Abwesenheiten"), (self.tab_proben, "Proben"), (self.tab_kalender, "Kalender"),
        ):
            self.notebook.add(tab, text=title)
        self.refresh_all()

    def refresh_all(self) -> None:
        self.data.sync_proben()
        for tab in self.notebook.winfo_children():
            tab.refresh()

    def _report_error(self, exc, val, tb) -> None:
        traceback.print_exception(exc, val, tb)
        messagebox.showerror("Fehler", f"{exc.__name__}: {val}")

    # ---- save / load ----
    def save_data(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Speichern unter...", defaultextension=".json", filetypes=JSON_TYPES, initialfile="theaterplanung.json"
        )
        if path:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.data.to_dict(), f, indent=2, ensure_ascii=False)
            messagebox.showinfo("Gespeichert", "Daten wurden erfolgreich gespeichert.")

    def load_data(self) -> None:
        path = filedialog.askopenfilename(title="Datei laden...", filetypes=JSON_TYPES)
        if not path:
            return
        try:
            with open(path, encoding="utf-8") as f:
                self.data.load_from_dict(json.load(f))
        except (OSError, ValueError, KeyError, TypeError) as e:
            self.data.clear()
            self.refresh_all()
            messagebox.showerror("Fehler", f"Datei konnte nicht geladen werden:\n{e}")
            return
        self.refresh_all()
        messagebox.showinfo("Geladen", "Daten wurden erfolgreich geladen.")

    # ---- export ----
    def open_export_dialog(self) -> None:
        dlg = tk.Toplevel(self.root)
        dlg.title("Exportieren")
        dlg.resizable(False, False)
        dlg.grab_set()

        tk.Label(dlg, text="Welche Daten exportieren?").pack(anchor="w", padx=10, pady=(10, 5))
        checks = {name: tk.BooleanVar(value=True) for name in exporter.SECTIONS}
        var_cal = tk.BooleanVar(value=True)
        for name, var in checks.items():
            tk.Checkbutton(dlg, text=name, variable=var).pack(anchor="w", padx=20)
        tk.Checkbutton(dlg, text="Kalender (Monatsübersichten, nur PDF)", variable=var_cal).pack(anchor="w", padx=20)

        tk.Label(dlg, text="Format:").pack(anchor="w", padx=10, pady=(10, 5))
        var_fmt = tk.StringVar(value="csv")
        for text, value in (("CSV", "csv"), ("TXT", "txt"), ("PDF (eine Datei)", "pdf")):
            tk.Radiobutton(dlg, text=text, variable=var_fmt, value=value).pack(anchor="w", padx=20)

        def run() -> None:
            sections = [n for n, v in checks.items() if v.get()]
            fmt, with_cal = var_fmt.get(), var_cal.get() and var_fmt.get() == "pdf"
            if not sections and not with_cal:
                messagebox.showwarning("Export", "Bitte mindestens einen Bereich auswählen.", parent=dlg)
                return
            target = filedialog.askdirectory(title="Zielordner für Export wählen", parent=dlg)
            if not target:
                return
            try:
                if fmt == "pdf":
                    exporter.export_pdf(self.data, target, sections, with_cal)
                else:
                    exporter.export_csv_txt(self.data, target, fmt, sections)
            except Exception as e:
                messagebox.showerror("Fehler", f"Export fehlgeschlagen:\n{e}", parent=dlg)
                return
            dlg.destroy()
            messagebox.showinfo("Export", "Export abgeschlossen.")

        buttons = tk.Frame(dlg)
        buttons.pack(pady=10)
        tk.Button(buttons, text="Abbrechen", command=dlg.destroy).pack(side="right", padx=5)
        tk.Button(buttons, text="Exportieren", command=run).pack(side="right", padx=5)


def main() -> None:
    root = tk.Tk()
    TheaterProbenplaner(root)
    root.mainloop()


if __name__ == "__main__":
    main()
