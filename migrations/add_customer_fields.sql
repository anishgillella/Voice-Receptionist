-- Add missing columns to customers table in brokerage schema
ALTER TABLE brokerage.customers ADD COLUMN IF NOT EXISTS first_name TEXT;
ALTER TABLE brokerage.customers ADD COLUMN IF NOT EXISTS last_name TEXT;
ALTER TABLE brokerage.customers ADD COLUMN IF NOT EXISTS email TEXT;
