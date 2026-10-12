from __future__ import annotations
from livekit.agents import (
    AutoSubscribe,
    AgentSession,
    JobContext,
    WorkerOptions,
    cli,
)
from livekit.plugins import openai
from dotenv import load_dotenv
from api import AssistantFnc
from prompts import WELCOME_MESSAGE

load_dotenv()

async def entrypoint(ctx: JobContext):
    await ctx.connect(auto_subscribe=AutoSubscribe.SUBSCRIBE_ALL)
    await ctx.wait_for_participant()

    session = AgentSession(
        llm=openai.realtime.RealtimeModel(voice="shimmer", temperature=0.8)
    )
    await session.start(agent=AssistantFnc(), room=ctx.room)
    session.generate_reply(instructions=WELCOME_MESSAGE)

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))