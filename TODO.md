# Submission #30 Failed: Not enough tasks with graders

## Analysis
3 graders exist in ev_charging_env/tasks/__init__.py but validator not detecting.

## Fix Plan
- Export grade_easy_task, grade_medium_task, grade_hard_task to ev_charging_env/__init__.py
- Ensure create_easy_task etc use real env (already done post-pull)

## Steps:
- [ ] Step 1: Edit ev_charging_env/__init__.py - Add grader exports
- [ ] Step 2: Test python inference.py (real task)
- [ ] Step 3: git add/commit/push origin main + hf main
- [ ] Step 4: Resubmit #31

Previous fix complete.
