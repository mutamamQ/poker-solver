# Probe mission: does BryantGPT work as a CODING agent?

Context: the poker-solver project in this directory is already complete and verified (do NOT modify src/, tests/, or the existing docs). Your job now is a controlled probe of the BryantGPT subagent provider as a coding agent, and to report verdict + evidence.

## Task
1. Create a scratch area: /home/genomix-node/poker-solver/probe/
2. Dispatch a batch of **4 tool-enabled** subagents (one delegate_task call, 4 items) in parallel. Each must actually USE its tools (terminal/read_file/write_file/search_files) — this is the point of the probe. Give each a small, distinct, self-contained coding task in probe/, e.g.:
   - A: write probe/fizzbuzz.py implementing fizzbuzz + 3 pytest tests in probe/test_fizzbuzz.py, run them, report the pytest output.
   - B: write probe/roman.py (int<->roman converter) + tests, run them.
   - C: write a probe/README.md documenting the two files above (read them first with read_file).
   - D: adversarial reviewer — run the test suites of A and B, try to break them with edge cases, and write probe/review.md with findings.
   Each task must state: work only inside /home/genomix-node/poker-solver/probe/, write files with absolute paths, and end with the exact pytest/verification output as evidence.
3. After the batch, VERIFY yourself (do not trust child self-reports):
   - ls probe/ — all files present?
   - Run the full probe test suite yourself; paste the real output.
   - Check ~/.hermes/logs/agent.log for `unknown tool requested:` lines (new diagnostic logging in the bryant provider adapter) and any `HTTP 502` during this probe.
4. Write /home/genomix-node/poker-solver/PROBE_REPORT.md with:
   - Verdict: does BryantGPT work as a coding agent right now? (works / works-with-retries / broken)
   - Per-subagent: did it complete, did it actually execute tools, what was its output.
   - Any 502/unknown-tool occurrences with the exact logged unknown tool name (if any).
   - If broken: the minimal reproduction and what to fix in the provider.
   - Recommendations for using it as a swarm coding agent.
5. Final chat message: 5-line summary of the verdict and evidence.

## Rules
- YOLO is on; approvals are bypassed.
- Do NOT touch anything outside probe/ and PROBE_REPORT.md.
- Evidence over claims: every "it worked" must have real output.
