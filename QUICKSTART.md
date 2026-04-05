# 🚀 Quick Start Guide

## 5-Minute Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run Baseline Agents
```bash
python inference.py
```
This runs all 3 tasks with baseline agents and prints scores.

### 3. Launch Interactive UI
```bash
python ui.py
```
Open browser to `http://localhost:7860`

---

## 10-Minute Exploration

### Try Different Tasks
```python
from ev_charging_env import create_easy_task, GreedyAgent

# Create a task
task = create_easy_task()
agent = GreedyAgent()

# Run episode
obs = task.reset()
for step in range(100):
    action = agent.get_action(obs)
    result = task.step(action)
    obs = result.observation
    if result.done:
        break

# Get score
grade = task.grade()
print(f"Score: {grade.score:.3f}")
print(f"Vehicles charged: {grade.vehicles_charged}")
print(f"Total cost: ${grade.total_cost:.2f}")
```

---

## Test Environment
```bash
pytest test_environment.py -v
```

---

## Train RL Agent (Optional)
```bash
python train_rl.py
```

---

## Docker Deployment
```bash
docker build -t ev_charging .
docker run -e OPENAI_API_KEY=sk-... ev_charging
```

---

## Key Files

| File | Use Case |
|------|----------|
| **inference.py** | Run all tasks with OpenAI API |
| **ui.py** | Interactive visualization |
| **train_rl.py** | Train DQN agent |
| **test_environment.py** | Verify functionality |
| **README.md** | Full documentation |
| **openenv.yaml** | Environment specification |

---

## Common Tasks

### Create Custom Task
```python
from ev_charging_env import Task, EnvironmentConfig

config = EnvironmentConfig(
    num_vehicles=20,
    num_stations=6,
    max_steps=250
)
task = Task("custom", "custom", config)
```

### Implement Custom Agent
```python
from ev_charging_env import BaseAgent

class MyAgent(BaseAgent):
    def get_action(self, observation):
        # Your logic here
        return {
            "action_type": "assign",
            "vehicle_id": 0,
            "station_id": 0,
            "power_level": 0.8
        }
```

### Evaluate Multiple Agents
```python
from ev_charging_env import (
    create_medium_task,
    RandomAgent,
    GreedyAgent,
    PriorityAwareAgent,
)

task = create_medium_task()
agents = {
    "random": RandomAgent(),
    "greedy": GreedyAgent(),
    "priority": PriorityAwareAgent(),
}

for name, agent in agents.items():
    obs = task.reset()
    for _ in range(200):
        action = agent.get_action(obs)
        result = task.step(action)
        obs = result.observation
        if result.done:
            break
    grade = task.grade()
    print(f"{name}: {grade.score:.3f}")
```

---

## Need Help?

1. **API Errors**: Set `OPENAI_API_KEY=sk-...`
2. **Import Errors**: Run `pip install -r requirements.txt`
3. **Slow Performance**: Use `gpt-3.5-turbo` model
4. **Tests Failing**: Check `test_environment.py` for examples

---

**Ready to go! 🚀**
