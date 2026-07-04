"""
Package: agents
Purpose: All 5 WaterSentinel ADK agents.
         Import root_agent from orchestrator for ADK runner.
"""
from agents.orchestrator.agent import root_agent

__all__ = ["root_agent"]
