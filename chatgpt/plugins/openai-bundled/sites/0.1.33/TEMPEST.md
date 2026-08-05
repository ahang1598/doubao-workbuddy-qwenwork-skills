---
schema: tempest-risk-guidance/v2
auto_resolve_policies:
  - applicability: evaluate_only
    eligible_requirements:
      - codeownerous
      - compliance
    require:
      - author_matches_any:
          - github_team: openai/codex-cloud-apps-team
---

# Purpose

This directory owns the Sites Codex plugin manifest, skills, and plugin-facing instructions.

# Risk Posture

Treat a change as low risk only when it is limited to one of these cases:

- Comments, tests, or test-only build metadata with no production behavior change.
- Documentation that does not change a skill, prompt, plugin manifest, tool description, or other instruction consumed at runtime.
- Additive diagnostic logging that uses existing non-sensitive values and does not change control flow, errors, tool output, or user-visible behavior.

Require human review for changes to skills, prompts, plugin manifests, tool descriptions, user-visible text, authentication, authorization, user data, network access, connector behavior, runtime configuration, deployment, or dependencies.

When a pull request mixes a low-risk change with any other change, require human review for the full pull request.

# Required Inspection

Inspect the changed plugin manifest or skill in full and inspect the implementation of every tool or behavior named by the changed instructions.
