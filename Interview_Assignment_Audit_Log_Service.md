# Interview Assignment: Audit Log Service

> Extracted from the assignment PDF and reformatted for easier review.

> Charles Schwab & Co., Inc. — Confidential & Proprietary. Provided solely for individual candidate assessment. Do not copy, distribute, re-host, or retain after submission.
> Version: 2.0 | Date: 2026-08-03

## 0. How to Submit & Integrity Expectations — Read First

This is an individual, confidential assessment. The system you build and the evidence of how you built it will be evaluated. Please read and follow these expectations carefully because they are part of the assessment.

### 0.1 Submit via a Private GitHub Repository

- Do your work in a Git repository from the start and push it to a private GitHub repository.
- Grant the panel read access when you submit.
- Develop in the open in your own repository: commit your work as you go so the history reflects the full process from requirement analysis through design, implementation, and validation.
- Commit under your own GitHub identity, and keep your AI usage log connected to the work in the repository.
- Submit the repository itself, not a zip/tarball or a snapshot with no development history.

### 0.2 Do Your Own Work, on Your Own Setup

- Complete the assignment individually, on your own machine and under your own accounts.
- The submission must be your own original work.
- Do not start from, copy, or share another person’s solution, and do not use a jointly accessed copy.
- Keep this assignment and your solution confidential; do not forward, re-host, or distribute them.

### 0.3 AI Use Is Expected — Just Be Honest About It

- Using AI tools such as Copilot or Claude is the purpose of this exercise.
- The submission should honestly represent your process and authorship, including how you used AI and how you can explain and defend your work.

### 0.4 Attestation (Required)

Add an ATTESTATION.md file at the root of your repository. It should include:

- Your full name
- Your email address
- The assignment title
- The start date and submission date
- The following statement:

> I, [your full name], attest that this submission is my own individual work, completed on my own machine and accounts, and that it honestly reflects my development process and use of AI.

## 1. Objective

Build a working prototype that transforms a set of requirements into a reviewable engineering outcome using AI-assisted engineering execution. The solution should demonstrate:

- Requirement understanding
- Task decomposition
- Multi-step autonomous orchestration

The emphasis is on engineer-led execution accelerated by AI rather than autonomous orchestration.

## 2. Scenario

You will build a tamper-evident audit log service: a system that records an append-only history of events and guarantees that past records cannot be modified or deleted without detection.

Your task is to design and build it over 2–3 days using AI assistance while demonstrating strong engineering judgment at every step.

## 3. Scope

This exercise may include:

- Greenfield scenarios (new systems or features)
- Feature extension on your own codebase
- Test and documentation improvements
- Well-defined and ambiguous requirements

## 4. Core Requirements

### Requirement Understanding

- Interpret intent
- Identify ambiguity
- Normalize the problem into a clear engineering problem

### Task Decomposition

- Convert high-level requirements into actionable tasks with dependencies and sequencing

### AI-Assisted Execution (Critical Differentiator)

- Use AI across implementation, debugging, refactoring, test generation, documentation, and review preparation
- Define tasks with intent, constraints, acceptance criteria, and technical context
- Use disciplined prompting with iterative refinement
- Maintain traceability of AI use within the repository, including what was generated, edited, rejected, and why
- Apply quality gates such as analysis, linting, tests, security, and performance
- Enforce secure AI usage
- Require human sign-off for high-impact changes
- Retain explicit engineer ownership of correctness, maintainability, and production readiness

### Engineering Output Generation

- Produce production-quality code
- Define APIs and schemas
- Create unit and integration tests
- Provide supporting documentation with clean design and maintainability

### Validation and Risk Control

- Identify risks, trade-offs, and failure scenarios
- Define validation and safety guardrails

### Controlled Oversight

- The engineer leads execution and approves outputs
- AI assists within tasks

### Final Engineering Summary

Include:

- Plan and rationale
- Artifacts
- Risks, trade-offs, and validation
- Assumptions and limitations

## 5. Scenario Details

### Scenario A — Greenfield: Core Audit Log Service

Build an audit log service with the following capabilities:

#### Write API

Accept an event record containing at minimum:

- eventType — what happened, such as USER_LOGIN, RECORD_UPDATED, or PERMISSION_GRANTED
- actorId — who or what caused the event
- resourceType — the type of resource affected
- resourceId — the specific resource affected
- payload — a structured object with event-specific detail
- timestamp — when the event occurred (caller-supplied or server-assigned; document the choice)

Records are append-only: the API must not expose an update or delete operation.

#### Query API

Retrieve events with filtering by any combination of:

- actorId
- resourceType and resourceId
- eventType
- Time range (from/to)

Support pagination for large result sets.

#### Tamper Evidence — Hash Chain

Each stored record must include:

- A hash of its own content
- A hash of the immediately preceding record, or a defined genesis value for the first record

Together these form a hash chain: any modification to a past record invalidates its own hash and every hash that follows it, making tampering detectable.

#### Chain Verification Endpoint

Expose a GET /audit/verify endpoint that walks the full chain and reports:

- Whether the chain is intact
- If broken, which record is the first inconsistency and what kind of violation was detected

The assignment is validated through these APIs: write events, query them, verify the chain, then modify a record directly in the data store and verify again to confirm detection. No external application or consumer is required.

### Scenario B — Extend Your Own System: Retention and Redaction

Extend the service from Scenario A with:

#### Retention Policy

Records older than a configurable window should be archivable or soft-deletable. The chain verification endpoint must handle archived records correctly and not report a false positive break for records that were legitimately archived per policy.

#### Structured Redaction

Certain fields in a record’s payload may contain sensitive data, such as account numbers or personal identifiers, and must be redactable without breaking the hash chain. This is a genuine engineering problem because the original hash covers the original value. Simply removing the value would invalidate the hash. The solution should document the chosen approach, trade-offs, and limitations.

#### Bulk Export

Provide an endpoint to export all records for a given resourceId or actorId as a self-contained, verifiable bundle. The bundle must include enough chain metadata for a recipient to independently verify that the records were not altered since export.

### Scenario C — Ambiguous: Compliance Reporting

Product says: "Regulators need to be able to audit access to client account data."

This requirement is intentionally under-specified. The submission should demonstrate:

- How the requirement is clarified and normalized before coding
- What ambiguities were identified and what assumptions or questions were made
- How the clarified requirement is translated into a concrete technical design
- What was implemented versus what was scoped out, and why

The submission should include the clarified requirement statement, the design decisions, and the implementation or a documented partial implementation with a scope boundary.

## 6. Live Defense (Scheduled After Submission)

After submission, you will join a live review session with the panel to walk through the solution, explain and defend design and AI-usage decisions, and work through a small requirement change live in your own codebase. Your environment should be ready to run and modify the code.

## 7. Deliverables

All deliverables should be present in your private GitHub repository:

- The repository itself, shared with the panel and containing the development history
- ATTESTATION.md
- A working prototype that is runnable end-to-end with setup instructions
- An architecture overview covering components, data model, API design, key decisions, and trade-offs, including hash algorithm choice and chain design
- Three scenarios showing decomposition, execution, and validation (A, B, and C)
- Setup instructions for local execution, including dependencies and prerequisites
- A testing approach that explains what is covered, what is not, and why
- AI usage logs or traceability notes describing what was prompted, and what was accepted, modified, or rejected and why
- A final engineering summary covering plan, rationale, artifacts, risks, trade-offs, assumptions, and limitations

## 8. Evaluation Criteria (High Level)

Your work will be scored against a detailed reviewer rubric. At a high level, reviewers assess:

- Engineering reasoning and ambiguity management
- System design and correctness
- Effective, well-governed AI-assisted execution
- Authenticity and ownership of the work
- Code quality
- Testing and validation rigor
- Security and production readiness
- How effectively you defend and adapt the solution live
- Communication

The work should reflect genuine engineering judgment that can be explained and defended, not a checklist-driven artifact.

## 9. Expectation

Treat this as production-grade engineering work. Demonstrate strong design fundamentals, effective AI use as an accelerator, output ownership, and defensible reasoning, supported by an authentic and verifiable development process.

> Principle: AI assists the engineer within tasks; the engineer owns execution, quality, and authorship.
