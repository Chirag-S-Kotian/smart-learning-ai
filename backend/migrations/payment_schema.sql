-- Payment and Certificate Schema for Smart LMS

-- Create ENUM types for payments
CREATE TYPE payment_status AS ENUM ('pending', 'processing', 'completed', 'failed', 'refunded');
CREATE TYPE payment_method AS ENUM ('upi', 'card', 'netbanking', 'wallet');
CREATE TYPE currency_type AS ENUM ('USD', 'INR');
CREATE TYPE badge_type AS ENUM ('bronze', 'silver', 'gold', 'platinum', 'completion');

-- Exam Pricing table
CREATE TABLE exam_pricing (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    assessment_id UUID REFERENCES assessments(id) ON DELETE CASCADE,
    price_usd DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    price_inr DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    discount_percentage DECIMAL(5,2) DEFAULT 0.00,
    is_free BOOLEAN DEFAULT FALSE,
    valid_from TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    valid_until TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(assessment_id)
);

-- Payment Orders table
CREATE TABLE payment_orders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    order_id VARCHAR(255) UNIQUE NOT NULL, -- DodoPay order ID
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    assessment_id UUID REFERENCES assessments(id) ON DELETE CASCADE,
    amount DECIMAL(10,2) NOT NULL,
    currency currency_type NOT NULL DEFAULT 'USD',
    payment_method payment_method,
    status payment_status DEFAULT 'pending',
    payment_gateway_response JSONB,
    dodopay_payment_id VARCHAR(255),
    dodopay_reference VARCHAR(255),
    failure_reason TEXT,
    payment_date TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Payment access (track which exams user has paid for)
CREATE TABLE exam_access (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    assessment_id UUID REFERENCES assessments(id) ON DELETE CASCADE,
    payment_order_id UUID REFERENCES payment_orders(id) ON DELETE SET NULL,
    is_free BOOLEAN DEFAULT FALSE,
    access_granted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE, -- Optional: for time-limited access
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, assessment_id)
);

-- Certificates table
CREATE TABLE certificates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    certificate_number VARCHAR(50) UNIQUE NOT NULL,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    assessment_id UUID REFERENCES assessments(id) ON DELETE CASCADE,
    course_id UUID REFERENCES courses(id) ON DELETE CASCADE,
    score DECIMAL(5,2) NOT NULL,
    percentage DECIMAL(5,2) NOT NULL,
    grade VARCHAR(5),
    issued_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    certificate_url TEXT, -- Link to PDF certificate
    verification_code VARCHAR(100) UNIQUE NOT NULL,
    qr_code_url TEXT,
    is_verified BOOLEAN DEFAULT TRUE,
    metadata JSONB, -- Additional certificate data
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Badges table
CREATE TABLE badges (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL,
    description TEXT,
    badge_type badge_type NOT NULL,
    icon_url TEXT,
    criteria JSONB, -- JSON defining how to earn this badge
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- User badges (earned badges)
CREATE TABLE user_badges (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    badge_id UUID REFERENCES badges(id) ON DELETE CASCADE,
    assessment_id UUID REFERENCES assessments(id) ON DELETE SET NULL,
    certificate_id UUID REFERENCES certificates(id) ON DELETE SET NULL,
    earned_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, badge_id, assessment_id)
);

-- Payment transactions log (for audit trail)
CREATE TABLE payment_transactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    payment_order_id UUID REFERENCES payment_orders(id) ON DELETE CASCADE,
    transaction_type VARCHAR(50) NOT NULL, -- 'payment', 'refund', 'webhook'
    gateway_response JSONB,
    status payment_status,
    amount DECIMAL(10,2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes
CREATE INDEX idx_payment_orders_user ON payment_orders(user_id);
CREATE INDEX idx_payment_orders_assessment ON payment_orders(assessment_id);
CREATE INDEX idx_payment_orders_status ON payment_orders(status);
CREATE INDEX idx_payment_orders_order_id ON payment_orders(order_id);
CREATE INDEX idx_exam_access_user ON exam_access(user_id);
CREATE INDEX idx_exam_access_assessment ON exam_access(assessment_id);
CREATE INDEX idx_certificates_user ON certificates(user_id);
CREATE INDEX idx_certificates_verification ON certificates(verification_code);
CREATE INDEX idx_certificates_number ON certificates(certificate_number);
CREATE INDEX idx_user_badges_user ON user_badges(user_id);
CREATE INDEX idx_user_badges_badge ON user_badges(badge_id);

-- Insert default badges
INSERT INTO badges (name, description, badge_type, criteria) VALUES
('Completion Master', 'Awarded for completing your first exam', 'bronze', '{"type": "first_exam", "min_score": 50}'),
('High Achiever', 'Scored above 75% in an exam', 'silver', '{"type": "score", "min_percentage": 75}'),
('Excellence Award', 'Scored above 90% in an exam', 'gold', '{"type": "score", "min_percentage": 90}'),
('Perfect Score', 'Achieved 100% in an exam', 'platinum', '{"type": "score", "min_percentage": 100}'),
('Course Champion', 'Completed all exams in a course', 'gold', '{"type": "course_completion"}');

-- Function to check if user has access to exam
CREATE OR REPLACE FUNCTION has_exam_access(p_user_id UUID, p_assessment_id UUID)
RETURNS BOOLEAN AS $$
DECLARE
    has_access BOOLEAN;
    is_free BOOLEAN;
BEGIN
    -- Check if exam is free
    SELECT ep.is_free INTO is_free
    FROM exam_pricing ep
    WHERE ep.assessment_id = p_assessment_id;
    
    IF is_free THEN
        RETURN TRUE;
    END IF;
    
    -- Check if user has paid for access
    SELECT EXISTS(
        SELECT 1 FROM exam_access
        WHERE user_id = p_user_id 
        AND assessment_id = p_assessment_id
        AND (expires_at IS NULL OR expires_at > NOW())
    ) INTO has_access;
    
    RETURN has_access;
END;
$$ LANGUAGE plpgsql;

-- Function to generate certificate number
CREATE OR REPLACE FUNCTION generate_certificate_number()
RETURNS VARCHAR(50) AS $$
DECLARE
    cert_number VARCHAR(50);
    year_prefix VARCHAR(4);
BEGIN
    year_prefix := TO_CHAR(NOW(), 'YYYY');
    cert_number := year_prefix || '-' || LPAD(NEXTVAL('certificate_sequence')::TEXT, 6, '0');
    RETURN cert_number;
END;
$$ LANGUAGE plpgsql;

-- Create sequence for certificates
CREATE SEQUENCE IF NOT EXISTS certificate_sequence START 1000;

-- Function to auto-award badges based on performance
CREATE OR REPLACE FUNCTION award_badges_on_completion()
RETURNS TRIGGER AS $$
DECLARE
    badge_record RECORD;
BEGIN
    -- Award badges based on percentage
    IF NEW.percentage >= 100 THEN
        -- Perfect Score
        INSERT INTO user_badges (user_id, badge_id, assessment_id)
        SELECT NEW.user_id, b.id, NEW.assessment_id
        FROM badges b
        WHERE b.name = 'Perfect Score'
        ON CONFLICT DO NOTHING;
    END IF;
    
    IF NEW.percentage >= 90 THEN
        -- Excellence Award
        INSERT INTO user_badges (user_id, badge_id, assessment_id)
        SELECT NEW.user_id, b.id, NEW.assessment_id
        FROM badges b
        WHERE b.name = 'Excellence Award'
        ON CONFLICT DO NOTHING;
    END IF;
    
    IF NEW.percentage >= 75 THEN
        -- High Achiever
        INSERT INTO user_badges (user_id, badge_id, assessment_id)
        SELECT NEW.user_id, b.id, NEW.assessment_id
        FROM badges b
        WHERE b.name = 'High Achiever'
        ON CONFLICT DO NOTHING;
    END IF;
    
    IF NEW.percentage >= 50 THEN
        -- Completion Master (first exam)
        IF NOT EXISTS(
            SELECT 1 FROM user_badges ub
            JOIN badges b ON ub.badge_id = b.id
            WHERE ub.user_id = NEW.user_id AND b.name = 'Completion Master'
        ) THEN
            INSERT INTO user_badges (user_id, badge_id, assessment_id)
            SELECT NEW.user_id, b.id, NEW.assessment_id
            FROM badges b
            WHERE b.name = 'Completion Master'
            ON CONFLICT DO NOTHING;
        END IF;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to award badges when certificate is issued
CREATE TRIGGER trigger_award_badges
    AFTER INSERT ON certificates
    FOR EACH ROW
    EXECUTE FUNCTION award_badges_on_completion();

-- Update trigger for payment orders and exam pricing
CREATE TRIGGER update_payment_orders_updated_at BEFORE UPDATE ON payment_orders
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_exam_pricing_updated_at BEFORE UPDATE ON exam_pricing
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- RLS Policies for payment tables
ALTER TABLE payment_orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE exam_access ENABLE ROW LEVEL SECURITY;
ALTER TABLE certificates ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_badges ENABLE ROW LEVEL SECURITY;

-- Payment orders: users can view their own
CREATE POLICY "Users can view own payment orders"
    ON payment_orders FOR SELECT
    USING (user_id IN (SELECT id FROM users WHERE auth_id = auth.uid()));

-- Exam access: users can view their own
CREATE POLICY "Users can view own exam access"
    ON exam_access FOR SELECT
    USING (user_id IN (SELECT id FROM users WHERE auth_id = auth.uid()));

-- Certificates: users can view their own
CREATE POLICY "Users can view own certificates"
    ON certificates FOR SELECT
    USING (user_id IN (SELECT id FROM users WHERE auth_id = auth.uid()));

-- Certificates: anyone can verify (public)
CREATE POLICY "Anyone can verify certificates"
    ON certificates FOR SELECT
    USING (true);

-- User badges: users can view their own
CREATE POLICY "Users can view own badges"
    ON user_badges FOR SELECT
    USING (user_id IN (SELECT id FROM users WHERE auth_id = auth.uid()));

COMMENT ON TABLE exam_pricing IS 'Pricing information for exams';
COMMENT ON TABLE payment_orders IS 'Payment transactions and order details';
COMMENT ON TABLE exam_access IS 'Tracks which users have access to which paid exams';
COMMENT ON TABLE certificates IS 'Digital certificates issued to students';
COMMENT ON TABLE badges IS 'Available achievement badges';
COMMENT ON TABLE user_badges IS 'Badges earned by users';