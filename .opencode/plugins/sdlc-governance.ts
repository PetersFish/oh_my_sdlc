import type { Plugin } from "@opencode-ai/plugin";
import { execFile } from "node:child_process";
import { promisify } from "node:util";

const execFileAsync = promisify(execFile);

const WORKFLOW_SCRIPT = ".ai/workflows/scripts/workflow.py";

const injectedHashes = new Set<string>();

export const sdlcGovernance: Plugin = async ({ client, directory }) => {
  return {
    event: async ({ event }) => {
      if (event.type !== "session.idle") return;

      try {
        const { stdout } = await execFileAsync(
          "python3",
          [WORKFLOW_SCRIPT, "--root", directory, "governance-check"],
          { timeout: 15000, maxBuffer: 1024 * 1024 },
        );

        const result = JSON.parse(stdout.trim());

        if (!result.block || !Array.isArray(result.findings) || result.findings.length === 0) {
          return;
        }

        const newFindings = result.findings.filter(
          (f: { hash?: string }) => f.hash && !injectedHashes.has(f.hash),
        );

        if (newFindings.length === 0) return;

        for (const f of newFindings) {
          injectedHashes.add(f.hash);
        }

        const lines: string[] = [
          "[SDLC Governance] Found " + newFindings.length + " issue(s):",
          "",
        ];

        for (const f of newFindings) {
          const label =
            f.type === "dangling_archive"
              ? "Dangling Archive"
              : f.type === "pending_hooks"
                ? "Pending Hooks"
                : f.type;
          lines.push("**" + label + "**: " + f.message);
          lines.push("Remediation: " + f.remediation);
          lines.push("");
        }

        lines.push(
          "Re-run `workflow.py governance-check` and continue remediation until `block=false`.",
        );

        await client.tui.appendPrompt({
          body: { text: lines.join("\n") },
          query: { directory },
        });
      } catch (err) {
        console.error(
          "[sdlc-governance] governance-check failed:",
          err instanceof Error ? err.message : err,
        );
      }
    },
  };
};
