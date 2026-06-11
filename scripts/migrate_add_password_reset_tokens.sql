-- Migration: Add password_reset_tokens table
-- Run this migration on the production database

-- Create password reset tokens table
CREATE TABLE IF NOT EXISTS password_reset_tokens (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL,
    token VARCHAR(255) NOT NULL UNIQUE,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes for faster lookups
CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_email 
ON password_reset_tokens(email);

CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_token 
ON password_reset_tokens(token);

CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_expires 
ON password_reset_tokens(expires_at);

-- Add a cleanup function to remove expired tokens (optional)
-- This can be run periodically via a cron job or database scheduler
CREATE OR REPLACE FUNCTION cleanup_expired_password_reset_tokens()
RETURNS void AS $$
BEGIN
    DELETE FROM password_reset_tokens WHERE expires_at < NOW();
END;
$$ LANGUAGE plpgsql;

-- Comment for documentation
COMMENT ON TABLE password_reset_tokens IS 'Stores temporary tokens for password reset functionality';
COMMENT ON COLUMN password_reset_tokens.email IS 'Email of the user requesting password reset';
COMMENT ON COLUMN password_reset_tokens.token IS 'Secure random token sent to user email';
COMMENT ON COLUMN password_reset_tokens.expires_at IS 'Token expiration time (1 hour from creation)';
