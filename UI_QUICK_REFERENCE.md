# ⚡ EV Charging Scheduler - Enhanced UI Quick Reference

## 🚀 Quick Start

```bash
# Start the enhanced UI
python ui.py

# With custom settings
python ui.py --host 127.0.0.1 --port 7860 --share
```

**Access UI at:** http://localhost:7860

---

## 📑 Tab Overview

### Tab 1: 🎮 Interactive Playground
**For:** Real-time simulation and agent behavior observation

**Steps:**
1. Set vehicle count (3-30)
2. Set station count (2-10)
3. Set max steps (50-300)
4. Select agent type (random/greedy/priority)
5. Click "Initialize Environment"
6. Click "Execute Step" repeatedly
7. Optional: "Render ASCII Visualization"

**Output:**
- Current state with vehicles and stations
- Last action in JSON format
- Episode log with history

---

### Tab 2: 📊 Full Episode Evaluation
**For:** Running complete episodes and getting detailed metrics

**Steps:**
1. Select task difficulty:
   - **Easy** (10 vehicles, 5 stations, 100+ steps)
   - **Medium** (20 vehicles, 7 stations, 50-100 steps)
   - **Hard** (30 vehicles, 5 stations, 20-50 steps)
2. Choose agent (random/greedy/priority)
3. Set max steps
4. Click "Run Full Episode"

**Outputs:**
- Overall Score (0-1)
- Episode Reward
- Vehicles Charged / Missed Deadlines
- Grid Overload Count
- Total Cost
- Execution Time
- Timeline of last 20 steps

---

### Tab 3: 🏆 Benchmark Suite
**For:** Comparing multiple agents across difficulty levels

**Steps:**
1. Specify agents (comma-separated):
   ```
   random,greedy,priority
   ```
2. Specify tasks (comma-separated):
   ```
   easy,medium,hard
   ```
3. Set max steps per episode (50-300)
4. Click "Run Benchmarks"

**Outputs:**
- Detailed results table
- Agent comparison summary
- Rankings by score

**Default Config:**
- Agents: random, greedy, priority
- Tasks: easy, medium, hard
- This runs 9 total episodes (3 agents × 3 tasks)

---

### Tab 4: 📖 Documentation
**For:** Learning about the environment and development

**Available Docs:**
1. **Main** - Full environment overview
   - Problem statement
   - Key features
   - Configuration details
   - Agent strategies
   - Metrics explained

2. **Agents** - Custom agent development
   - BaseAgent interface
   - How to implement `get_action()`
   - Accessing observation data
   - Valid action formats
   - Strategy patterns

3. **Tasks** - Task types and grading
   - Easy/Medium/Hard difficulty
   - Grading system
   - Score components
   - Episode results

4. **Quickstart** - 5-minute setup
   - Installation
   - UI launch
   - Running benchmarks
   - Common tasks

---

### Tab 5: ℹ️ About
**For:** Project information and reference

**Contains:**
- Project description
- Key features overview
- Environment statistics
- Citation template
- Links to documentation

---

## 🎯 Common Workflows

### Workflow 1: Quick Agent Test
```
1. Interactive Playground tab
2. Initialize with default settings
3. Execute a few steps
4. Observe behavior
```
⏱️ Time: ~2 minutes

### Workflow 2: Full Episode Run
```
1. Full Episode Evaluation tab
2. Medium difficulty
3. Greedy agent
4. Run full episode
5. Review metrics
```
⏱️ Time: ~3-5 minutes

### Workflow 3: Compare All Agents
```
1. Benchmark Suite tab
2. Use default configs
3. Run benchmarks
4. Review comparison table
```
⏱️ Time: ~10-15 minutes (3 agents × 3 tasks)

### Workflow 4: Learn and Develop
```
1. Documentation tab
2. Read Main documentation
3. Check Agents guide
4. Implement custom agent
5. Test in Interactive Playground
```
⏱️ Time: Variable (learning + development)

---

## 📊 Metrics Quick Reference

### Primary Metrics
| Metric | Range | Meaning |
|--------|-------|---------|
| Score | 0-1 | Overall performance |
| Reward | Varies | Cumulative episode reward |
| Vehicles Charged | 0-N | Successfully charged count |

### Secondary Metrics
| Metric | Range | Meaning |
|--------|-------|---------|
| Missed Deadlines | 0-N | Failed to charge in time |
| Grid Overloads | 0-N | Peak capacity exceeded |
| Total Cost | $+ | Electricity expenses |
| Time | Seconds | Execution duration |

---

## 🤖 Agent Strategy Guide

### Random Agent
- **Best for:** Baseline comparison
- **Strategy:** Random valid actions
- **Expected Score:** 0.3-0.5
- **Use case:** Sanity checking

### Greedy Agent
- **Best for:** Good balance
- **Strategy:** Nearest deadline first
- **Expected Score:** 0.5-0.7
- **Use case:** Quick solutions

### Priority Agent
- **Best for:** Handling urgency
- **Strategy:** Priority queue + load balancing
- **Expected Score:** 0.6-0.8
- **Use case:** Mission-critical vehicles

---

## ⚙️ Configuration Options

### Environment Parameters
```
Vehicles:     3-30 (default: 10)
Stations:     2-10 (default: 5)
Max Steps:    50-300 (default: 200)
```

### Agent Selection
```
random   - Stochastic baseline
greedy   - Heuristic approach
priority - Smart scheduling
optimal  - Exhaustive search (slow)
```

### Task Difficulties
```
Easy     - 10 vehicles, generous deadlines
Medium   - 20 vehicles, standard deadlines
Hard     - 30 vehicles, tight deadlines
```

---

## 🐛 Troubleshooting

### "Environment not initialized" error
**Solution:** Click "Initialize Environment" first in Playground tab

### Benchmark seems stuck
**Solution:** Reduce max steps or use fewer agents

### UI not responsive
**Solution:** 
- Refresh the browser
- Restart the server with `Ctrl+C` and `python ui.py`

### Memory issues with many benchmarks
**Solution:** Run smaller batches (1-2 agents at a time)

---

## 💡 Tips & Tricks

1. **Benchmark Efficiently**
   - Start with easy tasks (faster)
   - Test single agent first
   - Use lower step counts for quick tests

2. **Interactive Playground**
   - Use "Render ASCII" to visualize state
   - Execute steps one at a time to learn
   - Watch grid load percentages

3. **Full Episode Evaluation**
   - Medium difficulty is balanced
   - Compare same agent across difficulties
   - Note cost differences

4. **Documentation**
   - Read Main first for overview
   - Check Agents guide before implementing
   - Reference Tasks for grading details

---

## 📁 Files Reference

**Main Files:**
- `ui.py` - The enhanced web interface (UPDATED)
- `benchmarks.py` - Benchmarking suite (NEW)
- `documentation.py` - Documentation content (NEW)

**Supporting Files:**
- `baseline_evaluation.py` - CLI evaluation
- `ev_charging_env/` - Core environment

---

## 🎓 Learning Path

1. **5 min:** Read this quick reference
2. **10 min:** Launch UI, explore tabs
3. **15 min:** Run Interactive Playground
4. **20 min:** Run single Full Episode
5. **30 min:** Run complete Benchmark Suite
6. **Ongoing:** Read Documentation, implement agents

---

## ✨ Feature Highlights

✅ **5 Tabs** for different workflows
✅ **Real-time Simulation** with step control
✅ **Complete Episode Evaluation** with metrics
✅ **Benchmark Suite** for multi-agent comparison
✅ **In-app Documentation** for learning
✅ **Beautiful Formatting** with emoji and tables
✅ **Detailed Metrics** for analysis
✅ **Production Ready** interface

---

**Happy Scheduling! ⚡🚗**

For more details, check `ENHANCED_FEATURES.md`
