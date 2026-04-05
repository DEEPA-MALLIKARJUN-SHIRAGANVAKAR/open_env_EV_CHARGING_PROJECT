"""
Test suite for EV Charging Scheduler Environment.
Validates OpenEnv compliance and basic functionality.
"""

import pytest
from ev_charging_env import (
    EVChargingEnvironment,
    EnvironmentConfig,
    Observation,
    ChargingAction,
    create_easy_task,
    create_medium_task,
    create_hard_task,
    RandomAgent,
    GreedyAgent,
    PriorityAwareAgent,
)


class TestEnvironmentBasics:
    """Test basic environment functionality."""

    def test_environment_initialization(self):
        """Test environment can be initialized."""
        config = EnvironmentConfig(
            num_vehicles=5,
            num_stations=3,
            max_steps=100,
        )
        env = EVChargingEnvironment(config)
        assert env is not None
        assert env.time_step == 0

    def test_reset_returns_observation(self):
        """Test reset returns valid observation."""
        env = EVChargingEnvironment()
        obs = env.reset()

        assert isinstance(obs, Observation)
        assert obs.time_step == 0
        assert len(obs.vehicles) > 0
        assert len(obs.stations) > 0
        assert obs.grid is not None

    def test_state_returns_observation(self):
        """Test state method returns current observation."""
        env = EVChargingEnvironment()
        env.reset()
        obs = env.state()

        assert isinstance(obs, Observation)
        assert obs.time_step == 0

    def test_observation_structure(self):
        """Test observation has all required fields."""
        env = EVChargingEnvironment()
        obs = env.reset()

        # Check observation structure
        obs_dict = obs.to_dict()
        assert "time_step" in obs_dict
        assert "vehicles" in obs_dict
        assert "stations" in obs_dict
        assert "grid" in obs_dict
        assert "total_reward" in obs_dict


class TestStepFunction:
    """Test step function (OpenEnv required method)."""

    def test_step_with_valid_action(self):
        """Test step with valid assign action."""
        env = EVChargingEnvironment()
        obs = env.reset()

        action = {
            "action_type": "assign",
            "vehicle_id": 0,
            "station_id": 0,
            "power_level": 0.8,
        }

        result = env.step(action)

        assert result.observation is not None
        assert isinstance(result.reward, float)
        assert -1.0 <= result.reward <= 1.0
        assert isinstance(result.done, bool)
        assert isinstance(result.info, dict)

    def test_step_with_delay_action(self):
        """Test step with delay action."""
        env = EVChargingEnvironment()
        obs = env.reset()

        action = {
            "action_type": "delay",
            "vehicle_id": 0,
            "duration": 1,
        }

        result = env.step(action)

        assert result.observation is not None
        assert isinstance(result.reward, float)

    def test_step_increments_time(self):
        """Test each step increments time."""
        env = EVChargingEnvironment()
        env.reset()

        action = {"action_type": "delay", "vehicle_id": 0, "duration": 1}

        for i in range(10):
            result = env.step(action)
            assert result.observation.time_step == i + 1

    def test_step_ends_episode(self):
        """Test episode ends after max steps."""
        config = EnvironmentConfig(max_steps=50)
        env = EVChargingEnvironment(config)
        env.reset()

        action = {"action_type": "delay", "vehicle_id": 0, "duration": 1}

        for i in range(50):
            result = env.step(action)

        assert result.done is True


class TestRewardRange:
    """Test reward is properly normalized."""

    def test_reward_in_valid_range(self):
        """Test reward remains in [-1, 1] range."""
        env = EVChargingEnvironment()
        env.reset()

        action = {"action_type": "delay", "vehicle_id": 0, "duration": 1}

        for _ in range(100):
            result = env.step(action)
            assert -1.0 <= result.reward <= 1.0


class TestTasks:
    """Test task creation and grading."""

    def test_easy_task_creation(self):
        """Test easy task can be created."""
        task = create_easy_task()
        assert task is not None
        assert task.difficulty == "easy"

    def test_medium_task_creation(self):
        """Test medium task can be created."""
        task = create_medium_task()
        assert task is not None
        assert task.difficulty == "medium"

    def test_hard_task_creation(self):
        """Test hard task can be created."""
        task = create_hard_task()
        assert task is not None
        assert task.difficulty == "hard"

    def test_task_reset(self):
        """Test task reset functionality."""
        task = create_easy_task()
        obs = task.reset()
        assert isinstance(obs, Observation)
        assert task.episode_steps == 0

    def test_task_grading(self):
        """Test task grading after completion."""
        task = create_easy_task()
        task.reset()

        # Run some steps
        action = {"action_type": "delay", "vehicle_id": 0, "duration": 1}
        for _ in range(10):
            result = task.step(action)

        # Grade
        grade = task.grade()
        assert grade is not None
        assert 0.0 <= grade.score <= 1.0
        assert grade.task_name == "easy"


class TestBaselineAgents:
    """Test baseline agent implementations."""

    def test_random_agent(self):
        """Test random agent action selection."""
        agent = RandomAgent()
        obs = EVChargingEnvironment().reset()

        action = agent.get_action(obs)

        assert "action_type" in action
        assert action["action_type"] in ["assign", "delay"]
        assert "vehicle_id" in action

    def test_greedy_agent(self):
        """Test greedy agent action selection."""
        agent = GreedyAgent()
        obs = EVChargingEnvironment().reset()

        action = agent.get_action(obs)

        assert "action_type" in action
        assert "vehicle_id" in action

    def test_priority_agent(self):
        """Test priority-aware agent action selection."""
        agent = PriorityAwareAgent()
        obs = EVChargingEnvironment().reset()

        action = agent.get_action(obs)

        assert "action_type" in action
        assert "vehicle_id" in action


class TestDeterminism:
    """Test environment determinism with seeds."""

    def test_seeded_environments_identical(self):
        """Test two seeded environments produce identical sequences."""
        config1 = EnvironmentConfig(seed=42, num_vehicles=5, num_stations=3)
        env1 = EVChargingEnvironment(config1)
        obs1 = env1.reset()

        config2 = EnvironmentConfig(seed=42, num_vehicles=5, num_stations=3)
        env2 = EVChargingEnvironment(config2)
        obs2 = env2.reset()

        # Check initial observations match
        assert len(obs1.vehicles) == len(obs2.vehicles)
        assert len(obs1.stations) == len(obs2.stations)

        for v1, v2 in zip(obs1.vehicles, obs2.vehicles):
            assert v1.battery_level == v2.battery_level
            assert v1.required_charge == v2.required_charge


class TestConfigurationParameters:
    """Test environment configuration."""

    def test_custom_config(self):
        """Test custom environment configuration."""
        config = EnvironmentConfig(
            num_vehicles=20,
            num_stations=8,
            max_steps=300,
            slots_per_station=4,
            max_power_per_station=200.0,
            max_grid_load=1.2,
        )

        env = EVChargingEnvironment(config)
        obs = env.reset()

        assert len(obs.vehicles) == 20
        assert len(obs.stations) == 8
        assert env.config.max_steps == 300


class TestOpenEnvCompliance:
    """Test OpenEnv specification compliance."""

    def test_step_interface(self):
        """Test step method returns correct tuple format."""
        env = EVChargingEnvironment()
        env.reset()

        action = {"action_type": "delay", "vehicle_id": 0, "duration": 1}
        result = env.step(action)

        # Check StepResult object
        assert hasattr(result, "observation")
        assert hasattr(result, "reward")
        assert hasattr(result, "done")
        assert hasattr(result, "info")

    def test_reset_interface(self):
        """Test reset method returns observation."""
        env = EVChargingEnvironment()
        obs = env.reset()

        assert isinstance(obs, Observation)

    def test_state_interface(self):
        """Test state method returns observation."""
        env = EVChargingEnvironment()
        env.reset()
        obs = env.state()

        assert isinstance(obs, Observation)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
