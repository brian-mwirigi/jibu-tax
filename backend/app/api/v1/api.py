"""
File: backend/app/api/v1/api.py
Description:
    API Version 1 Router Aggregator.
    - Aggregates sub-routers into a single APIRouter instance:
        * /agent: Role 4 LangGraph conversational agent invoke & checkpoint endpoints.
"""

from fastapi import APIRouter
from app.api.v1.agent import router as agent_router

api_router = APIRouter()
api_router.include_router(agent_router)
