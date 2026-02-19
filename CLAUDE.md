# CLAUDE.md

> Last updated: 2026-02-19

## Repository Overview

This is a **planning and strategy workspace** for a team preparing for the **Gemini 3 Seoul Hackathon (2026-02-28)**, targeting the semiconductor/display patent intelligence domain.

The repository currently contains only documents and configuration stubs — no runnable code, no build system, no test suite. All text documents are written in **Korean**.

---

## Branch Structure

| Branch | Role |
|---|---|
| `main` | Primary upstream branch (managed by the human team) |
| `master` | Legacy local branch (no longer active) |
| `claude/claude-md-mltdgpwnxu9702qm-RCHZc` | Claude Code session branch (diverged from `main` at `c4dc962`) |

The `main` and `claude/` branches diverged after the `claude/` branch was created. `main` has received new files (`antigravity_agent.config`, `patent_analysis_US9846323.json`, KIPRIS PDF) while the `claude/` branch has `CLAUDE.md`.

---

## File Inventory (`main` branch)

```
gemini_paper/ (main)
├── README.md                                           # Hackathon strategy guide (389 lines)
├── readme.md                                           # Alternate/earlier version of strategy guide
├── antigravity_agent.config                            # Antigravity agent definition (JSON)
├── patent_analysis_US9846323.json                      # Real patent analysis output (Samsung Display)
├── 특허정보활용서비스(KIPRISPlus) Open API 이용 가이드(2020.10).pdf  # KIPRIS Plus API reference PDF
└── CLAUDE.md                                           # This file (exists on claude/ branch only)
```

> `problem.md` (medical school game-theory problem) was deleted from `main` on 2026-02-19.

---

## File Descriptions

### `README.md` / `readme.md`
The primary strategy document. Both files contain similar content (different revision states). Topics covered:

1. **Hackathon Overview** — Gemini 3 Seoul Hackathon (2026-02-28)
   - Agentic workflows + multimodal AI as the core theme
   - Scoring: Technical implementation 40% / Innovation 30% / Impact 20% / Presentation 10%

2. **Three Project Ideas** for semiconductor/display engineers:
   - **Semicon-Insight Agent** — Predicts competitor R&D roadmaps via multimodal patent analysis (KIPRIS + Google Patent API + Gemini 3)
   - **Fab-Care Co-pilot** — Matches patent process recipes against fab anomaly data; assists engineering decisions using Gemini 3's large context window
   - **IP Strategy Architect** — Uploads design drawings, detects patent infringement risk, suggests avoidance strategies

3. **Firebase Firestore Schema**
   - `patents` — Raw patent data + image URLs (for multimodal input)
   - `analyses` — Gemini 3-generated insights (impact score, yield implications, competitor comparison, reasoning log)
   - `trends` — Pre-aggregated weekly stats for dashboard charts (written by Cloud Functions)
   - `users` — Engineer profiles with interest keywords and alert thresholds

4. **Dashboard KPIs**
   - Emerging Tech Heatmap, Competitor R&D Velocity, High-Impact Alert List, Patent Overlap Ratio, Yield-Related Patent Ratio, Analysis Coverage

5. **Gemini 3 Prompt Templates**
   - System role: "세계 최고의 반도체/디스플레이 공정 전문가, 20년 현장 경험" (world-class semiconductor expert, 20 years on-site experience)
   - Task prompt: 4-axis analysis — Technical Novelty / Fab Scalability / Competitive Landscape / Strategic Advice

6. **Mailing Architecture**
   - PyMuPDF for patent PDF/image extraction → Firebase Storage → Cloud Functions → Gemini 3 analysis → SendGrid email
   - GitHub Actions cron for automated patent collection

> Note: `README.md` contains duplicated sections from revision history; content is consistent despite repetition.

---

### `antigravity_agent.config`
Antigravity agent definition (JSON). This is the first concrete implementation artifact in the repo.

```json
{
  "name": "IP_Strategist",
  "persona": "반도체 20년차 수석 엔지니어",
  "skills": ["patent_search", "firebase_sync", "email_sender"]
}
```

- Agent name: `IP_Strategist`
- Persona: 20-year veteran semiconductor lead engineer
- Skills wired up: `patent_search`, `firebase_sync`, `email_sender`

---

### `patent_analysis_US9846323.json`
A real Gemini 3-generated patent analysis output. Patent: **US9846323 B2** — "DISPLAY APPARATUS AND MANUFACTURING METHOD THEREOF" (Samsung Display Co., Ltd.)

Key fields:
- `process_advantages` — Analysis of TSC (tunnel-cavity) formation via sacrificial layer removal (microwave O₂ plasma), enabling single-substrate integration and yield improvement
- `avoidance_strategy` — Three concrete IP avoidance paths: (1) change sacrificial layer material/removal method, (2) eliminate sacrificial layer entirely, (3) vary TSC geometry or electrode arrangement

This file demonstrates the `analyses` Firestore collection format and the output quality of the Gemini 3 expert persona.

---

### `특허정보활용서비스(KIPRISPlus) Open API 이용 가이드(2020.10).pdf`
Official KIPRIS Plus Open API usage guide (Korean Intellectual Property Rights Information Service), published 2020-10. This is the reference document for integrating Korea's national patent database into the data pipeline.

---

## Proposed Technology Stack

| Layer | Technology |
|---|---|
| AI Model | Google Gemini 3 (multimodal, long-context) |
| Agent Platform | Antigravity (Google) |
| Database | Firebase Firestore |
| File Storage | Firebase Storage |
| Backend Triggers | Firebase Cloud Functions |
| Email | SendGrid / Nodemailer |
| Frontend | React / Next.js + Tailwind CSS |
| Patent Sources | KIPRIS Plus API, Google Patents API |
| PDF Processing | PyMuPDF (fitz) |
| Automation | GitHub Actions (cron) |
| Frontend Prototyping | Claude Code |

---

## Git Workflow

- **Human team pushes to**: `main`
- **Claude Code session branch**: `claude/claude-md-mltdgpwnxu9702qm-RCHZc`
- **Remote**: `http://local_proxy@127.0.0.1:29330/git/waterfirst/gemini_paper`
- Always push Claude work to the `claude/` branch. Never push to `main` without explicit instruction.
- Push command: `git push -u origin claude/claude-md-mltdgpwnxu9702qm-RCHZc`

---

## Conventions for AI Assistants

1. **Language**: Documents are in Korean. Maintain Korean when editing; default to Korean for new content unless told otherwise.

2. **Scope**: This is a planning/strategy repo. Do not create source code or new config files unless explicitly asked. The `antigravity_agent.config` and `.json` files were created by the human team.

3. **No build or test commands**: Nothing to install, build, or test.

4. **Firestore schema is canonical**: The `patents` / `analyses` / `trends` / `users` schema in README.md is the reference data model. Use it when discussing data structure.

5. **Gemini prompt persona**: Always preserve the "반도체 20년차 수석 엔지니어" (20-year veteran semiconductor engineer) persona in any prompt engineering work.

6. **patent_analysis_US9846323.json is an output example**: Treat it as a ground-truth sample of what Gemini 3 analysis output should look like.

7. **Commit messages**: Use concise English commit messages (existing history convention).

8. **README duplication**: `README.md` has repeated sections from revision history. Do not deduplicate unless explicitly asked.
