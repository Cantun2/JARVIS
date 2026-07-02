import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import MissionControl from "../components/MissionControl";
import { makeNightReport, makeProject, makeTask } from "./fixtures";

// On mocke le client API : le composant est piloté par ses retours.
vi.mock("../lib/api", () => ({
  getProjects: vi.fn(),
  getProjectTasks: vi.fn(),
  getNightReport: vi.fn(),
  transitionTask: vi.fn(),
  runNight: vi.fn(),
  createProject: vi.fn(),
}));

import {
  getNightReport,
  getProjects,
  getProjectTasks,
  transitionTask,
} from "../lib/api";

const mockGetProjects = vi.mocked(getProjects);
const mockGetProjectTasks = vi.mocked(getProjectTasks);
const mockGetNightReport = vi.mocked(getNightReport);
const mockTransitionTask = vi.mocked(transitionTask);

const TASKS = [
  makeTask({ id: "t1", status: "backlog", title: "Écrire le schéma" }),
  makeTask({
    id: "t2",
    status: "review",
    title: "Ajouter le endpoint",
    report: "OK",
    acceptance_criteria: ["Retourne 200"],
  }),
  makeTask({ id: "t3", status: "done", title: "Setup CI" }),
  makeTask({ id: "t4", status: "blocked", title: "Déployer", blocker: "accès manquant" }),
];

describe("MissionControl", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGetProjects.mockResolvedValue([makeProject({ id: "proj-1", name: "Projet démo" })]);
    mockGetProjectTasks.mockResolvedValue(TASKS);
    mockGetNightReport.mockResolvedValue(makeNightReport({ done: 3, dry_run: true }));
    mockTransitionTask.mockResolvedValue(makeTask({ id: "t2", status: "done" }));
  });

  it("charge un projet et affiche les tâches dans les bonnes colonnes", async () => {
    render(<MissionControl events={[]} />);

    await waitFor(() => expect(screen.getAllByTestId("task-card")).toHaveLength(4));

    const backlog = screen.getByTestId("column-backlog");
    expect(within(backlog).getByText("Écrire le schéma")).toBeInTheDocument();

    const review = screen.getByTestId("column-review");
    expect(within(review).getByText("Ajouter le endpoint")).toBeInTheDocument();

    const done = screen.getByTestId("column-done");
    expect(within(done).getByText("Setup CI")).toBeInTheDocument();

    const blocked = screen.getByTestId("blocked-queue");
    expect(within(blocked).getByText("Déployer")).toBeInTheDocument();

    // La carte porte son statut.
    const reviewCard = within(review).getByTestId("task-card");
    expect(reviewCard).toHaveAttribute("data-status", "review");
  });

  it("affiche le Night Report avec le badge dry-run", async () => {
    render(<MissionControl events={[]} />);
    await waitFor(() => expect(screen.getByTestId("mission-night")).toBeInTheDocument());
    expect(screen.getByTestId("night-dryrun")).toBeInTheDocument();
    expect(screen.getByTestId("night-done")).toHaveTextContent("3");
  });

  it("un clic Approve appelle transitionTask puis refetch", async () => {
    render(<MissionControl events={[]} />);
    await waitFor(() => expect(screen.getAllByTestId("task-card")).toHaveLength(4));

    const review = screen.getByTestId("column-review");
    fireEvent.click(within(review).getByTestId("task-action-approve"));

    await waitFor(() => expect(mockTransitionTask).toHaveBeenCalledWith("t2", "approve"));
    // Refetch des tâches après transition (>= 2 appels : initial + après action).
    await waitFor(() => expect(mockGetProjectTasks.mock.calls.length).toBeGreaterThanOrEqual(2));
  });
});
