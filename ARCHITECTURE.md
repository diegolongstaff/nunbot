# NUNBot Architecture

> Current architecture snapshot from Phase 1 analysis.

## Purpose
NUNBot helps orthopedic and trauma surgeons find likely Argentine NUN procedure codes from natural-language surgical descriptions.

## Runtime stack
- Python 3.11
- Streamlit
- Pandas
- OpenAI API
- CSV dataset (`nun_procedimientos.csv`)
- Optional environment-variable configuration

## Main components

### 1) Streamlit UI layer
**File:** `app.py`

Responsibilities:
- set the page layout and title
- initialize the OpenAI client from environment variables
- load and cache the dataset
- collect the user description
- validate the query before search
- display the selected codes and fees

This file is now mostly UI glue, which is the right shape for a Streamlit app.

### 2) Search and validation core
**File:** `nunbot_core.py`

Responsibilities:
- normalize and validate search text
- load and clean the CSV
- infer anatomy region locally when possible
- call OpenAI only when needed
- build prompts for region inference and code ranking
- validate AI responses
- rank deterministic candidates locally
- provide fallback suggestions when ranking fails

This is the most important file in the repository. It contains the reliability logic that protects the app when AI output is incomplete or malformed.

### 3) Dataset
**File:** `nun_procedimientos.csv`

Observed structure:
- `Código`
- `Descripción`
- `Región`
- `Complejidad`
- `Palabras clave`
- `Cirujano`
- `Ayudantes`
- `Total`

Observed characteristics:
- 665 rows
- 5 regions: `MS`, `CO`, `PC`, `RO`, `PP`
- 1 duplicate code value
- no missing values in the current columns
- honorarios actualizados a los valores referenciales de *marzo 2026*

### 4) Test suite
**File:** `tests/test_nunbot_core.py`

Coverage currently includes:
- query normalization
- low-signal query rejection
- deterministic candidate ranking
- region response validation
- suggestion validation
- CSV path resolution
- March 2026 tariff regression coverage
- fallback behavior when OpenAI fails
- local region preference before OpenAI
- prompt construction

## Current data flow

### Happy path
1. User enters a procedure description.
2. The app validates the query.
3. The core tries local anatomical region detection.
4. If needed, OpenAI infers the region.
5. The dataset is filtered by region.
6. Local scoring builds a shortlist of candidate codes.
7. OpenAI reranks only that shortlist.
8. The app validates the returned codes and displays them.

### Fallback path
1. OpenAI ranking fails or returns invalid data.
2. The core returns deterministic fallback suggestions.
3. The UI still shows useful results instead of failing completely.

## Why this architecture is good
- It keeps Streamlit lightweight.
- It reduces token usage by narrowing the search before the model sees it.
- It keeps the important medical logic in pure Python functions that are easy to test.
- It allows better control over false matches than a direct LLM-only approach.

## Main weaknesses still present

### 1) Region inference failure is not fully isolated
If local region detection does not find a match and the OpenAI call fails, the search can still raise an exception.

That is the highest-priority reliability gap remaining.

### 2) Prompt size is still not minimal
The app already narrows the search, but the second prompt can still be larger than necessary in broad regions.

### 3) Dataset ambiguity
A duplicate code entry exists in the CSV. That should be handled explicitly so the UI and validators do not become ambiguous.

### 4) Configuration spread
A few runtime values are still defined as module-level constants rather than in one dedicated config layer.

## Current strengths worth preserving
- Deterministic first-pass region detection
- Local candidate ranking before AI reranking
- Validation of AI-generated regions and codes
- Fallback behavior when the ranking call is bad
- Streamlit caching for app resources and data
- Small and understandable codebase

## Suggested target shape after hardening
Keep the same lightweight architecture, but reinforce it with a cleaner boundary:

- `app.py`
  - UI only
- `nunbot_core.py`
  - validation, search, prompts, deterministic ranking, fallback logic
- `tests/`
  - pure unit and integration-style regression tests
- `.env.example`
  - documented runtime settings
- `.streamlit/config.toml`
  - deployment defaults

## Data flow improvement direction

### Current flow
User input → validation → region inference → region filter → OpenAI rerank → display

### Preferred flow
User input → validation → deterministic region hints → deterministic shortlist → OpenAI only if needed → schema validation → fallback → display

That preferred flow is already partly in place. The next work is to make it more robust and cheaper.

## Operational notes
- `default_data_path()` uses the module location, which is more reliable than relying on the working directory.
- The repository now includes `.env.example` and `.streamlit/config.toml`, which is good for deployment consistency.
- The app currently depends on `OPENAI_API_KEY` being available at runtime.

## Bottom line
NUNBot is already a good candidate for incremental hardening, not a rewrite. The architecture is small enough to keep simple, but it should now be protected with stronger fallback behavior, clearer config, and more tests.
