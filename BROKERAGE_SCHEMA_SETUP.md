# Brokerage Schema Setup Guide

## Overview

Your database now uses a **`brokerage`** schema to organize all tables related to the voice agent. This keeps your database structure clean and scalable.

## ✅ What Was Created

A new migration file: `migrations/brokerage_schema.sql`

This creates:
- `brokerage.customers` - Customer profiles
- `brokerage.conversations` - Call transcripts with summaries
- `brokerage.embeddings` - Vector embeddings for semantic search
- `brokerage.customer_memory` - Cross-session memory storage

All with proper indexes and vector search capabilities.

## 🚀 Step 1: Run the Migration

### In Supabase Dashboard:

1. Go to **SQL Editor**
2. Open file: `migrations/brokerage_schema.sql`
3. Copy all the SQL code
4. Paste into Supabase SQL Editor
5. Click **Run** (or Cmd+Enter)

Wait for completion. You should see:
```
✅ Created schema brokerage
✅ Created table customers
✅ Created table conversations
✅ Created table embeddings
✅ Created table customer_memory
✅ Created indexes
```

### Verify Creation:

Run this query in Supabase SQL Editor:
```sql
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'brokerage'
ORDER BY table_name;
```

You should see:
- conversations
- customer_memory
- customers
- embeddings

## 🔧 Step 2: Configure Your Application

Make sure your `.env` file has:

```bash
# Your existing configs...
SUPABASE_URL=postgresql://...
SUPABASE_KEY=...

# NEW: Specify the schema (default is "brokerage")
DB_SCHEMA=brokerage

# Your OpenRouter config
OPENROUTER_API_KEY=your_key_here

# Other existing configs...
```

**Note:** If you don't set `DB_SCHEMA`, it defaults to `brokerage` automatically.

## 🔄 Step 3: Test the Connection

Run this Python script to verify:

```python
from app.db import get_db

db = get_db()
result = db.execute("SELECT 1 as test")
print("✅ Connection successful!")
print(result)
```

## 📊 Tables Overview

### `brokerage.customers`
```
id (UUID)                 - Primary key
phone_number (TEXT)       - Unique phone number
company_name (TEXT)       - Company/business name
industry (TEXT)           - Business industry
location (TEXT)           - Geographic location
created_at (TIMESTAMP)    - Record creation time
updated_at (TIMESTAMP)    - Last update time
```

### `brokerage.conversations`
```
id (UUID)                    - Primary key
call_id (TEXT)               - Unique VAPI call ID
customer_id (UUID)           - Reference to customer
transcript (TEXT)            - Full call transcript
summary (TEXT)               - AI-generated summary
summary_embedding (vector)   - 1024-dim embedding of summary
created_at (TIMESTAMP)       - Call creation time
```

### `brokerage.embeddings`
```
call_id (TEXT)               - Reference to conversation
embedding (vector(1024))     - Vector embedding
embedding_type (TEXT)        - Type: 'full', 'summary', etc.
created_at (TIMESTAMP)       - Creation time
PRIMARY KEY: (call_id, embedding_type)
```

### `brokerage.customer_memory`
```
id (UUID)                    - Primary key
customer_id (UUID)           - Reference to customer
call_id (TEXT)               - Reference to conversation
memory_type (TEXT)           - Type: 'objection', 'commitment', etc.
content (TEXT)               - Memory content
created_at (TIMESTAMP)       - Creation time
```

## 🎯 How It Works

1. **Call Ends** → Webhook received
2. **Transcript Stored** → Saved to `conversations` table
3. **Summary Generated** → OpenRouter API (GPT-4 Nano) creates summary
4. **Embeddings Created** → Both transcript and summary get embeddings
5. **Data Stored** → Summary + summary_embedding saved to `conversations`
6. **Transcript Embedding** → Stored in `embeddings` table

## 🔍 Example Query

Get recent calls with summaries:

```sql
SELECT 
    c.call_id,
    cu.company_name,
    c.transcript,
    c.summary,
    c.created_at
FROM brokerage.conversations c
JOIN brokerage.customers cu ON c.customer_id = cu.id
ORDER BY c.created_at DESC
LIMIT 10;
```

Find similar conversations using embeddings:

```sql
SELECT 
    c.call_id,
    cu.company_name,
    1 - (c.summary_embedding <=> '[0.1, 0.2, ...]'::vector) as similarity
FROM brokerage.conversations c
JOIN brokerage.customers cu ON c.customer_id = cu.id
ORDER BY c.summary_embedding <=> '[0.1, 0.2, ...]'::vector
LIMIT 5;
```

## ⚠️ Troubleshooting

### "Schema brokerage does not exist"
- Run the migration SQL again
- Make sure you ran ALL the SQL code

### "Column summary does not exist"
- The `summary_embedding` column needs to be added (see Step 1)
- Run the ALTER TABLE commands from `SUPABASE_MIGRATION.md`

### "Permission denied for schema brokerage"
- The user role might not have permissions
- In Supabase, go to Database → Users and add permissions to your user

## 📝 Next Steps

1. ✅ Run the migration SQL
2. ✅ Update `.env` with `DB_SCHEMA=brokerage`
3. ✅ Test connection
4. ✅ Make a test call to populate data
5. ✅ Verify data appears in `brokerage.conversations`

Happy calling! 🎉
