-- Create course_videos table for storing video metadata

CREATE TABLE IF NOT EXISTS course_videos (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    video_id UUID NOT NULL UNIQUE,
    course_id UUID NOT NULL,
    module_id UUID NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    storage_filename VARCHAR(255) NOT NULL,
    storage_path TEXT NOT NULL,
    file_size BIGINT NOT NULL,
    mime_type VARCHAR(100) NOT NULL,
    video_url TEXT NOT NULL,
    title VARCHAR(255),
    description TEXT,
    status VARCHAR(50) DEFAULT 'uploaded', -- uploaded, processing, ready, error
    duration INTEGER, -- Duration in seconds
    thumbnail_url TEXT,
    uploaded_by UUID NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE,
    FOREIGN KEY (module_id) REFERENCES course_modules(id) ON DELETE CASCADE,
    FOREIGN KEY (uploaded_by) REFERENCES users(id) ON DELETE SET NULL,
    
    CONSTRAINT valid_file_size CHECK (file_size > 0 AND file_size <= 536870912), -- Max 500MB
    CONSTRAINT valid_mime_type CHECK (mime_type LIKE 'video/%')
);

-- Create indexes for faster queries
CREATE INDEX IF NOT EXISTS idx_course_videos_course_id ON course_videos(course_id);
CREATE INDEX IF NOT EXISTS idx_course_videos_module_id ON course_videos(module_id);
CREATE INDEX IF NOT EXISTS idx_course_videos_uploaded_by ON course_videos(uploaded_by);
CREATE INDEX IF NOT EXISTS idx_course_videos_status ON course_videos(status);
CREATE INDEX IF NOT EXISTS idx_course_videos_created_at ON course_videos(created_at DESC);

-- Create trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_course_videos_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS course_videos_update_timestamp ON course_videos;
CREATE TRIGGER course_videos_update_timestamp
BEFORE UPDATE ON course_videos
FOR EACH ROW
EXECUTE FUNCTION update_course_videos_timestamp();

-- Enable RLS (Row Level Security)
ALTER TABLE course_videos ENABLE ROW LEVEL SECURITY;

-- RLS Policy: Users can see videos from courses they're enrolled in or taught
CREATE POLICY course_videos_select_policy ON course_videos
FOR SELECT USING (
    -- User is the uploader
    uploaded_by = auth.uid()
    OR
    -- User is the course instructor
    course_id IN (SELECT id FROM courses WHERE instructor_id = auth.uid())
    OR
    -- User is enrolled in the course
    course_id IN (SELECT course_id FROM enrollments WHERE user_id = auth.uid())
    OR
    -- User is admin
    (SELECT role FROM users WHERE id = auth.uid()) = 'admin'
);

-- RLS Policy: Only instructors and admins can upload/delete videos
CREATE POLICY course_videos_insert_policy ON course_videos
FOR INSERT WITH CHECK (
    -- User is the course instructor
    course_id IN (SELECT id FROM courses WHERE instructor_id = auth.uid())
    OR
    -- User is admin
    (SELECT role FROM users WHERE id = auth.uid()) = 'admin'
);

CREATE POLICY course_videos_delete_policy ON course_videos
FOR DELETE USING (
    -- User uploaded the video
    uploaded_by = auth.uid()
    OR
    -- User is admin
    (SELECT role FROM users WHERE id = auth.uid()) = 'admin'
);

CREATE POLICY course_videos_update_policy ON course_videos
FOR UPDATE USING (
    -- User uploaded the video
    uploaded_by = auth.uid()
    OR
    -- User is admin
    (SELECT role FROM users WHERE id = auth.uid()) = 'admin'
);
