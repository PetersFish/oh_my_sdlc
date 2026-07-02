# Focused Test Log

## Exact focused commands from active run evidence
- `python3 -m pytest tests/test_workflow.py::TestRoadmapReadyHook::test_ready_hook_blocks_when_item_not_ready -v` → pass
- `python3 -m pytest tests/test_workflow.py::TestRoadmapReadyHook::test_ready_hook_completes_when_item_is_ready -v` → pass
- `python3 -m pytest tests/test_workflow.py::TestRoadmapReadyHook::test_ready_hook_completes_no_linked_item -v` → pass
- `python3 -m pytest tests/test_workflow.py::TestRoadmapReadyHook::test_ready_hook_blocks_multiple_linked_items -v` → pass
- `python3 -m pytest tests/test_workflow.py::TestRoadmapApplyStartHook::test_apply_start_hook_blocks_when_item_still_ready -v` → pass
- `python3 -m pytest tests/test_workflow.py::TestRoadmapApplyStartHook::test_apply_start_hook_completes_when_item_is_active -v` → pass
- `python3 -m pytest tests/test_workflow.py::TestRoadmapApplyStartHook::test_apply_start_hook_completes_no_linked_item -v` → pass
- `python3 -m pytest tests/test_workflow.py::TestRoadmapApplyStartHook::test_apply_start_hook_blocks_multiple_linked_items -v` → pass
- `python3 -m pytest tests/test_workflow.py::TestRoadmapAgentRouting::test_roadmap_agent_accepted_by_before_dispatch -v` → pass
- `python3 -m pytest tests/test_workflow.py::TestRoadmapAgentRouting::test_roadmap_agent_accepted_in_apply_change_phase -v` → pass
- `python3 -m pytest tests/test_workflow.py::TestRoadmapAgentRouting::test_roadmap_agent_blocked_when_no_active_run -v` → pass
- `python3 -m pytest tests/test_workflow.py::TestRoadmapAgentRouting::test_roadmap_agent_not_blocked_by_done_run_with_history -v` → pass

## Implement-agent handoff commands rerun where executable
- `python3 -m pytest tests/test_workflow.py::TestDispatchHooks -v` → 33 passed
- `python3 -m pytest tests/test_workflow.py -k roadmap -v` → 46 passed
- `python3 -m pytest tests/test_wrapper_contracts.py::TestAgentFrontmatter -v` → 29 passed
- `python3 -m pytest tests/test_workflow.py::TestRoadmapAgentRouting -v` → 4 passed

## Notes
- Unquoted wildcard command from implement handoff (`...test_after_dispatch_roadmap_agent_*...`) is not zsh-safe; per-test focused reruns and the enclosing `TestDispatchHooks` class cover the same behavior and passed.
