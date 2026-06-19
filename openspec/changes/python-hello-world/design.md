## Context

New Python project with no existing application code. The change introduces a minimal Python script as a baseline for OpenSpec workflow testing.

## Goals / Non-Goals

**Goals:**
- Provide a single Python script that prints "Hello, World!" to stdout
- Include a unit test that verifies the output

**Non-Goals:**
- No CLI arguments, configuration, or external dependencies
- No packaging, logging, or error handling beyond basic Python conventions

## Decisions

- **Single script file (`hello.py`):** A function-based approach (`def main(): print("Hello, World!")`) with an `if __name__ == "__main__"` guard, following standard Python conventions.
- **No external dependencies:** Uses only the Python standard library.
- **Mitigation:** Minimal surface area — no decisions with material risk.

## Risks / Trade-offs

- None — this is the minimal viable application.
