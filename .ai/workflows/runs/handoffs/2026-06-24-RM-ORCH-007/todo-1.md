# Deferred wrapper-dispatch follow-ups

These items were intentionally deferred while scoping the current implementation down to the verified vertical slice (`spec.create` and `memory.repository_sync`).

- [ ] Re-introduce `spec.continue` provider dispatch after adding a real `openspec.continue` verifier and behavior tests.
- [ ] Re-introduce `spec.apply` provider dispatch after adding a real `openspec.apply` verifier and behavior tests.
- [ ] Re-introduce `spec.archive` provider dispatch after adding both an `openspec.archive` verifier and a `spec_archive` result contract normalizer.
- [ ] Re-introduce `memory.load` provider dispatch after adding both a `local.load` verifier and a `memory_context` result contract normalizer.
- [ ] Re-introduce `memory.spec_post_archive_sync` provider dispatch after adding a real `local.spec_post_archive_sync` verifier and behavior tests.
- [ ] Decide whether `github/spec-kit` should become a supported provider or stay explicitly deferred; do not re-add it without verifier + normalizer coverage.
- [ ] Add eval coverage for the dev-orchestrator resolve→dispatch→verify→normalize prompt path, because pytest prompt-string checks are not enough to validate LLM execution quality.
