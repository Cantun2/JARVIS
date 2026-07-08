import { describe, expect, it } from "vitest";
import { monthMatrix, sameDay, toYmd, todayYmd } from "../lib/date";

describe("toYmd", () => {
  it("formate en YYYY-MM-DD (heure locale, zéros de tête)", () => {
    expect(toYmd(new Date(2024, 1, 5))).toBe("2024-02-05");
    expect(toYmd(new Date(2026, 11, 31))).toBe("2026-12-31");
    expect(toYmd(new Date(2024, 0, 1))).toBe("2024-01-01");
  });

  it("todayYmd correspond au toYmd de maintenant", () => {
    expect(todayYmd()).toBe(toYmd(new Date()));
  });
});

describe("sameDay", () => {
  it("compare année/mois/jour en ignorant l'heure", () => {
    expect(sameDay(new Date(2024, 1, 5, 8, 0), new Date(2024, 1, 5, 22, 30))).toBe(true);
    expect(sameDay(new Date(2024, 1, 5), new Date(2024, 1, 6))).toBe(false);
    expect(sameDay(new Date(2024, 1, 5), new Date(2023, 1, 5))).toBe(false);
  });
});

describe("monthMatrix", () => {
  it("rend des semaines de 7 jours, lundi en première colonne", () => {
    const weeks = monthMatrix(2024, 2); // Février 2024 (bissextile)
    expect(weeks.length).toBeGreaterThanOrEqual(4);
    for (const week of weeks) {
      expect(week).toHaveLength(7);
      // getDay() : 1 = lundi.
      expect(week[0]!.getDay()).toBe(1);
      expect(week[6]!.getDay()).toBe(0); // dimanche
    }
  });

  it("couvre tous les jours de février 2024 (29 jours, bissextile)", () => {
    const weeks = monthMatrix(2024, 2);
    const inMonth = new Set<string>();
    for (const week of weeks) {
      for (const day of week) {
        if (day.getMonth() === 1) inMonth.add(toYmd(day));
      }
    }
    expect(inMonth.size).toBe(29);
    expect(inMonth.has("2024-02-01")).toBe(true);
    expect(inMonth.has("2024-02-29")).toBe(true);
  });

  it("inclut les jours débordant des mois adjacents", () => {
    const weeks = monthMatrix(2024, 2);
    const first = weeks[0]![0]!; // 1er lundi de la grille
    // Février 2024 commence un jeudi -> la grille démarre le 29 janvier.
    expect(toYmd(first)).toBe("2024-01-29");
  });
});
