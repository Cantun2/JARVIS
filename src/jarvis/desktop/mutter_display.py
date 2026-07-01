"""Découverte des écrans via l'API D-Bus de Mutter (org.gnome.Mutter.DisplayConfig).

Sous Wayland, la seule source fiable de la disposition des moniteurs (position, taille,
scale, connecteur, moniteur primaire) est `DisplayConfig.GetCurrentState`. On l'interroge
avec `gdbus call` et on parse la sortie texte au format GVariant.

Le parsing est isolé dans `parse_display_state`, une fonction PURE testable sans session
graphique. La signature de retour de la méthode D-Bus est :

    (u
     a((ssss)a(siiddad{sv}){sv})              # moniteurs physiques + modes
     a(iiduba(ssss){sv})                       # moniteurs LOGIQUES  <- ce qu'on lit
     {sv})                                      # propriétés globales

Un moniteur logique est ``(x, y, scale, transform, primary, [(connector, ...)], props)``.
On produit une entrée `Screen` par moniteur logique ; la taille est reprise du mode courant
du moniteur physique associé (via son connecteur), divisée par le scale.
"""

from __future__ import annotations

from dataclasses import dataclass

from jarvis.desktop.controller import Geometry, Screen

# Commande D-Bus interrogeant l'état d'affichage courant de Mutter.
DISPLAY_STATE_ARGV: list[str] = [
    "gdbus",
    "call",
    "--session",
    "--dest",
    "org.gnome.Mutter.DisplayConfig",
    "--object-path",
    "/org/gnome/Mutter/DisplayConfig",
    "--method",
    "org.gnome.Mutter.DisplayConfig.GetCurrentState",
]


@dataclass(frozen=True)
class _Tokenizer:
    """Petit curseur sur le texte GVariant pour un parsing récursif tolérant."""

    text: str
    pos: int = 0


def _skip_ws(text: str, i: int) -> int:
    n = len(text)
    while i < n and text[i] in " \t\n\r":
        i += 1
    return i


def _parse_string(text: str, i: int) -> tuple[str, int]:
    """Lit une chaîne GVariant ``'...'`` en gérant les échappements ``\\'`` et ``\\\\``."""
    assert text[i] == "'"
    i += 1
    out: list[str] = []
    n = len(text)
    while i < n:
        c = text[i]
        if c == "\\" and i + 1 < n:
            out.append(text[i + 1])
            i += 2
            continue
        if c == "'":
            return "".join(out), i + 1
        out.append(c)
        i += 1
    return "".join(out), i


def _parse_group(text: str, i: int, open_ch: str, close_ch: str) -> tuple[str, int]:
    """Retourne le contenu brut entre `open_ch`/`close_ch` équilibrés (hors chaînes)."""
    assert text[i] == open_ch
    depth = 0
    start = i
    n = len(text)
    while i < n:
        c = text[i]
        if c == "'":
            _, i = _parse_string(text, i)
            continue
        if c in "([<{":
            depth += 1
        elif c in ")]>}":
            depth -= 1
            if depth == 0:
                return text[start + 1 : i], i + 1
        i += 1
    return text[start + 1 :], n


def _split_top_level(text: str) -> list[str]:
    """Découpe une liste GVariant sur les virgules de premier niveau (respecte chaînes/groupes)."""
    parts: list[str] = []
    depth = 0
    cur: list[str] = []
    i = 0
    n = len(text)
    while i < n:
        c = text[i]
        if c == "'":
            _s, j = _parse_string(text, i)
            cur.append(text[i:j])
            i = j
            continue
        if c in "([<{":
            depth += 1
        elif c in ")]>}":
            depth -= 1
        if c == "," and depth == 0:
            parts.append("".join(cur).strip())
            cur = []
            i += 1
            continue
        cur.append(c)
        i += 1
    tail = "".join(cur).strip()
    if tail:
        parts.append(tail)
    return parts


def _connector_of(tuple_text: str) -> str:
    """Extrait le connecteur (1re chaîne) d'un n-uplet ``('eDP-1', 'AUO', ...)``."""
    j = _skip_ws(tuple_text, 0)
    if j < len(tuple_text) and tuple_text[j] == "'":
        value, _ = _parse_string(tuple_text, j)
        return value
    return ""


def _int_of(token: str) -> int:
    """Convertit un scalaire GVariant entier (``int32``, ``uint32 3``, ``3``…) en `int`."""
    tok = token.strip()
    for prefix in ("uint32", "int32", "uint64", "int64", "uint16", "int16", "byte"):
        if tok.startswith(prefix):
            tok = tok[len(prefix) :].strip()
            break
    return int(float(tok)) if tok else 0


def _float_of(token: str) -> float:
    return float(token.strip())


def _physical_sizes(monitors_text: str) -> dict[str, tuple[int, int]]:
    """Mappe connecteur -> (largeur, hauteur) du mode courant (``is-current``)."""
    sizes: dict[str, tuple[int, int]] = {}
    i = _skip_ws(monitors_text, 0)
    n = len(monitors_text)
    while i < n:
        if monitors_text[i] != "(":
            i += 1
            continue
        body, i = _parse_group(monitors_text, i, "(", ")")
        fields = _split_top_level(body)
        if len(fields) < 2:
            continue
        connector = _connector_of(fields[0].strip().lstrip("("))
        modes_text = fields[1].strip()
        if modes_text.startswith("["):
            modes_text = modes_text[1:-1]
        chosen: tuple[int, int] | None = None
        first: tuple[int, int] | None = None
        for mode in _iter_tuples(modes_text):
            mf = _split_top_level(mode)
            if len(mf) < 3:
                continue
            width = _int_of(mf[1])
            height = _int_of(mf[2])
            if first is None:
                first = (width, height)
            if "'is-current': <true>" in mode.replace(" ", " "):
                chosen = (width, height)
                break
        if chosen is None:
            chosen = first
        if connector and chosen is not None:
            sizes[connector] = chosen
    return sizes


def _iter_tuples(text: str) -> list[str]:
    """Retourne les contenus de chaque n-uplet ``(...)`` de premier niveau d'une liste."""
    out: list[str] = []
    i = _skip_ws(text, 0)
    n = len(text)
    while i < n:
        if text[i] == "(":
            body, i = _parse_group(text, i, "(", ")")
            out.append(body)
        else:
            i += 1
    return out


def _extract_sections(text: str) -> tuple[str, str] | None:
    """Sépare les deux grands tableaux ``a(...)`` : moniteurs physiques puis logiques."""
    top = text.strip()
    if top.startswith("(") and top.endswith(")"):
        top = top[1:-1]
    arrays: list[str] = []
    i = 0
    n = len(top)
    while i < n and len(arrays) < 2:
        if top[i] == "[":
            body, i = _parse_group(top, i, "[", "]")
            arrays.append(body)
        else:
            i += 1
    if len(arrays) < 2:
        return None
    return arrays[0], arrays[1]


def parse_display_state(text: str) -> list[Screen]:
    """Parse la sortie texte de ``DisplayConfig.GetCurrentState`` en `list[Screen]`.

    Fonction pure : aucun effet de bord, aucune dépendance à une session graphique.
    Une entrée `Screen` par moniteur logique ; la taille logique = taille du mode courant
    divisée par le scale (arrondie). L'``id`` est le connecteur (stable), le ``name`` reprend
    le connecteur enrichi éventuellement du nom d'affichage.
    """
    sections = _extract_sections(text)
    if sections is None:
        return []
    physical_text, logical_text = sections
    sizes = _physical_sizes(physical_text)

    screens: list[Screen] = []
    for idx, body in enumerate(_iter_tuples(logical_text)):
        fields = _split_top_level(body)
        if len(fields) < 6:
            continue
        x = _int_of(fields[0])
        y = _int_of(fields[1])
        scale = _float_of(fields[2])
        primary = fields[4].strip().lower() == "true"
        connectors_text = fields[5].strip()
        if connectors_text.startswith("["):
            connectors_text = connectors_text[1:-1]
        conn_tuples = _iter_tuples(connectors_text)
        connector = _connector_of(conn_tuples[0]) if conn_tuples else f"monitor-{idx}"

        phys_w, phys_h = sizes.get(connector, (0, 0))
        eff_scale = scale if scale > 0 else 1.0
        width = round(phys_w / eff_scale) if phys_w else 0
        height = round(phys_h / eff_scale) if phys_h else 0

        screens.append(
            Screen(
                id=connector,
                name=connector,
                geometry=Geometry(x=x, y=y, width=width, height=height),
                primary=primary,
                scale=scale,
            )
        )
    return screens
