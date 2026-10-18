# Shortlist

A local recruitment prototype built with FastAPI, React and a paper-toned editorial interface. Seven guided steps lead from sign-in to a printable hiring brief.

## Run with one command

On Windows, open PowerShell in this folder:

```powershell
powershell -ExecutionPolicy Bypass -File .\start.ps1
```

Open **http://127.0.0.1:8000**. Sign in with **recruiter@demo.com / demo123**. No AI key is needed for local evidence checks. After signing in, choose **Turn on the assistant** for a four-slide setup, or **Continue manually**. Setup explains the checks, sets the role, connects a CV folder and asks you to start explicitly. You can change this later from the header. First launch installs dependencies, prepares the six sample CVs and builds the interface. Internet is required for that first install.

Prerequisites: Python 3.11+ and Node.js 20.19+ or 22+. This workspace also includes local development tools used during verification; the launcher detects them automatically. On macOS/Linux, with Python and Node installed, use `sh start.sh`.

If setup has already run, start immediately with:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.app:app --host 127.0.0.1 --port 8000 --no-access-log
```

Keep that window open; press Ctrl+C to stop. This is a local prototype with a shared demo account, not production authentication.

## Optional public sample demo on Render

The included `render.yaml` and `Dockerfile` configure a single-service deployment that serves both the frontend and API. The source is at [github.com/svarshat-gif/Shortlist](https://github.com/svarshat-gif/Shortlist).

To publish it, sign in to [Render](https://dashboard.render.com/blueprint/new), choose **New > Blueprint**, connect the `svarshat-gif/Shortlist` repository, select the `main` branch, review `render.yaml`, then choose **Deploy Blueprint**. Render will build the app and provide a public `*.onrender.com` URL. Commits pushed to the connected branch will deploy automatically. A Render URL is public and shareable, but it is not guaranteed to appear in search-engine results; share the full URL directly.

The service is configured with `PUBLIC_DEMO=true`: it forces sample mode, allows the included fictional sample CVs, and rejects candidate CV uploads, assistant folder intake, and saved-hire changes. Sessions are temporary and the free service may sleep while idle. Use fictional data only. Do not share GitHub or hosting credentials in chat.

## The seven steps

1. **Sign in:** demo credentials and a time-of-day greeting in India time.
2. **Add the job description:** PDF, Word or pasted text; editable skill chips, job health fixes and scoring priorities.
3. **Add CVs:** multiple PDF/Word files; separate success and failure rows; six downloadable-in-the-workspace fictional sample files.
4. **Ranked shortlist:** weighted evidence scores, exact supporting quotations, course-only warnings, live reorder, human corrections with reasons, shortlist CSV, fairness comparison, decision histories, kind feedback, candidate preview, sharing choices and preferences.
5. **Call questions:** a separate ten-question plan for each candidate, covering Technical, Experience and Fit. Questions follow exact work examples, distinguish study from work and clarify gaps. Candidate selection, answer guidance, accessible alternatives, easier/harder settings and a shorter version are available in a keyboard-accessible carousel. Each candidate’s difficulty/length choices stay separate during the current desk session.
6. **Market view:** clearly marked sample estimates, public careers links, honest verification states and optional live public-web research.
7. **Search strings:** search or add custom job titles and skills, or describe a specific sourcing request to generate editable titles, skills and filters. Refine the LinkedIn/Naukri search with all/any skill matching and optional exclusions; review the plain-language preview, copy the search and follow site-specific instructions. Location and experience stay separate as platform filters. No profiles are fetched by this page. Edited choices are included in the hiring brief and clear when the job changes.

The final **Hiring brief** is a single-page PDF and print view with the first three ranked candidates, a market note, search string and fairness result. “First three to review” is distinct from the recruiter's checked shortlist.

## Optional live public-web research

Copy `.env.example` to `.env`, put your own key in `OPENAI_API_KEY`, and restart the app. The Hiring assistant settings then offer **Use connected AI for review notes** and **Check public job posts**. `OPENAI_MODEL` can be changed to a compatible model available to your account. Never put a key in the interface or commit `.env`.

Public market research uses the [OpenAI Responses web search tool](https://developers.openai.com/api/docs/guides/tools-web-search), excluding LinkedIn and Naukri. Only job title, hiring location and the company being checked are sent for that feature. If you separately enable connected review notes, only filtered work-skill evidence and anonymous retrieved hire references are sent; names and contact details are removed. Both integrations request `store=false`; provider handling remains subject to your account's retention policies.

Without a key, or if live research fails, the market screen clearly falls back to illustrative estimates. **Double-check** never pretends a sample opening or salary was verified. Demo company names are examples to investigate, not claims of current openings. The brief deliberately uses a labelled sample market note; it does not present demo pay as researched fact.

Live paid requests were not exercised during this build because no key was supplied. Their success, malformed-response and failure paths are verified with simulated responses. No recording or account sign-in is needed to demonstrate the full sample journey.

## How the score works

The demo uses deterministic, inspectable evidence rules rather than asking a remote service to decide who should be hired. Draft text, sample fixtures and application code were developed with AI assistance. The UI labels drafts for human review.

- Only named work, course and education sections enter scoring. Unknown layouts receive a reading warning and need review. Uploaded skill names can be added manually to the job. This is a conservative prototype, not general-purpose CV understanding.
- A work example earns more skill credit than a course mention. Bare skill lists receive course-level credit. Exact supporting lines remain visible. No evidence is fabricated.
- Work duration uses dated year ranges and counts overlapping years once. Month precision is not inferred, and gaps do not subtract points. Education receives credit for evidence of study, not institution prestige. These heuristic scores are not validated hiring predictions.
- Domain credit requires an explicit domain in the JD and supporting work text. Unknown domain/experience is left unconfirmed rather than guessed. Nice-to-have skills are recorded for review; must-have skills drive the skills component.
- The four priorities are relative and normalised to total 100%; all-zero priorities are rejected. The code in `backend/engine.py` contains the complete formulas.
- Names and stated personal details, preferences, career breaks and contact sections do not enter the score. The fairness test actually replaces the candidate's name and adds different age/gender/marital signals, then recomputes the suggested score. It tests one transformation on one CV; it cannot prove a process is perfectly fair.
- Human overrides are separate from the suggested score. Every override needs a reason and records who, when and why. Changing the job clears prior overrides, shortlist selections and the fairness result, while preserving the decision history.

Use fictional data only. The samples include three real PDF files and three real Word files, a course-heavy case, varied layouts, a career gap and a typo. The sample button reads these files through the same reader used for uploads.

## Session privacy

Current CVs and reviews live in session memory. Explicitly confirmed hires are retained in `data/hiring-history.sqlite3` as anonymous work evidence grouped by role and level, until you remove them under Past hires. Files placed in the incoming folder remain on your device; the assistant reads them but does not delete or move them. There is no browser storage. The session cookie is HttpOnly and SameSite Strict. Ending or closing the session stops the assistant and clears the current desk. If a close request cannot be delivered, the idle session expires after 30 minutes. Stopping the process clears active sessions; saved hiring history survives a restart. Logs omit CV contents and keys.

The candidate view and sharing switches are explicitly labelled previews. They record choices but never publish or send a profile. No messages are sent from the app.

## Suggested seven-minute recording

| Time | Show and explain |
|---|---|
| 0:00–0:25 | Sign in. Optionally enable the hiring assistant. Say you built the prototype with Codex, FastAPI and React and are using fictional people. |
| 0:25–1:15 | Use the sample job. Review extracted details, fix the vague wording and missing pay range, then show the skill chips and priorities. |
| 1:15–1:45 | Load six sample CVs. Point out the PDF/Word mix and the personal-details note. |
| 1:45–3:35 | Review the ranked ledger. Expand Dev Patel's proof: the keywords come from a course. Correct a score or skill with a reason, mark reviewed, select candidates and download the shortlist. Move one priority to show a reorder. Run the fairness check and show the Decision Record. |
| 3:35–4:10 | Preview kind feedback and the candidate view. Request a review, show profile sharing and the pay/location preferences. |
| 4:10–5:00 | Show exactly ten call questions, open answer guidance and an accessible option, then choose a harder or shorter set. |
| 5:00–5:50 | Show market estimates and public source links. Double-check one row and explain that the unconfirmed result remains unconfirmed. |
| 5:50–6:30 | Switch between LinkedIn and Naukri; copy a smart search and show simple keywords and alternative titles. |
| 6:30–7:00 | Open and download the one-page brief. Explain that the recruiter makes the decision, then end the session to clear the desk. |

For the required “checked or corrected” moment, explain that a keyword mention is not equivalent to professional experience. Inspect Dev's course quotation, make a defensible correction with a reason, and show that reason in the record. Do not invent an error or claim that a sample salary is verified.

## Development and verification

```powershell
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
npm run build
# Start the app in another terminal before running the browser journey:
$env:TEST_PHASE='3'; npm run test:browser
```

Browser checks use Playwright with installed Google Chrome (`channel: 'chrome'`). They walk the full flow, check special features and downloads, scan rendered text for forbidden wording and look for horizontal overflow at laptop and phone sizes. Screenshots go to ignored `test-results/`. The Python checks cover scoring evidence, personal detail invariance, course credit, file failures, review reasons, exports, privacy and market fallback behavior.

For the WCAG accessibility audit, set `$env:AUDIT='1'` before the browser journey. `node tests/interactions.mjs` separately checks uploaded files, job fixes, skill-chip editing, keyboard focus and operation with external connections blocked. DM Sans and Newsreader are bundled locally with their open-font licenses in `public/fonts/`.

Main files: `frontend/main.jsx`, `frontend/styles.css`, `backend/app.py`, `backend/engine.py`, `backend/data.py`. No hosted deployment is required.

## Hiring assistant and role memory

- Open **Hiring assistant** at any time, or choose it in the popup after sign-in. The four slides explain the checks, confirm the job and role level, connect a folder, and show a final review before starting. Nothing is processed until **Start reviewing** or **Start watching for CVs** is clicked.
- **Choose a folder on my computer** opens Chrome/Edge’s folder chooser with read-only access. You can create a folder there, put PDF/Word CVs directly inside it, and grant access. Folder access stays in memory for the current desk and must be reconnected after a reload or sign-in. Keep the browser tab open for this source to bring in new files. Nested folders are not read.
- **Create an app folder** creates a dedicated folder under the local workspace’s `inbox/`. **Open folder** opens it in Windows Explorer. Check **Allow Shortlist to read CVs in this folder**, then start. This source is watched by the running app while the desk is active. Folder counts and filenames are shown before starting; an empty folder is explicitly labelled. **Try with six sample CVs** copies the fictional examples into this app folder and still requires permission and a separate start. It never writes to a folder selected through the browser.
- Use **Change folder or view setup**, **Check folder**, or **Disconnect folder** in the assistant drawer. Changing folders pauses reading; disconnecting or revoking access stops it. The app does not delete original CVs. Files and app-created folders remain on your computer when a session ends.
- The assistant waits for files to finish copying, reads and scores them, skips duplicate contents, retrieves related confirmed hires, flags missing or course-only evidence and prepares ten call questions. Recommendations update on screen. **Check now**, **Retry unreadable CVs** and the pause switch are available. Updating priorities or the role triggers a fresh review of existing CVs.
- Set **Role level** under the job: Intern, Graduate, Experienced or Senior. After reviewing a CV, open **Record a hire** on the shortlist and give a work-related reason. Saved records contain supported evidence, not names, full CVs or contact details. Past hires can be filtered, removed, or given a follow-up result. Records marked **Needs follow-up** are excluded from future comparisons.
- The RAG implementation uses SQLite FTS5/BM25 to retrieve evidence within the same role and level. Sources are shown by saved-hire ID with exact quotations. Local generation produces grounded comparisons and follow-up questions without a key. History never silently increases a candidate's score or makes a past hire a mandatory benchmark.
- With a key and **Use connected AI for review notes** enabled, a bounded [function-calling agent](https://developers.openai.com/api/docs/guides/function-calling) chooses among read-only evidence, past-hire retrieval and follow-up tools, then returns a structured draft. Both evidence and retrieval tools must run, and unknown citations trigger a local fallback. No agent can hire, reject, send messages or change a score. Paid calls are limited to three candidate reviews per scan; the next scan continues the remaining work.
- Automatic intake currently means a local watched folder. Email, an ATS or a shared drive can feed that folder through your own sync arrangement; the app does not claim to be connected to those services. It never scrapes job sites. The full local workflow is operational without a paid connection. Paid execution is verified with simulated responses only.

Additional checks: `tests/test_folder_setup.py` covers explicit start, permissions, empty folders, browser intake and disconnection. `tests/folder-intake.mjs` exercises the browser folder flow using a simulated permitted folder handle, new arrivals, permission revocation and reconnecting; the native OS chooser requires a person to select the folder. `tests/assistant.mjs` checks the setup slides, folder previews, automatic intake and accessibility at laptop/phone sizes. `tests/test_assistant_history.py` covers background intake without uploads, duplicate suppression, pause/retry, changed priorities, anonymous persistence, category boundaries, exact citations, outcomes and the bounded agent. Runtime history and incoming folders are ignored by version control.


## Workspace design and candidate call plans

All pages use a continuous deep-teal canvas, mint accents and locally bundled Sora/Public Sans fonts. Each workspace section has a related arrangement of animated 3D geometry. Artwork plays automatically without a play button and respects reduced-motion preferences and background tabs. The right-hand Workspace selector replaces the former numbered top strip. Large footer panels are removed from every page; privacy, help and scoring guidance remain available in the Workspace menu. Search ends with an explicit **See the hiring brief** action; there is no inactive next-step arrow. Decision records, fairness, candidate previews and kind-feedback editing have dedicated side panels. The assistant setup and all existing scoring, hire memory, review controls and session behaviour remain available.

Candidate-specific questions are prepared by `backend/call_plans.py` from occupational CV evidence and the current role. Missing evidence becomes a clarification question; course evidence becomes a practical application question. These drafts do not score interview answers or make hiring decisions. `frontend/CallQuestions.jsx` handles the candidate selector, per-person settings and carousel. `frontend/SearchBuilder.jsx` explains and edits searches, following [LinkedIn’s official Boolean guidance](https://www.linkedin.com/help/recruiter/answer/a524335) and linking to [Naukri’s Resdex recruiter search](https://recruit.naukri.com/recruit/resume-database-access-resdex). Platform account limits can differ. Links open the external site for the recruiter; the app does not log in or retrieve profiles.

`npm run test:redesign` checks distinct plans for all six candidates, separate settings, carousel boundaries, search edits, clipboard contents, side panels, menus and WCAG checks through all sections at laptop and 390/360px phone widths. `tests/test_call_plans_search.py` checks source grounding, personal-detail invariance, changed jobs, candidate IDs, search breadth, internship handling and saved choices. Screenshots of Sign in, Shortlist, Questions and Search are in `artifacts/`. Font licenses are bundled in `public/fonts/`.
