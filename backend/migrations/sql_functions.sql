-- Create increment function for counters
CREATE OR REPLACE FUNCTION increment_counter(
    table_name text,
    column_name text,
    row_id uuid
)
RETURNS void
LANGUAGE plpgsql
SET search_path = public, extensions
AS $$
BEGIN
    EXECUTE format('UPDATE %I SET %I = COALESCE(%I, 0) + 1 WHERE id = $1', 
                   table_name, column_name, column_name)
    USING row_id;
END;
$$
SECURITY DEFINER;

-- Function to calculate course progress
CREATE OR REPLACE FUNCTION calculate_course_progress(
    p_user_id uuid,
    p_course_id uuid
)
RETURNS decimal
LANGUAGE plpgsql
SET search_path = public, extensions
AS $$
DECLARE
    total_content integer;
    completed_content integer;
    progress decimal;
BEGIN
    -- Get total content items
    SELECT COUNT(ci.id) INTO total_content
    FROM content_items ci
    JOIN course_modules cm ON ci.module_id = cm.id
    WHERE cm.course_id = p_course_id;
    
    -- Get completed content items
    SELECT COUNT(cp.id) INTO completed_content
    FROM content_progress cp
    JOIN content_items ci ON cp.content_item_id = ci.id
    JOIN course_modules cm ON ci.module_id = cm.id
    WHERE cm.course_id = p_course_id 
    AND cp.user_id = p_user_id 
    AND cp.completed = true;
    
    -- Calculate progress
    IF total_content > 0 THEN
        progress := (completed_content::decimal / total_content) * 100;
    ELSE
        progress := 0;
    END IF;
    
    -- Update enrollment progress
    UPDATE enrollments 
    SET progress_percentage = progress
    WHERE user_id = p_user_id AND course_id = p_course_id;
    
    RETURN progress;
END;
$$;

-- Function to get student dashboard statistics
CREATE OR REPLACE FUNCTION get_student_dashboard_stats(p_user_id uuid)
RETURNS json
LANGUAGE plpgsql
SET search_path = public, extensions
AS $$
DECLARE
    result json;
BEGIN
    SELECT json_build_object(
        'total_courses', (
            SELECT COUNT(*) FROM enrollments 
            WHERE user_id = p_user_id AND status = 'active'
        ),
        'completed_courses', (
            SELECT COUNT(*) FROM enrollments 
            WHERE user_id = p_user_id AND status = 'completed'
        ),
        'total_assessments', (
            SELECT COUNT(*) FROM assessment_attempts 
            WHERE user_id = p_user_id AND submitted_at IS NOT NULL
        ),
        'average_score', (
            SELECT COALESCE(AVG(percentage), 0) 
            FROM assessment_attempts 
            WHERE user_id = p_user_id AND submitted_at IS NOT NULL
        ),
        'upcoming_assessments', (
            SELECT COUNT(*) FROM assessments a
            JOIN enrollments e ON a.course_id = e.course_id
            WHERE e.user_id = p_user_id 
            AND e.status = 'active'
            AND a.available_from > NOW()
        )
    ) INTO result;
    
    RETURN result;
END;
$$;

-- Function to get instructor dashboard statistics
CREATE OR REPLACE FUNCTION get_instructor_dashboard_stats(p_instructor_id uuid)
RETURNS json
LANGUAGE plpgsql
SET search_path = public, extensions
AS $$
DECLARE
    result json;
BEGIN
    SELECT json_build_object(
        'total_courses', (
            SELECT COUNT(*) FROM courses 
            WHERE instructor_id = p_instructor_id
        ),
        'total_students', (
            SELECT COUNT(DISTINCT e.user_id) 
            FROM enrollments e
            JOIN courses c ON e.course_id = c.id
            WHERE c.instructor_id = p_instructor_id AND e.status = 'active'
        ),
        'total_assessments', (
            SELECT COUNT(*) FROM assessments a
            JOIN courses c ON a.course_id = c.id
            WHERE c.instructor_id = p_instructor_id
        ),
        'pending_grading', (
            SELECT COUNT(*) FROM student_answers sa
            JOIN assessment_attempts aa ON sa.attempt_id = aa.id
            JOIN assessments a ON aa.assessment_id = a.id
            JOIN courses c ON a.course_id = c.id
            WHERE c.instructor_id = p_instructor_id 
            AND sa.marks_awarded IS NULL
            AND aa.submitted_at IS NOT NULL
        ),
        'proctoring_alerts', (
            SELECT COUNT(*) FROM proctoring_alerts pa
            JOIN proctoring_sessions ps ON pa.session_id = ps.id
            JOIN assessment_attempts aa ON ps.attempt_id = aa.id
            JOIN assessments a ON aa.assessment_id = a.id
            JOIN courses c ON a.course_id = c.id
            WHERE c.instructor_id = p_instructor_id 
            AND pa.reviewed = false
        )
    ) INTO result;
    
    RETURN result;
END;
$$;

-- Enable Row Level Security (RLS) on tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE courses ENABLE ROW LEVEL SECURITY;
ALTER TABLE enrollments ENABLE ROW LEVEL SECURITY;
ALTER TABLE assessments ENABLE ROW LEVEL SECURITY;
ALTER TABLE assessment_attempts ENABLE ROW LEVEL SECURITY;
ALTER TABLE proctoring_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE proctoring_snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE proctoring_alerts ENABLE ROW LEVEL SECURITY;

-- RLS Policies for users table
CREATE POLICY "Users can view their own profile"
    ON users FOR SELECT
    USING (auth.uid() = auth_id OR EXISTS (
        SELECT 1 FROM users WHERE users.auth_id = auth.uid() AND users.role IN ('admin', 'instructor')
    ));

CREATE POLICY "Users can update their own profile"
    ON users FOR UPDATE
    USING (auth.uid() = auth_id);

-- RLS Policies for courses
CREATE POLICY "Anyone can view published courses"
    ON courses FOR SELECT
    USING (is_published = true OR instructor_id IN (
        SELECT id FROM users WHERE auth_id = auth.uid()
    ));

CREATE POLICY "Instructors can create courses"
    ON courses FOR INSERT
    WITH CHECK (EXISTS (
        SELECT 1 FROM users 
        WHERE users.auth_id = auth.uid() 
        AND users.role IN ('instructor', 'admin')
    ));

CREATE POLICY "Instructors can update their own courses"
    ON courses FOR UPDATE
    USING (instructor_id IN (
        SELECT id FROM users WHERE auth_id = auth.uid()
    ));

-- RLS Policies for enrollments
CREATE POLICY "Students can view their own enrollments"
    ON enrollments FOR SELECT
    USING (user_id IN (
        SELECT id FROM users WHERE auth_id = auth.uid()
    ) OR EXISTS (
        SELECT 1 FROM users u
        JOIN courses c ON c.instructor_id = u.id
        WHERE u.auth_id = auth.uid() AND c.id = enrollments.course_id
    ));

CREATE POLICY "Students can enroll themselves"
    ON enrollments FOR INSERT
    WITH CHECK (user_id IN (
        SELECT id FROM users WHERE auth_id = auth.uid()
    ));

-- RLS Policies for assessments
CREATE POLICY "Users can view assessments for enrolled courses"
    ON assessments FOR SELECT
    USING (
        course_id IN (
            SELECT course_id FROM enrollments
            WHERE user_id IN (SELECT id FROM users WHERE auth_id = auth.uid())
        ) OR
        course_id IN (
            SELECT id FROM courses 
            WHERE instructor_id IN (SELECT id FROM users WHERE auth_id = auth.uid())
        )
    );

-- Create indexes for RLS policies
CREATE INDEX idx_users_auth_id ON users(auth_id);
CREATE INDEX idx_courses_published ON courses(is_published);