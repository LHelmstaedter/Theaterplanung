from __future__ import annotations

from datetime import date, datetime

DATE_DISPLAY = "%d.%m.%Y"


def parse_date(s: str) -> date:
    return datetime.strptime(s, DATE_DISPLAY).date()


def format_date(d: date) -> str:
    return d.strftime(DATE_DISPLAY)


def format_range(von: date, bis: date) -> str:
    return format_date(von) if von == bis else f"{format_date(von)}–{format_date(bis)}"


class TheaterData:
    """Central data store: actors, roles, scenes, absences and rehearsals.

    rollen:                 {"Romeo": "Max"}            role -> actor
    rollen_wichtigkeit:     {"Romeo": 3}                role -> importance (1-5)
    szenen:                 {"Szene 1": ["Romeo", ...]} scene -> roles
    szenen_geplante_proben: {"Szene 1": 4}              optional planned rehearsals
    abwesenheiten:          {"Max": [(von, bis), ...]}  actor -> absence ranges
    proben:                 [{"datum": date, "szenen": [..], "szene": str | None,
                              "rollen": [..], "notiz": str, "done": bool}]
    "szenen" is the source of truth; "szene" (display text) and "rollen" are
    derived from it by set_probe_szenen() / sync_proben().
    """

    def __init__(self) -> None:
        self.clear()

    def clear(self) -> None:
        self.schauspieler: list[str] = []
        self.rollen: dict[str, str] = {}
        self.rollen_wichtigkeit: dict[str, int] = {}
        self.szenen: dict[str, list[str]] = {}
        self.szenen_geplante_proben: dict[str, int] = {}
        self.abwesenheiten: dict[str, list[tuple[date, date]]] = {}
        self.proben: list[dict] = []

    # ---- absences ----
    def is_absent(self, actor: str, dt: date) -> bool:
        return any(v <= dt <= b for v, b in self.abwesenheiten.get(actor, []))

    def absente_for_probe(self, dt: date, rollen_liste: list[str]) -> list[str]:
        """Actors who are absent on `dt` and play one of the given roles."""
        actors = (self.rollen.get(r) for r in rollen_liste)
        return sorted({a for a in actors if a and self.is_absent(a, dt)})

    def abwesenheiten_pro_rolle(self, rolle: str) -> list[tuple[date, date]]:
        return list(self.abwesenheiten.get(self.rollen.get(rolle, ""), []))

    # ---- lookups ----
    def szenen_pro_rolle(self, rolle: str) -> list[str]:
        return sorted(s for s, rollen in self.szenen.items() if rolle in rollen)

    def proben_pro_rolle(self, rolle: str) -> list[date]:
        return sorted({p["datum"] for p in self.proben if rolle in p.get("rollen", [])})

    def proben_fuer_szene(self, szene: str) -> list[dict]:
        return [p for p in self.proben if szene in self.probe_szenen(p)]

    def geprobt_text(self, szene: str) -> str:
        """'done' or 'done/planned' rehearsal count for a scene."""
        done = sum(1 for p in self.proben_fuer_szene(szene) if p.get("done"))
        planned = self.szenen_geplante_proben.get(szene)
        return str(done) if planned is None else f"{done}/{planned}"

    # ---- role value & scene suggestions ----
    def rollenwert(self, rolle: str) -> int:
        """Importance of a role (1-5), default 3."""
        try:
            return max(1, min(5, int(self.rollen_wichtigkeit.get(rolle, 3))))
        except (TypeError, ValueError):
            return 3

    def szenen_score_fuer_datum(self, szene: str, dt: date) -> tuple[int, list[str], list[str]]:
        """(score, missing roles, present roles) of a scene on a date.
        The score is the sum of the importance values of the present roles."""
        score, fehlende, anwesend = 0, [], []
        for rolle in self.szenen.get(szene, []):
            actor = self.rollen.get(rolle)
            if actor and self.is_absent(actor, dt):
                fehlende.append(rolle)
            else:
                score += self.rollenwert(rolle)
                anwesend.append(rolle)
        return score, fehlende, anwesend

    def vorgeschlagene_proben_fuer_datum(self, dt: date) -> list[dict]:
        """Scene suggestions for a date, best score first."""
        result = []
        for szene in self.szenen:
            score, fehlende, anwesend = self.szenen_score_fuer_datum(szene, dt)
            result.append({"szene": szene, "score": score, "fehlende": fehlende, "anwesend": anwesend})
        result.sort(key=lambda x: (-x["score"], x["szene"]))
        return result

    # ---- rehearsals ----
    @staticmethod
    def probe_szenen(probe: dict) -> list[str]:
        """Scenes of a rehearsal (also understands old data with only 'szene')."""
        if isinstance(probe.get("szenen"), list):
            return list(probe["szenen"])
        return [probe["szene"]] if probe.get("szene") else []

    def set_probe_szenen(self, probe: dict, szenen: list[str]) -> None:
        szenen = list(dict.fromkeys(szenen))
        probe["szenen"] = szenen
        probe["szene"] = ", ".join(szenen) or None
        probe["rollen"] = sorted({r for s in szenen for r in self.szenen.get(s, [])})

    def sync_proben(self) -> None:
        """Recompute display text and roles of all rehearsals from their scenes."""
        for p in self.proben:
            self.set_probe_szenen(p, self.probe_szenen(p))

    # ---- rename / delete with cleanup ----
    def rename_actor(self, old: str, new: str) -> None:
        self.schauspieler = list(dict.fromkeys(new if a == old else a for a in self.schauspieler))
        for rolle, actor in self.rollen.items():
            if actor == old:
                self.rollen[rolle] = new
        if old in self.abwesenheiten:
            self.abwesenheiten.setdefault(new, []).extend(self.abwesenheiten.pop(old))

    def delete_actor(self, name: str) -> None:
        """Removes the actor together with their roles and absences."""
        self.schauspieler = [a for a in self.schauspieler if a != name]
        for rolle in [r for r, a in self.rollen.items() if a == name]:
            self.delete_role(rolle)
        self.abwesenheiten.pop(name, None)

    def delete_role(self, rolle: str) -> None:
        self.rollen.pop(rolle, None)
        self.rollen_wichtigkeit.pop(rolle, None)
        for szene, rollen in self.szenen.items():
            self.szenen[szene] = [r for r in rollen if r != rolle]
        self.sync_proben()

    def rename_scene(self, old: str, new: str) -> None:
        if old == new:
            return
        self.szenen = {(new if k == old else k): v for k, v in self.szenen.items()}
        if old in self.szenen_geplante_proben:
            self.szenen_geplante_proben[new] = self.szenen_geplante_proben.pop(old)
        for p in self.proben:
            self.set_probe_szenen(p, [new if s == old else s for s in self.probe_szenen(p)])

    def delete_scene(self, name: str) -> None:
        """Removes the scene; rehearsals that only had this scene become general rehearsals."""
        self.szenen.pop(name, None)
        self.szenen_geplante_proben.pop(name, None)
        for p in self.proben:
            self.set_probe_szenen(p, [s for s in self.probe_szenen(p) if s != name])

    # ---- persistence ----
    def to_dict(self) -> dict:
        return {
            "schauspieler": self.schauspieler,
            "rollen": self.rollen,
            "rollen_wichtigkeit": self.rollen_wichtigkeit,
            "szenen": self.szenen,
            "szenen_geplante_proben": self.szenen_geplante_proben,
            "abwesenheiten": {
                actor: [(v.isoformat(), b.isoformat()) for v, b in ranges]
                for actor, ranges in self.abwesenheiten.items()
            },
            "proben": [{**p, "datum": p["datum"].isoformat()} for p in self.proben],
        }

    def load_from_dict(self, d: dict) -> None:
        self.clear()
        self.schauspieler = list(d.get("schauspieler", []))
        self.rollen = dict(d.get("rollen", {}))
        self.rollen_wichtigkeit = dict(d.get("rollen_wichtigkeit", {}))
        self.szenen = {k: list(v) for k, v in d.get("szenen", {}).items()}
        self.szenen_geplante_proben = dict(d.get("szenen_geplante_proben", {}))
        self.abwesenheiten = {
            actor: [(date.fromisoformat(a), date.fromisoformat(b)) for a, b in ranges]
            for actor, ranges in d.get("abwesenheiten", {}).items()
        }
        self.proben = [{**p, "datum": date.fromisoformat(p["datum"])} for p in d.get("proben", [])]
        self.sync_proben()
