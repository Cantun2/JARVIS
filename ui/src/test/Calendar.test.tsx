import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import Calendar from "../components/Calendar";

const noop = (): void => {};

describe("Calendar", () => {
  it("rend des semaines de 7 jours et les en-têtes lundi→dimanche", () => {
    render(
      <Calendar
        year={2024}
        month={2}
        selected="2024-02-10"
        marked={new Set()}
        onSelectDay={noop}
      />,
    );

    const days = screen.getAllByTestId("calendar-day");
    // Grille pleine : multiple de 7.
    expect(days.length % 7).toBe(0);
    expect(days.length).toBeGreaterThanOrEqual(28);
    expect(screen.getByText("Lun")).toBeInTheDocument();
    expect(screen.getByText("Dim")).toBeInTheDocument();
    expect(screen.getByTestId("calendar-title")).toHaveTextContent("Février 2024");
  });

  it("cliquer un jour appelle onSelectDay avec son ymd", () => {
    const onSelectDay = vi.fn();
    const { container } = render(
      <Calendar
        year={2024}
        month={2}
        selected="2024-02-10"
        marked={new Set()}
        onSelectDay={onSelectDay}
      />,
    );

    const cell = container.querySelector('[data-ymd="2024-02-15"]') as HTMLElement;
    expect(cell).not.toBeNull();
    fireEvent.click(cell);
    expect(onSelectDay).toHaveBeenCalledWith("2024-02-15");
  });

  it("les jours marqués portent une pastille", () => {
    render(
      <Calendar
        year={2024}
        month={2}
        selected="2024-02-10"
        marked={new Set(["2024-02-15"])}
        onSelectDay={noop}
      />,
    );

    const dots = screen.getAllByTestId("calendar-dot");
    expect(dots).toHaveLength(1);
  });

  it("les boutons de navigation déclenchent onPrevMonth / onNextMonth", () => {
    const onPrev = vi.fn();
    const onNext = vi.fn();
    render(
      <Calendar
        year={2024}
        month={2}
        selected="2024-02-10"
        marked={new Set()}
        onSelectDay={noop}
        onPrevMonth={onPrev}
        onNextMonth={onNext}
      />,
    );

    fireEvent.click(screen.getByTestId("calendar-prev"));
    fireEvent.click(screen.getByTestId("calendar-next"));
    expect(onPrev).toHaveBeenCalledTimes(1);
    expect(onNext).toHaveBeenCalledTimes(1);
  });
});
