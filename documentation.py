"""
Documentation and guides for the EV Charging Scheduler environment.
"""

MAIN_DOCUMENTATION = """
# ⚡ EV Charging Scheduler - Production OpenEnv Environment

## Overview

A sophisticated, production-ready OpenEnv environment for optimizing electric vehicle (EV) charging scheduling across distributed charging infrastructure with dynamic pricing, grid constraints, and priority management.

## Problem Statement

Modern electric grids face critical challenges:
- **Peak demand management**: Grid overload during high charging periods
- **Cost optimization**: Dynamic electricity pricing requires intelligent scheduling
- **Infrastructure constraints**: Limited charging stations vs. growing EV fleet
- **Priority management**: Emergency vehicles and time-constrained deadlines

## Key Features

✅ **Multi-Objective Optimization**
- Minimize total charging cost
- Avoid grid overload peaks
- Respect vehicle charge deadlines
- Handle priority classifications (standard vs. urgent)

✅ **Realistic Grid Dynamics**
- Dynamic electricity pricing based on load
- Grid overload penalties
- Charging station capacity constraints
- Battery charging physics simulation

✅ **Mission-Critical Vehicles**
- Emergency vehicles with highest priority
- Time-sensitive charging deadlines
- Priority-based queue management
- Missed deadline penalties

✅ **Production-Ready Design**
- OpenEnv-compatible interface
- Task-based evaluation with grading
- Multiple agent baselines
- Comprehensive benchmarking

## Environment Configuration

### Vehicle Parameters
- **Fleet Size**: 5-50 vehicles (configurable)
- **Battery Capacity**: 50-100 kWh
- **Charge Deadlines**: 1-200 time steps
- **Priority Levels**: Standard, Urgent

### Station Parameters
- **Number of Stations**: 2-10 (configurable)
- **Charging Capacity**: 5-20 kW per station
- **Number of Slots**: 2-5 slots per station
- **Availability**: 100% uptime

### Grid Parameters
- **Base Electricity Price**: $0.15/kWh
- **Peak Load Multiplier**: Up to 3x base price
- **Grid Overload Threshold**: 80% capacity
- **Overload Penalty**: -1.0 reward per step

## Agent Strategies

### 1. Random Agent (Baseline)
- Takes random valid actions
- Stochastic assignment and power levels
- Useful for comparison baseline

### 2. Greedy Agent
- Assigns vehicles with nearest deadlines first
- Selects cheapest available station
- Adjusts power level based on bottle bottlenecks
- Simple but effective heuristic

### 3. Priority-Aware Agent
- Prioritizes urgent vehicles
- Balances grid load distribution
- Minimizes peak overload periods
- Coordinates multi-vehicle arrivals

### 4. Optimal Search Agent
- Uses exhaustive search on small problems
- Guarantees near-optimal solutions
- Limited by computational complexity
- Useful as upper-bound reference

## Evaluation Metrics

- **Score (0-1)**: Overall balanced performance
- **Episode Reward**: Cumulative task rewards
- **Vehicles Charged**: Count of successfully charged vehicles
- **Missed Deadlines**: Count of deadline misses
- **Grid Overloads**: Number of overload events
- **Total Cost**: Sum of electricity costs ($)

## Quick Start

### Installation
bash
pip install -r requirements.txt

### Run Interactive Playground
bash
python ui.py

### Run Full Episode Evaluation
bash
python baseline_evaluation.py

### Run Benchmarks
bash
python benchmarks.py

### Run with Docker
bash
docker build -t ev_charging_env .
docker run -p 7860:7860 ev_charging_env

## Task Difficulties

### Easy Task
- 10 vehicles, 5 stations
- Generous time windows (100+ steps)
- Moderate grid load
- 80% success is achievable

### Medium Task
- 20 vehicles, 7 stations
- Standard time windows (50-100 steps)
- Higher grid load
- 60% success is good

### Hard Task
- 30 vehicles, 5 stations
- Tight time windows (20-50 steps)
- Peak grid load periods
- 40% success is excellent

## Advanced Usage

### Custom Environment Configuration
python
from ev_charging_env import EVChargingEnvironment, EnvironmentConfig

config = EnvironmentConfig(
    num_vehicles=25,
    num_stations=6,
    max_steps=150,
    seed=42
)
env = EVChargingEnvironment(config)

### Training Custom Agents
- Inherit from `BaseAgent`
- Implement `get_action(observation)` method
- Work with the provided environment interface
- Use baseline agents as examples

### Integration with RL Libraries
- Compatible with OpenAI Gym interface
- Works with Stable Baselines3
- Supports PyTorch/TensorFlow training
- Full episode trajectory logging

## Performance Benchmarks (Reference)

| Agent | Easy Score | Medium Score | Hard Score |
|-------|-----------|-------------|-----------|
| Random | 0.45 | 0.35 | 0.25 |
| Greedy | 0.72 | 0.58 | 0.42 |
| Priority | 0.78 | 0.65 | 0.48 |
| Optimal | 0.88 | 0.75 | 0.60 |

## Architecture

```
EV Charging Scheduler
├── Environment
│   ├── Vehicle Management
│   ├── Station Management
│   └── Grid Dynamics
├── Agents
│   ├── Random
│   ├── Greedy
│   ├── Priority-Aware
│   └── Optimal Search
├── Tasks
│   ├── Easy
│   ├── Medium
│   └── Hard
└── Evaluation
    ├── Grading System
    ├── Benchmarking
    └── Visualization
```

## API Reference

### Core Classes

**EVChargingEnvironment**
- `reset()` → Observation
- `step(action)` → StepResult
- `render()` → str (ASCII visualization)

**ChargingAction**
```python
{
    "action_type": "assign",  # or "power_level"
    "vehicle_id": int,
    "station_id": int,
    "power_level": float  # 0-1
}
```

**Observation**
```python
{
    "time_step": int,
    "vehicles": [VehicleStatus, ...],
    "stations": [ChargingStationStatus, ...],
    "grid": GridStatus
}
```

## Troubleshooting

**Gradio Import Error**
bash
pip install gradio

**OPENAI_API_KEY Error**
bash
export OPENAI_API_KEY=sk-...

**CUDA/GPU Issues**
bash
pip install torch --index-url https://download.pytorch.org/whl/cpu

## Contributing

Contributions welcome! Areas for improvement:
- New agent strategies
- Alternative reward functions
- Extended vehicle types
- Real-world data integration

## Citation

If you use this environment in research, please cite:
```
@software{ev_charging_2024,
  title={EV Charging Scheduler - OpenEnv Environment},
  year={2024},
  publisher={GitHub}
}
```

## License

MIT License - See LICENSE file for details

## Support

- 📖 Documentation: See FILE_REFERENCE.md
- 🐛 Issues: Check IMPLEMENTATION_SUMMARY.md
- 📋 Quick Reference: QUICKSTART.md
"""

AGENT_GUIDE = """
# Agent Implementation Guide

## Creating Custom Agents

### Basic Structure

```python
from ev_charging_env import BaseAgent
from ev_charging_env.models import Observation, ChargingAction

class MyCustomAgent(BaseAgent):
    def __init__(self):
        self.name = "MyAgent"
    
    def get_action(self, obs: Observation) -> ChargingAction:
        # Your agent logic here
        # Return a valid ChargingAction
        pass
```

### Accessing Observation Data

```python
def get_action(self, obs: Observation) -> ChargingAction:
    # Current time
    current_time = obs.time_step
    
    # Vehicle information
    for vehicle in obs.vehicles:
        vehicle_id = vehicle.id
        battery_level = vehicle.battery_level
        deadline = vehicle.deadline
        priority = vehicle.priority
        fully_charged = vehicle.fully_charged
    
    # Station information
    for station in obs.stations:
        station_id = station.id
        occupied_slots = station.occupied_slots
        max_slots = station.max_slots
        available_power = station.available_power
        max_power = station.max_power
    
    # Grid information
    grid_load = obs.grid.current_load
    electricity_price = obs.grid.electricity_price
```

### Valid Actions

```python
# Assign vehicle to station
action = {
    "action_type": "assign",
    "vehicle_id": 0,
    "station_id": 1,
    "power_level": 0.8  # 80% of max power
}

# Release vehicle from charging
action = {
    "action_type": "release",
    "vehicle_id": 0,
    "station_id": 1
}

# Adjust power level
action = {
    "action_type": "power_level",
    "vehicle_id": 0,
    "station_id": 1,
    "power_level": 0.5
}
```

## Strategy Patterns

### Greedy Assignment
"""

TASK_GUIDE = """
# Task and Grading System

## Task Types

### Easy Task
- Straightforward optimization problem
- Plenty of charging capacity
- Long time windows
- Lower reward variability

### Medium Task
- Balanced difficulty
- Mixed capacity constraints
- Standard time windows
- Moderate reward challenges

### Hard Task
- Challenging optimization
- Tight capacity constraints
- Short time windows
- High reward variability

## Grading System

Scores are calculated on a 0-1 scale considering:

1. **Task Completion (40%)**
   - Percentage of vehicles successfully charged
   - Deadline adherence

2. **Resource Efficiency (30%)**
   - Electricity cost minimization
   - Grid load balancing

3. **Priority Management (20%)**
   - Urgent vehicle handling
   - Priority queue performance

4. **Constraint Satisfaction (10%)**
   - Grid overload avoidance
   - Station capacity respect

## Episode Results

Each episode returns:
- **score**: Final normalized score (0-1)
- **episode_reward**: Cumulative reward sum
- **steps_taken**: Number of steps executed
- **vehicles_charged**: Successfully charged vehicles
- **missed_deadlines**: Vehicle deadline misses
- **grid_overloads**: Number of overload events
- **total_cost**: Total electricity cost
"""

QUICKSTART_GUIDE = """
# 5-Minute Quick Start

## 1. Install and Setup (30 seconds)
```bash
cd ev_charging_env
pip install -r requirements.txt
```

## 2. Launch Interactive UI (15 seconds)
```bash
python ui.py
```
Opens at `http://localhost:7860`

## 3. Try the Playground (1 minute)
1. Click "Initialize Environment"
2. Select "greedy" agent
3. Click "Execute Step" repeatedly
4. Watch the visualization

## 4. Run Benchmarks (2 minutes)
```bash
python baseline_evaluation.py
```
See how different agents perform

## 5. Explore Further
- Check `README.md` for full documentation
- See `examples/` for custom agent code
- Review `baseline_evaluation.py` for evaluation patterns

## Common Tasks

**Run a single episode**
```bash
python inference.py --agent greedy --task medium
```

**Train a custom agent**
```bash
python train_rl.py --episodes 100 --seed 42
```

**Test environment setup**
```bash
python verify_environment.py
```

**View available options**
```bash
python ui.py --help
```
"""

RESOURCES = {
    "main": MAIN_DOCUMENTATION,
    "agents": AGENT_GUIDE,
    "tasks": TASK_GUIDE,
    "quickstart": QUICKSTART_GUIDE,
}
