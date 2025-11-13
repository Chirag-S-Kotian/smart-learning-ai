-- Create certificates table
CREATE TABLE IF NOT EXISTS certificates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    certificate_number VARCHAR(255) UNIQUE NOT NULL,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    course_id UUID REFERENCES courses(id) ON DELETE SET NULL,
    assessment_id UUID REFERENCES assessments(id) ON DELETE SET NULL,
    type VARCHAR(50) NOT NULL CHECK (type IN ('course_completion', 'exam_completion')),
    title TEXT NOT NULL,
    issued_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completion_percentage DECIMAL(5, 2),
    total_watch_time_minutes INTEGER,
    grade VARCHAR(3),
    score DECIMAL(10, 2),
    percentage DECIMAL(5, 2),
    verification_code VARCHAR(255) UNIQUE NOT NULL,
    is_verified BOOLEAN DEFAULT TRUE,
    instructor_id UUID REFERENCES users(id) ON DELETE SET NULL,
    course_duration_hours DECIMAL(8, 2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT valid_exam_cert CHECK (
        type = 'exam_completion' IMPLIES (assessment_id IS NOT NULL AND score IS NOT NULL AND percentage IS NOT NULL)
    ),
    CONSTRAINT valid_course_cert CHECK (
        type = 'course_completion' IMPLIES (course_id IS NOT NULL AND completion_percentage IS NOT NULL)
    )
);

-- Create indexes for performance
CREATE INDEX idx_certificates_user_id ON certificates(user_id);
CREATE INDEX idx_certificates_course_id ON certificates(course_id);
CREATE INDEX idx_certificates_assessment_id ON certificates(assessment_id);
CREATE INDEX idx_certificates_verification_code ON certificates(verification_code);
CREATE INDEX idx_certificates_issued_date ON certificates(issued_date DESC);

-- Enable RLS on certificates
ALTER TABLE certificates ENABLE ROW LEVEL SECURITY;

-- RLS policies for certificates
CREATE POLICY "Users can view own certificates"
    ON certificates FOR SELECT
    USING (auth.uid() = user_id OR is_verified = TRUE);

CREATE POLICY "Users can view certificates they are instructors for"
    ON certificates FOR SELECT
    USING (auth.uid() = instructor_id);

-- Create user_badges table
CREATE TABLE IF NOT EXISTS user_badges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    badge_key VARCHAR(100) NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    icon VARCHAR(50),
    category VARCHAR(50) CHECK (category IN ('milestone', 'achievement')),
    awarded_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_featured BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Ensure unique badge per user
    UNIQUE(user_id, badge_key)
);

-- Create indexes for performance
CREATE INDEX idx_user_badges_user_id ON user_badges(user_id);
CREATE INDEX idx_user_badges_badge_key ON user_badges(badge_key);
CREATE INDEX idx_user_badges_category ON user_badges(category);
CREATE INDEX idx_user_badges_awarded_date ON user_badges(awarded_date DESC);

-- Enable RLS on user_badges
ALTER TABLE user_badges ENABLE ROW LEVEL SECURITY;

-- RLS policies for user_badges
CREATE POLICY "Users can view own badges"
    ON user_badges FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Public can view featured badges"
    ON user_badges FOR SELECT
    USING (is_featured = TRUE);

-- Create certificate_templates table for customization
CREATE TABLE IF NOT EXISTS certificate_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    type VARCHAR(50) NOT NULL CHECK (type IN ('course_completion', 'exam_completion')),
    template_html TEXT NOT NULL,
    css_styles TEXT,
    logo_url VARCHAR(500),
    signature_image_url VARCHAR(500),
    organization_name VARCHAR(255),
    organization_seal_url VARCHAR(500),
    is_default BOOLEAN DEFAULT FALSE,
    created_by UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX idx_certificate_templates_type ON certificate_templates(type);
CREATE INDEX idx_certificate_templates_is_default ON certificate_templates(is_default);

-- Enable RLS on certificate_templates
ALTER TABLE certificate_templates ENABLE ROW LEVEL SECURITY;

-- RLS policies for certificate_templates
CREATE POLICY "Admins can manage templates"
    ON certificate_templates FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM users
            WHERE users.id = auth.uid()
            AND users.role = 'admin'
        )
    );

CREATE POLICY "Everyone can view templates"
    ON certificate_templates FOR SELECT
    USING (TRUE);

-- Create badge_awards_log table for tracking
CREATE TABLE IF NOT EXISTS badge_awards_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    badge_key VARCHAR(100) NOT NULL,
    reason VARCHAR(255),
    triggered_by_event VARCHAR(255),
    triggered_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX idx_badge_awards_log_user_id ON badge_awards_log(user_id);
CREATE INDEX idx_badge_awards_log_badge_key ON badge_awards_log(badge_key);
CREATE INDEX idx_badge_awards_log_triggered_at ON badge_awards_log(triggered_at DESC);

-- Enable RLS on badge_awards_log
ALTER TABLE badge_awards_log ENABLE ROW LEVEL SECURITY;

-- RLS policies for badge_awards_log
CREATE POLICY "Admins can view all logs"
    ON badge_awards_log FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM users
            WHERE users.id = auth.uid()
            AND users.role = 'admin'
        )
    );

CREATE POLICY "Users can view own logs"
    ON badge_awards_log FOR SELECT
    USING (auth.uid() = user_id);

-- Create achievements_stats materialized view for performance
CREATE MATERIALIZED VIEW user_achievements_stats AS
SELECT
    u.id as user_id,
    u.full_name,
    COUNT(DISTINCT CASE WHEN c.type = 'course_completion' THEN c.id END) as total_courses,
    COUNT(DISTINCT CASE WHEN c.type = 'exam_completion' THEN c.id END) as total_exams,
    COUNT(DISTINCT ub.id) as total_badges,
    AVG(CASE WHEN c.type = 'exam_completion' THEN c.percentage ELSE NULL END) as avg_exam_score,
    MAX(c.issued_date) as last_achievement_date
FROM users u
LEFT JOIN certificates c ON u.id = c.user_id
LEFT JOIN user_badges ub ON u.id = ub.user_id
WHERE u.deleted_at IS NULL
GROUP BY u.id, u.full_name;

-- Create index on materialized view
CREATE INDEX idx_user_achievements_stats_user_id ON user_achievements_stats(user_id);

-- Create trigger to update certificates.updated_at
CREATE OR REPLACE FUNCTION update_certificate_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER certificate_updated_at_trigger
BEFORE UPDATE ON certificates
FOR EACH ROW
EXECUTE FUNCTION update_certificate_timestamp();

-- Create trigger to update certificate_templates.updated_at
CREATE TRIGGER certificate_template_updated_at_trigger
BEFORE UPDATE ON certificate_templates
FOR EACH ROW
EXECUTE FUNCTION update_certificate_timestamp();

-- Create function to award badges based on achievements
CREATE OR REPLACE FUNCTION award_badges_on_completion(
    p_user_id UUID,
    p_event_type VARCHAR
) RETURNS TABLE(badge_key VARCHAR, awarded BOOLEAN) AS $$
DECLARE
    v_badge_key VARCHAR;
    v_already_awarded BOOLEAN;
    v_certificate_count INTEGER;
    v_avg_score DECIMAL;
BEGIN
    -- Get stats
    SELECT
        COUNT(DISTINCT CASE WHEN c.type = 'course_completion' THEN c.id END),
        AVG(CASE WHEN c.type = 'exam_completion' THEN c.percentage ELSE NULL END)
    INTO v_certificate_count, v_avg_score
    FROM certificates c
    WHERE c.user_id = p_user_id;

    -- Check for first course completion
    IF p_event_type = 'course_completion' AND v_certificate_count = 1 THEN
        v_badge_key := 'first_course';
        SELECT EXISTS(SELECT 1 FROM user_badges WHERE user_id = p_user_id AND badge_key = v_badge_key)
        INTO v_already_awarded;
        
        IF NOT v_already_awarded THEN
            INSERT INTO user_badges (user_id, badge_key, name, description, icon, category)
            VALUES (p_user_id, v_badge_key, '🎓 First Course', 'Completed your first course', '🎓', 'milestone')
            ON CONFLICT DO NOTHING;
            RETURN QUERY SELECT v_badge_key::VARCHAR, TRUE;
        END IF;
    END IF;

    -- Check for consistency badge (10 courses)
    IF v_certificate_count >= 10 THEN
        v_badge_key := 'consistency';
        SELECT EXISTS(SELECT 1 FROM user_badges WHERE user_id = p_user_id AND badge_key = v_badge_key)
        INTO v_already_awarded;
        
        IF NOT v_already_awarded THEN
            INSERT INTO user_badges (user_id, badge_key, name, description, icon, category)
            VALUES (p_user_id, v_badge_key, '🔥 Consistency', 'Completed 10 courses', '🔥', 'milestone')
            ON CONFLICT DO NOTHING;
            RETURN QUERY SELECT v_badge_key::VARCHAR, TRUE;
        END IF;
    END IF;

    -- Check for high achiever badge
    IF v_certificate_count >= 5 AND v_avg_score >= 85 THEN
        v_badge_key := 'high_achiever';
        SELECT EXISTS(SELECT 1 FROM user_badges WHERE user_id = p_user_id AND badge_key = v_badge_key)
        INTO v_already_awarded;
        
        IF NOT v_already_awarded THEN
            INSERT INTO user_badges (user_id, badge_key, name, description, icon, category)
            VALUES (p_user_id, v_badge_key, '🏆 High Achiever', 'Completed 5 courses with 85%+ average', '🏆', 'achievement')
            ON CONFLICT DO NOTHING;
            RETURN QUERY SELECT v_badge_key::VARCHAR, TRUE;
        END IF;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Create function to generate certificate number
CREATE OR REPLACE FUNCTION generate_certificate_number()
RETURNS VARCHAR AS $$
BEGIN
    RETURN 'CERT-' || TO_CHAR(CURRENT_TIMESTAMP, 'YYYYMMDD') || '-' || UPPER(substring(gen_random_uuid()::text, 1, 8));
END;
$$ LANGUAGE plpgsql;

-- Grant permissions
GRANT SELECT, INSERT, UPDATE ON certificates TO authenticated;
GRANT SELECT, INSERT, UPDATE ON user_badges TO authenticated;
GRANT SELECT ON user_achievements_stats TO authenticated;
