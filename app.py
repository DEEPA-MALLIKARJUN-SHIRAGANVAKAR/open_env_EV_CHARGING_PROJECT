from typing import Any, Dict

from fastapi import Body, FastAPI


app = FastAPI(title="OpenEnv Minimal API", version="1.0.0")


def _initial_state() -> Dict[str, Any]:
    return {
        "step": 0,
        "energy": 0.0,
    }


current_state: Dict[str, Any] = _initial_state()


@app.post("/reset")
def reset_environment() -> Dict[str, Any]:
    global current_state
    current_state = _initial_state()
    return {"state": dict(current_state)}


@app.post("/step")
def step_environment(payload: Dict[str, Any] = Body(default_factory=dict)) -> Dict[str, Any]:
    global current_state

    current_state["step"] += 1

    action = payload.get("action")
    if isinstance(action, dict):
        action_type = str(action.get("action_type", "noop"))
    else:
        action_type = str(payload.get("action_type", "noop"))
    if action_type == "charge":
        current_state["energy"] += 1.0
        reward = 1.0
    else:
        reward = 0.0

    done = current_state["step"] >= 5
    observation = dict(current_state)

    return {
        "observation": observation,
        "reward": float(reward),
        "done": bool(done),
        "info": {},
    }


@app.get("/state")
def get_state() -> Dict[str, Any]:
    return dict(current_state)
