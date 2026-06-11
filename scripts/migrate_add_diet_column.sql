-- Migration: Add diet column to users table
-- Run this on existing databases to add the diet column

-- Add diet column if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'users' AND column_name = 'diet'
    ) THEN
        ALTER TABLE users ADD COLUMN diet VARCHAR(50);
        RAISE NOTICE 'Added diet column to users table';
    ELSE
        RAISE NOTICE 'diet column already exists in users table';
    END IF;
END $$;