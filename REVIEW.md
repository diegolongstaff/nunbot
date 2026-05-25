# NUNBot Engineering Review

> Phase 1 baseline review captured from the current repository state.

## Scope reviewed
- `app.py`
- `nunbot_core.py`
- `tests/test_nunbot_core.py`
- `README.md`
- `requirements.txt`
- `.env.example`
- `.streamlit/config.toml`
- `nun_procedimientos.csv`

## High-level assessment
NUNBot is now a small but reasonably well-structured Streamlit app. The codebase already follows the right direction for a medical search assistant: deterministic filtering first, then OpenAI only when needed, plus validation and fallback logic. That said, there are still a few reliability gaps that matter in production, especially around failure handling when OpenAI cannot infer the region.

## What is working well
- The app is no longer a single monolith: UI and search logic are separated into `app.py` and `nunbot_core.py`.
- Search input is validated before API calls.
- Region detection prefers a local deterministic pass before OpenAI.
- Candidate ranking is narrowed locally before the model reranks suggestions.
- OpenAI responses are validated before display.
- There is a fallback path when the ranking call fails or returns invalid output.
- The test suite exists and currently passes.
- The CSV dataset is clean: 665 rows, 8 columns, and no missing values in the current fields.

## Repository architecture summary

### 1) Entry points
- Main app entry point: `app.py -> main()`
- Core search entry point: `nunbot_core.py -> search_nun_codes()`
- Test entry point: `tests/test_nunbot_core.py`

### 2) UI flow
1. User opens the Streamlit page.
2. The app initializes the OpenAI client from `OPENAI_API_KEY`.
3. The NUN CSV is loaded and cached.
4. The user types a surgical description.
5. The query is validated.
6. The app calls the core search pipeline.
7. Results are rendered with code, description, fees, confidence, and reason.

### 3) Core search flow
1. Normalize and validate the query.
2. Try local anatomical region detection first.
3. If no local region is found, call OpenAI to infer the region.
4. Filter the dataset by region.
5. Rank local candidates deterministically.
6. Send only the shortlist to OpenAI for reranking.
7. Validate the response and filter invalid codes.
8. Fall back to deterministic suggestions if needed.

### 4) OpenAI API usage
- One call for region inference when local detection is inconclusive.
- One call for code ranking.
- Calls use JSON response formatting.
- Calls are wrapped with retry and timeout logic in `nunbot_core.py`.

### 5) Data layer
- Source file: `nun_procedimientos.csv`
- Columns used: `Código`, `Descripción`, `Región`, `Palabras clave`, `Cirujano`, `Ayudantes`, `Total`
- Dataset characteristics observed:
  - 665 rows
  - 5 regions: `MS`, `CO`, `PC`, `RO`, `PP`
  - 1 duplicate code value in the dataset
  - average description length: about 78 characters
  - average keyword count: about 6.55 keywords per row

## Key findings

### Security / safety
- No obvious API key is hardcoded.
- User text is inserted into prompts, so prompt injection remains a general risk.
- Logs are minimal and do not appear to expose secrets, which is good.
- AI output is validated, which reduces hallucination risk.
- The ranking validation rejects unknown codes, invalid confidences, and malformed structures.

### Reliability
- The ranking path has fallback behavior.
- The region path still has a gap: if no local region is found and OpenAI inference fails, that exception can still bubble up.
- That is the biggest production reliability risk remaining.
- There is no user-visible offline mode yet.

### Performance / cost
- The app has already improved token efficiency by filtering locally before reranking.
- The ranking prompt is still larger than it needs to be in the biggest regions.
- Query processing still rebuilds candidate lists on each search.
- The dataset is small enough that current performance is acceptable, but there is room to reduce token spend further.

### Maintainability
- The current split between `app.py` and `nunbot_core.py` is good.
- Constants are still somewhat scattered across the core module and UI.
- A few configuration values remain hardcoded, such as the default model and token limits.
- The repo would benefit from clearer operational docs and safer defaults.

### Data quality
- The CSV is clean enough to work with directly.
- The duplicate code value should be reviewed because it can confuse validation and display logic.
- No missing values were found in the current fields.

## Risk assessment

### High risk
- OpenAI region inference can still fail hard when local detection returns no region.
- A malformed or slow API response can still affect the user experience if the request path is not fully guarded.
- Duplicate code entries in the CSV can create ambiguity in result rendering.

### Medium risk
- Prompt size is still larger than necessary for the biggest regions.
- More structured logging would help debugging without exposing secrets.
- Some configuration values are still hardcoded.

### Low risk
- Streamlit caching is already in place.
- The UI is simple and understandable.
- The test suite exists and passes.

## Quick wins
1. Add a safe fallback for OpenAI region inference failures.
2. Improve logging with structured, secret-safe messages.
3. Add a maximum query length guard.
4. Cache repeated normalized searches or rerank outputs.
5. Use the `Palabras clave` field more aggressively in local ranking.
6. Deduplicate or explicitly handle repeated codes in the CSV.
7. Tighten configuration into a single source of truth.

## High-impact future improvements
1. Use deterministic local candidate ranking as the primary shortlist for all searches.
2. Reduce prompt size further by sending only top N candidates per region.
3. Add offline or degraded-mode behavior when OpenAI is unavailable.
4. Add a tiny golden regression suite for the most important procedures.
5. Add better health checks and deployment notes.
6. Introduce safer logging and clearer failure states in the UI.

## Bottom line
NUNBot is functional and already trending in the right direction. The remaining work is not a rewrite; it is hardening. The highest-value next step is to close the OpenAI failure gap on region inference, then continue with caching, validation, and regression tests.
