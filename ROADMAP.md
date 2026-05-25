# NUNBot Improvement Roadmap

> Roadmap updated from the current repository state and Phase 1 review.

## Guiding principles
1. Preserve current functionality.
2. Make the smallest safe change first.
3. Reduce false medical matches before optimizing UI polish.
4. Prefer deterministic logic before AI whenever possible.
5. Add tests before bigger refactors.

---

## Phase 1: Repository analysis and baselining
**Status:** completed

### Deliverables
- repository review
- architecture summary
- risk assessment
- quick wins
- improvement roadmap

### Key findings
- the app is functional and already partially hardened
- region detection now prefers local hints before OpenAI when possible
- local candidate ranking exists
- response validation exists
- tests exist and currently pass
- the biggest remaining reliability gap is the OpenAI region-inference failure path
- the dataset has one duplicate code value that should be handled explicitly

---

## Phase 2: Safe reliability hardening
**Priority:** highest

### 2.1 Close the region inference failure gap
**Goal**
- if local detection fails and OpenAI is unavailable, the app should still return a safe, deterministic degraded result instead of crashing

**Why this matters**
- this is the biggest remaining production reliability risk
- it protects the app during provider outages

### 2.2 Improve input validation
**Goal**
- reject empty, too-short, or excessively long searches early
- normalize whitespace consistently
- block obvious garbage queries

**Why this matters**
- avoids wasting API calls
- improves UX
- reduces nonsense prompts

### 2.3 Tighten OpenAI response validation
**Goal**
- validate region values
- validate code list structure
- reject duplicate or unknown codes
- ensure confidence is numeric and bounded

**Why this matters**
- prevents malformed output from reaching the user
- reduces hallucination risk

### 2.4 Add safer logging
**Goal**
- log search start/end, fallback usage, and API errors without secrets

**Why this matters**
- easier debugging
- safer operations

---

## Phase 3: Cost optimization
**Status:** completed
**Priority:** high

### Completed work
- compacted the rerank prompt to include only the highest-value shortlist
- deduplicated repeated codes before prompting the model
- truncated verbose candidate text to reduce token waste
- added session-level caching for repeated searches in Streamlit

### Result
- repeated searches now reuse cached results during the same session
- the OpenAI rerank prompt is smaller and less noisy
- duplicate CSV rows no longer inflate the prompt

---

## Phase 4: Production hardening
**Status:** completed
**Priority:** medium-high

### Completed work
- added centralized startup health checks for missing CSV / missing OpenAI key
- improved README with setup, env vars, failure behavior, and deployment notes
- tightened Streamlit defaults for production safety
- cleaned up requirements headers for readability

### Result
- startup failures are now clearer and earlier
- deployment guidance is explicit
- browser usage stats are disabled and error details are hidden in the Streamlit config

---

## Phase 5: Testing and regression coverage
**Priority:** medium-high

### Required test areas
1. input validation
2. prompt construction
3. AI response validation
4. region inference fallback
5. local candidate filtering
6. malformed input handling
7. duplicate-code behavior
8. missing-file behavior
9. degraded-mode behavior when OpenAI fails

### Best first tests
- empty string search returns a validation error
- very short garbage input is rejected
- invalid region JSON is rejected
- invalid code list is filtered out
- returned code not in CSV is dropped
- fallback path works when OpenAI raises an exception
- duplicate CSV code entries are handled predictably

---

## Quick wins to implement first
1. add a safe fallback when OpenAI region inference fails
2. add a maximum query length guard
3. add structured, secret-safe logging
4. use `Palabras clave` more aggressively in deterministic ranking
5. cache repeated normalized searches or ranking results
6. explicitly handle duplicate codes in the dataset
7. centralize runtime configuration

---

## High-impact future improvements
1. deterministic shortlist first, AI rerank second
2. smaller prompts for the second model call
3. degraded/offline mode when OpenAI is unavailable
4. golden regression cases for important procedures
5. stronger deployment and health documentation
6. clearer UI markers for deterministic vs AI vs fallback paths

---

## Recommended execution order from here
1. close the OpenAI region inference failure path
2. add safe logging and tighter validation
3. reduce prompt size and cache repeated work
4. add regression tests for critical procedures
5. finish production docs and deployment hardening
