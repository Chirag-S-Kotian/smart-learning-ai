-- Advanced Proctoring Tables
-- Tables for eye tracking, noise detection, and face recognition

-- Eye Tracking Data Table
CREATE TABLE IF NOT EXISTS eye_tracking_data (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES proctoring_sessions(id) ON DELETE CASCADE,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    
    -- Eye detection
    left_eye_detected BOOLEAN DEFAULT false,
    right_eye_detected BOOLEAN DEFAULT false,
    both_eyes_visible BOOLEAN DEFAULT false,
    
    -- Gaze direction (normalized 0-1)
    gaze_point_x FLOAT DEFAULT 0.5,
    gaze_point_y FLOAT DEFAULT 0.5,
    gaze_on_screen BOOLEAN DEFAULT true,
    gaze_confidence FLOAT DEFAULT 0.0,
    
    -- Eye state
    eyes_open BOOLEAN DEFAULT true,
    blinking_rate FLOAT DEFAULT 0.0,
    eye_closure_duration_ms INTEGER DEFAULT 0,
    prolonged_blink BOOLEAN DEFAULT false,
    
    -- Head position
    head_pose_yaw FLOAT DEFAULT 0.0,
    head_pose_pitch FLOAT DEFAULT 0.0,
    head_pose_roll FLOAT DEFAULT 0.0,
    
    -- Pupil metrics
    pupil_diameter_left FLOAT DEFAULT 0.0,
    pupil_diameter_right FLOAT DEFAULT 0.0,
    pupil_size_difference FLOAT DEFAULT 0.0,
    
    -- Fixation analysis
    fixation_duration_ms INTEGER DEFAULT 0,
    fixation_point_x FLOAT DEFAULT 0.5,
    fixation_point_y FLOAT DEFAULT 0.5,
    number_of_fixations INTEGER DEFAULT 0,
    average_fixation_duration_ms INTEGER DEFAULT 0,
    
    -- Gaze patterns
    saccade_speed FLOAT DEFAULT 0.0,
    gaze_stability FLOAT DEFAULT 1.0,
    smooth_pursuit_detected BOOLEAN DEFAULT false,
    
    -- Suspicious patterns
    gaze_away_from_screen BOOLEAN DEFAULT false,
    repeated_off_screen_glances BOOLEAN DEFAULT false,
    gaze_at_keyboard BOOLEAN DEFAULT false,
    gaze_at_external_object BOOLEAN DEFAULT false,
    
    -- Risk indicators
    eye_fatigue_indicator BOOLEAN DEFAULT false,
    suspicious_eye_pattern BOOLEAN DEFAULT false,
    potential_cheating_sign BOOLEAN DEFAULT false,
    
    -- Confidence
    overall_confidence FLOAT DEFAULT 0.5,
    violation_probability FLOAT DEFAULT 0.0,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_eye_tracking_session_id ON eye_tracking_data(session_id);
CREATE INDEX idx_eye_tracking_timestamp ON eye_tracking_data(timestamp);

-- Noise Detection Data Table
CREATE TABLE IF NOT EXISTS noise_detection_data (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES proctoring_sessions(id) ON DELETE CASCADE,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    duration_seconds FLOAT DEFAULT 5.0,
    
    -- Noise levels
    ambient_noise_level_db FLOAT DEFAULT 0,
    background_noise_detected BOOLEAN DEFAULT false,
    noise_above_threshold BOOLEAN DEFAULT false,
    
    -- Speech analysis
    speech_detected BOOLEAN DEFAULT false,
    speech_confidence FLOAT DEFAULT 0.0,
    number_of_speakers INTEGER DEFAULT 0,
    language_detected VARCHAR(50) DEFAULT 'unknown',
    
    -- Specific sounds
    keyboard_clicking_detected BOOLEAN DEFAULT false,
    mouse_clicking_detected BOOLEAN DEFAULT false,
    phone_ringing_detected BOOLEAN DEFAULT false,
    door_knock_detected BOOLEAN DEFAULT false,
    notification_sound_detected BOOLEAN DEFAULT false,
    footsteps_detected BOOLEAN DEFAULT false,
    paper_rustling_detected BOOLEAN DEFAULT false,
    whisper_detected BOOLEAN DEFAULT false,
    
    -- Communication patterns
    conversation_detected BOOLEAN DEFAULT false,
    multiple_voices BOOLEAN DEFAULT false,
    external_communication_suspected BOOLEAN DEFAULT false,
    suspicious_audio_pattern BOOLEAN DEFAULT false,
    
    -- Quality metrics
    audio_quality_score FLOAT DEFAULT 0.5,
    signal_to_noise_ratio FLOAT DEFAULT 0.0,
    clipping_detected BOOLEAN DEFAULT false,
    audio_degradation BOOLEAN DEFAULT false,
    
    -- Risk indicators
    potential_cheating_audio BOOLEAN DEFAULT false,
    suspicious_sound_pattern BOOLEAN DEFAULT false,
    environment_integrity_concern BOOLEAN DEFAULT false,
    
    -- Confidence and recommendations
    analysis_confidence FLOAT DEFAULT 0.5,
    violation_probability FLOAT DEFAULT 0.0,
    recommended_action VARCHAR(100) DEFAULT 'none',
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_noise_detection_session_id ON noise_detection_data(session_id);
CREATE INDEX idx_noise_detection_timestamp ON noise_detection_data(timestamp);

-- Face Recognition Data Table
CREATE TABLE IF NOT EXISTS face_recognition_data (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES proctoring_sessions(id) ON DELETE CASCADE,
    user_id UUID,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    
    -- Face detection
    face_detected BOOLEAN DEFAULT false,
    number_of_faces INTEGER DEFAULT 0,
    face_quality FLOAT DEFAULT 0.0,
    face_area_percentage FLOAT DEFAULT 0.0,
    
    -- Identity verification
    identity_match_confidence FLOAT DEFAULT 0.0,
    identity_verified BOOLEAN DEFAULT false,
    identity_mismatch_detected BOOLEAN DEFAULT false,
    
    -- Liveness detection
    liveness_score FLOAT DEFAULT 0.0,
    liveness_detected BOOLEAN DEFAULT false,
    spoofing_detected BOOLEAN DEFAULT false,
    spoofing_confidence FLOAT DEFAULT 0.0,
    presentation_attack_detected BOOLEAN DEFAULT false,
    
    -- Facial characteristics
    age_estimated INTEGER DEFAULT 0,
    gender_detected VARCHAR(20) DEFAULT 'unknown',
    ethnicity_detected VARCHAR(50) DEFAULT 'unknown',
    expression_neutral BOOLEAN DEFAULT false,
    expression_anomaly BOOLEAN DEFAULT false,
    
    -- Eye and mouth analysis
    eyes_open BOOLEAN DEFAULT true,
    mouth_open BOOLEAN DEFAULT false,
    blinking BOOLEAN DEFAULT false,
    smile_detected BOOLEAN DEFAULT false,
    
    -- Facial landmarks
    face_landmarks_detected INTEGER DEFAULT 0,
    landmarks_quality FLOAT DEFAULT 0.0,
    
    -- Face orientation
    face_yaw FLOAT DEFAULT 0.0,
    face_pitch FLOAT DEFAULT 0.0,
    face_roll FLOAT DEFAULT 0.0,
    frontal_face BOOLEAN DEFAULT false,
    
    -- Suspicious indicators
    masked_face_detected BOOLEAN DEFAULT false,
    face_covered_detected BOOLEAN DEFAULT false,
    glasses_detected BOOLEAN DEFAULT false,
    sun_glasses_detected BOOLEAN DEFAULT false,
    face_obscured BOOLEAN DEFAULT false,
    
    -- Lighting and quality
    lighting_conditions VARCHAR(50) DEFAULT 'normal',
    overexposed BOOLEAN DEFAULT false,
    underexposed BOOLEAN DEFAULT false,
    shadow_on_face BOOLEAN DEFAULT false,
    
    -- Anti-spoofing
    anti_spoofing_score FLOAT DEFAULT 0.0,
    texture_analysis_score FLOAT DEFAULT 0.0,
    depth_map_quality FLOAT DEFAULT 0.0,
    
    -- Risk indicators
    identity_risk BOOLEAN DEFAULT false,
    potential_spoofing_risk BOOLEAN DEFAULT false,
    suspicious_face_pattern BOOLEAN DEFAULT false,
    
    verification_confidence FLOAT DEFAULT 0.5,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_face_recognition_session_id ON face_recognition_data(session_id);
CREATE INDEX idx_face_recognition_timestamp ON face_recognition_data(timestamp);
CREATE INDEX idx_face_recognition_user_id ON face_recognition_data(user_id);

-- Update proctoring_sessions table to include advanced features flags
ALTER TABLE proctoring_sessions 
ADD COLUMN IF NOT EXISTS advanced_proctoring_enabled BOOLEAN DEFAULT false,
ADD COLUMN IF NOT EXISTS eye_tracking_enabled BOOLEAN DEFAULT false,
ADD COLUMN IF NOT EXISTS noise_detection_enabled BOOLEAN DEFAULT false,
ADD COLUMN IF NOT EXISTS face_recognition_enabled BOOLEAN DEFAULT false;

-- Create analytics view for advanced proctoring
CREATE OR REPLACE VIEW advanced_proctoring_analytics AS
SELECT 
    ps.id as session_id,
    ps.user_id,
    ps.assessment_id,
    COUNT(DISTINCT etd.id) as eye_tracking_frames,
    COUNT(DISTINCT ndd.id) as audio_samples,
    COUNT(DISTINCT frd.id) as face_verifications,
    ROUND(AVG(etd.gaze_stability)::numeric, 2) as avg_gaze_stability,
    ROUND(AVG(ndd.ambient_noise_level_db)::numeric, 2) as avg_noise_level,
    ROUND(AVG(frd.identity_match_confidence)::numeric, 2) as avg_identity_confidence,
    COUNT(DISTINCT CASE WHEN etd.gaze_away_from_screen = true THEN etd.id END) as gaze_away_count,
    COUNT(DISTINCT CASE WHEN ndd.speech_detected = true THEN ndd.id END) as speech_detected_count,
    COUNT(DISTINCT CASE WHEN frd.spoofing_detected = true THEN frd.id END) as spoofing_attempts,
    MAX(ps.updated_at) as last_update
FROM proctoring_sessions ps
LEFT JOIN eye_tracking_data etd ON ps.id = etd.session_id
LEFT JOIN noise_detection_data ndd ON ps.id = ndd.session_id
LEFT JOIN face_recognition_data frd ON ps.id = frd.session_id
GROUP BY ps.id, ps.user_id, ps.assessment_id;
