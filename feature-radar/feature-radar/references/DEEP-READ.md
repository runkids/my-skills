# Deep Read — Preflight Checklist

<HARD-GATE>
Before ANY action, complete ALL steps — do NOT skip or rush:

1. `.feature-radar/` directory exists — if not, tell user to run `feature-radar` skill first and STOP
2. **Read base.md thoroughly** — understand Project Context, Feature Inventory, Classification Rules, and current Tracking Summary counts
3. **Scan existing files** — list what's already in archive/, opportunities/, specs/, references/. Read file names and headers to understand current state
4. **Identify context** — extract and state:
   - Project Language & Architecture
   - Key Feature Areas (from Feature Inventory)
   - Inspiration Sources
   - Current counts: {archive: n, opportunities: n, specs: n, references: n}
5. **State your understanding** — in 2-3 sentences, describe what the project does, what's already tracked, and what gaps you see
6. **Reconcile state** — verify consistency before proceeding:
   - Count actual files in archive/, opportunities/, specs/, references/
   - Compare with Tracking Summary counts in base.md
   - If mismatch: update base.md counts and state "Reconciled: {category} {old} → {new}"
   - Check archive/ files for incomplete extraction checklists (missing specs/, no derived opportunities noted)
   - State reconciliation result: "State consistent" or list corrections made

Proceed to workflow ONLY after completing all 6 steps.
</HARD-GATE>
