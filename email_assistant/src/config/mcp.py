"""
Load MCP configuration from config/mcp.yaml.
Exposes models, agents, routing, memory for use by agents and workflow.
"""
import os
import yaml

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
# src/config -> src -> project root (email_assistant/)
PROJECT_ROOT = os.path.dirname(os.path.dirname(_THIS_DIR))
_CONFIG_PATH = os.path.join(PROJECT_ROOT, "config", "mcp.yaml")

_cfg = {}

def _load():
    global _cfg
    if _cfg:
        return _cfg
    if not os.path.isfile(_CONFIG_PATH):
        _cfg = {
            "models": {"primary": {"model": "gpt-4o", "temperature": 0.7, "max_tokens": 1000},
                      "fallback": {"model": "command-r", "temperature": 0.7, "max_tokens": 1000}},
            "routing": {"max_retries": 2},
            "agents": {},
            "memory": {"max_history_per_user": 10, "persist_path": "src/memory/user_profiles.json"},
        }
        return _cfg
    with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
        _cfg = yaml.safe_load(f) or {}
    return _cfg

def get_config():
    return _load()

models = _load().get("models", {})
agents = _load().get("agents", {})
routing = _load().get("routing", {})
memory = _load().get("memory", {})
