# Sponsorship Intelligence Agent

A lightweight AI-powered monitoring agent that researches companies, detects business signals, verifies supporting evidence, and identifies potential sponsorship opportunities for **RAISE**, **MACHINA**, and **SIGNAL WEEK**.

This project was developed as part of an **AI & Data Intern Assessment**.

---

## 1. Problem

A sales team wants to approach potential sponsors only when there is a clear business reason.

Examples include:

- a company launching a new product,
- entering a new market,
- raising funding,
- announcing a strategic partnership,
- expanding internationally,
- investing in new infrastructure.

These opportunities appear over time, but manually monitoring every company is inefficient.

The goal of this project is to build a small automated agent that:

- researches public information about companies,
- remembers what it has already found,
- detects new information on later runs,
- uses an LLM to evaluate business relevance,
- verifies supporting evidence,
- matches opportunities with relevant events,
- generates a short recommendation,
- avoids repeated alerts when possible.

---

## 2. Companies Monitored

The current configuration monitors:

- **Mistral AI**
- **ElevenLabs**

The companies are defined in:

```text
companies.yaml
```

They can easily be replaced or extended.

---

## 3. Sponsorship Events

The agent evaluates opportunities against three configured event profiles:

- **RAISE**
- **MACHINA**
- **SIGNAL WEEK**

The profiles are stored in:

```text
events.yaml
```

Each profile contains:

- a short description,
- relevant themes,
- target audiences.

These profiles are lightweight internal matching profiles used by the agent.

If no event has a sufficiently clear connection with the business signal, the system can return:

```text
NONE
```

This prevents the agent from forcing every company development into an event.

---

## 4. Main Idea

The application combines:

- **LLM reasoning**
- **deterministic Python rules**
- **persistent SQLite memory**
- **semantic similarity**
- **evidence verification**

The LLM is used for understanding and reasoning.

Python rules are used for important safeguards such as:

- thresholds,
- recency,
- source-quality rules,
- generic-page filtering,
- deduplication,
- final recommendation logic.

This hybrid design makes the agent more predictable and easier to test.

---

## 5. Architecture

The main workflow is:

```text
companies.yaml
      |
      v
Research Agent
      |
      v
Search + Scraping
      |
      v
Article Memory
SQLite Database
      |
      v
Exact + Semantic Deduplication
      |
      v
Signal Agent
      |
      v
Evidence Verification Agent
      |
      v
Event Matching
RAISE / MACHINA / SIGNAL WEEK / NONE
      |
      v
Recommendation Agent
      |
      v
Event-Level Deduplication
      |
      v
Markdown Run Report
```

Each execution performs one monitoring cycle.

The database persists between executions, allowing later runs to identify previously known information.

---

## 6. Technology Stack

The project uses lightweight and mostly local components.

| Technology | Purpose |
|---|---|
| Python 3.12 | Main implementation language |
| Ollama | Local LLM runtime |
| Qwen3 8B | Structured reasoning and analysis |
| Pydantic | LLM output validation |
| SQLite | Persistent memory |
| DDGS | Public web search |
| Requests | HTTP retrieval |
| BeautifulSoup | Article content extraction |
| Sentence Transformers | Semantic similarity |
| all-MiniLM-L6-v2 | Embedding model |
| PyYAML | Configuration |
| Rich | Terminal output |
| Pytest | Automated testing |
| PowerShell | Scheduled execution wrapper |

No paid LLM API is required.

---

## 7. Project Structure

```text
sponsorship-intelligence-agent/
│
├── README.md
├── requirements.txt
├── .env.example
├── .gitignore
├── companies.yaml
├── events.yaml
├── pytest.ini
│
├── scripts/
│   └── run_agent.ps1
│
├── src/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   │
│   ├── agents/
│   │   ├── research_agent.py
│   │   ├── signal_agent.py
│   │   ├── verification_agent.py
│   │   └── recommendation_agent.py
│   │
│   ├── memory/
│   │   ├── database.py
│   │   ├── deduplication.py
│   │   └── event_deduplication.py
│   │
│   ├── models/
│   │   ├── article.py
│   │   ├── signal.py
│   │   ├── evidence.py
│   │   ├── opportunity.py
│   │   └── recommendation.py
│   │
│   ├── prompts/
│   │   ├── signal_extraction.txt
│   │   ├── evidence_verification.txt
│   │   └── opportunity_analysis.txt
│   │
│   ├── services/
│   │   ├── ollama_service.py
│   │   ├── search_service.py
│   │   ├── scraper_service.py
│   │   └── embedding_service.py
│   │
│   └── utils/
│       ├── hashing.py
│       ├── logger.py
│       ├── recency.py
│       ├── run_report.py
│       └── text_cleaning.py
│
├── demo/
│   ├── run_1.md
│   └── run_2.md
│
└── tests/
    ├── test_deduplication.py
    ├── test_event_deduplication.py
    ├── test_memory.py
    ├── test_ollama.py
    ├── test_recency.py
    ├── test_recommendation_agent.py
    ├── test_research.py
    ├── test_signal_agent.py
    └── test_verification_agent.py
```

The SQLite database is generated locally and is intentionally excluded from Git.

---

## 8. Research Agent

The Research Agent searches public information using business-oriented queries.

Example:

```text
"Mistral AI"
(
    "product launch"
    OR "new product"
    OR "partnership"
    OR "funding"
    OR "expansion"
    OR "enterprise"
    OR "new market"
    OR "acquisition"
)
```

If the main query returns no results, the search service automatically uses simpler fallback queries.

Examples:

```text
Mistral AI funding
Mistral AI product launch
Mistral AI partnership
Mistral AI expansion
```

This is useful because public search engines do not always return results for complex Boolean queries.

---

## 9. Scraping and Search Failure Handling

External websites are not always accessible.

During the demo, some sources returned errors such as:

```text
403 Forbidden
429 Too Many Requests
```

The pipeline does not stop when this happens.

Instead, it:

1. logs the error,
2. preserves available search-result information,
3. continues with the remaining sources.

This keeps the monitoring cycle resilient to individual source failures.

---

## 10. Persistent Memory

The agent stores its state in SQLite.

Default database:

```text
data/sponsorship_agent.db
```

The database stores information about:

- articles,
- extracted signals,
- recommendations,
- previous business events,
- run history.

Because the database persists between executions, the second run can distinguish:

```text
NEW
KNOWN
SEMANTIC DUPLICATE
```

This allows the system to remember what it has already processed.

---

## 11. Article Deduplication

Two levels of article deduplication are used.

### Exact duplicate detection

A deterministic content hash is generated from article information.

If the article already exists, it is marked:

```text
[KNOWN]
```

### Semantic duplicate detection

Different pages can describe almost the same information using different wording.

Sentence embeddings are used to compare article meaning.

Configured threshold:

```text
SEMANTIC_DUPLICATE_THRESHOLD=0.88
```

A sufficiently similar result can be marked:

```text
[SEMANTIC DUPLICATE]
```

---

## 12. Signal Agent

New articles are analyzed by the Signal Agent.

Possible signal types include:

```text
PRODUCT_LAUNCH
FUNDING
PARTNERSHIP
MARKET_EXPANSION
ACQUISITION
LEADERSHIP_CHANGE
OTHER
```

The structured output contains:

- company,
- signal type,
- summary,
- evidence,
- business relevance,
- confidence,
- relevance decision.

Current signal thresholds:

```text
SIGNAL_RELEVANCE_THRESHOLD=60
SIGNAL_CONFIDENCE_THRESHOLD=0.60
```

Signals below these requirements are retained in memory but do not proceed as strong opportunities.

---

## 13. Generic Page Filtering

A common false-positive case is a general company page that contains historical funding or product information.

Examples include:

- Wikipedia pages,
- company homepages,
- company profiles,
- funding databases,
- general news pages,
- statistics pages.

The agent uses deterministic filtering to prevent these pages from being treated as new business events.

Example:

```text
https://mistral.ai/
```

should not generate a new funding alert simply because the homepage contains historical information.

This behavior is covered by automated tests.

---

## 14. Evidence Verification

A relevant business signal is not automatically treated as a sponsorship opportunity.

The Verification Agent evaluates:

- source quality,
- whether the claim is supported,
- whether the evidence is clear,
- confidence.

Source quality can be:

```text
HIGH
MEDIUM
LOW
```

A `LOW` quality source is not allowed to directly generate a sponsorship alert.

Example policy:

```text
LOW source
    ↓
MONITOR / NO ALERT
```

Even when the extracted claim appears plausible.

---

## 15. Opportunity Scoring

The Recommendation Agent evaluates each verified opportunity using a 100-point model.

| Criterion | Maximum |
|---|---:|
| Business Trigger | 25 |
| Event Fit | 25 |
| Evidence Quality | 20 |
| Commercial Intent | 15 |
| Recency | 15 |
| **Total** | **100** |

Current recommendation thresholds:

```text
SPONSORSHIP_THRESHOLD=75
CONFIDENCE_THRESHOLD=0.70
```

A final recommendation also requires:

- supported evidence,
- clear evidence,
- source quality not LOW,
- event not equal to `NONE`.

Otherwise:

```text
MONITOR / NO ALERT
```

---

## 16. Deterministic Recency

Recency is calculated by Python.

It is not accepted directly from the LLM.

This provides deterministic scoring based on publication date.

Recency contributes up to:

```text
15 points
```

to the final opportunity score.

---

## 17. Event Matching

The Recommendation Agent evaluates the business event against all configured event profiles.

Possible outputs:

```text
RAISE
MACHINA
SIGNAL WEEK
NONE
```

The output also includes an event-fit explanation.

Example:

```text
Recommended event: RAISE
```

with a reason connecting:

- the company development,
- event themes,
- event audience,
- plausible sponsorship value.

---

## 18. Business Event Deduplication

Article deduplication is not enough because two different articles can describe the same underlying business event.

The application therefore performs event-level deduplication.

Configured general threshold:

```text
EVENT_DUPLICATE_THRESHOLD=0.84
```

Example:

```text
Article A:
ElevenLabs raises $500M Series D at $11B valuation

Article B:
ElevenLabs raises $500M from Sequoia at an $11B valuation
```

These may describe the same business event even though the titles are different.

The event-level logic helps prevent repeated sponsorship alerts.

---

## 19. Funding Event Validation

Funding events receive additional deterministic validation.

The system extracts:

- funding amount,
- round,
- valuation.

Example:

```text
$500M Series D at $11B valuation
```

is interpreted as:

```text
Funding amount: $500M
Funding round: Series D
Valuation: $11B
```

This allows the system to distinguish:

```text
$180M Series C
```

from:

```text
$500M Series D
```

even when the surrounding article text is semantically similar.

The automated test suite explicitly covers this behavior.

---

## 20. LLM Reliability

All important LLM outputs use Pydantic schemas.

This provides structured validation before results are used by the application.

The Ollama service also includes retry behavior.

For example, during one demo run the local model returned:

```text
Structured output failed (attempt 1/2):
LLM returned an empty response.
```

The service retried and the monitoring cycle continued.

---

## 21. Example Recommendation

One recommendation generated during the demo was based on the Mistral 3 launch.

Example result:

```text
Company: Mistral AI
Signal: PRODUCT_LAUNCH
Recommended event: RAISE

Business trigger: 25/25
Event fit: 22/25
Evidence quality: 18/20
Commercial intent: 14/15
Recency: 5/15

Total: 84/100
Confidence: 0.95

Decision: RECOMMEND
```

The recommendation was based on a verified product launch and a clear connection with the configured RAISE themes around AI innovation, enterprise AI, and generative AI.

---

## 22. Demo Runs

Two demo runs are included:

```text
demo/run_1.md
demo/run_2.md
```

### Run 1

Run 1 was executed with a clean active database.

Results:

```text
Articles found:        19
New articles:          18
New recommendations:  10
```

Its purpose was to establish the initial knowledge base.

### Run 2

Run 2 was executed immediately afterward without deleting the database.

Results:

```text
Articles found:        17
New articles:          13
New recommendations:  3
```

Run 2 demonstrates persistent memory.

It contains examples of:

```text
[KNOWN]
[SEMANTIC DUPLICATE]
Underlying business event already alerted.
No duplicate alert.
```

The second run therefore demonstrates that the application is not stateless.

---

## 23. Automated Tests

The final project contains:

```text
27 automated tests
```

Run them with:

```bash
pytest -s
```

Final result:

```text
27 passed in 12.35s
```

The tests cover:

- exact deduplication,
- semantic deduplication,
- persistent memory,
- Ollama connectivity,
- recency scoring,
- signal extraction,
- generic-page filtering,
- homepage filtering,
- evidence verification,
- strong recommendations,
- duplicate recommendation prevention,
- unsupported evidence,
- `NONE` event behavior,
- LOW source blocking,
- funding event conflicts,
- same funding event detection,
- valuation vs funding amount,
- product-launch event comparison.

---

## 24. Installation

### Requirements

Recommended:

```text
Python 3.12+
Ollama
```

Clone the repository:

```bash
git clone <YOUR_REPOSITORY_URL>
cd sponsorship-intelligence-agent
```

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it on Windows:

```powershell
.venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

## 25. Ollama Setup

Install Ollama and make sure it is running.

Download the configured model:

```bash
ollama pull qwen3:8b
```

Optional connectivity check:

```bash
pytest -s tests/test_ollama.py
```

---

## 26. Environment Configuration

Copy:

```text
.env.example
```

to:

```text
.env
```

Example:

```env
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=qwen3:8b

SPONSORSHIP_THRESHOLD=75
CONFIDENCE_THRESHOLD=0.70

SIGNAL_RELEVANCE_THRESHOLD=60
SIGNAL_CONFIDENCE_THRESHOLD=0.60

SEMANTIC_DUPLICATE_THRESHOLD=0.88
EVENT_DUPLICATE_THRESHOLD=0.84
```

Do not commit `.env`.

---

## 27. Run the Agent

Run one monitoring cycle with:

```bash
python -m src.main
```

The pipeline will:

1. load company configuration,
2. search public sources,
3. compare results with SQLite memory,
4. analyze new articles,
5. verify evidence,
6. evaluate event fit,
7. generate recommendations,
8. save a Markdown run report.

---

## 28. Run Reports

Each monitoring cycle generates a Markdown report.

Examples:

```text
demo/run_1.md
demo/run_2.md
```

The reports include:

- article information,
- signal type,
- business-event summary,
- evidence quality,
- recommended event,
- event-fit reason,
- opportunity score,
- confidence,
- decision,
- reason,
- suggested next step,
- source links,
- memory behavior.

---

## 29. Scheduling

The application performs one monitoring cycle per execution.

A PowerShell wrapper is provided:

```text
scripts/run_agent.ps1
```

It can be scheduled with Windows Task Scheduler.

Example:

```text
Program:
powershell.exe
```

Arguments:

```text
-ExecutionPolicy Bypass -File "C:\path\to\sponsorship-intelligence-agent\scripts\run_agent.ps1"
```

This separates scheduling from the Python application itself.

For the assessment demo, the two runs were executed manually so that memory behavior could be observed directly.

---

## 30. Alert Policy

The system intentionally uses a conservative alert policy.

An article can be interesting but still produce:

```text
MONITOR / NO ALERT
```

Reasons include:

- low signal relevance,
- low confidence,
- unsupported evidence,
- unclear evidence,
- LOW-quality source,
- score below 75,
- no suitable event,
- known recommendation,
- duplicate underlying business event.

The objective is to produce fewer, more meaningful alerts rather than maximize recommendation volume.

---

## 31. Failure Handling

The application handles several common failure cases.

### Search returns no results

Fallback queries are executed.

### Source cannot be scraped

The error is logged and processing continues.

### HTTP 403 / 429

The source failure does not stop the monitoring cycle.

### LLM returns invalid or empty structured output

The Ollama service retries.

### Article already known

It is not processed as a new article.

### Business event already alerted

No duplicate recommendation is saved.

### Evidence is weak

The result becomes `MONITOR / NO ALERT`.

---

## 32. Design Choices

### Why SQLite?

It provides persistent memory with no external database server.

### Why Ollama?

It allows the project to run locally without a paid LLM API.

### Why Pydantic?

LLM responses are validated before they are used.

### Why deterministic rules?

Important decisions should not depend entirely on LLM reasoning.

### Why semantic embeddings?

Different articles can describe the same information with different words.

### Why event-level deduplication?

Different URLs can still refer to the same real business event.

---

## 33. Limitations

This is intentionally a small assessment project rather than a production monitoring platform.

Current limitations include:

### Search variability

Public search results can change between executions.

### Website restrictions

Some sources block automated scraping.

### LLM variability

Local model wording and scores can vary slightly.

### Publication date quality

Not every source exposes a reliable publication date.

### Product-launch deduplication

Very similar articles about the same product launch can occasionally remain separate if their wording differs enough.

For example, multiple descriptions of the Mistral 3 launch appeared during the demo.

This could be improved with stronger product-entity extraction.

### Lightweight event profiles

The event profiles are designed for assessment-level matching rather than complete production event intelligence.

---

## 34. Possible Future Improvements

Possible extensions include:

- canonical entity extraction,
- stronger product-event deduplication,
- multi-source evidence confirmation,
- improved publication-date extraction,
- configurable domain reputation,
- asynchronous research,
- more detailed event profiles,
- monitoring additional companies,
- email or Slack notifications,
- optional CRM integration,
- a lightweight monitoring dashboard.

These features were intentionally excluded to keep the assessment focused and easy to review.

---

## 35. Out of Scope

The following were intentionally not implemented:

- polished frontend,
- CRM integration,
- automatic sales outreach,
- production deployment infrastructure,
- large-scale company monitoring.

The assessment focuses on research, memory, reasoning, evidence verification, event matching, and recommendations.

---

## 36. Final Validation

The final implementation includes:

```text
2 monitored companies
3 sponsorship event profiles
SQLite persistent memory
Exact duplicate detection
Semantic duplicate detection
Business-event duplicate detection
Evidence verification
Source-quality safeguards
Event matching
Deterministic scoring
Scheduled execution support
Markdown demo reports
27 automated tests
```

Final test result:

```text
============================== 27 passed in 12.35s ==============================
```

---

## 37. Summary

The Sponsorship Intelligence Agent demonstrates a complete small-scale monitoring workflow:

```text
Research
   ↓
Memory
   ↓
Deduplication
   ↓
Business Signal
   ↓
Evidence Verification
   ↓
Event Fit
   ↓
Scoring
   ↓
Recommendation / Monitor
   ↓
Persistent Report
```

Run 1 establishes the initial knowledge base.

Run 2 reuses the stored state to distinguish known information from new information and reduce repeated alerts.

The result is a small, testable, and explainable sponsorship intelligence workflow built with local AI and deterministic safeguards.