# Design Decisions

Key architectural and technical decisions made during ModelMora development.

## POC-Validated Decisions

### Multi-Process Worker Architecture

**Decision**: One model per subprocess with process termination for cleanup.

**Rationale**: POC 1 demonstrated subprocess approach provides 5000x better memory reclamation than Python GC (0.1MB vs 516MB leak).

**Trade-offs**:

- ✅ Excellent memory isolation
- ✅ GPU memory fully reclaimed
- ✅ Crash isolation per model
- ❌ Higher process spawn overhead (~2s load time)
- ❌ IPC complexity

### asyncio.PriorityQueue

**Decision**: Use `asyncio.PriorityQueue` for request scheduling.

**Rationale**: POC 4 showed 730,108 ops/sec throughput (730x headroom above 1,000 req/sec target) with 0.7μs enqueue latency.

**Trade-offs**:

- ✅ Native async/await integration
- ✅ Excellent performance (730k ops/sec)
- ✅ Priority ordering guarantee
- ✅ No external dependencies
- ❌ Not distributed (single-node only for MVP)

### Lazy Loading Strategy

**Decision**: Load models on first request, not at startup.

**Rationale**: POC 3 showed 2s cached load time is acceptable, allowing dynamic model management without upfront memory cost.

**Trade-offs**:

- ✅ Lower memory footprint at startup
- ✅ Flexible model catalog
- ✅ Pay-per-use resource allocation
- ❌ First request latency penalty
- ❌ Requires warmup for latency-sensitive workloads

### gRPC and REST Dual Protocol

**Decision**: Support both gRPC (streaming) and REST (simple queries).

**Rationale**: POC 2 showed gRPC 31.92 MB/s throughput suitable for large payloads, while REST simpler for basic requests.

**Trade-offs**:

- ✅ Flexibility for different clients
- ✅ Streaming support for large outputs
- ✅ REST simplicity for testing
- ❌ Dual API surface to maintain
- ❌ Protocol translation overhead

## Technology Choices

### FastAPI

**Why**: Async-first, automatic OpenAPI docs, Pydantic integration, excellent performance.

**Alternatives Considered**: Flask (sync), Starlette (lower-level).

### SQLAlchemy + Alembic

**Why**: Mature ORM, migration support, PostgreSQL compatibility.

**Alternatives Considered**: Raw SQL, Tortoise ORM, Django ORM.

### Poetry

**Why**: Modern dependency management, deterministic builds, PEP 517/621 compliance.

**Alternatives Considered**: pip + requirements.txt, pipenv, PDM.

## Next Steps

- [Architecture Overview](architecture.md)
- [Requirements](requirements.md)
- [Roadmap](roadmap.md)
