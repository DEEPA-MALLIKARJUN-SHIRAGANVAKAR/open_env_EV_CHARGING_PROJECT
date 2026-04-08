from typing import Any, Dict, Tuple


def _clamp_score(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


class SimpleTask:
    def __init__(self, name: str, difficulty: str):
        self.name = name
        self.difficulty = difficulty
        self.step_count = 0
        self.total_reward = 0.0
        self.state = {"task": self.name, "difficulty": self.difficulty, "step": 0}

    def reset(self) -> Dict[str, Any]:
        self.step_count = 0
        self.total_reward = 0.0
        self.state = {"task": self.name, "difficulty": self.difficulty, "step": 0}
        return dict(self.state)

    def step(self, action: Dict[str, Any]) -> Tuple[Dict[str, Any], float, bool, Dict[str, Any]]:
        self.step_count += 1
        action_type = str((action or {}).get("action_type", "noop"))
        reward = 1.0 if action_type == "charge" else 0.2
        self.total_reward += reward
        self.state = {
            "task": self.name,
            "difficulty": self.difficulty,
            "step": self.step_count,
            "last_action": action_type,
        }
        done = self.step_count >= 5
        return dict(self.state), float(reward), bool(done), {}

    def grade(self, use_llm: bool = False) -> float:
        if self.step_count <= 0:
            return 0.0
        score = self.total_reward / float(self.step_count)
        return _clamp_score(score)


def create_easy_task() -> SimpleTask:
    return SimpleTask(name="easy_charging", difficulty="easy")


def create_medium_task() -> SimpleTask:
    return SimpleTask(name="medium_charging", difficulty="medium")


def create_hard_task() -> SimpleTask:
    return SimpleTask(name="hard_charging", difficulty="hard")
