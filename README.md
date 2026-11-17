# Agent Skills

Reusable skills for coding agents. Each skill lives in its own directory with a `SKILL.md` entry point and any supporting scripts or references.

## Available skills

| Skill | What it does |
|---|---|
| [MirrorGate](mirror-gate/README.md) | Examines your understanding of the GitHub work you shipped, summarizes your week, and helps you catch up on knowledge gaps. |

### MirrorGate

**You shipped it. Do you still understand it?**

MirrorGate runs a short, evidence-based examination of your merged pull requests. It asks about intent, implementation, and code behavior one question at a time, then provides a comprehension score, corrections, and a weekly digest. Open PRs are summarized separately and are not quizzed.

Optional local learning memory tracks your stated goals, demonstrated strengths, and topics needing practice. Later catch-up sessions explain those topics and test understanding with fresh questions. Assisted practice and independent understanding are recorded separately; follow-up learning does not rewrite the original exam score.

## Install

Run either option from this repository's root. Both examples install for your user so the skill is available across projects.

### With `npx skills`

Requires Node.js and npm. Install MirrorGate for Codex:

```bash
npx skills add . --skill mirror-gate --agent codex --global
```

The `.` selects this local repository, `--skill` selects the skill, `--agent` selects the target agent, and `--global` selects user-level installation. To choose agents interactively, omit `--agent codex`.

See the [skills CLI documentation](https://github.com/vercel-labs/skills/blob/main/docs/commands.md#skills-add) for other sources and installation options.

### Copy manually

Copy the complete skill directory into Codex's user skills directory:

```bash
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills"
cp -R mirror-gate "${CODEX_HOME:-$HOME/.codex}/skills/"
```

For another skills-compatible agent, use that agent's skills directory. Keep the scripts and references together with `SKILL.md`. Manual copies must be updated when the source skill changes; choose one installation method to avoid duplicate installations.

## Use MirrorGate

Start a new agent session after installation, then invoke `$mirror-gate`.

### Examine last week's work

```text
Use $mirror-gate on last week's changes in org/backend and org/frontend.
Quiz me for at most 10 minutes, then give me my score and weekly digest.
```

The default examination covers the last completed Monday-to-Monday calendar week. Specify a different week or timezone when needed. The agent shows the exact range and repository coverage. You can skip a question or stop early; incomplete examinations are labeled partial.

For the bundled collector, use Python 3.10 or later and the GitHub CLI authenticated with access to the repositories:

```bash
gh auth login
```

An available GitHub connector can also supply evidence, although commit-attribution coverage may be incomplete. If you are working inside a GitHub checkout, the collector can infer its repository; otherwise name the repositories to examine. GitHub access is read-only: the skill does not post comments or modify PRs.

### Get a digest without a quiz

```text
Use $mirror-gate to summarize last week's merged and ongoing PRs in
org/backend. Skip the quiz.
```

### Remember learning progress

```text
Use $mirror-gate and enable local learning memory. Remember my stated
goals, demonstrated strengths, and gaps from this examination.
```

Memory is opt-in and requires local filesystem access. Its default location is `~/.codex/mirror-gate-memory/<github-login>/learning.md`, or beneath `$CODEX_HOME` when set. It stores compact learning evidence and source links, not raw diffs or full answers. You can choose another location outside your repositories.

### Catch up after an examination

```text
Use $mirror-gate to help me catch up on the gaps from my last examination.
I have 15 minutes. Explain one topic at a time, then check my understanding.
```

You can ask to show or correct your learning profile, forget a topic, disable future memory use, or delete the profile. Without saved memory, provide a previous assessment or choose a topic in the current conversation.

MirrorGate does not schedule recurring sessions automatically. Its score describes the sampled answers, not overall engineering ability. See the [MirrorGate guide](mirror-gate/README.md) for scoring details and direct collector commands.
