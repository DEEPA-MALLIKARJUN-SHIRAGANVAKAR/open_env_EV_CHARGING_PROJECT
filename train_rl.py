"""
Optional RL training script for EV Charging Scheduler.
Implements DQN training using PyTorch.
"""

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from collections import deque
import random
from typing import Tuple, Dict, Any

try:
    from ev_charging_env import (
        EVChargingEnvironment,
        EnvironmentConfig,
        create_easy_task,
        create_medium_task,
    )
except ImportError:
    print("EV Charging Environment not installed")
    exit(1)


class DQNNetwork(nn.Module):
    """Simple DQN network for EV charging agent."""

    def __init__(self, state_size: int, action_size: int, hidden_size: int = 128):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(state_size, hidden_size),
            nn.ReLU(),
            nn.Linear(hidden_size, hidden_size),
            nn.ReLU(),
            nn.Linear(hidden_size, action_size),
        )

    def forward(self, state: torch.Tensor) -> torch.Tensor:
        return self.net(state)


class DQNAgent:
    """DQN Agent for EV Charging Scheduler."""

    def __init__(
        self,
        state_size: int = 128,
        action_size: int = 25,
        learning_rate: float = 1e-3,
        gamma: float = 0.99,
        epsilon: float = 1.0,
        device: str = "cpu",
    ):
        self.device = torch.device(device)
        self.state_size = state_size
        self.action_size = action_size
        self.gamma = gamma
        self.epsilon = epsilon
        self.epsilon_min = 0.01
        self.epsilon_decay = 0.995

        # Networks
        self.q_network = DQNNetwork(state_size, action_size).to(self.device)
        self.target_network = DQNNetwork(state_size, action_size).to(self.device)
        self.target_network.load_state_dict(self.q_network.state_dict())

        self.optimizer = optim.Adam(self.q_network.parameters(), lr=learning_rate)
        self.memory = deque(maxlen=10000)
        self.batch_size = 32

    def remember(self, state: np.ndarray, action: int, reward: float, next_state: np.ndarray, done: bool):
        """Store experience in memory."""
        self.memory.append((state, action, reward, next_state, done))

    def act(self, state: np.ndarray, training: bool = True) -> int:
        """Choose action using epsilon-greedy policy."""
        if training and random.random() < self.epsilon:
            return random.randint(0, self.action_size - 1)

        state_tensor = torch.tensor(state, dtype=torch.float32).unsqueeze(0).to(self.device)
        with torch.no_grad():
            q_values = self.q_network(state_tensor)
        return torch.argmax(q_values, dim=1).item()

    def replay(self, batch_size: int):
        """Train on a batch of experiences."""
        if len(self.memory) < batch_size:
            return

        batch = random.sample(self.memory, batch_size)
        states, actions, rewards, next_states, dones = zip(*batch)

        states = torch.tensor(np.array(states), dtype=torch.float32).to(self.device)
        actions = torch.tensor(np.array(actions), dtype=torch.long).to(self.device)
        rewards = torch.tensor(np.array(rewards), dtype=torch.float32).to(self.device)
        next_states = torch.tensor(np.array(next_states), dtype=torch.float32).to(self.device)
        dones = torch.tensor(np.array(dones), dtype=torch.bool).to(self.device)

        # Current Q values
        q_values = self.q_network(states).gather(1, actions.unsqueeze(1)).squeeze(1)

        # Target Q values
        with torch.no_grad():
            target_q_values = self.target_network(next_states).max(1)[0]
            target_q_values[dones] = 0.0
            target_q_values = rewards + self.gamma * target_q_values

        # Loss
        loss = nn.MSELoss()(q_values, target_q_values)

        # Update
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()

        return loss.item()

    def update_target_network(self):
        """Update target network weights."""
        self.target_network.load_state_dict(self.q_network.state_dict())

    def decay_epsilon(self):
        """Decay exploration rate."""
        self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)


def observation_to_vector(obs: Dict[str, Any]) -> np.ndarray:
    """Convert observation dict to flat vector for neural network."""
    features = []

    # Time step (normalized)
    features.append(obs["time_step"] / 200.0)

    # Grid features
    features.append(obs["grid"]["current_load"])
    features.append(obs["grid"]["electricity_price"] / 1.0)  # Normalize price

    # Vehicle features (max 20 vehicles)
    num_vehicles = min(len(obs["vehicles"]), 20)
    for i in range(num_vehicles):
        v = obs["vehicles"][i]
        features.append(v["battery_level"])
        features.append(v["required_charge"])
        features.append((v["deadline"] - obs["time_step"]) / 200.0)  # Time to deadline
        features.append(1.0 if v["fully_charged"] else 0.0)
        features.append(1.0 if v["priority"] == "urgent" else 0.0)

    # Pad with zeros if fewer than 20 vehicles
    while len(features) < 1 + 2 + 20 * 5:
        features.append(0.0)

    # Station features (max 5 stations)
    num_stations = min(len(obs["stations"]), 5)
    for i in range(num_stations):
        s = obs["stations"][i]
        features.append(s["occupied_slots"] / s["max_slots"])
        features.append(s["available_power"] / s["max_power"])

    # Pad with zeros if fewer than 5 stations
    while len(features) < len(features) + 5 * 2 - num_stations * 2:
        features.append(0.0)

    return np.array(features, dtype=np.float32)[:128]  # Limit to 128 features


def action_to_dict(action_idx: int, obs: Dict[str, Any]) -> Dict[str, Any]:
    """Convert action index to action dict."""
    num_vehicles = len(obs["vehicles"])
    num_stations = len(obs["stations"])

    # Simple mapping: action_idx encodes vehicle_id and station_id
    vehicle_id = (action_idx // num_stations) % num_vehicles
    station_id = action_idx % num_stations
    power_level = 0.5 + 0.5 * (action_idx // (num_vehicles * num_stations)) / 2.0

    return {
        "action_type": "assign",
        "vehicle_id": vehicle_id,
        "station_id": station_id,
        "power_level": min(1.0, power_level),
    }


def train_dqn(episodes: int = 50, task_difficulty: str = "easy") -> Dict[str, Any]:
    """Train DQN agent on EV charging task."""
    print(f"\n{'='*60}")
    print(f"Training DQN Agent on {task_difficulty.upper()} Task")
    print('='*60)

    # Create task
    if task_difficulty == "easy":
        task = create_easy_task()
    else:
        task = create_medium_task()

    # Create agent
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}")

    agent = DQNAgent(
        state_size=128,
        action_size=25,
        learning_rate=1e-3,
        device=device,
    )

    # Training loop
    episode_rewards = []
    episode_losses = []

    for episode in range(episodes):
        obs = task.reset()
        episode_reward = 0.0
        episode_losses_iter = []

        for step in range(task.config.max_steps):
            # Convert observation
            state = observation_to_vector(obs)

            # Choose action
            action_idx = agent.act(state, training=True)
            action = action_to_dict(action_idx, obs)

            # Step environment
            result = task.step(action)
            next_obs = result.observation
            reward = result.reward
            done = result.done

            next_state = observation_to_vector(next_obs)
            agent.remember(state, action_idx, reward, next_state, done)

            episode_reward += reward
            obs = next_obs

            # Train
            loss = agent.replay(agent.batch_size)
            if loss is not None:
                episode_losses_iter.append(loss)

            if done or result.info.get("done", False):
                break

        # Update target network every 10 episodes
        if (episode + 1) % 10 == 0:
            agent.update_target_network()

        agent.decay_epsilon()
        episode_rewards.append(episode_reward)

        avg_loss = np.mean(episode_losses_iter) if episode_losses_iter else 0.0
        episode_losses.append(avg_loss)

        if (episode + 1) % 10 == 0:
            print(f"Episode {episode+1:3d}/{episodes}: "
                  f"Reward={episode_reward:7.3f}, "
                  f"Avg Loss={avg_loss:8.5f}, "
                  f"Epsilon={agent.epsilon:.3f}")

    # Final evaluation
    print(f"\nTraining Complete!")
    print(f"Final Epsilon: {agent.epsilon:.3f}")
    print(f"Average Reward (last 10): {np.mean(episode_rewards[-10:]):.3f}")

    return {
        "agent": agent,
        "episode_rewards": episode_rewards,
        "episode_losses": episode_losses,
        "task": task,
    }


def evaluate_agent(agent: DQNAgent, task, episodes: int = 5) -> float:
    """Evaluate trained agent."""
    print(f"\nEvaluating Agent ({episodes} episodes)...")

    eval_rewards = []

    for episode in range(episodes):
        obs = task.reset()
        episode_reward = 0.0

        for step in range(task.config.max_steps):
            state = observation_to_vector(obs)
            action_idx = agent.act(state, training=False)
            action = action_to_dict(action_idx, obs)

            result = task.step(action)
            episode_reward += result.reward
            obs = result.observation

            if result.done or result.info.get("done", False):
                break

        eval_rewards.append(episode_reward)
        print(f"  Episode {episode+1}: {episode_reward:.3f}")

    avg_reward = np.mean(eval_rewards)
    print(f"\nAverage Evaluation Reward: {avg_reward:.3f}")

    return avg_reward


if __name__ == "__main__":
    # Train on easy task
    results = train_dqn(episodes=50, task_difficulty="easy")
    agent = results["agent"]
    task = results["task"]

    # Evaluate
    evaluate_agent(agent, task, episodes=5)

    print("\n" + "="*60)
    print("Training complete! Agent ready for deployment.")
    print("="*60)
