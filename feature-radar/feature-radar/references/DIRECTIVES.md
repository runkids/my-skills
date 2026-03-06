# Shared Behavioral Directives

<HARD-GATE>
Follow ALL directives throughout this skill's execution:

1. **Read deeply, not superficially** — When reading files, understand the intricacies: relationships between files, naming conventions, architectural patterns. Do NOT skim. If a file references another, follow the reference.
2. **Artifacts over conversation** — Write findings to files, not just chat messages. Every substantive output must persist in `.feature-radar/`.
3. **Do not stop mid-flow** — Complete ALL workflow steps before stopping. If a step yields no results, state "No findings" and continue to the next step.
4. **State what you produced** — After each step, explicitly state: what file was created/updated, what changed, and what's next.
</HARD-GATE>

## Completion Summary Template

When all steps are done, present:

```
── Feature Radar: {Skill Name} Complete ──

Files created:  + {path} (new)
Files updated:  ~ {path} (what changed)
Files removed:  - {path} (why)
Counts: archive {n}, opportunities {n}, specs {n}, references {n}

Suggested next:
- {skill} — {reason based on this session's output}
- {skill} — {reason}
```

Pick 2-3 suggestions from this menu based on what happened in this session:

| Condition | Suggest |
|-----------|---------|
| New opportunities were created | `/feature-radar evaluate` — prioritize the new opportunities |
| A high-priority opportunity was identified | `/feature-radar #N` — deep-dive on {opportunity name} |
| Features were archived | `/feature-radar-learn` — extract learnings from the archived work |
| External observations were recorded | `/feature-radar-ref` — expand on the reference with more research |
| Opportunities backlog is stale (>2 weeks) | `/feature-radar-scan` — refresh with a new scan |
| Top recommendation was proposed | `enter plan mode` — start implementing the top pick |

Do not end with "this should work" or "try this". End with the summary above.
