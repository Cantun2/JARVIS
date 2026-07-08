"""Routes REST du chat multi-tours : dialoguer avec un agent conversationnel.

Route dédiée (et non le générique `/api/agents/{name}/run`) car les champs `message` /
`conversation_id` ne figurent pas dans `RunRequest` (qui les filtrerait).
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from jarvis.agents.conversational import ConversationInput, ConversationOutput
from jarvis.api.schemas import ChatHistoryDTO, ChatReplyDTO, ChatRequest, ConversationDTO
from jarvis.api.views import chat_history_dto, conversation_dtos
from jarvis.assembly import JarvisContext
from jarvis.core.errors import AgentDisarmed, BudgetExceeded, PermissionDenied

router = APIRouter()


def _ctx(request: Request) -> JarvisContext:
    ctx: JarvisContext = request.app.state.ctx
    return ctx


@router.post("/chat", response_model=ChatReplyDTO)
async def chat(request: Request, body: ChatRequest) -> ChatReplyDTO:
    ctx = _ctx(request)
    if not ctx.registry.has(body.agent):
        raise HTTPException(status_code=404, detail=f"Agent inconnu : {body.agent}")
    agent = ctx.registry.get(body.agent)
    if not agent.contract.conversational:
        raise HTTPException(
            status_code=400, detail=f"{body.agent} n'est pas un agent conversationnel"
        )
    data = ConversationInput(
        message=body.message, conversation_id=body.conversation_id, project=body.project
    )
    try:
        out = await ctx.runner.run(agent, data)
    except AgentDisarmed as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except PermissionDenied as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except BudgetExceeded as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    assert isinstance(out, ConversationOutput)
    return ChatReplyDTO(
        conversation_id=out.conversation_id, agent=body.agent, reply=out.reply, turns=out.turns
    )


@router.get("/chat/{conversation_id}", response_model=ChatHistoryDTO)
async def chat_history(request: Request, conversation_id: str) -> ChatHistoryDTO:
    dto = chat_history_dto(_ctx(request), conversation_id)
    if dto is None:
        raise HTTPException(status_code=404, detail=f"Conversation inconnue : {conversation_id}")
    return dto


@router.get("/conversations", response_model=list[ConversationDTO])
async def conversations(request: Request, agent: str | None = None) -> list[ConversationDTO]:
    return conversation_dtos(_ctx(request), agent)
