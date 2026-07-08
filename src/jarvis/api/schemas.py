"""DTO REST/WS — séparés des modèles internes (contrat de câble stable avec l'UI)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel


class HealthDTO(BaseModel):
    mode: str
    version: str
    inference_backend: str
    desktop_backend: str
    placement_available: bool


class LastRunDTO(BaseModel):
    correlation_id: str
    status: str
    tokens: int
    usd: float
    ended_ts: str | None = None
    error: str | None = None


class AgentDTO(BaseModel):
    name: str
    mode: str
    permissions: list[str]
    enabled: bool
    conversational: bool = False  # True → clic ouvre le chat ; False → clic lance l'agent
    status: str  # idle | started | finished | failed | escalated
    last_run: LastRunDTO | None = None


class RunRequest(BaseModel):
    profile: str | None = None


class RunResultDTO(BaseModel):
    correlation_id: str
    status: str
    output: dict[str, Any]


class EventDTO(BaseModel):
    seq: int
    id: str
    type: str
    ts: str
    source: str
    correlation_id: str | None = None
    payload: dict[str, Any]


class EventsPageDTO(BaseModel):
    events: list[EventDTO]
    latest_seq: int


class InboxItemDTO(BaseModel):
    id: str
    sender: str
    subject: str
    category: str
    priority: int
    summary: str
    draft: str | None = None
    corrected: bool = False


class InboxDTO(BaseModel):
    items: list[InboxItemDTO]
    counts: dict[str, int]


class DraftDTO(BaseModel):
    mail_id: str
    sender: str
    subject: str
    body: str
    created_ts: str


class ReclassifyRequest(BaseModel):
    category: Literal["urgent", "action", "info", "newsletter", "spam"]


class ChatRequest(BaseModel):
    agent: str
    message: str
    conversation_id: str | None = None
    project: str | None = None


class ChatReplyDTO(BaseModel):
    conversation_id: str
    agent: str
    reply: str
    turns: int


class ChatMessageDTO(BaseModel):
    role: str
    text: str
    created_ts: str


class ChatHistoryDTO(BaseModel):
    conversation_id: str
    agent: str
    messages: list[ChatMessageDTO]


class ConversationDTO(BaseModel):
    id: str
    agent: str
    title: str
    updated_ts: str


class EchoRequest(BaseModel):
    utterance: str


class EchoResponseDTO(BaseModel):
    heard: str
    wake_detected: bool
    intent: str
    routed_to: str | None
    response: str
    spoke: bool


class BriefingDTO(BaseModel):
    text: str
    sections: dict[str, Any]


class ProjectDTO(BaseModel):
    id: str
    name: str
    goal: str
    created_ts: str
    task_counts: dict[str, int]


class TaskDTO(BaseModel):
    id: str
    project_id: str
    title: str
    description: str
    acceptance_criteria: list[str]
    status: str
    report: str
    diff: str
    blocker: str | None
    updated_ts: str


class NightTaskDTO(BaseModel):
    title: str
    status: str
    branch: str | None = None
    note: str = ""


class NightReportDTO(BaseModel):
    date: str
    done: int
    blocked: int
    failed: int
    cost_usd: float
    dry_run: bool
    tasks: list[NightTaskDTO]
    blockers: list[str]


class CreateProjectRequest(BaseModel):
    goal: str
    name: str | None = None


class CreateProjectResponse(BaseModel):
    project: ProjectDTO
    tasks: list[TaskDTO]


class TransitionRequest(BaseModel):
    action: Literal["approve", "reject", "retry"]


class TodoDTO(BaseModel):
    id: str
    kind: str
    title: str
    date: str
    time: str | None
    notes: str
    status: str
    remind_lead_min: int
    reminded_ts: str | None
    tags: list[str]
    proposal: str
    updated_ts: str


class CreateTodoRequest(BaseModel):
    title: str
    date: str
    kind: Literal["task", "appointment"] = "task"
    time: str | None = None
    notes: str = ""
    remind_lead_min: int = 0
    tags: list[str] = []


class UpdateTodoRequest(BaseModel):
    title: str | None = None
    date: str | None = None
    time: str | None = None
    notes: str | None = None
    kind: Literal["task", "appointment"] | None = None
    remind_lead_min: int | None = None
    tags: list[str] | None = None


class TodoStatusRequest(BaseModel):
    status: Literal["pending", "done", "cancelled"]
