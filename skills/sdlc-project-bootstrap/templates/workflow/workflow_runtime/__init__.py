"""workflow_runtime — modular workflow runtime package.

Importing this package does not execute any command or produce side effects.
Sub-modules follow an acyclic dependency direction:

    core → state / definitions / domains → policies / dispatch /
    lifecycle / governance → cli
"""