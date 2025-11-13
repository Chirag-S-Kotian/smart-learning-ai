-- Create video_watching table for tracking student video watching
CREATE TABLE IF NOT EXISTS video_watching (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    video_id UUID NOT NULL,
    course_id UUID NOT NULL,
    module_id UUID NOT NULL,
    watch_start_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    watch_end_time TIMESTAMP WITH TIME ZONE,
    duration_watched INTEGER DEFAULT 0,  -- in seconds
    total_video_duration INTEGER,  -- in seconds
    watch_percentage NUMERIC DEFAULT 0,  -- percentage watched (0-100)
    playback_speed NUMERIC DEFAULT 1.0,
    is_completed BOOLEAN DEFAULT false,
    completion_date TIMESTAMP WITH TIME ZONE,
    view_count INTEGER DEFAULT 0,  -- how many times viewed
    session_id VARCHAR(255),  -- to track individual watch sessions
    metadata JSONB DEFAULT '{}',  -- additional tracking data
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (video_id) REFERENCES course_videos(video_id) ON DELETE CASCADE,
    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE,
    FOREIGN KEY (module_id) REFERENCES course_modules(id) ON DELETE CASCADE
);

-- Create course_progress table for tracking overall course progress
CREATE TABLE IF NOT EXISTS course_progress (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    course_id UUID NOT NULL,
    enrollment_id UUID NOT NULL,
    total_modules INTEGER DEFAULT 0,
    completed_modules INTEGER DEFAULT 0,
    total_videos INTEGER DEFAULT 0,
    videos_watched INTEGER DEFAULT 0,
    total_assessments INTEGER DEFAULT 0,
    assessments_passed INTEGER DEFAULT 0,
    overall_completion_percentage NUMERIC DEFAULT 0,
    course_status VARCHAR(50) DEFAULT 'in_progress',  -- in_progress, completed, dropped
    time_spent INTEGER DEFAULT 0,  -- total time in seconds
    last_accessed TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completion_date TIMESTAMP WITH TIME ZONE,
    estimated_completion_date TIMESTAMP WITH TIME ZONE,
    current_module_id UUID,
    current_video_id UUID,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE,
    FOREIGN KEY (enrollment_id) REFERENCES enrollments(id) ON DELETE CASCADE,
    FOREIGN KEY (current_module_id) REFERENCES course_modules(id) ON DELETE SET NULL,
    FOREIGN KEY (current_video_id) REFERENCES course_videos(video_id) ON DELETE SET NULL,
    
    UNIQUE(user_id, course_id)
);

-- Create module_progress table for module-level tracking
CREATE TABLE IF NOT EXISTS module_progress (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    module_id UUID NOT NULL,
    course_id UUID NOT NULL,
    total_content_items INTEGER DEFAULT 0,
    completed_content_items INTEGER DEFAULT 0,
    total_videos INTEGER DEFAULT 0,
    videos_watched INTEGER DEFAULT 0,
    total_assessments INTEGER DEFAULT 0,
    assessments_passed INTEGER DEFAULT 0,
    module_completion_percentage NUMERIC DEFAULT 0,
    time_spent INTEGER DEFAULT 0,  -- total time in seconds
    last_accessed TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completion_date TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (module_id) REFERENCES course_modules(id) ON DELETE CASCADE,
    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE,
    
    UNIQUE(user_id, module_id)
);

-- Create indexes for faster queries
CREATE INDEX IF NOT EXISTS idx_video_watching_user_video ON video_watching(user_id, video_id);
CREATE INDEX IF NOT EXISTS idx_video_watching_course ON video_watching(course_id);
CREATE INDEX IF NOT EXISTS idx_video_watching_completed ON video_watching(is_completed);
CREATE INDEX IF NOT EXISTS idx_video_watching_created_at ON video_watching(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_course_progress_user_course ON course_progress(user_id, course_id);
CREATE INDEX IF NOT EXISTS idx_course_progress_status ON course_progress(course_status);
CREATE INDEX IF NOT EXISTS idx_module_progress_user_module ON module_progress(user_id, module_id);

-- Create trigger to update updated_at for video_watching
CREATE OR REPLACE FUNCTION update_video_watching_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS video_watching_update_timestamp ON video_watching;
CREATE TRIGGER video_watching_update_timestamp
BEFORE UPDATE ON video_watching
FOR EACH ROW
EXECUTE FUNCTION update_video_watching_timestamp();

-- Create trigger to update updated_at for course_progress
CREATE OR REPLACE FUNCTION update_course_progress_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS course_progress_update_timestamp ON course_progress;
CREATE TRIGGER course_progress_update_timestamp
BEFORE UPDATE ON course_progress
FOR EACH ROW
EXECUTE FUNCTION update_course_progress_timestamp();

-- Create trigger to update updated_at for module_progress
CREATE OR REPLACE FUNCTION update_module_progress_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS module_progress_update_timestamp ON module_progress;
CREATE TRIGGER module_progress_update_timestamp
BEFORE UPDATE ON module_progress
FOR EACH ROW
EXECUTE FUNCTION update_module_progress_timestamp();

-- Enable RLS
ALTER TABLE video_watching ENABLE ROW LEVEL SECURITY;
ALTER TABLE course_progress ENABLE ROW LEVEL SECURITY;
ALTER TABLE module_progress ENABLE ROW LEVEL SECURITY;

-- RLS Policies for video_watching
CREATE POLICY video_watching_select_self ON video_watching
FOR SELECT USING (
    user_id = auth.uid()
    OR (SELECT role FROM users WHERE id = auth.uid()) = 'admin'
);

CREATE POLICY video_watching_insert_self ON video_watching
FOR INSERT WITH CHECK (
    user_id = auth.uid()
    OR (SELECT role FROM users WHERE id = auth.uid()) = 'admin'
);

CREATE POLICY video_watching_update_self ON video_watching
FOR UPDATE USING (
    user_id = auth.uid()
    OR (SELECT role FROM users WHERE id = auth.uid()) = 'admin'
);

-- RLS Policies for course_progress
CREATE POLICY course_progress_select_self ON course_progress
FOR SELECT USING (
    user_id = auth.uid()
    OR (SELECT role FROM users WHERE id = auth.uid()) = 'admin'
    OR course_id IN (SELECT id FROM courses WHERE instructor_id = auth.uid())
);

CREATE POLICY course_progress_insert_self ON course_progress
FOR INSERT WITH CHECK (
    user_id = auth.uid()
    OR (SELECT role FROM users WHERE id = auth.uid()) = 'admin'
);

CREATE POLICY course_progress_update_self ON course_progress
FOR UPDATE USING (
    user_id = auth.uid()
    OR (SELECT role FROM users WHERE id = auth.uid()) = 'admin'
);

-- RLS Policies for module_progress
CREATE POLICY module_progress_select_self ON module_progress
FOR SELECT USING (
    user_id = auth.uid()
    OR (SELECT role FROM users WHERE id = auth.uid()) = 'admin'
    OR course_id IN (SELECT id FROM courses WHERE instructor_id = auth.uid())
);

CREATE POLICY module_progress_insert_self ON module_progress
FOR INSERT WITH CHECK (
    user_id = auth.uid()
    OR (SELECT role FROM users WHERE id = auth.uid()) = 'admin'
);

CREATE POLICY module_progress_update_self ON module_progress
FOR UPDATE USING (
    user_id = auth.uid()
    OR (SELECT role FROM users WHERE id = auth.uid()) = 'admin'
);
