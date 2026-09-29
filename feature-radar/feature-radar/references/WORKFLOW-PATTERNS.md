# Annotation Checkpoint Pattern

After writing a file for user review, tell the user:

"I've written `{path}`. Please review it. You can:
1. **Approve as-is** — say 'looks good' or 'continue'
2. **Annotate the file** — add `> NOTE: your correction here` anywhere in the file, then say 'address my notes'
3. **Give verbal feedback** — tell me what to change

I will not proceed until you confirm."

<HARD-GATE>
When the user says "address my notes":
1. Read the file and find ALL lines starting with `> NOTE:`
2. Address each note — modify the surrounding content accordingly
3. Remove the `> NOTE:` lines after addressing them
4. Present a summary of changes made
5. Ask again: "All notes addressed. Anything else to adjust?"

Do NOT proceed to the next step until the user approves.
</HARD-GATE>
