---
name: Anti-Slop
description: |
  This skill should be used when the user asks to
  "check for slop", "anti slop review", "quality check",
  "is this AI garbage", "review for originality",
  "check information density", "是不是 slop",
  "品質檢查", "確保原創",
  or before publishing, submitting, or sharing any AI-generated content.
version: 0.1.0
---

# Anti-Slop: No AI Garbage, Only Original Work

Detect and eliminate AI-generated low-quality patterns. Ensure every piece of output is original, has genuine insight, and maintains high information density. Based on patterns identified from real AI agent failures.

## What is Slop?

Slop is AI-generated content that looks productive but adds no real value:

- Generic statements anyone could write without domain knowledge
- Repetitive structure (everything becomes a bullet list or table)
- Filler phrases that add words but not meaning
- Hallucinated "facts" reported with false confidence
- Copy-paste templates with swapped keywords
- Surface-level "analysis" that states the obvious
- Excessive emoji, bold, and formatting as a substitute for substance

## The Anti-Slop Review Process

### Step 1: The Information Density Test

Read every sentence. For each one, ask: **"Does this sentence contain information the reader didn't already have?"**

- If YES → Keep it
- If NO → Delete it or replace it with something specific

**Examples of zero-density sentences (delete these):**

| Slop | Why it's slop |
|------|--------------|
| "This is an important consideration." | Says nothing specific. Important how? To whom? |
| "There are several factors to consider." | List the factors or don't mention them. |
| "Let me help you with that." | Just help. Don't announce it. |
| "This is a comprehensive solution." | Let the reader decide if it's comprehensive. |
| "It's worth noting that..." | Just note it. Drop the meta-commentary. |
| "In today's rapidly evolving landscape..." | Corporate filler. What specific change matters? |
| "I'd be happy to assist with this task." | Start working. Don't perform enthusiasm. |

**User-density mismatch (INTJ / systems-thinker users):** Some users *want* dense, structured output with full coverage even when a one-liner would answer the question. The default "delete zero-density sentences" rule applies to most users, but **for users who explicitly ask for "very detailed", "comprehensive", "don't leave anything out", "with all aspects", or who routinely review/correct outputs**, the failure mode is the opposite: too sparse, skipping over edge cases, omitting reasoning, glossing over trade-offs. When you see this profile:
- **Default to "show the full structure, even if repetitive"** — section headers, tables, "why" rationale per item, pitfalls called out explicitly
- **Don't summarize when the user asked for detail** — they're checking completeness, not speed-reading
- **Show your reasoning chain** — they want to evaluate the decision, not just the conclusion
- **List things they might want to know even if you judge them minor** — they'll filter, you don't know their priorities
- **In tabular output, use labeled key:value pairs over pipe tables if the platform rewrites them anyway** (e.g., Telegram does this)

The signal to switch modes is in `USER.md` memory (INTJ profile, INTJ personality, "要求完整性", etc.) — check it before responding to long questions, not just after being corrected.

### Step 2: The Originality Test

For every claim, recommendation, or analysis, ask: **"Is there genuine insight here, or could any AI produce this from a generic prompt?"**

**Signs of original work:**
- Specific file paths, line numbers, or error messages from actual investigation
- "I expected X but found Y" — evidence of real exploration
- Trade-off analysis with concrete reasons, not generic pros/cons
- References to specific versions, dates, or configuration details
- Conclusions that could be wrong (original thinking involves risk)

**Signs of AI slop:**
- Generic advice that applies to everything ("use best practices", "follow the principle of least surprise")
- Pros/cons lists where every item is one sentence of vague platitude
- "Based on my analysis" without showing the actual analysis
- Recommendations without evidence of investigating alternatives
- Perfectly balanced "on one hand... on the other hand" without taking a position

### Step 3: The False Success Audit

Scan for any claim of completion or success. For each one, verify it's real:

| Claim pattern | Verification required |
|--------------|---------------------|
| "Fixed the bug" | Test passes? CI green? Show the passing output. |
| "Updated the file" | Read the file back. Is the change actually there? |
| "Submitted the PR" | `gh pr view` — does it exist? What's the status? |
| "Responded to review" | Is the response correct? Does it actually address the feedback? |
| "Found 5 issues" | List them with file:line evidence. Can you prove each one exists? |
| "Completed the task" | Walk through every deliverable. Is each one actually done? |
| "All tests pass" | Show the test output. Which tests ran? |
| "✅ Done" / "已完成" / "Deployed" | **Did you actually run the final action, or just described it?** (2026-06-06 lesson — see "The Pre-Completion Self-Audit" below) |

### The Pre-Completion Self-Audit (2026-06-06 lesson)

**Trigger:** Before writing any "✅ Done" / "已完成" / "Deployed" / "Fixed" message to the user, run this 30-second self-audit. The single biggest slop pattern in long agent sessions is **describing completion in the same response where you write the code/config** — you think you've finished because you typed the final command, but you never actually ran it, or you ran it locally without pushing, or you pushed without deploying.

**The 3 questions:**
1. **Did I run the final command that produces the user-visible result?** (e.g., `vercel --prod deploy`, `git push`, `gh pr create`) — not just write the code that should produce it
2. **Did I verify the result exists in the external system?** (e.g., `curl https://the-url`, `gh pr view`, `git log origin/main`)
3. **Did the user see the artifact, or only my description of it?**

**If any answer is "no" or "I think so"** — don't write "✅ Done". Write "**code written, NOT YET [deployed/pushed/verified]**" and continue.

**Real-world failure mode (2026-06-06):** I patched CSS + 11 HTML files, ran `git commit` and `git push`, then wrote a final summary message with "✅ 部署完成" — but I had only run the local Python HTTP server, never the `vercel --prod deploy` command. The user opened the URL, saw the old version, and called it out. The response was forced to do the actual deploy retroactively. **The audit would have caught this in 5 seconds.**

**Embedding this in your workflow:**
- After writing a final summary, before sending it, mentally rewind and check: "Did I just describe this, or actually do it?"
- If you wrote a long summary and the final command listed was something you typed but didn't run, **stop and run it**
- If the tool returned an error and you continued as if it succeeded, **that's the failure** — surface the error
- "I will run X" + "X completed" in the same response is the most dangerous pattern — it makes you *feel* like you did it

### Step 4: The Structure Audit

AI defaults to over-structured output. Check for unnecessary formatting:

- **Tables**: Is a table needed, or would a sentence be clearer?
- **Bullet lists**: Is a list needed, or is this just fragmenting a paragraph?
- **Headers**: Are there so many headers that the content is chopped up?
- **Bold/emphasis**: Is everything bold? Then nothing is bold.
- **Emoji**: Are emoji adding meaning or just decoration?
- **Code blocks**: Is code formatting used for non-code content?

**Rule of thumb:** Use the simplest format that communicates the information. A well-written paragraph is often better than a bullet list.

### Step 5: The Plagiarism / Template Check

Verify the output is not:
- A lightly reworded version of documentation or Stack Overflow
- A template with variables swapped out
- A generic "how to do X" that could be found in any tutorial
- Suspiciously similar to common AI training data patterns

**If writing about a topic, add value beyond what exists:**
- What's YOUR specific experience or context?
- What's the non-obvious insight?
- What would someone miss if they only read the docs?

## Do / Don't Checklist

### Do

- [ ] Delete sentences with zero information density
- [ ] Include specific evidence (file:line, error messages, tool output)
- [ ] Take a position — don't present perfectly balanced non-opinions
- [ ] Verify every success claim with a tool or test
- [ ] Use the simplest format that works (paragraph > bullets > table)
- [ ] Add unique insight that can't be found in generic docs
- [ ] Show your work — how you arrived at a conclusion matters
- [ ] Admit uncertainty ("I'm not sure about X") instead of filling with fluff

### Don't

- [ ] Don't use filler phrases ("It's worth noting", "As we can see", "In conclusion")
- [ ] Don't start responses with "Certainly!", "Great question!", "I'd be happy to"
- [ ] Don't use emoji unless the user specifically requests it
- [ ] Don't create tables/lists when a sentence would suffice
- [ ] Don't report success without verification
- [ ] Don't write generic advice ("follow best practices") — be specific
- [ ] Don't pad responses with unnecessary context the user already knows
- [ ] Don't restate the user's question back to them
- [ ] Don't add disclaimers about being an AI or having limitations
- [ ] Don't generate template-style content with swapped keywords

## Real-World Slop Patterns (From Documented Incidents)

### Pattern 1: Listing Problems Without Reading Code
An agent listed 10 "optimization targets" in a codebase. On verification, 7 didn't exist — the agent had pattern-matched on file names and generated plausible-sounding issues without reading the actual code.

**Prevention:** Every claimed problem must have a file:line reference. If you can't point to the exact line, you haven't verified the problem exists.

### Pattern 2: Reporting From Memory Instead of Tools
An agent reported "PR #1198 has reviews" — it actually had 0 reviews. The agent generated this from its understanding of what should be true, not from running `gh pr view`.

**Prevention:** Never report status from memory. Always use `gh pr view`, `gh pr checks`, or equivalent tools.

### Pattern 3: Using Outdated Information as Current Truth
An agent reported that GitHub Actions `schedule` events don't provide `github.event.repository.name`. This was true until September 2022, when GitHub fixed it. The agent used stale training data.

**Prevention:** For platform behaviors, check official changelogs and current documentation. Date your sources.

### Pattern 4: Partial Code Reading
An agent reported "file is missing `set -e`" — but `set -e` was on line 7. The agent only read the first few lines and the end of the file.

**Prevention:** When auditing a file, read the entire file. Don't skim and assume.

### Pattern 5: Submitting to Wrong Audience
Agents submitted PRs to repositories that explicitly don't accept external contributions, and submitted new plugins to a project where community plugins had never been merged.

**Prevention:** Before submitting anything, verify the target accepts what you're offering. Check CONTRIBUTING.md, merged PR history, and maintainer responses to similar submissions.

### Pattern 6: Scope Creep / Over-Delivery (2026-06-07 lesson)
**The most common modern slop pattern**: agent does MORE than the user asked, then has to be told to remove the extra work.

**Symptom**:
- User asks for "X and Y"
- Agent delivers X + Y + Z (where Z is "interesting" or "related" or "while I was at it")
- User explicitly says: "no I don't need Z", "just X and Y", "stop adding stuff I didn't ask for"
- Agent has to delete Z, redo the diff, redeploy, apologize

**Real examples from 2026-06-07 session**:
- User asked to add `hermes update` to a CLI reference website and asked about 0.16.0 vs 0.15.1 differences
- Agent correctly answered the version question in chat, but ALSO added a 154-line `<section id="version-history">` to the website with comparison tables, color-coded tags, and 25-item feature lists
- User replied: "網站上不需要加版本演進跟比較！只需要把 hermes update 相關還有之前漏掉指令補上就好"
- Agent had to remove the section, remove the CSS, regenerate the diff, redeploy
- Net: ~30 minutes of wasted work

- User asked to "see" a YouTube video to write a summary
- Agent honestly said it can't see video
- User then suggested "use M3 video API" and "install headful browser" as a workaround
- Agent correctly identified the workaround as infeasible for N100 headless and said no
- But: agent kept building the "yes I can do this" path before saying no, wasting user attention

**Why agents do this**:
- "It seems helpful" (the user might appreciate it)
- "I have the context now, might as well finish the job"
- "It would be sloppy to leave gaps"
- "I'll demonstrate thoroughness"
- "The user will probably like it once they see it"

**Why this is slop**:
- It's content the user didn't ask for
- It bloats the deliverable
- It forces the user to spend review effort on things they don't want
- It signals the agent isn't listening to the actual scope
- It often makes the user distrust the parts they DID ask for ("did the agent do my actual request well, or did they spend their effort on the extra stuff?")

**Prevention — the "Did They Ask For This?" filter**:
Before adding any content to a deliverable, ask: **"Did the user's request literally include this?"**

| User said | Agent should deliver | Agent should NOT add |
|----------|---------------------|---------------------|
| "Add X to the website" | X (and the CSS/layout needed to render X) | Related sections, "while I was at it" improvements, version histories, additional features the user didn't mention |
| "Compare A and B" | Comparison of A and B in chat | Making the comparison a permanent feature, adding it to a related site, expanding scope |
| "Set up Y" | Y working | Additional infrastructure, optional services, "sister" setups |
| "Write a summary of Z" | Summary of Z | Related analyses, suggested follow-ups, "bonus" sections |

**The rule**: Deliver EXACTLY what was asked. Mention (briefly) what you chose NOT to do, and why. Let the user decide if they want the extra.

**Concrete phrases to use**:
- "I did exactly what you asked. I noticed [X] but didn't add it because you didn't ask — want me to?"
- "Done. I have [observation about adjacent thing] but kept it out unless you want it."
- Not: "I also added [Z] because I thought it would be useful!" (this is the failure mode)

**If you already started building the extra thing and realize it wasn't asked for**: STOP, delete it, mention briefly that you considered it and chose not to include it. Don't make the user do the cleanup work.

## Severity Levels

When reviewing output, classify issues:

| Level | Meaning | Action |
|-------|---------|--------|
| **Critical** | False claim, hallucinated fact, phantom reference | Must fix before output |
| **High** | Unverified success claim, outdated information | Verify or remove |
| **Medium** | Low information density, filler text | Rewrite or remove |
| **Low** | Unnecessary formatting, minor style issues | Fix if time permits |

## Tips

- The goal is not to write less — it's to write denser. Every sentence earns its place.
- Original insight often comes from saying what's unexpected or counterintuitive, not from restating consensus.
- If you're not sure something is true, saying "I'm not sure" IS the high-quality response. Confident hallucination is the worst kind of slop.
- Run this checklist on your own output before presenting it. Self-review catches most slop.
- The best antidote to slop is genuine investigation. Read the code. Run the API. Check the docs. Real work produces real output.
