# Implement-Agent Verification Plan

## Environment Limitation

The implement-agent dispatch environment does not provide a bash/shell tool.
All test commands below require execution by test-agent or manual invocation.

## Focused Tests to Run

### 1. Agent Config Lib Tests
```bash
python3 -m pytest tests/test_agent_config_lib.py -v
```
Expected: 23 tests pass (config loading, validation, model resolution, variant precedence, frontmatter mutation, normalized comparison, file scanning).

### 2. Install Agents Tests
```bash
python3 -m pytest tests/test_install_agents.py -v
```
Expected: all tests pass including new config template, normalized check, and no-injection tests.

### 3. Activate Agents Config Tests
```bash
python3 -m pytest tests/test_activate_agents_config.py -v
```
Expected: 14 tests pass (profile defaults, agent overrides, frontmatter insertion, check drift, dry-run, idempotency).

### 4. Setup Agents Tests
```bash
python3 -m pytest tests/test_setup_agents.py -v
```
Expected: 6+ tests pass (script existence, check modes, dry-run, drift detection).

### 5. Bootstrap Skills Tests
```bash
python3 -m pytest tests/test_project_bootstrap_skills.py -v
```
Expected: all tests pass including new agent setup guidance tests.

### 6. Wrapper Contracts Tests
```bash
python3 -m pytest tests/test_wrapper_contracts.py -v
```
Expected: no regressions from canonical agent model/variant removal.

### 7. Full Regression
```bash
python3 -m pytest tests/test_agent_config_lib.py tests/test_install_agents.py tests/test_activate_agents_config.py tests/test_setup_agents.py tests/test_project_bootstrap_skills.py tests/test_wrapper_contracts.py -v
```
Expected: all tests green.

## Regeneration Commands
After tests pass, regenerate distributed agent copies:
```bash
python3 scripts/setup_agents.py --target .opencode/agents
python3 scripts/setup_agents.py --target .claude/agents
python3 scripts/setup_agents.py --target .cursor/agents
```
Then rerun wrapper_contracts tests to verify.
