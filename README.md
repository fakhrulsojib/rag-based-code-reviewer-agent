# Automated Code Review Agent

An intelligent code review agent that automatically reviews Pull Requests in Bitbucket using Retrieval-Augmented Generation (RAG) to apply only relevant coding rules.

## 🎯 Overview

This agent acts like a senior engineer who knows exactly which checklist to look at based on the code being reviewed. Instead of applying all rules to every PR (context stuffing), it:

1. **Analyzes** the code changes to detect patterns (file types, annotations, keywords)
2. **Retrieves** only relevant rules from a vector database
3. **Reviews** the code using Google Gemini AI with just-in-time rule context
4. **Posts** inline comments directly to Bitbucket PRs

## 🏗️ Architecture

```
Bitbucket PR → Webhook/API → Diff Analysis → Anchor Detection
                                                    ↓
Vector Store ← Rule Ingestion              Smart Retrieval
     ↓                                             ↓
  Rules (Markdown)                    LLM Review (Gemini)
                                                    ↓
                                         Bitbucket Comments
```

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose
- Bitbucket workspace with API access
- Google Gemini API key

### Setup

1. **Clone and configure**:
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

2. **Add your rule files** to the `rules/` directory:
   ```bash
   # Example structure:
   rules/
   ├── java-entity-rules.md
   ├── sql-migration-rules.md
   └── web-layer-rules.md
   ```

3. **Build and start**:
   ```bash
   docker-compose up -d
   ```

4. **Ingest rules** into vector store:
   ```bash
   docker-compose exec review-agent python -m src.ingestion.ingest_cli --rules-dir ./rules --rebuild
   ```

5. **Configure Bitbucket webhook**:
   - URL: `http://your-server:8000/webhook`
   - Events: Pull Request Created, Pull Request Updated
   - Secret: Set in `.env` as `BITBUCKET_WEBHOOK_SECRET`

## 📡 API Endpoints

### Health Check
```bash
GET /health
```

### Webhook (Automatic Reviews)
```bash
POST /webhook
# Triggered automatically by Bitbucket
```

### Manual Review
```bash
POST /review/{pr_id}
{
  "pr_id": 123,
  "force_refresh": false
}
```

## 🔧 Configuration

Key environment variables in `.env`:

```bash
# LLM Provider
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-1.5-flash

# Bitbucket
BITBUCKET_WORKSPACE=your_workspace
BITBUCKET_REPO_SLUG=your_repo
BITBUCKET_APP_PASSWORD=your_app_password

# Retrieval Settings
TOP_K_RULES=10
SIMILARITY_THRESHOLD=0.7
```

## 📝 Writing Rule Files

Rules are written in Markdown with special metadata:

```markdown
# Rule Category Name

## Specific Rule

**Severity**: High|Medium|Low
**Applies to**: @Entity, .sql, etc.

Rule description and guidelines...

## Example

\`\`\`java
// Good example
\`\`\`
```

### Metadata Fields

- **Severity**: `High` (blocking), `Medium` (important), `Low` (suggestion)
- **Applies to**: Comma-separated list of file types, annotations, or patterns

## 🧠 How It Works

### 1. Anchor Detection

The system detects "anchors" in code changes:

- **File extensions**: `.java`, `.sql`, `.js`
- **Annotations**: `@Entity`, `@RestController`, `@Service`
- **Patterns**: `CREATE TABLE`, `class extends`, etc.

### 2. Smart Retrieval

Anchors are converted to semantic queries:
- `["entity", "jpa"]` → "JPA entity structure and naming conventions"
- Query the vector store for top-K relevant rules
- Filter by similarity threshold

### 3. LLM Review

- Build dynamic prompt with only retrieved rules
- Send to Gemini API for analysis
- Parse JSON response with findings

### 4. Comment Posting

- Post inline comments to specific lines
- Include severity indicators (🔴 High, 🟡 Medium, 🔵 Low)
- Add summary comment with statistics

## 🧪 Testing

### Run Tests
```bash
pytest tests/
```

### Test Ingestion
```bash
python -m src.ingestion.ingest_cli --file rules/java-entity-rules.md
```

### Test Manual Review
```bash
curl -X POST http://localhost:8000/review/123 \
  -H "Content-Type: application/json" \
  -d '{"pr_id": 123}'
```

## 📊 Monitoring

Logs are written to:
- Console: Real-time output
- File: `logs/app.log`

Check vector store stats:
```python
from src.ingestion.vector_store import VectorStore
vs = VectorStore()
print(vs.get_stats())
```

## 🔄 Updating Rules

To update existing rules:

```bash
# Update specific file
docker-compose exec review-agent python -m src.ingestion.ingest_cli --file rules/java-entity-rules.md

# Rebuild entire knowledge base
docker-compose exec review-agent python -m src.ingestion.ingest_cli --rules-dir ./rules --rebuild
```

## 🎛️ Advanced Configuration

### Custom Anchor Patterns

Create `anchor_registry.json`:

```json
[
  {
    "pattern": "class.*Repository",
    "tags": ["repository", "data-access"]
  }
]
```

### LLM Provider Switching

Change provider in `.env`:

```bash
LLM_PROVIDER=openai  # or anthropic
OPENAI_API_KEY=your_key
```

## 🐛 Troubleshooting

### No rules retrieved
- Check vector store has data: `vs.get_stats()`
- Lower `SIMILARITY_THRESHOLD` in `.env`
- Verify anchor detection is working

### Webhook not triggering
- Verify webhook secret matches
- Check Bitbucket webhook delivery logs
- Ensure server is publicly accessible

### LLM errors
- Check API key is valid
- Verify rate limits not exceeded
- Check model name is correct

## 📚 Project Structure

```
ionic-halo/
├── src/
│   ├── ingestion/      # Rule ingestion & vector store
│   ├── analysis/       # Anchor detection
│   ├── retrieval/      # Smart rule retrieval
│   ├── bitbucket/      # Bitbucket API integration
│   ├── review/         # LLM review generation
│   ├── workflow/       # LangGraph orchestration
│   ├── config.py       # Configuration management
│   ├── models.py       # Data models
│   └── main.py         # FastAPI application
├── rules/              # Rule files (Markdown)
├── tests/              # Test suite
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## 🤝 Contributing

To add new features:

1. Add anchor patterns in `src/analysis/anchor_detector.py`
2. Update query builder in `src/retrieval/query_builder.py`
3. Add tests in `tests/`

## 📄 License

MIT License - feel free to use and modify.

## 🙏 Acknowledgments

Built with:
- [LangChain](https://langchain.com/) - LLM orchestration
- [LangGraph](https://langchain-ai.github.io/langgraph/) - Workflow management
- [ChromaDB](https://www.trychroma.com/) - Vector database
- [FastAPI](https://fastapi.tiangolo.com/) - Web framework
- [Google Gemini](https://ai.google.dev/) - LLM provider
