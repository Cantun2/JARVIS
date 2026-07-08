// Helpers de dates purs et sans dépendance (Date natif uniquement).
// Toutes les opérations raisonnent en HEURE LOCALE : on n'utilise jamais les
// variantes UTC pour éviter les décalages de fuseau sur les clés "YYYY-MM-DD".

/** Formate une date en "YYYY-MM-DD" (heure locale). */
export function toYmd(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

/** Date du jour au format "YYYY-MM-DD" (heure locale). */
export function todayYmd(): string {
  return toYmd(new Date());
}

/** Vrai si `a` et `b` tombent le même jour calendaire (heure ignorée). */
export function sameDay(a: Date, b: Date): boolean {
  return (
    a.getFullYear() === b.getFullYear() &&
    a.getMonth() === b.getMonth() &&
    a.getDate() === b.getDate()
  );
}

/**
 * Grille mensuelle : renvoie des semaines (tableaux de 7 dates) commençant le
 * lundi et couvrant tout le mois `month` (1-12) de `year`, en complétant avec
 * les jours débordant des mois adjacents pour remplir chaque semaine.
 */
export function monthMatrix(year: number, month: number): Date[][] {
  const first = new Date(year, month - 1, 1);
  // getDay() : 0=dimanche..6=samedi. On veut lundi=0..dimanche=6.
  const offset = (first.getDay() + 6) % 7;
  // Nombre de jours du mois : le "jour 0" du mois suivant = dernier jour courant.
  const daysInMonth = new Date(year, month, 0).getDate();
  const weekCount = Math.ceil((offset + daysInMonth) / 7);

  const weeks: Date[][] = [];
  for (let w = 0; w < weekCount; w += 1) {
    const week: Date[] = [];
    for (let d = 0; d < 7; d += 1) {
      // Décalage depuis le 1er du mois : recule de `offset` jours pour le lundi.
      const dayNum = 1 - offset + w * 7 + d;
      week.push(new Date(year, month - 1, dayNum));
    }
    weeks.push(week);
  }
  return weeks;
}
