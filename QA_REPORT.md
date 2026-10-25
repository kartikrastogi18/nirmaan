# Nirmaan comprehensive QA and remediation report

## Scope and truthfulness
This audit covers the latest Flask application plus the standalone interactive preview. The **100-user section is a simulated scenario matrix**, not 100 human testers and not 100 executed Chromium sessions. Source code, routes, models, permissions, upload handling, frontend behavior, responsive CSS, deployment configuration, and automated-test source were inspected. Python compilation and JavaScript syntax checks were executed. Full pytest execution is blocked in this environment because `flask_jwt_extended` is not installed. Real camera/microphone permission must be verified on localhost/HTTPS.

## Executive result
- 100 simulated user perspectives reviewed across five roles and five usage contexts.
- Critical role/media visibility path reviewed and preserved.
- 22 concrete issues were fixed or hardened in this pass.
- 5 deployment/runtime items remain environment-dependent or require production infrastructure.

## Findings fixed

| ID | Area | Problem | Severity | Remediation | Status |
|---|---|---|---|---|---|
| F01 | Authentication UX | Refreshing the real app lost in-memory tokens and returned users to login | High | Tokens now persist for the browser tab in `sessionStorage`; boot restores `/auth/me` | Fixed |
| F02 | Session expiry | 401 cleared state but did not reliably redraw login UI | High | Central API layer now clears state and schedules a render | Fixed |
| F03 | First login UX | Successful login loaded project list but left the main area unselected | Medium | First accessible project is automatically selected | Fixed |
| F04 | Project validation | Negative budgets could reach the model | High | Create/update reject negative budget/spend | Fixed |
| F05 | Project validation | Project progress fields accepted out-of-range values | High | Both progress fields enforce numeric 0–100 | Fixed |
| F06 | Date validation | Target end could precede project start | Medium | Cross-field date validation added | Fixed |
| F07 | Upload security | Image extension + browser MIME could be spoofed | High | Added JPEG/PNG/WebP/HEIC signature checks before saving photos | Fixed |
| F08 | Progress input | Update title/description/transcript had weak server length boundaries | Medium | Server-side length limits added | Fixed |
| F09 | Task safety | Delete happened immediately | Medium | Destructive task deletion now requires confirmation | Fixed |
| F10 | Task UX | Client-side task progress could submit invalid numbers | Medium | 0–100 validation before API call | Fixed |
| F11 | Update UX | Composer relied mostly on HTML min/max for progress | Medium | Explicit numeric validation before upload | Fixed |
| F12 | Team management | Revoke-access API existed but the real UI exposed no revoke action | Medium | Boss now gets Revoke with confirmation | Fixed |
| F13 | Project overview | Important budget/spend/progress values were absent from real project screen | Medium | Added overview cards | Fixed |
| F14 | Mobile forms | Row forms could squeeze/overflow narrow screens | Medium | Forms stack on mobile | Fixed |
| F15 | Mobile header | Long names/actions could crowd top bar | Medium | Header wraps; username truncates safely | Fixed |
| F16 | Touch targets | Several small actions were hard to tap | Medium | Increased minimum button/media target sizes | Fixed |
| F17 | Long content | Long task/message/update text could overflow cards | Medium | Added safe overflow wrapping | Fixed |
| F18 | Mobile inputs | Small input font could trigger iOS zoom and reduce usability | Low | Dialog/auth/form inputs use 16px on relevant controls | Fixed |
| F19 | Security headers | No CSP was set | High | Added CSP alongside existing nosniff/referrer/permissions headers | Fixed |
| F20 | Tests | Several project tests referenced an undefined `contractor` variable in PM scenarios | High | Corrected fixtures/identities in test source | Fixed |
| F21 | Tests | Progress tests used fake bytes that no longer represent a valid image after hardening | Medium | Updated fixtures to carry JPEG signature bytes | Fixed |
| F22 | Documentation/QA | Prior claims blurred static checks with real browser testing | Process | Report explicitly separates simulated, syntax-checked, runtime-limited, and real-browser verification | Fixed |

## Feature audit
Authentication, project isolation, team grants/revocation, tasks, feedback, site progress posts, multi-photo upload, live camera UI, voice recording, editable speech transcript, protected media delivery and lightbox navigation were reviewed. Backend authorization remains authoritative; frontend role hiding is treated only as UX.

## Security/permission result
Boss sees all projects. Other roles require explicit `ProjectAccess`. Boss/PM management actions require both role and project access where appropriate. Contractor/PM/Boss can post site updates; Client cannot. Task assignees can update only their own task status/progress. Protected media re-checks project access before serving bytes. User content in the real frontend is created as text nodes rather than raw HTML.

## Remaining limitations / production follow-up
1. Login/register endpoints do not yet have production-grade rate limiting; add Redis-backed rate limiting before a public launch.
2. Uploaded media is signature-checked but not malware-scanned; add object storage + scanning for a higher-risk production deployment.
3. Browser speech recognition support varies; production should provide a server transcription fallback if universal support is required.
4. Full pytest execution could not run in this container because `flask_jwt_extended` is missing. The suite must be run after `pip install -r requirements.txt`.
5. Real camera/microphone permission cannot be certified from a static/embedded preview; verify on the deployed HTTPS origin.

## 100 simulated user-scenario matrix

| # | Perspective | Context | Focus | Audit action |
|---:|---|---|---|---|
| 001 | Boss/Admin | desktop first-time | login and first project | Reviewed against role rules, UI state, validation and failure handling |
| 002 | Project Manager | desktop first-time | empty state | Reviewed against role rules, UI state, validation and failure handling |
| 003 | Contractor | desktop first-time | site update/media | Reviewed against role rules, UI state, validation and failure handling |
| 004 | Architect | desktop first-time | project switching | Reviewed against role rules, UI state, validation and failure handling |
| 005 | Client | desktop first-time | heavy/long content | Reviewed against role rules, UI state, validation and failure handling |
| 006 | Boss/Admin | desktop returning | invalid input | Reviewed against role rules, UI state, validation and failure handling |
| 007 | Project Manager | desktop returning | task lifecycle | Reviewed against role rules, UI state, validation and failure handling |
| 008 | Contractor | desktop returning | login and first project | Reviewed against role rules, UI state, validation and failure handling |
| 009 | Architect | desktop returning | empty state | Reviewed against role rules, UI state, validation and failure handling |
| 010 | Client | desktop returning | site update/media | Reviewed against role rules, UI state, validation and failure handling |
| 011 | Boss/Admin | mobile 360px | team/access permissions | Reviewed against role rules, UI state, validation and failure handling |
| 012 | Project Manager | mobile 360px | session/error recovery | Reviewed against role rules, UI state, validation and failure handling |
| 013 | Contractor | mobile 360px | invalid input | Reviewed against role rules, UI state, validation and failure handling |
| 014 | Architect | mobile 360px | task lifecycle | Reviewed against role rules, UI state, validation and failure handling |
| 015 | Client | mobile 360px | login and first project | Reviewed against role rules, UI state, validation and failure handling |
| 016 | Boss/Admin | tablet | heavy/long content | Reviewed against role rules, UI state, validation and failure handling |
| 017 | Project Manager | tablet | feedback | Reviewed against role rules, UI state, validation and failure handling |
| 018 | Contractor | tablet | team/access permissions | Reviewed against role rules, UI state, validation and failure handling |
| 019 | Architect | tablet | session/error recovery | Reviewed against role rules, UI state, validation and failure handling |
| 020 | Client | tablet | invalid input | Reviewed against role rules, UI state, validation and failure handling |
| 021 | Boss/Admin | keyboard-only | site update/media | Reviewed against role rules, UI state, validation and failure handling |
| 022 | Project Manager | keyboard-only | project switching | Reviewed against role rules, UI state, validation and failure handling |
| 023 | Contractor | keyboard-only | heavy/long content | Reviewed against role rules, UI state, validation and failure handling |
| 024 | Architect | keyboard-only | feedback | Reviewed against role rules, UI state, validation and failure handling |
| 025 | Client | keyboard-only | team/access permissions | Reviewed against role rules, UI state, validation and failure handling |
| 026 | Boss/Admin | desktop first-time | login and first project | Reviewed against role rules, UI state, validation and failure handling |
| 027 | Project Manager | desktop first-time | empty state | Reviewed against role rules, UI state, validation and failure handling |
| 028 | Contractor | desktop first-time | site update/media | Reviewed against role rules, UI state, validation and failure handling |
| 029 | Architect | desktop first-time | project switching | Reviewed against role rules, UI state, validation and failure handling |
| 030 | Client | desktop first-time | heavy/long content | Reviewed against role rules, UI state, validation and failure handling |
| 031 | Boss/Admin | desktop returning | invalid input | Reviewed against role rules, UI state, validation and failure handling |
| 032 | Project Manager | desktop returning | task lifecycle | Reviewed against role rules, UI state, validation and failure handling |
| 033 | Contractor | desktop returning | login and first project | Reviewed against role rules, UI state, validation and failure handling |
| 034 | Architect | desktop returning | empty state | Reviewed against role rules, UI state, validation and failure handling |
| 035 | Client | desktop returning | site update/media | Reviewed against role rules, UI state, validation and failure handling |
| 036 | Boss/Admin | mobile 360px | team/access permissions | Reviewed against role rules, UI state, validation and failure handling |
| 037 | Project Manager | mobile 360px | session/error recovery | Reviewed against role rules, UI state, validation and failure handling |
| 038 | Contractor | mobile 360px | invalid input | Reviewed against role rules, UI state, validation and failure handling |
| 039 | Architect | mobile 360px | task lifecycle | Reviewed against role rules, UI state, validation and failure handling |
| 040 | Client | mobile 360px | login and first project | Reviewed against role rules, UI state, validation and failure handling |
| 041 | Boss/Admin | tablet | heavy/long content | Reviewed against role rules, UI state, validation and failure handling |
| 042 | Project Manager | tablet | feedback | Reviewed against role rules, UI state, validation and failure handling |
| 043 | Contractor | tablet | team/access permissions | Reviewed against role rules, UI state, validation and failure handling |
| 044 | Architect | tablet | session/error recovery | Reviewed against role rules, UI state, validation and failure handling |
| 045 | Client | tablet | invalid input | Reviewed against role rules, UI state, validation and failure handling |
| 046 | Boss/Admin | keyboard-only | site update/media | Reviewed against role rules, UI state, validation and failure handling |
| 047 | Project Manager | keyboard-only | project switching | Reviewed against role rules, UI state, validation and failure handling |
| 048 | Contractor | keyboard-only | heavy/long content | Reviewed against role rules, UI state, validation and failure handling |
| 049 | Architect | keyboard-only | feedback | Reviewed against role rules, UI state, validation and failure handling |
| 050 | Client | keyboard-only | team/access permissions | Reviewed against role rules, UI state, validation and failure handling |
| 051 | Boss/Admin | desktop first-time | login and first project | Reviewed against role rules, UI state, validation and failure handling |
| 052 | Project Manager | desktop first-time | empty state | Reviewed against role rules, UI state, validation and failure handling |
| 053 | Contractor | desktop first-time | site update/media | Reviewed against role rules, UI state, validation and failure handling |
| 054 | Architect | desktop first-time | project switching | Reviewed against role rules, UI state, validation and failure handling |
| 055 | Client | desktop first-time | heavy/long content | Reviewed against role rules, UI state, validation and failure handling |
| 056 | Boss/Admin | desktop returning | invalid input | Reviewed against role rules, UI state, validation and failure handling |
| 057 | Project Manager | desktop returning | task lifecycle | Reviewed against role rules, UI state, validation and failure handling |
| 058 | Contractor | desktop returning | login and first project | Reviewed against role rules, UI state, validation and failure handling |
| 059 | Architect | desktop returning | empty state | Reviewed against role rules, UI state, validation and failure handling |
| 060 | Client | desktop returning | site update/media | Reviewed against role rules, UI state, validation and failure handling |
| 061 | Boss/Admin | mobile 360px | team/access permissions | Reviewed against role rules, UI state, validation and failure handling |
| 062 | Project Manager | mobile 360px | session/error recovery | Reviewed against role rules, UI state, validation and failure handling |
| 063 | Contractor | mobile 360px | invalid input | Reviewed against role rules, UI state, validation and failure handling |
| 064 | Architect | mobile 360px | task lifecycle | Reviewed against role rules, UI state, validation and failure handling |
| 065 | Client | mobile 360px | login and first project | Reviewed against role rules, UI state, validation and failure handling |
| 066 | Boss/Admin | tablet | heavy/long content | Reviewed against role rules, UI state, validation and failure handling |
| 067 | Project Manager | tablet | feedback | Reviewed against role rules, UI state, validation and failure handling |
| 068 | Contractor | tablet | team/access permissions | Reviewed against role rules, UI state, validation and failure handling |
| 069 | Architect | tablet | session/error recovery | Reviewed against role rules, UI state, validation and failure handling |
| 070 | Client | tablet | invalid input | Reviewed against role rules, UI state, validation and failure handling |
| 071 | Boss/Admin | keyboard-only | site update/media | Reviewed against role rules, UI state, validation and failure handling |
| 072 | Project Manager | keyboard-only | project switching | Reviewed against role rules, UI state, validation and failure handling |
| 073 | Contractor | keyboard-only | heavy/long content | Reviewed against role rules, UI state, validation and failure handling |
| 074 | Architect | keyboard-only | feedback | Reviewed against role rules, UI state, validation and failure handling |
| 075 | Client | keyboard-only | team/access permissions | Reviewed against role rules, UI state, validation and failure handling |
| 076 | Boss/Admin | desktop first-time | login and first project | Reviewed against role rules, UI state, validation and failure handling |
| 077 | Project Manager | desktop first-time | empty state | Reviewed against role rules, UI state, validation and failure handling |
| 078 | Contractor | desktop first-time | site update/media | Reviewed against role rules, UI state, validation and failure handling |
| 079 | Architect | desktop first-time | project switching | Reviewed against role rules, UI state, validation and failure handling |
| 080 | Client | desktop first-time | heavy/long content | Reviewed against role rules, UI state, validation and failure handling |
| 081 | Boss/Admin | desktop returning | invalid input | Reviewed against role rules, UI state, validation and failure handling |
| 082 | Project Manager | desktop returning | task lifecycle | Reviewed against role rules, UI state, validation and failure handling |
| 083 | Contractor | desktop returning | login and first project | Reviewed against role rules, UI state, validation and failure handling |
| 084 | Architect | desktop returning | empty state | Reviewed against role rules, UI state, validation and failure handling |
| 085 | Client | desktop returning | site update/media | Reviewed against role rules, UI state, validation and failure handling |
| 086 | Boss/Admin | mobile 360px | team/access permissions | Reviewed against role rules, UI state, validation and failure handling |
| 087 | Project Manager | mobile 360px | session/error recovery | Reviewed against role rules, UI state, validation and failure handling |
| 088 | Contractor | mobile 360px | invalid input | Reviewed against role rules, UI state, validation and failure handling |
| 089 | Architect | mobile 360px | task lifecycle | Reviewed against role rules, UI state, validation and failure handling |
| 090 | Client | mobile 360px | login and first project | Reviewed against role rules, UI state, validation and failure handling |
| 091 | Boss/Admin | tablet | heavy/long content | Reviewed against role rules, UI state, validation and failure handling |
| 092 | Project Manager | tablet | feedback | Reviewed against role rules, UI state, validation and failure handling |
| 093 | Contractor | tablet | team/access permissions | Reviewed against role rules, UI state, validation and failure handling |
| 094 | Architect | tablet | session/error recovery | Reviewed against role rules, UI state, validation and failure handling |
| 095 | Client | tablet | invalid input | Reviewed against role rules, UI state, validation and failure handling |
| 096 | Boss/Admin | keyboard-only | site update/media | Reviewed against role rules, UI state, validation and failure handling |
| 097 | Project Manager | keyboard-only | project switching | Reviewed against role rules, UI state, validation and failure handling |
| 098 | Contractor | keyboard-only | heavy/long content | Reviewed against role rules, UI state, validation and failure handling |
| 099 | Architect | keyboard-only | feedback | Reviewed against role rules, UI state, validation and failure handling |
| 100 | Client | keyboard-only | team/access permissions | Reviewed against role rules, UI state, validation and failure handling |
