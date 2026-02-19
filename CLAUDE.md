# CLAUDE.md

## Repository Overview

This is a **documentation-only repository** — there is no source code, build system, or test suite. It serves as a planning and strategy workspace for a team preparing for the **Gemini 3 Seoul Hackathon (2026-02-28)**.

All documents are written in **Korean**.

---

## Repository Structure

```
gemini_paper/
├── README.md      # Hackathon strategy guide and Firebase schema design (~389 lines)
├── problem.md     # Standalone game-theory problem statement (medical school enrollment)
└── CLAUDE.md      # This file
```

---

## File Contents

### `README.md`
The primary document. It covers four interconnected topics accumulated through multiple revisions:

1. **Hackathon Overview**
   - Event: Gemini 3 Seoul Hackathon, 2026-02-28
   - Focus: Agentic workflows and multimodal AI using Google Gemini 3
   - Scoring: Technical implementation (40%), Innovation (30%), Impact (20%), Presentation (10%)

2. **Three Project Ideas** for the semiconductor/display industry:
   - **Semicon-Insight Agent** — Multimodal patent analysis using KIPRIS/Google Patent API + Gemini 3 to predict competitor R&D roadmaps
   - **Fab-Care Co-pilot** — Correlates patent data with fab process anomalies using Gemini 3's long context window
   - **IP Strategy Architect** — Compares design drawings against existing patent claims to detect infringement risk

3. **Firebase Firestore Schema Design**
   - `patents`: Raw patent data + image URLs for multimodal analysis
   - `analyses`: Gemini 3-generated expert insights (impact score, yield implications, competitor comparison)
   - `trends`: Pre-aggregated stats for dashboard visualizations (written by Cloud Functions)
   - `users` / `subscriptions`: Mailing preferences and alert thresholds per engineer

4. **Dashboard KPIs and Gemini 3 Prompts**
   - Emerging Tech Heatmap, Competitor R&D Velocity, High-Impact Alert List, Patent Overlap Ratio, Yield-Related Patent Ratio
   - System role prompt: semiconductor/display expert persona with 20+ years of experience
   - Task prompt structure: technical novelty → fab scalability → competitive landscape → strategic advice

5. **Mailing Service Architecture**
   - Patent image extraction via PyMuPDF or patent APIs
   - Firebase Storage for images, Cloud Functions for triggers, SendGrid for delivery
   - GitHub Actions (cron) for periodic patent collection

> Note: README.md contains some duplicated sections from earlier iterations. The content is structurally consistent despite the repetition.

### `problem.md`
An unrelated standalone document. Describes the South Korean medical school enrollment policy conflict (proposed increase from 3,000 to 5,000 seats per year) and asks for game-theory-based solutions. This is not connected to the hackathon content.

---

## Technology Stack (Proposed, Not Yet Implemented)

| Layer | Technology |
|---|---|
| AI Model | Google Gemini 3 (multimodal, long-context) |
| Agent Workflow | Antigravity (Google's agent platform) |
| Database | Firebase Firestore |
| Storage | Firebase Storage |
| Backend Triggers | Firebase Cloud Functions |
| Email Delivery | SendGrid / Nodemailer |
| Frontend | React / Next.js + Tailwind CSS |
| Patent Data Source | KIPRIS API, Google Patents API |
| PDF Processing | PyMuPDF (fitz) |
| CI/Automation | GitHub Actions (cron for patent collection) |
| Frontend Prototyping | Claude Code |

---

## Git Workflow

- **Active branch**: `claude/claude-md-mltdgpwnxu9702qm-RCHZc`
- **Main branch**: `master`
- **Remote**: `http://local_proxy@127.0.0.1:29330/git/waterfirst/gemini_paper`
- All commits pushed to the `claude/` branch; never push directly to `master` without explicit instruction.

---

## Conventions for AI Assistants

1. **Language**: All documents in this repository are in Korean. When editing existing documents, maintain Korean. When asked to add new content, default to Korean unless told otherwise.

2. **Document type**: This is a strategy/planning repo. Do not create source code files, configuration files, or build scripts unless explicitly asked.

3. **README.md editing**: The README contains intentional repetition from revision history. When editing, preserve existing structure and only modify the sections directly relevant to the request.

4. **No build or test commands**: There are no scripts to run, no dependencies to install, and no tests to execute.

5. **Schema references**: The Firebase Firestore schema (`patents`, `analyses`, `trends`, `users`) is the canonical data model for the project. Refer to it when answering questions about data structure.

6. **Prompt engineering**: The Gemini 3 prompts in README.md use a "20-year veteran semiconductor engineer" persona. Preserve this persona when extending or modifying prompts.

7. **Commit messages**: Use concise English commit messages (the existing history uses English commit messages despite Korean content).
