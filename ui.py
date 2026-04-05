"""
Enhanced Gradio UI for EV Charging Scheduler visualization.
Provides interactive visualization, full episode evaluation, benchmarking, and documentation.
"""

try:
    import gradio as gr
except ImportError:
    print("Gradio not installed. Install with: pip install gradio")
    exit(1)

from ev_charging_env import (
    EVChargingEnvironment,
    EnvironmentConfig,
    RandomAgent,
    GreedyAgent,
    PriorityAwareAgent,
    create_easy_task,
    create_medium_task,
    create_hard_task,
)
from benchmarks import BenchmarkSuite
from documentation import RESOURCES
import json
import argparse
from typing import Dict, Tuple, Any
import time


class UIRunner:
    """Interactive UI for EV charging scheduler."""

    def __init__(self):
        self.env = None
        self.agent = None
        self.agent_type = "greedy"
        self.step_count = 0
        self.episode_log = []
        self.benchmark_suite = BenchmarkSuite()
        self.last_benchmark_results = []

    def initialize_environment(
        self,
        num_vehicles: int,
        num_stations: int,
        max_steps: int,
        agent_type: str,
    ) -> str:
        """Initialize environment with given parameters."""
        config = EnvironmentConfig(
            num_vehicles=num_vehicles,
            num_stations=num_stations,
            max_steps=max_steps,
            seed=42,
        )

        self.env = EVChargingEnvironment(config)
        self.agent_type = agent_type

        if agent_type == "random":
            self.agent = RandomAgent()
        elif agent_type == "greedy":
            self.agent = GreedyAgent()
        elif agent_type == "priority":
            self.agent = PriorityAwareAgent()

        self.step_count = 0
        self.episode_log = []

        obs = self.env.reset()
        return f"✅ Environment initialized with {num_vehicles} vehicles, {num_stations} stations, {agent_type} agent.\n\n" + self._format_state(obs)

    def step_environment(self) -> tuple:
        """Execute one environment step."""
        if self.env is None:
            return "Error: Environment not initialized", "{}", ""

        obs = self.env.state()
        action = self.agent.get_action(obs)

        result = self.env.step(action)
        self.step_count += 1

        # Log
        log_entry = {
            "step": self.step_count,
            "action": action,
            "reward": float(result.reward),
            "grid_load": float(result.observation.grid.current_load),
        }
        self.episode_log.append(log_entry)

        state_str = self._format_state(result.observation)
        action_str = json.dumps(action, indent=2)
        log_str = "\n".join(
            f"T{entry['step']}: {entry['action']['action_type']} "
            f"(reward={entry['reward']:.3f}, load={entry['grid_load']:.1%})"
            for entry in self.episode_log[-10:]
        )

        return state_str, action_str, log_str

    def render_environment(self) -> str:
        """Render current environment state."""
        if self.env is None:
            return "Environment not initialized"
        return self.env.render()

    def _format_state(self, obs) -> str:
        """Format observation for display."""
        lines = [
            f"⏱️  Time Step: {obs.time_step}",
            f"🔌 Grid Load: {obs.grid.current_load:.1%}",
            f"💰 Electricity Price: ${obs.grid.electricity_price:.3f}/kWh",
            "",
            "🚗 Vehicles:",
        ]

        for v in obs.vehicles[:5]:  # Show first 5
            status = "✓ CHARGED" if v.fully_charged else f"  {v.battery_level:.0%}"
            urgent = " [URGENT]" if v.priority.value == "urgent" else ""
            lines.append(f"   V{v.id}: {status} | Deadline: T{v.deadline}{urgent}")

        if len(obs.vehicles) > 5:
            lines.append(f"   ... and {len(obs.vehicles) - 5} more vehicles")

        lines.extend(["", "🔋 Charging Stations:"])

        for s in obs.stations[:3]:  # Show first 3
            lines.append(
                f"   S{s.id}: {s.occupied_slots}/{s.max_slots} slots | "
                f"{s.available_power:.1f}/{s.max_power:.1f} kW"
            )

        if len(obs.stations) > 3:
            lines.append(f"   ... and {len(obs.stations) - 3} more stations")

        return "\n".join(lines)


    # ===== FULL EPISODE EVALUATION METHODS =====

    def run_full_episode(self, task_type: str, agent_type: str, max_steps: int = None) -> Tuple[str, str]:
        """Run a complete episode and return detailed results."""
        try:
            # Create task
            if task_type == "easy":
                task = create_easy_task()
            elif task_type == "medium":
                task = create_medium_task()
            else:
                task = create_hard_task()

            max_steps = max_steps or task.config.max_steps

            # Create agent
            if agent_type == "random":
                agent = RandomAgent()
            elif agent_type == "greedy":
                agent = GreedyAgent()
            else:
                agent = PriorityAwareAgent()

            # Run episode
            obs = task.reset()
            total_reward = 0.0
            episode_log = []

            start_time = time.time()
            for step in range(max_steps):
                action = agent.get_action(obs)
                result = task.step(action)
                total_reward += result.reward
                obs = result.observation

                episode_log.append({
                    "step": step + 1,
                    "reward": float(result.reward),
                    "grid_load": float(obs.grid.current_load),
                    "price": float(obs.grid.electricity_price),
                })

                if result.done:
                    break

            elapsed_time = time.time() - start_time

            # Grade episode
            grade_result = task.grade(use_llm=False)

            # Format results
            results_text = f"""
╔════════════════════════════════════════════════════════════════╗
║               FULL EPISODE EVALUATION RESULTS                   ║
╚════════════════════════════════════════════════════════════════╝

📊 TASK: {task_type.upper()} | AGENT: {agent_type.upper()} | TIME: {elapsed_time:.2f}s

═══════════════════════════════════════════════════════════════

🎯 PRIMARY METRICS:
  • Overall Score:        {grade_result.score:.4f} / 1.0
  • Episode Reward:       {grade_result.episode_reward:.2f}
  • Steps Executed:       {grade_result.steps_taken}
  • Execution Time:       {elapsed_time:.3f} seconds

🚗 VEHICLE METRICS:
  • Vehicles Charged:     {grade_result.vehicles_charged}
  • Missed Deadlines:     {grade_result.missed_deadlines}
  • Success Rate:         {(grade_result.vehicles_charged / max(grade_result.vehicles_charged + grade_result.missed_deadlines, 1) * 100):.1f}%

⚡ GRID METRICS:
  • Grid Overloads:       {grade_result.grid_overloads}
  • Total Cost:           ${grade_result.total_cost:.2f}
  • Avg Cost per Vehicle: ${(grade_result.total_cost / max(grade_result.vehicles_charged, 1)):.2f}

═══════════════════════════════════════════════════════════════

📝 DETAILED BREAKDOWN:
{grade_result.details}
"""

            log_text = "EPISODE TIMELINE (Last 20 steps):\n"
            log_text += "Step | Reward  | Grid Load | Price\n"
            log_text += "-----+---------+-----------+--------\n"
            for entry in episode_log[-20:]:
                log_text += f"{entry['step']:4d} | {entry['reward']:7.2f} | {entry['grid_load']:9.1%} | ${entry['price']:.3f}\n"

            return results_text, log_text

        except Exception as e:
            return f"Error running episode: {str(e)}", ""

    # ===== BENCHMARK SUITE METHODS =====

    def run_benchmark_suite(self, agents: str, tasks: str, max_steps: int) -> str:
        """Run comprehensive benchmark suite."""
        try:
            agents_list = [a.strip() for a in agents.split(",")]
            tasks_list = [t.strip() for t in tasks.split(",")]

            results = self.benchmark_suite.run_benchmark(agents_list, tasks_list, max_steps)
            self.last_benchmark_results = results

            summary_text = self.benchmark_suite.format_results_for_display(results)
            return summary_text

        except Exception as e:
            return f"Error running benchmarks: {str(e)}"

    def get_benchmark_comparison(self) -> str:
        """Get formatted benchmark comparison."""
        if not self.last_benchmark_results:
            return "No benchmark results available. Run benchmarks first."

        summary = self.benchmark_suite.get_summary_by_agent(self.last_benchmark_results)

        output = "AGENT PERFORMANCE COMPARISON\n"
        output += "=" * 100 + "\n\n"
        output += f"{'Agent':<15} {'Avg Score':<12} {'Avg Reward':<12} {'Vehicles':<12} {'Cost':<12} {'Time(s)':<12}\n"
        output += "-" * 100 + "\n"

        for agent, metrics in sorted(summary.items(), key=lambda x: x[1]['avg_score'], reverse=True):
            output += (
                f"{agent:<15} {metrics['avg_score']:<12.4f} {metrics['avg_reward']:<12.2f} "
                f"{metrics['avg_vehicles_charged']:<12.1f} ${metrics['avg_cost']:<11.2f} "
                f"{metrics['total_time']:<12.2f}\n"
            )

        return output

    # ===== DOCUMENTATION METHODS =====

    def get_documentation(self, doc_type: str) -> str:
        """Get documentation content."""
        return RESOURCES.get(doc_type, "Documentation not found.")


# Create UI runner
runner = UIRunner()

# Build Gradio interface with multiple tabs
with gr.Blocks(title="⚡ EV Charging Scheduler - Benchmark Suite") as demo:
    gr.Markdown("# ⚡ EV Charging Scheduler - Production Benchmark Suite")
    gr.Markdown("*Multi-agent optimization environment for smart grid EV charging scheduling*")

    with gr.Tabs():

        # ===== TAB 1: INTERACTIVE PLAYGROUND =====
        with gr.TabItem("🎮 Interactive Playground"):
            gr.Markdown("## Interactive Environment Simulator")
            gr.Markdown("Configure and control the simulation step-by-step to observe agent behavior in real-time.")

            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("### Configuration")
                    num_vehicles = gr.Slider(
                        minimum=3, maximum=30, step=1, value=10, label="Number of Vehicles"
                    )
                    num_stations = gr.Slider(
                        minimum=2, maximum=10, step=1, value=5, label="Number of Stations"
                    )
                    max_steps = gr.Slider(
                        minimum=50, maximum=300, step=10, value=200, label="Max Steps"
                    )
                    agent_type = gr.Radio(
                        choices=["random", "greedy", "priority"],
                        value="greedy",
                        label="Agent Type",
                    )
                    init_button = gr.Button("Initialize Environment", scale=2, size="lg")

                with gr.Column(scale=1):
                    gr.Markdown("### Simulation Control")
                    state_display = gr.Textbox(
                        label="Current State",
                        lines=18,
                        interactive=False,
                    )

            with gr.Row():
                action_display = gr.Code(
                    language="json", label="Last Action", interactive=False, lines=6
                )
                log_display = gr.Textbox(
                    label="Episode Log", lines=6, interactive=False
                )

            with gr.Row():
                step_button = gr.Button("Execute Step", scale=2, size="lg", variant="primary")
                render_button = gr.Button("Render ASCII Visualization", scale=1, size="lg")

            render_output = gr.Textbox(
                label="ASCII Render", lines=12, interactive=False
            )

            # Event handlers for interactive playground
            init_button.click(
                fn=runner.initialize_environment,
                inputs=[num_vehicles, num_stations, max_steps, agent_type],
                outputs=[state_display],
            )

            step_button.click(
                fn=runner.step_environment,
                inputs=[],
                outputs=[state_display, action_display, log_display],
            )

            render_button.click(
                fn=runner.render_environment,
                inputs=[],
                outputs=[render_output],
            )

        # ===== TAB 2: FULL EPISODE EVALUATION =====
        with gr.TabItem("📊 Full Episode Evaluation"):
            gr.Markdown("## Complete Episode Evaluation")
            gr.Markdown("Run full episodes on predefined tasks and get detailed metrics.")

            with gr.Row():
                with gr.Column():
                    gr.Markdown("### Configuration")
                    eval_task = gr.Radio(
                        choices=["easy", "medium", "hard"],
                        value="medium",
                        label="Task Difficulty",
                    )
                    eval_agent = gr.Radio(
                        choices=["random", "greedy", "priority"],
                        value="greedy",
                        label="Agent Type",
                    )
                    eval_max_steps = gr.Slider(
                        minimum=50, maximum=300, step=10, value=200, label="Max Steps"
                    )
                    run_episode_button = gr.Button("Run Full Episode", scale=2, size="lg", variant="primary")

                with gr.Column():
                    gr.Markdown("### Results")
                    results_display = gr.Textbox(
                        label="Evaluation Results",
                        lines=18,
                        interactive=False,
                    )

            episode_log_display = gr.Textbox(
                label="Episode Timeline", lines=12, interactive=False
            )

            run_episode_button.click(
                fn=runner.run_full_episode,
                inputs=[eval_task, eval_agent, eval_max_steps],
                outputs=[results_display, episode_log_display],
            )

        # ===== TAB 3: BENCHMARK SUITE =====
        with gr.TabItem("🏆 Benchmark Suite"):
            gr.Markdown("## Comprehensive Benchmarking")
            gr.Markdown("Compare multiple agents across different task difficulties to identify optimal strategies.")

            with gr.Row():
                with gr.Column():
                    gr.Markdown("### Benchmark Configuration")
                    benchmark_agents = gr.Textbox(
                        value="random,greedy,priority",
                        label="Agents (comma-separated)",
                        info="Options: random, greedy, priority"
                    )
                    benchmark_tasks = gr.Textbox(
                        value="easy,medium,hard",
                        label="Tasks (comma-separated)",
                        info="Options: easy, medium, hard"
                    )
                    benchmark_max_steps = gr.Slider(
                        minimum=50, maximum=300, step=10, value=200, label="Max Steps per Episode"
                    )
                    run_benchmark_button = gr.Button("Run Benchmarks", scale=2, size="lg", variant="primary")

            benchmark_results = gr.Textbox(
                label="Benchmark Results",
                lines=20,
                interactive=False,
            )

            benchmark_comparison = gr.Textbox(
                label="Agent Comparison Summary",
                lines=10,
                interactive=False,
            )

            run_benchmark_button.click(
                fn=runner.run_benchmark_suite,
                inputs=[benchmark_agents, benchmark_tasks, benchmark_max_steps],
                outputs=[benchmark_results],
            ).then(
                fn=runner.get_benchmark_comparison,
                inputs=[],
                outputs=[benchmark_comparison],
            )

        # ===== TAB 4: DOCUMENTATION =====
        with gr.TabItem("📖 Documentation"):
            gr.Markdown("## Complete Environment Documentation")

            with gr.Row():
                doc_selector = gr.Radio(
                    choices=["main", "agents", "tasks", "quickstart"],
                    value="main",
                    label="Select Documentation",
                )

            with gr.Row():
                doc_refresher = gr.Button("Load Documentation", variant="primary")

            documentation_display = gr.Markdown(
                value=RESOURCES["main"],
                label="Documentation Content",
            )

            def update_documentation(doc_type):
                return gr.Markdown(RESOURCES.get(doc_type, "Documentation not found."))

            doc_selector.change(
                fn=lambda doc_type: RESOURCES.get(doc_type, "Documentation not found."),
                inputs=[doc_selector],
                outputs=[documentation_display],
            )

        # ===== TAB 5: ABOUT =====
        with gr.TabItem("ℹ️ About"):
            gr.Markdown("""
## About This Environment

**EV Charging Scheduler** is a production-ready OpenEnv environment designed for:
- Multi-objective optimization challenges
- Reinforcement learning research
- AI agent benchmarking
- Smart grid applications

### Key Features
✅ **Multi-objective optimization** across cost, efficiency, and constraints  
✅ **Realistic grid dynamics** with dynamic pricing and overload penalties  
✅ **Multiple difficulty levels** (Easy, Medium, Hard)  
✅ **Agent baselines** (Random, Greedy, Priority-Aware, Optimal)  
✅ **Comprehensive evaluation** with detailed metrics  

### Usage Links
- 📖 **Full Documentation**: See Documentation tab
- 🚀 **Quick Start**: Check QUICKSTART.md
- 🐛 **Troubleshooting**: Check IMPLEMENTATION_SUMMARY.md
- 📊 **Benchmarks**: Run Benchmark Suite tab

### Environment Stats
| Metric | Value |
|--------|-------|
| Vehicle Fleet | 3-50 vehicles |
| Charging Stations | 2-10 stations |
| Episode Length | 50-300 steps |
| State Dimensions | ~500 (variable) |
| Action Space | Discrete (assign/release/power) |

### Citation
```
@software{ev_charging_2024,
  title={EV Charging Scheduler - OpenEnv Environment},
  year={2024}
}
```

*Built for the OpenEnv Initiative*
            """)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run EV Charging Scheduler UI")
    parser.add_argument("--port", type=int, default=7860, help="Port to run the Gradio UI on")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host interface to bind")
    parser.add_argument("--share", action="store_true", help="Enable Gradio share link")
    args = parser.parse_args()

    demo.launch(share=args.share, server_name=args.host, server_port=args.port, show_error=True)
