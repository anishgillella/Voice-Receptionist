# Task MCP Enrichment Module

Integrate the **Task MCP (Parallel API)** for powerful parallel data enrichment and deep research capabilities. This module enables your application to enrich customer data, perform batch research, and extract intelligent insights at scale.

## Overview

The Task MCP provides:

- **Parallel Enrichment**: Enrich multiple items simultaneously using task groups
- **Deep Research**: Perform comprehensive research on any topic
- **Async Architecture**: Non-blocking operations with optional polling
- **Scalable Processing**: Handle large datasets through intelligent batching
- **Flexible Configuration**: Customize timeouts, batch sizes, and retry behavior

## Quick Start

### 1. Setup Environment

Add to your `.env` file:

```env
# Required
PARALLEL_API_KEY=your_parallel_api_key_here

# Optional (with defaults)
PARALLEL_API_BASE_URL=https://api.parallel.com
TASK_TIMEOUT_SECONDS=300
MAX_PARALLEL_TASKS=10
MAX_BATCH_SIZE=50
RETRY_ATTEMPTS=3
RETRY_DELAY_SECONDS=2
```

### 2. Install Dependencies

The enrichment module uses `httpx` for async HTTP requests (already in requirements.txt).

### 3. Basic Usage

```python
from enrichment import TaskManager, EnrichmentItem

async def enrich_customers():
    # Create items to enrich
    items = [
        EnrichmentItem(
            id="cust_001",
            data={"company_name": "TechCorp Inc", "location": "SF, CA"}
        ),
        EnrichmentItem(
            id="cust_002",
            data={"company_name": "StartupX", "location": "NYC, NY"}
        ),
    ]
    
    # Define what enrichment to perform
    prompt = """
    For each company, find:
    - Employee count
    - Annual revenue
    - Industry
    - Recent funding
    """
    
    # Enrich in parallel
    manager = TaskManager()
    try:
        responses = await manager.enrich_items_parallel(
            items=items,
            enrichment_prompt=prompt,
            poll=True,  # Wait for completion
        )
        
        # Get results
        results = await manager.get_results(responses[0].task_group_id)
        print(f"Enriched {results.completed_count} items")
        
    finally:
        await manager.close()

# Run it
import asyncio
asyncio.run(enrich_customers())
```

## Core Components

### TaskManager

High-level orchestration for enrichment tasks. Main methods:

```python
# Parallel enrichment
responses = await manager.enrich_items_parallel(
    items=[...],
    enrichment_prompt="...",
    batch_size=50,  # Optional
    poll=False,     # Wait for completion?
)

# Deep research
response = await manager.deep_research(
    query="AI trends in 2024",
    description="Optional detailed description"
)

# Get results (for completed tasks)
results = await manager.get_results(task_id)

# Process with callbacks
await manager.process_results_callback(
    task_id=task_id,
    callback=lambda r: print(r.enriched_data),
    error_callback=lambda r: print(r.error)
)

# Cancel task
await manager.cancel_task(task_id)

# Check active tasks
active_tasks = manager.get_active_tasks()
```

### TaskMCPClient

Low-level API client for direct Parallel API calls:

```python
from enrichment.client import TaskMCPClient

async with TaskMCPClient() as client:
    # Create task group
    response = await client.create_task_group(request)
    
    # Create deep research
    response = await client.create_deep_research_task(request)
    
    # Get results
    results = await client.get_result(task_id)
    
    # Check status
    status = await client.get_task_status(task_id)
    
    # Cancel
    await client.cancel_task(task_id)
```

### Models

All data models are in `models.py`:

- `EnrichmentItem`: Single item to be enriched
- `TaskGroupRequest`: Request to enrich multiple items
- `DeepResearchRequest`: Research query request
- `TaskResult`: Result for a single item
- `TaskStatus`: Status enum (pending, in_progress, completed, failed, cancelled)

## Usage Patterns

### Pattern 1: Fire-and-Forget (Async)

Start enrichment and handle results later:

```python
# Start task without waiting
responses = await manager.enrich_items_parallel(
    items=customers,
    enrichment_prompt="Find company revenue",
    poll=False  # Don't wait
)

# Store task IDs for later
task_ids = [r.task_group_id for r in responses]

# ... do other work ...

# Later, retrieve results
results = await manager.get_results(task_ids[0])
```

### Pattern 2: Synchronous Wait

Enrich and wait for completion:

```python
responses = await manager.enrich_items_parallel(
    items=customers,
    enrichment_prompt="Find company info",
    poll=True,  # Wait for completion
    poll_timeout_seconds=300  # 5 minutes max
)

# Results are ready immediately
results = await manager.get_results(responses[0].task_group_id)
```

### Pattern 3: Batch Processing

Process large datasets in batches:

```python
# Get customers from database
all_customers = await db.get_all_customers()  # 1000 items

# Split and enrich in batches
responses = await manager.enrich_items_parallel(
    items=all_customers,
    enrichment_prompt="Identify upsell opportunities",
    batch_size=50  # 20 batches
)

# Process results batch by batch
for response in responses:
    results = await manager.get_results(response.task_group_id)
    await store_enriched_data(results)
```

### Pattern 4: Deep Research

Research topics in parallel with enrichment:

```python
# Parallel enrichment task
task1 = await manager.enrich_items_parallel(
    items=leads,
    enrichment_prompt="Find industry info"
)

# Parallel research task
task2 = await manager.deep_research(
    query="Latest trends in SaaS market"
)

# Wait for both
results_enrich = await manager.get_results(task1[0].task_group_id)
results_research = await manager.get_results(task2.task_id)

# Combine insights
insights = combine_results(results_enrich, results_research)
```

### Pattern 5: Result Processing with Callbacks

Process results as they complete:

```python
async def on_success(result):
    """Save enriched data."""
    await db.update_customer(
        customer_id=result.item_id,
        enriched_data=result.enriched_data
    )

async def on_error(result):
    """Log failed enrichments."""
    logger.error(f"Failed to enrich {result.item_id}: {result.error}")

await manager.process_results_callback(
    task_id=task_group_id,
    callback=on_success,
    error_callback=on_error
)
```

## Integration with Your App

### In FastAPI

```python
from fastapi import FastAPI
from enrichment import TaskManager, EnrichmentItem

app = FastAPI()

@app.post("/enrich")
async def trigger_enrichment(customer_ids: List[str]):
    """Trigger customer enrichment."""
    
    # Get customers
    customers = await db.get_customers(customer_ids)
    
    # Create enrichment items
    items = [
        EnrichmentItem(id=c.id, data=c.dict())
        for c in customers
    ]
    
    # Start enrichment
    manager = TaskManager()
    try:
        responses = await manager.enrich_items_parallel(
            items=items,
            enrichment_prompt="Find company size and industry",
        )
        
        return {
            "status": "enrichment_started",
            "task_ids": [r.task_group_id for r in responses],
        }
    finally:
        await manager.close()

@app.get("/enrich-results/{task_id}")
async def get_enrichment_results(task_id: str):
    """Get enrichment results."""
    
    manager = TaskManager()
    try:
        results = await manager.get_results(task_id)
        return {
            "task_id": task_id,
            "completed": results.completed_count,
            "failed": results.failed_count,
            "results": results.results,
        }
    finally:
        await manager.close()
```

### In Background Tasks

```python
import asyncio
from celery import shared_task

@shared_task
def enrich_customers_task(customer_ids):
    """Background task for customer enrichment."""
    
    async def run():
        manager = TaskManager()
        try:
            # Create items
            items = [
                EnrichmentItem(id=cid, data={"id": cid})
                for cid in customer_ids
            ]
            
            # Enrich with polling
            responses = await manager.enrich_items_parallel(
                items=items,
                enrichment_prompt="...",
                poll=True,
                poll_timeout_seconds=600,
            )
            
            # Store results
            for response in responses:
                results = await manager.get_results(response.task_group_id)
                await store_results(results)
                
        finally:
            await manager.close()
    
    asyncio.run(run())
```

## Configuration

All settings are loaded from environment variables via `EnrichmentSettings`:

```python
from enrichment.config import get_enrichment_settings

settings = get_enrichment_settings()
print(settings.parallel_api_key)
print(settings.max_batch_size)
print(settings.task_timeout_seconds)
```

See `config.py` for all available settings.

## Error Handling

```python
from enrichment.models import TaskStatus

results = await manager.get_results(task_id)

for result in results.results:
    if result.status == TaskStatus.COMPLETED:
        print(f"✓ {result.item_id}: {result.enriched_data}")
    elif result.status == TaskStatus.FAILED:
        print(f"✗ {result.item_id}: {result.error}")
    else:
        print(f"? {result.item_id}: {result.status}")
```

## Best Practices

1. **Always use context managers or call `close()`**:
   ```python
   async with TaskManager() as manager:
       # Use manager
   # Or
   manager = TaskManager()
   try:
       # Use manager
   finally:
       await manager.close()
   ```

2. **Set appropriate timeouts**:
   ```python
   # For quick tasks
   poll_timeout_seconds=60
   
   # For comprehensive research
   poll_timeout_seconds=600
   ```

3. **Batch large datasets**:
   ```python
   # Good: 50-100 items per batch
   batch_size=50
   
   # Avoid: Context window overflow
   batch_size=1000  # Too large
   ```

4. **Handle async operations properly**:
   ```python
   # Fire multiple tasks in parallel
   tasks = [
       manager.enrich_items_parallel(items1, prompt1),
       manager.enrich_items_parallel(items2, prompt2),
   ]
   responses = await asyncio.gather(*tasks)
   ```

5. **Store task IDs for tracking**:
   ```python
   # Save for status checks and result retrieval
   await db.save_enrichment_job(
       task_id=response.task_group_id,
       status="pending",
       created_at=datetime.now(),
   )
   ```

## Examples

See `examples.py` for 7 complete usage examples:

1. Basic parallel customer enrichment
2. Enrichment with polling
3. Deep research
4. Batch processing with callbacks
5. Multi-step enrichment workflow
6. Database integration
7. Task management and monitoring

Run examples:
```python
python -m enrichment.examples
```

## Troubleshooting

### "PARALLEL_API_KEY not found"
- Ensure `PARALLEL_API_KEY` is set in `.env` file
- Verify the file is in the project root or referenced path
- Check file permissions

### Task timeout errors
- Increase `TASK_TIMEOUT_SECONDS` for complex enrichments
- Consider smaller `MAX_BATCH_SIZE`
- Check network connectivity

### "Failed to get results"
- Task may still be processing - wait and retry
- Check task status with `get_task_status()`
- Verify task ID is correct

### High memory usage
- Reduce `MAX_BATCH_SIZE`
- Use fire-and-forget mode instead of polling
- Process results in streaming fashion

## Performance Tuning

```python
# For speed (smaller batches, faster feedback)
manager = TaskManager(EnrichmentSettings(
    max_batch_size=10,
    task_poll_interval_seconds=2,
))

# For efficiency (larger batches, fewer API calls)
manager = TaskManager(EnrichmentSettings(
    max_batch_size=100,
    task_poll_interval_seconds=10,
))

# For reliability (more retries, longer timeouts)
manager = TaskManager(EnrichmentSettings(
    retry_attempts=5,
    task_timeout_seconds=600,
))
```

## API Reference

See docstrings in:
- `manager.py` - TaskManager class
- `client.py` - TaskMCPClient class
- `models.py` - Data models

## Support

For issues or questions:
1. Check examples in `examples.py`
2. Review docstrings in source files
3. Check Parallel API documentation
4. Enable debug logging: `LOG_LEVEL=DEBUG`
