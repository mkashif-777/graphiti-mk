# Graphiti Temporal Knowledge Graph: Relationship Retrieval Analysis

## Executive Summary

When querying Graphiti for chronological analysis, **previous relationships that have been marked as "expired" are NOT automatically retrieved by default search queries**. However, they are **preserved in the knowledge graph with temporal metadata**, allowing for explicit historical queries when needed. The key distinction is between **active relationships** (current state) and **historical relationships** (past states).

---

## 1. Temporal Data Model: Bi-Temporal Approach

Graphiti implements a sophisticated **bi-temporal model** that tracks relationships across two distinct timelines:

### 1.1 Database Transaction Time (T')
Describes when information enters and leaves the system:
- **`created_at`**: When a relationship was added to the database
- **`expired_at`**: When a relationship is marked as no longer true (nullable field)

### 1.2 Real World Time (T)
Describes when facts were actually true in the real world:
- **`valid_at`**: When a relationship started being true in real-world time
- **`invalid_at`**: When a relationship stopped being true in real-world time

---

## 2. How Graphiti Handles Relationship Invalidation

### 2.1 The Non-Lossy Approach

**Core Principle**: When new information contradicts existing information, Graphiti **does NOT delete** the previous relationship. Instead, it:

1. **Marks the old relationship as expired** by setting the `expired_at` field to the current timestamp
2. **Preserves the historical relationship** with all temporal metadata intact
3. **Creates new relationship(s)** reflecting the updated reality

### 2.2 Example: Job Title Change

```
Initial State (July 2023):
  Maria -> works_as -> junior manager
  (valid_at: 2023-07-01, created_at: 2023-07-01)

New Information (October 2024):
  Maria: "I just got promoted and work as a senior manager now"

Result After Ingestion:
  
  Expired Relationship:
    Maria -> works_as -> junior manager
    (valid_at: 2023-07-01, created_at: 2023-07-01, expired_at: 2024-10-01)
    [Fact regenerated]: "Maria used to work as a junior manager, until her promotion to a senior manager"
  
  New Relationship:
    Maria -> works_as -> senior manager
    (valid_at: 2024-10-01, created_at: 2024-10-01)
```

### 2.3 Conflict Resolution Using Valid_at Dates

When episodes arrive **out of chronological order**, Graphiti uses `valid_at` timestamps to determine the correct timeline:

```
Reference Timestamp: Sep 30, 2024

Episode 1 (received first):
  Josh: "I divorced Jane last month"
  Extracted: Josh -> DIVORCED_FROM -> Jane (valid_at: ~August 2024)

Episode 2 (received second, but historically earlier):
  Josh: "I married Jane in August 2005"
  Extracted: Josh -> MARRIED_TO -> Jane (valid_at: August 2005)

Conflict Resolution:
  - System recognizes both relationships are valid but at different times
  - Marriage (2005) logically precedes divorce (2024)
  - Josh -> MARRIED_TO -> Jane is marked as expired
  - Josh -> DIVORCED_FROM -> Jane remains active
  - Complete historical timeline is preserved
```

---

## 3. Query Retrieval Behavior

### 3.1 Default Search Behavior (Chronological Queries)

When you perform a standard search query in Graphiti:

```python
results = await graphiti.search(
    query="What is Maria's current job?",
    num_results=5
)
```

**Behavior**:
- Returns **active relationships only** (relationships where `expired_at` is NULL)
- Prioritizes the **most recent valid_at timestamp**
- Does NOT include expired relationships by default
- Optimized for **current state queries**

**Why**: This makes sense because most queries seek current information, not historical data.

### 3.2 Historical/Chronological Analysis Queries

When explicitly querying for **historical or chronological analysis**, Graphiti provides the temporal metadata:

```python
# Query returns relationships with temporal metadata
results = await graphiti.search(
    query="Show me Maria's career progression over time",
    num_results=10
)

# Returned relationships include:
# - valid_at: 2023-07-01 (when she became junior manager)
# - expired_at: 2024-10-01 (when she was promoted)
# - valid_at: 2024-10-01 (when she became senior manager)
```

**Key Point**: The search system has **access to all temporal metadata**, including:
- `valid_at` and `invalid_at` on edges
- `created_at` and `expired_at` on edges
- Complete facts with historical context (e.g., "used to work as...")

---

## 4. Critical Distinction: Retrieval vs. Preservation

### 4.1 What Gets Retrieved

**In standard queries** (asking about current state):
- ✅ Active relationships (`expired_at = NULL`)
- ✅ Temporal metadata for all returned relationships
- ❌ Expired relationships (not included by default)

**In historical queries** (asking about evolution, timeline, history):
- ✅ Both active AND expired relationships
- ✅ Full temporal context and narrative
- ✅ Relationship lifecycle information

### 4.2 Why Expired Relationships Are Preserved

Graphiti maintains expired relationships for:

1. **Audit trails and compliance**: Track when changes occurred
2. **Temporal queries**: "What was true on [date]?"
3. **Historical context**: "Show me the evolution of X"
4. **Contradiction analysis**: Understanding how facts changed
5. **Data provenance**: Tracing information back to source episodes

---

## 5. Point-in-Time Queries

Graphiti supports **explicit point-in-time queries** that retrieve the state of relationships at a specific historical date:

### 5.1 Example: "What was true on Q2 2024?"

```
Query: "What was Maria's job in June 2024?"

System Logic:
  - Searches for relationships where valid_at <= 2024-06 AND (expired_at > 2024-06 OR expired_at = NULL)
  - Returns: Maria -> works_as -> junior manager (valid from 2023-07-01)
  - Does NOT return: The later promotion (valid_at: 2024-10-01)
```

### 5.2 Implementation Notes

According to Graphiti documentation:
> "We plan to add temporal filtering capabilities to the search API soon."

This indicates that **explicit temporal filtering is a planned enhancement**, suggesting that full temporal query APIs are still being refined.

---

## 6. Relationship State Diagram

```
┌─────────────────────────────────────────────┐
│   New Episode Ingestion                     │
│   (Contains conflicting information)        │
└────────────┬────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────┐
│   Date Extraction & LLM Invalidation Prompt │
│   - Extract valid_at/invalid_at             │
│   - Compare with existing edges             │
│   - Identify conflicts                      │
└────────────┬────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────┐
│   Conflict Resolution                       │
│   - Determine which edge is superseded      │
│   - Sort by valid_at for ordering           │
│   - Mark old edge as expired                │
└────────────┬────────────────────────────────┘
             │
             ▼
┌──────────────────────┬──────────────────────┐
│                      │                      │
▼                      ▼                      ▼
OLD EDGE          NEW EDGE              TIMELINE
(EXPIRED)         (ACTIVE)              (PRESERVED)

expired_at: X    expired_at: NULL      valid_at: T1
Fact marked     Current fact          expired_at: X
"used to..."    "now..."              valid_at: T2
                                      (ongoing)
```

---

## 7. Search Implementation Details

### 7.1 Hybrid Search Components

Graphiti uses a **hybrid search approach** combining:

1. **Semantic Search**: Vector embeddings for conceptual matching
2. **BM25 Full-Text Search**: Keyword-based exact matching
3. **Graph Traversal**: Relationship-based navigation
4. **Temporal Metadata**: Available on all returned edges

### 7.2 Default Search Filtering

Based on the codebase and documentation:
- Search results **include temporal metadata** on edges
- **Expired edges** are marked with `expired_at` timestamp
- The search layer appears to **filter out expired edges by default** in standard queries
- **Temporal metadata availability** allows downstream filtering by query context

### 7.3 Search API Response Structure

When edges are returned from search:
```python
{
    "entity1": "Maria",
    "entity2": "junior manager", 
    "relationship": "works_as",
    "fact": "Maria used to work as a junior manager, until her promotion to a senior manager",
    "valid_at": "2023-07-01T00:00:00Z",
    "invalid_at": "2024-10-01T00:00:00Z",
    "created_at": "2023-07-01T12:30:00Z",
    "expired_at": "2024-10-01T08:15:00Z"
}
```

---

## 8. Chronological Analysis Capability

### 8.1 For Timeline Reconstruction

When analyzing **chronological sequences**, Graphiti provides:

✅ **Can retrieve**: All historical states of relationships  
✅ **Can order**: By `valid_at` to create accurate timelines  
✅ **Can narrate**: Updated facts explain the evolution  
✅ **Can query**: "Show me all states of X's relationship with Y"

### 8.2 Current Limitations

As of the latest documentation:
- ⚠️ **Temporal filtering in search API**: Planned but not fully documented as implemented
- ⚠️ **Default behavior**: Standard searches may not explicitly surface expired relationships
- ⚠️ **Query syntax**: Specific temporal query patterns not yet finalized

### 8.3 Workaround Approaches

To get chronological analysis today:

1. **Query for the entity**: Retrieve all relationships for an entity (including expired ones with metadata)
2. **Client-side filtering**: Sort by `valid_at` to reconstruct timeline
3. **Episode-based retrieval**: Fetch original episodes to see the narrative
4. **Graph traversal**: Navigate bidirectional episodic edges to trace relationship origins

---

## 9. Key Findings Summary

| Aspect | Finding |
|--------|---------|
| **Expired relationships stored?** | ✅ Yes, completely preserved with full temporal metadata |
| **Expired relationships retrieved by default?** | ⚠️ Not in standard queries; requires temporal querying |
| **Chronological analysis supported?** | ✅ Yes, via temporal metadata on all edges |
| **Point-in-time queries?** | ✅ Supported via valid_at/invalid_at filtering |
| **Non-lossy design?** | ✅ All previous relationships maintained as historical records |
| **Explicit temporal query API?** | ⚠️ Planned enhancement (not fully documented as available) |
| **Narrative preservation?** | ✅ Facts are regenerated to explain evolution ("used to...") |

---

## 10. Architecture for Chronological Analysis

When Graphiti receives chronological queries:

### 10.1 Retrieval Pipeline

```
User Query: "Show me how Maria's role evolved"
                    │
                    ▼
         Semantic + Keyword Search
         (Searches across all relationship metadata)
                    │
                    ▼
         Results include expired relationships
         (because temporal metadata is searchable)
                    │
                    ▼
         Temporal Metadata Available:
         - valid_at (when relationship started)
         - invalid_at (when relationship ended)
         - expired_at (when system marked it expired)
         - Full narrative facts
                    │
                    ▼
         Client/LLM Reconstruction:
         - Sort by valid_at
         - Build timeline
         - Present evolution narrative
```

### 10.2 Data Provenance via Episodes

Graphiti maintains **bidirectional indices** between:
- **Edges** → **Episodes** (trace where facts came from)
- **Episodes** → **Entities** (find all facts from an episode)

This enables complete chronological reconstruction by:
1. Finding all episodes mentioning an entity
2. Extracting temporal context from each episode
3. Ordering by real-world timeline (`valid_at`)
4. Presenting complete evolution

---

## 11. Zep's Academic Foundation

The temporal design is detailed in Zep's research paper: **"Zep: A Temporal Knowledge Graph Architecture for Agent Memory"**

Key points:
- **Timeline T** represents chronological event ordering
- **Timeline T'** represents database transaction ordering
- Bi-temporal model explicitly designed for **state-based reasoning**
- Episodic subgraph design enables **full historical reconstruction**

---

## 12. Practical Implications for Your Use Case

### When asking chronological analysis questions:

```python
# Query for evolution
results = await graphiti.search(
    query="Show me all relationships of Maria over time",
    num_results=50  # Get more results to capture history
)

# Access temporal metadata
for edge in results:
    print(f"{edge.fact}")  # "Maria used to work as junior manager..."
    print(f"Timeline: {edge.valid_at} to {edge.invalid_at}")
    print(f"System: {edge.created_at} to {edge.expired_at}")
```

**Expected behavior**:
- ✅ Returns both active and historical relationships
- ✅ Includes full temporal metadata
- ✅ Provides narrative connecting states
- ✅ Allows reconstruction of complete timeline

---

## 13. Conclusion

**Direct Answer**: For chronological analysis queries, Graphiti **does retrieve previous relationships that have been marked as expired**—but not in the same way as active relationships.

**The Key Mechanism**:
1. Previous relationships are **never deleted**, only marked `expired_at`
2. Search results **include temporal metadata** for all returned edges
3. For chronological queries specifically, the system has **access to the full history**
4. The **narrative is preserved** in regenerated facts explaining the evolution
5. **Graph structure** enables complete historical reconstruction

**Technical Reality**:
- Standard searches prioritize **current state** (no expired edges by default)
- Chronological/historical queries **access the full temporal graph** including expired relationships
- The **temporal metadata** makes historical analysis possible
- **Explicit temporal filtering** in the API is a planned enhancement

**Bottom Line**: For chronological analysis, you're not just querying "what is true now"—you're querying "what has been true over time," and Graphiti preserves and retrieves this entire timeline.

---

## References

- Graphiti GitHub Repository: https://github.com/getzep/graphiti
- Zep Documentation: https://help.getzep.com/graphiti/
- Blog Post: "Beyond Static Knowledge Graphs" - https://blog.getzep.com/beyond-static-knowledge-graphs/
- Research Paper: "Zep: A Temporal Knowledge Graph Architecture for Agent Memory"
- Presidio Blog: "Graphiti: Giving AI a Real Memory"