---
name: code-sop-cli-argparse-pitfall
description: Pitfall + reference for argparse positional/subparser interactions, observed 2026-10-13 on raphael-harness meeting_pipeline.py.
---

# CLI arg parser — positional + subparser pitfall

Captured from raphael-harness Day 3 of project
`proj-20261011-021613-8016-會議錄音轉行事曆待辦-pipeline` (artifact
`art-20261013-022005-5f1f-code`). Session self-eval gave self_total 84.6
but explicitly listed as a defect: *"CLI 把 audio positional 拆到
subparser 後沒保留向後相容，舊的『python meeting_pipeline.py file.wav
--dry-run run』會壞"*. Future iterations of any CLI tool on the harness
(SOPs/code, any DevOps script) should apply this lesson before merging
argparse refactors.

## The trap

argparse parses **top-level options**, then **positionals**, then
**delegates to subparsers**. If a positional previously sat at the top
level (e.g. `audio`) and you later add `sub.add_subparsers(dest="cmd")`
*before* the positional in the parser list, argparse will steal
positional tokens for the subparser command name and you'll get:

```
error: argument cmd: invalid choice: '/tmp/test_meeting.wav'
(choose from 'run', 'inspect')
```

The order in source order *does not* matter — what matters is whether
the positional is added **before** or **after** the subparsers block.

## Tested combinations

| Layout                                                  | Top-level positional consumed? | Subparser flag works? |
|---------------------------------------------------------|-------------------------------|-----------------------|
| `audio` (positional) → `sub add_subparsers()` + `audio` re-declared per-subparser | never | OK |
| `sub add_subparsers()` (positional audio not in main) + `run_p.add_argument("audio")` inside subparser | never | OK, but old `prog file.wav run` syntax breaks |
| Keep `audio` as top-level positional **and** also declare it in `run_p` subparser | once, before subcommand | OK, but argparse complains about `--dry-run` placement |

## Fix (preserves backwards compatibility)

```python
ap = argparse.ArgumentParser(...)
ap.add_argument("--dry-run", ...)            # options first
ap.add_argument("--retry", ...)
ap.add_argument("--db", ...)
sub = ap.add_subparsers(dest="cmd", required=True)
run_p = sub.add_parser("run", help="...")    # subparser LAST
run_p.add_argument("audio", help="...")      # positional lives HERE
run_p.add_argument("--work-dir", ...)
run_p.set_defaults(func=cmd_run)
insp = sub.add_parser("inspect", help="...")
insp.set_defaults(func=cmd_db_inspect)
```

Then call:
```bash
prog --dry-run --db /tmp/x.db run /tmp/file.wav
# NOT prog /tmp/file.wav --dry-run run
```

User scripts written against the old `prog file.wav --dry-run run` order
will break. Either keep **both** layouts (top-level positional that
errors if absent, plus subparser positional) or **ship a CHANGELOG
note** in RUNLOG.md.

> **Follow-up (2026-10-14)**: the fix above is technically correct but
> UX-hostile — flags only work before the subcommand. See
> "The follow-up UX gap" below for the `parents=[common]` upgrade
> that makes both orderings work.

## Verification checklist (run before commit)

1. `python prog.py --help` shows `audio` listed only under `run` subparser, not as top-level.
2. Old invocation must produce a clear `usage: ... --dry-run {run,inspect}` error, NOT a stack trace.
3. New invocation: `prog --dry-run run /tmp/audio.wav` succeeds end-to-end.
4. `--db-inspect` flag works without `audio` (set subparsers `required=False`, conditional dispatch in `main()`).

## Pitfalls observed

- **`sub.add_subparsers(dest="cmd", required=True)` then top-level positional** → positional gets swallowed into `cmd` choice; gives cryptic `invalid choice: '/path/...'`.
- **`sub.add_subparsers(...)` without `required=True`** → silent no-subcommand error path; need explicit `if not getattr(args, "cmd", None): ap.error(...)` after `parse_args()`.
- **`audio` made optional (`nargs="?"`)** + subparsers required → argparse *still* rejects positional before subcommand key. Use the per-subparser positional declaration above instead.

## Where this lesson was learned

- File: `workspace/proj-20261011-021613-8016-會議錄音轉行事曆待辦-pipeline/meeting_pipeline.py`
- RUNLOG Day 3 section, T1–T5 tests.
- raphael-harness SOP path: `sops/code/SOP.md` should reference this file when CLI work happens.

---

## The follow-up UX gap (2026-10-14)

The fix above is **technically correct** but **UX-hostile**: it forces the user to put all flags before the subcommand, which is the opposite of how most CLIs work (`git log --oneline`, `docker run -d nginx`, etc.). First-time users who try the natural order will hit:

```bash
$ python meeting_pipeline.py run /tmp/audio.wav --dry-run
usage: meeting_pipeline.py [-h] [--db-inspect] [--db DB] [--work-dir WORK_DIR]
                           [--dry-run] [--retry RETRY]
                           {run,inspect} ...
meeting_pipeline.py: error: unrecognized arguments: --dry-run
```

This defect will show up in self-eval as `first_run_ux < 4` and in user feedback as "照 README 抄就壞". The proper fix is `parents=` so flags work in BOTH positions:

```python
# Common flags as a parent parser
common = argparse.ArgumentParser(add_help=False)
common.add_argument("--dry-run", action="store_true")
common.add_argument("--db", default=str(DEFAULT_DB))
common.add_argument("--retry", type=int, default=1)
common.add_argument("--work-dir", default="~/.local/share/meeting-pipeline")

ap = argparse.ArgumentParser(description="會議錄音到行事曆待辦 pipeline")
sub = ap.add_subparsers(dest="cmd", required=True)

run_p = sub.add_parser("run", parents=[common], help="執行 pipeline")
run_p.add_argument("audio", help="輸入 mp3 / wav / m4a 檔")
run_p.set_defaults(func=cmd_run)

insp = sub.add_parser("inspect", parents=[common], help="印出 trace DB 摘要")
insp.set_defaults(func=cmd_db_inspect)
```

After this change, all four invocation orders work:

| Order | Result |
|---|---|
| `prog --dry-run run /tmp/x.wav` | ✓ |
| `prog run /tmp/x.wav --dry-run` | ✓ |
| `prog --db /tmp/x.db inspect` | ✓ |
| `prog inspect --db /tmp/x.db` | ✓ |

**When to upgrade**: any CLI shipped to a non-author user. Internal one-shot scripts are fine with the simpler "flags before subcommand" pattern. Add an entry to the verification checklist above:

5. After adding `parents=[common]`, run **all four** orderings above and confirm none fail with `unrecognized arguments`.
