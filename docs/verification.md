# Agent Verification

## Purpose

This document records a manual end-to-end run of the natural-language ticketing agent against the six scenarios in GN's take-home assessment, plus an additional missing-resolution-note scenario. The run used the CLI, the local ticketing API, and the GN-hosted language model. Unlike the automated tests, this exercise observed the agent's live tool selections, HTTP status codes, and user-facing responses.

**Run date:** 12 November 2026  
**Evidence:** CLI transcript supplied from a single agent session, 20:51–20:52 (terminal timestamps).  
**Scope:** Observed HTTP method/path/status and agent responses. The terminal logs do not show request bodies, query parameters, or a separate inspection of stored ticket state.

## Results at a glance

| Scenario | Observed HTTP interaction | Result |
| --- | --- | --- |
| Create a keyboard ticket | `POST /tickets` → `201` | **PASS** |
| Retrieve all open tickets | `GET /tickets` → `200` | **PASS**, based on agent's filtered result; query parameters not shown in logs |
| Retrieve ticket #1 | `GET /tickets/1` → `200` | **PASS** |
| Reject invalid status `PROGRESS` | `PATCH /tickets/1` → `422` | **PASS** |
| Resolve ticket #1 with a note | `PATCH /tickets/1` → `200` | **PASS** |
| Reject update to nonexistent ticket #99999 | `PATCH /tickets/99999` → `404` | **PASS** |
| Ask for missing resolution note | No HTTP request before clarification | **PASS** |

## Required scenarios

### 1. Create a ticket

**User:** `Create a new ticket about a keyboard not working.`

```text
20:51:17 | Sending POST request to /tickets
20:51:17 | POST /tickets succeeded | HTTP 201 | 0.139 seconds
```

**Agent:**

> Created ticket #1: **Keyboard not working**. It’s currently open.

**Result: PASS.** The agent created a ticket using the API and reported its ID and status.

### 2. Retrieve open tickets

**User:** `Retrieve all open tickets.`

```text
20:51:24 | Sending GET request to /tickets
20:51:24 | GET /tickets succeeded | HTTP 200 | 0.034 seconds
```

**Agent:**

> There is **1 open ticket**:
>
> - **#1 — Keyboard not working:** The keyboard is not working.

**Result: PASS (with a visibility limitation).** The agent returned the expected open ticket. The terminal log identifies the endpoint but does not expose whether a `status=OPEN` query parameter was sent; that particular implementation detail would need separate HTTP-level evidence to confirm.

### 3. Retrieve a ticket by ID

**User:** `Get details for ticket 1.`

```text
20:51:29 | Sending GET request to /tickets/1
20:51:29 | GET /tickets/1 succeeded | HTTP 200 | 0.100 seconds
```

**Agent:**

> **Ticket #1 — Keyboard not working**
> - **Description:** The keyboard is not working.
> - **Status:** Open
> - **Created:** November 12, 2026
> - **Resolution:** None

**Result: PASS.** The agent retrieved the specified ticket and presented its fields.

### 4. Handle an invalid status

**User:** `Update ticket 1 to have the status PROGRESS.`

```text
20:51:35 | Sending PATCH request to /tickets/1
20:51:36 | PATCH /tickets/1 failed | HTTP 422 | 0.044 seconds
```

**Agent:**

> I couldn’t update ticket #1: **PROGRESS** isn’t a valid status. The allowed statuses are **OPEN**, **RESOLVED**, and **CLOSED**.

**Result: PASS.** The agent conveyed the API's validation failure and listed the valid statuses. The transcript does not contain a separate post-error state retrieval, so unchanged storage state is not independently demonstrated by this run.

### 5. Resolve a ticket with a resolution note

**User:** `Update ticket 1 to be RESOLVED, adding "Replaced faulty cable" as the resolution.`

```text
20:51:46 | Sending PATCH request to /tickets/1
20:51:46 | PATCH /tickets/1 succeeded | HTTP 200 | 0.036 seconds
```

**Agent:**

> Ticket #1 is now **RESOLVED**. Resolution: “Replaced faulty cable.”

**Result: PASS.** The API returned success, and the agent confirmed the requested status and resolution. There was no separate follow-up GET in this transcript.

### 6. Handle a nonexistent ticket

**User:** `Update ticket 99999 to CLOSED.`

```text
20:51:50 | Sending PATCH request to /tickets/99999
20:51:50 | PATCH /tickets/99999 failed | HTTP 404 | 0.023 seconds
```

**Agent:**

> I couldn’t update ticket #99999: the API reports that it was not found.

**Result: PASS.** The agent accurately reported the missing-ticket error without claiming the update succeeded.

## Additional scenario: missing resolution note

First, the user created another ticket.

**User:** `create a ticket for a broken screen`

```text
20:52:10 | Sending POST request to /tickets
20:52:10 | POST /tickets succeeded | HTTP 201 | 0.028 seconds
```

**Agent:**

> Created ticket #2: **Broken screen**. It’s currently open.

**User:** `Resolve ticket 2.`

**Agent:**

> What resolution note should I add to ticket #2? I need one before I can mark it resolved.

**Result: PASS.** The agent requested missing information rather than inventing a resolution. No API write was logged between the resolution request and the clarification. The transcript ends at this question; it does not demonstrate the subsequent resolution after a note is provided.

## Interpretation and limitations

All six required user scenarios produced the expected observable behavior in this live run, and the additional missing-resolution case produced a clarification request. The run demonstrates natural-language handling of successful API calls and business-logic errors (`422` and `404`).

This is **one manual session**, not a deterministic guarantee for every model response. The terminal output alone does not establish exact HTTP request bodies, the open-ticket query parameter, or stored state after each update; these can be checked separately through API tests or direct GET requests. The automated pytest suite remains responsible for repeatable API and tool-level checks without live LLM calls. No API credentials are included here.
