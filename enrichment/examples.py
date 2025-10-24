"""Examples demonstrating Task MCP integration for data enrichment."""

import asyncio
import logging
from typing import List

from .models import EnrichmentItem, TaskStatus
from .manager import TaskManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# Example 1: Parallel Customer Enrichment
# ============================================================================

async def example_customer_enrichment():
    """Enrich customer data in parallel (company info, industry, location)."""
    
    # Create items to enrich
    customers = [
        EnrichmentItem(
            id="cust_001",
            data={"company_name": "Acme Corp", "location": "San Francisco, CA"},
        ),
        EnrichmentItem(
            id="cust_002",
            data={"company_name": "TechStart Inc", "location": "New York, NY"},
        ),
        EnrichmentItem(
            id="cust_003",
            data={"company_name": "Global Solutions Ltd", "location": "London, UK"},
        ),
    ]
    
    # Define enrichment prompt
    enrichment_prompt = """
    For each company, enrich with:
    - Employee count estimate
    - Annual revenue estimate
    - Primary industry/sector
    - Key executives (CEO, CTO if available)
    - Recent funding or major news
    """
    
    # Create manager and enrich items
    manager = TaskManager()
    try:
        # Fire-and-forget style
        responses = await manager.enrich_items_parallel(
            items=customers,
            enrichment_prompt=enrichment_prompt,
            task_name="customer_enrichment_batch",
        )
        
        logger.info(f"Created {len(responses)} enrichment task(s)")
        for response in responses:
            logger.info(f"Task ID: {response.task_group_id}")
            logger.info(f"Progress: {response.progress_url}")
        
        # Note: In real usage, you'd poll later for results
        # results = await manager.get_results(responses[0].task_group_id)
        
    finally:
        await manager.close()


# ============================================================================
# Example 2: Parallel with Polling
# ============================================================================

async def example_customer_enrichment_with_polling():
    """Enrich customers and wait for results."""
    
    customers = [
        EnrichmentItem(
            id="prospect_001",
            data={
                "company_name": "Innovation Labs",
                "industry": "Software",
            },
        ),
    ]
    
    enrichment_prompt = "Find company size, valuation, and funding stage"
    
    manager = TaskManager()
    try:
        # Wait for completion
        responses = await manager.enrich_items_parallel(
            items=customers,
            enrichment_prompt=enrichment_prompt,
            poll=True,  # Wait for completion
            poll_timeout_seconds=60,
        )
        
        logger.info("✓ All enrichment tasks completed")
        
        # Get detailed results
        results = await manager.get_results(responses[0].task_group_id)
        
        logger.info(f"Completed: {results.completed_count}, Failed: {results.failed_count}")
        
        for result in results.results:
            logger.info(f"Item {result.item_id}: {result.status}")
            if result.enriched_data:
                logger.info(f"Enriched data: {result.enriched_data}")
    
    finally:
        await manager.close()


# ============================================================================
# Example 3: Deep Research
# ============================================================================

async def example_deep_research():
    """Perform deep research on a topic."""
    
    manager = TaskManager()
    try:
        # Start deep research
        response = await manager.deep_research(
            query="Latest AI trends in enterprise software",
            description="Research recent developments in AI adoption in enterprise software, "
                        "including LLM integration, cost implications, and ROI metrics",
            poll=False,  # Don't wait
        )
        
        logger.info(f"Deep research task created: {response.task_id}")
        logger.info(f"Track progress at: {response.progress_url}")
        
        # Later, retrieve results:
        # results = await manager.get_results(response.task_id)
        
    finally:
        await manager.close()


# ============================================================================
# Example 4: Batch Processing with Callbacks
# ============================================================================

async def example_batch_with_callbacks():
    """Process enrichment results with callbacks."""
    
    def on_success(result):
        """Handle successful enrichment."""
        logger.info(f"✓ Successfully enriched {result.item_id}")
        if result.enriched_data:
            logger.info(f"  Data: {result.enriched_data}")
    
    def on_error(result):
        """Handle failed enrichment."""
        logger.error(f"✗ Failed to enrich {result.item_id}: {result.error}")
    
    items = [
        EnrichmentItem(
            id=f"company_{i}",
            data={"name": f"Company {i}", "website": f"https://company{i}.com"},
        )
        for i in range(5)
    ]
    
    manager = TaskManager()
    try:
        # Create enrichment tasks
        responses = await manager.enrich_items_parallel(
            items=items,
            enrichment_prompt="Extract company information from website",
            batch_size=2,  # 2 items per batch
        )
        
        logger.info(f"Created {len(responses)} task(s), processing results...")
        
        # Process each batch's results
        for response in responses:
            await manager.process_results_callback(
                task_id=response.task_group_id,
                callback=on_success,
                error_callback=on_error,
            )
    
    finally:
        await manager.close()


# ============================================================================
# Example 5: Multiple Enrichment Types in Sequence
# ============================================================================

async def example_multi_step_enrichment():
    """Perform multiple enrichment steps in sequence."""
    
    # Step 1: Basic company enrichment
    logger.info("Step 1: Starting basic company enrichment...")
    
    companies = [
        EnrichmentItem(
            id="techcorp",
            data={"name": "TechCorp", "founded": "2015"},
        ),
        EnrichmentItem(
            id="startup_x",
            data={"name": "Startup X", "founded": "2023"},
        ),
    ]
    
    manager = TaskManager()
    try:
        response1 = await manager.enrich_items_parallel(
            items=companies,
            enrichment_prompt="Find funding rounds, investors, and current valuation",
            task_name="funding_enrichment",
        )
        
        logger.info(f"Created funding enrichment task: {response1[0].task_group_id}")
        
        # Step 2: Deep research on market trends (parallel to step 1)
        response2 = await manager.deep_research(
            query="Market trends in the software industry 2024-2025",
            description="Focus on AI adoption, spending patterns, and emerging opportunities",
        )
        
        logger.info(f"Created market research task: {response2.task_id}")
        
        # In real usage, you would:
        # 1. Wait for both tasks to complete
        # 2. Combine results for strategic insights
        # 3. Store enriched data in your database
        
    finally:
        await manager.close()


# ============================================================================
# Example 6: Integration with Database
# ============================================================================

async def example_with_database_storage():
    """Example showing how to store enriched data."""
    
    async def store_enriched_customer(result):
        """Store enriched data in your database."""
        logger.info(f"Storing enriched data for {result.item_id}")
        # In real implementation:
        # await db.update_customer(
        #     customer_id=result.item_id,
        #     enriched_data=result.enriched_data,
        # )
    
    items = [
        EnrichmentItem(id="cust_1", data={"name": "Customer 1"}),
        EnrichmentItem(id="cust_2", data={"name": "Customer 2"}),
    ]
    
    manager = TaskManager()
    try:
        responses = await manager.enrich_items_parallel(
            items=items,
            enrichment_prompt="Analyze customer profile and identify upsell opportunities",
        )
        
        # Process and store results
        for response in responses:
            await manager.process_results_callback(
                task_id=response.task_group_id,
                callback=store_enriched_customer,
            )
    
    finally:
        await manager.close()


# ============================================================================
# Example 7: Advanced Features - Task Management
# ============================================================================

async def example_task_management():
    """Show task monitoring and cancellation."""
    
    items = [
        EnrichmentItem(
            id=f"item_{i}",
            data={"value": f"data_{i}"},
        )
        for i in range(10)
    ]
    
    manager = TaskManager()
    try:
        # Start enrichment
        responses = await manager.enrich_items_parallel(
            items=items,
            enrichment_prompt="Perform comprehensive enrichment",
            batch_size=5,
        )
        
        # Monitor active tasks
        active = manager.get_active_tasks()
        logger.info(f"Active tasks: {len(active)}")
        for task_id, info in active.items():
            logger.info(f"  - {task_id}: {info['type']}")
        
        # Example: Cancel if needed
        if active:
            first_task_id = list(active.keys())[0]
            # await manager.cancel_task(first_task_id)
            # logger.info(f"Cancelled task: {first_task_id}")
    
    finally:
        await manager.close()


# ============================================================================
# Main entry point
# ============================================================================

async def main():
    """Run examples."""
    
    examples = [
        ("Customer Enrichment", example_customer_enrichment),
        ("Customer Enrichment with Polling", example_customer_enrichment_with_polling),
        ("Deep Research", example_deep_research),
        ("Batch with Callbacks", example_batch_with_callbacks),
        ("Multi-step Enrichment", example_multi_step_enrichment),
        ("Database Integration", example_with_database_storage),
        ("Task Management", example_task_management),
    ]
    
    print("\n" + "=" * 70)
    print("Task MCP Integration Examples")
    print("=" * 70 + "\n")
    
    for i, (name, example_func) in enumerate(examples, 1):
        print(f"{i}. {name}")
    
    print("\nNote: Make sure PARALLEL_API_KEY is set in your .env file")
    print("These examples demonstrate the API structure and usage patterns.")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
