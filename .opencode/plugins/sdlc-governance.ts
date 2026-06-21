import type { PluginInput } from "@opencode-ai/plugin";
import { execFile } from "node:child_process";
import { promisify } from "node:util";

const execFileAsync = promisify(execFile);

const WORKFLOW_SCRIPT = ".ai/workflows/scripts/workflow.py";

export default async function sdlcGovernance(input: PluginInput) {
  const injectedHashes = new Set<string>();

  const eventStream = await input.client.event.subscribe();

  for await (const event of eventStream.stream) {
    if (event.type !== "session.idle") continue;

    try {
      const { stdout } = await execFileAsync(
        "python3",
        [WORKFLOW_SCRIPT, "--root", input.directory, "governance-check"],
        { timeout: 15000, maxBuffer: 1024 * 1024 },
      );

      const result = JSON.parse(stdout.trim());

      if (!result.block || !Array.isArray(result.findings) || result.findings.length === 0) {
        continue;
      }

      const newFindings = result.findings.filter(
        (f: { hash?: string }) => f.hash && !injectedHashes.has(f.hash),
      );

      if (newFindings.length === 0) continue;

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

      await input.client.tui.appendPrompt({
        body: { text: lines.join("\n") },
        query: { directory: input.directory },
      });
    } catch (err) {
      console.error(
        "[sdlc-governance] governance-check failed:",
        err instanceof Error ? err.message : err,
      );
    }
  }
}
