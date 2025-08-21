-- Supabase Database Setup Script
-- Run this in your Supabase SQL Editor to create the required tables

-- Applications table
CREATE TABLE IF NOT EXISTS applications (
    id BIGSERIAL PRIMARY KEY,
    session_id TEXT NOT NULL,
    job_id TEXT NOT NULL,
    job_title TEXT,
    company_name TEXT,
    job_url TEXT,
    application_status TEXT,
    application_timestamp TIMESTAMPTZ,
    resume_path TEXT,
    cover_letter_preview TEXT,
    job_data JSONB,
    skill_analysis JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Skills tracking table
CREATE TABLE IF NOT EXISTS skills_tracking (
    id BIGSERIAL PRIMARY KEY,
    skill_name TEXT NOT NULL UNIQUE,
    job_count INTEGER DEFAULT 1,
    first_seen TIMESTAMPTZ DEFAULT NOW(),
    last_seen TIMESTAMPTZ DEFAULT NOW()
);

-- Workflow sessions table
CREATE TABLE IF NOT EXISTS workflow_sessions (
    id BIGSERIAL PRIMARY KEY,
    session_id TEXT UNIQUE NOT NULL,
    start_time TIMESTAMPTZ,
    end_time TIMESTAMPTZ,
    status TEXT,
    input_parameters JSONB,
    final_results JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_applications_session_id ON applications(session_id);
CREATE INDEX IF NOT EXISTS idx_applications_created_at ON applications(created_at);
CREATE INDEX IF NOT EXISTS idx_applications_job_id ON applications(job_id);
CREATE INDEX IF NOT EXISTS idx_applications_company_name ON applications(company_name);

CREATE INDEX IF NOT EXISTS idx_skills_tracking_job_count ON skills_tracking(job_count);
CREATE INDEX IF NOT EXISTS idx_skills_tracking_last_seen ON skills_tracking(last_seen);

CREATE INDEX IF NOT EXISTS idx_workflow_sessions_session_id ON workflow_sessions(session_id);
CREATE INDEX IF NOT EXISTS idx_workflow_sessions_status ON workflow_sessions(status);

-- Grant necessary permissions
GRANT ALL ON applications TO anon, authenticated;
GRANT ALL ON skills_tracking TO anon, authenticated;
GRANT ALL ON workflow_sessions TO anon, authenticated;

-- Grant usage on sequences
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO anon, authenticated;

-- IMPORTANT: Disable Row Level Security for this application
-- This allows the application to work without authentication
ALTER TABLE applications DISABLE ROW LEVEL SECURITY;
ALTER TABLE skills_tracking DISABLE ROW LEVEL SECURITY;
ALTER TABLE workflow_sessions DISABLE ROW LEVEL SECURITY;

-- Alternative: If you want to keep RLS enabled, create permissive policies
-- Uncomment the lines below and comment out the DISABLE RLS lines above

-- ALTER TABLE applications ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE skills_tracking ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE workflow_sessions ENABLE ROW LEVEL SECURITY;

-- Create permissive policies for the application to work
-- CREATE POLICY "Allow all operations on applications" ON applications
--     FOR ALL USING (true) WITH CHECK (true);

-- CREATE POLICY "Allow all operations on skills_tracking" ON skills_tracking
--     FOR ALL USING (true) WITH CHECK (true);

-- CREATE POLICY "Allow all operations on workflow_sessions" ON workflow_sessions
--     FOR ALL USING (true) WITH CHECK (true);

-- Insert some sample data for testing (optional)
-- INSERT INTO skills_tracking (skill_name, job_count) VALUES 
--     ('Python', 10),
--     ('JavaScript', 8),
--     ('React', 6),
--     ('SQL', 5),
--     ('AWS', 4)
-- ON CONFLICT (skill_name) DO NOTHING;
