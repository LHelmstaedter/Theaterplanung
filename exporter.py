"""CSV / TXT / PDF export of the planning data."""
from __future__ import annotations

import calendar
import csv
from pathlib import Path
from xml.sax.saxutils import escape

from data import TheaterData, format_date

SECTIONS = ("Schauspieler", "Rollen", "Szenen", "Abwesenheiten", "Proben")


def tables(data: TheaterData) -> dict[str, tuple[list[str], list[list[str]]]]:
    """section name -> (header, rows); all cells are strings."""
    return {
        "Schauspieler": (["Name"], [[a] for a in data.schauspieler]),
        "Rollen": (
            ["Rolle", "Schauspieler", "Wichtigkeit"],
            [[r, a, str(data.rollenwert(r))] for r, a in sorted(data.rollen.items())],
        ),
        "Szenen": (
            ["Szene", "Rollen"],
            [[s, ", ".join(rollen)] for s, rollen in sorted(data.szenen.items())],
        ),
        "Abwesenheiten": (
            ["Schauspieler", "Von", "Bis"],
            [[a, format_date(v), format_date(b)] for a, ranges in sorted(data.abwesenheiten.items()) for v, b in ranges],
        ),
        "Proben": (
            ["Datum", "Szene/Probe", "Rollen", "Notiz", "Durchgeführt"],
            [
                [format_date(p["datum"]), p["szene"] or "Probe", ", ".join(p["rollen"]),
                 p.get("notiz") or "", "Ja" if p.get("done") else "Nein"]
                for p in sorted(data.proben, key=lambda p: p["datum"])
            ],
        ),
    }


def export_csv_txt(data: TheaterData, target_dir: str, fmt: str, sections: list[str]) -> None:
    """One file per section. CSV uses ';' and a BOM so Excel shows umlauts correctly."""
    all_tables = tables(data)
    for name in sections:
        header, rows = all_tables[name]
        path = Path(target_dir) / f"{name.lower()}.{fmt}"
        if fmt == "csv":
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f, delimiter=";")
                writer.writerow(header)
                writer.writerows(rows)
        else:
            with open(path, "w", encoding="utf-8") as f:
                f.write(" | ".join(header) + "\n" + "-" * 40 + "\n")
                f.writelines(" | ".join(row) + "\n" for row in rows)


def export_pdf(data: TheaterData, target_dir: str, sections: list[str], with_calendar: bool) -> None:
    """Everything in one PDF (export.pdf), optionally with month calendars of rehearsal months."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    styles = getSampleStyleSheet()
    cell = styles["BodyText"]
    elems = []
    grid = [("GRID", (0, 0), (-1, -1), 0.25, colors.black), ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("VALIGN", (0, 0), (-1, -1), "TOP")]

    all_tables = tables(data)
    for name in sections:
        header, rows = all_tables[name]
        if not rows:
            continue
        elems += [Paragraph(f"<b>{name}</b>", styles["Heading2"]), Spacer(1, 6)]
        body = [[Paragraph(f"<b>{escape(h)}</b>", cell) for h in header]]
        body += [[Paragraph(escape(c), cell) for c in row] for row in rows]
        elems += [Table(body, repeatRows=1, style=TableStyle(grid)), Spacer(1, 14)]

    if with_calendar and data.proben:
        elems += [Paragraph("<b>Kalender (Monate mit Proben)</b>", styles["Heading2"]), Spacer(1, 6)]
        for year, month in sorted({(p["datum"].year, p["datum"].month) for p in data.proben}):
            days = {p["datum"].day for p in data.proben if (p["datum"].year, p["datum"].month) == (year, month)}
            weeks = calendar.Calendar(firstweekday=0).monthdayscalendar(year, month)
            style = TableStyle([("GRID", (0, 0), (-1, -1), 0.25, colors.black), ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey)])
            for r, week in enumerate(weeks, start=1):
                for c, day in enumerate(week):
                    if day in days:
                        style.add("BACKGROUND", (c, r), (c, r), colors.yellow)
            body = [["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]] + [[str(d) if d else "" for d in w] for w in weeks]
            elems.append(KeepTogether([Paragraph(f"{month:02d}.{year}", styles["Heading3"]), Spacer(1, 4),
                                       Table(body, style=style), Spacer(1, 14)]))  # never split a month

    if not elems:
        raise ValueError("Keine Daten zum Exportieren vorhanden.")
    SimpleDocTemplate(str(Path(target_dir) / "export.pdf"), pagesize=A4).build(elems)
