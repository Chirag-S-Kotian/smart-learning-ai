BEGIN;

-- Required extensions
CREATE EXTENSION IF NOT EXISTS "pgcrypto" SCHEMA extensions;
CREATE EXTENSION IF NOT EXISTS "citext" SCHEMA extensions;

-- Domain enumerations
CREATE TYPE IF NOT EXISTS user_role AS ENUM ('student', 'instructor', 'admin');
CREATE TYPE IF NOT EXISTS enrollment_status AS ENUM ('active', 'completed', 'dropped', 'pending');
CREATE TYPE IF NOT EXISTS assessment_type AS ENUM ('quiz', 'assignment', 'exam');
CREATE TYPE IF NOT EXISTS question_type AS ENUM ('mcq', 'true_false', 'descriptive', 'multiple_answer');
CREATE TYPE IF NOT EXISTS proctoring_alert_type AS ENUM ('no_face', 'multiple_faces', 'looking_away', 'suspicious_activity');

-- Helper functions ----------------------------------------------------------

CREATE OR REPLACE FUNCTION public.utc_now()
RETURNS timestamptz
LANGUAGE sql
STABLE
SET search_path = public, extensions
AS $$
  SELECT timezone('utc', now());
$$;

CREATE OR REPLACE FUNCTION public.current_app_user_id()
RETURNS uuid
LANGUAGE sql
STABLE
SET search_path = public, extensions
AS $$
  SELECT u.id
  FROM public.users u
  WHERE u.auth_id = auth.uid();
$$;

CREATE OR REPLACE FUNCTION public.has_any_role(required_roles user_role[])
RETURNS boolean
LANGUAGE sql
STABLE
SET search_path = public, extensions
AS $$
  SELECT COALESCE((
    SELECT TRUE
    FROM public.users u
    WHERE u.auth_id = auth.uid()
      AND u.role = ANY(required_roles)
    LIMIT 1
  ), FALSE);
$$;

CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = public, extensions
AS $$
BEGIN
  NEW.updated_at = public.utc_now();
  RETURN NEW;
END;
$$;

-- Tables --------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.users (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    auth_id uuid UNIQUE REFERENCES auth.users(id) ON DELETE CASCADE,
    email citext UNIQUE NOT NULL,
    phone text UNIQUE,
    full_name text NOT NULL,
    role user_role NOT NULL DEFAULT 'student',
    avatar_url text,
    bio text,
    is_active boolean NOT NULL DEFAULT TRUE,
    email_verified boolean NOT NULL DEFAULT FALSE,
    phone_verified boolean NOT NULL DEFAULT FALSE,
    created_at timestamptz NOT NULL DEFAULT public.utc_now(),
    updated_at timestamptz NOT NULL DEFAULT public.utc_now(),
    CONSTRAINT users_phone_length CHECK (phone IS NULL OR length(phone) BETWEEN 6 AND 30)
);

CREATE TABLE IF NOT EXISTS public.courses (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    title text NOT NULL,
    description text,
    instructor_id uuid REFERENCES public.users(id) ON DELETE SET NULL,
    thumbnail_url text,
    is_published boolean NOT NULL DEFAULT FALSE,
    enrollment_open boolean NOT NULL DEFAULT TRUE,
    start_date timestamptz,
    end_date timestamptz,
    created_at timestamptz NOT NULL DEFAULT public.utc_now(),
    updated_at timestamptz NOT NULL DEFAULT public.utc_now(),
    CONSTRAINT courses_valid_dates CHECK (
        start_date IS NULL
        OR end_date IS NULL
        OR start_date <= end_date
    )
);

CREATE TABLE IF NOT EXISTS public.course_modules (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id uuid NOT NULL REFERENCES public.courses(id) ON DELETE CASCADE,
    title text NOT NULL,
    description text,
    order_index integer NOT NULL DEFAULT 0,
    created_at timestamptz NOT NULL DEFAULT public.utc_now(),
    updated_at timestamptz NOT NULL DEFAULT public.utc_now()
);

CREATE TABLE IF NOT EXISTS public.content_items (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    module_id uuid NOT NULL REFERENCES public.course_modules(id) ON DELETE CASCADE,
    title text NOT NULL,
    description text,
    content_type text NOT NULL,
    content_url text NOT NULL,
    duration integer,
    file_size bigint,
    order_index integer NOT NULL DEFAULT 0,
    is_mandatory boolean NOT NULL DEFAULT FALSE,
    created_at timestamptz NOT NULL DEFAULT public.utc_now(),
    updated_at timestamptz NOT NULL DEFAULT public.utc_now(),
    CONSTRAINT content_items_duration_positive CHECK (duration IS NULL OR duration >= 0),
    CONSTRAINT content_items_file_size_positive CHECK (file_size IS NULL OR file_size >= 0)
);

CREATE TABLE IF NOT EXISTS public.enrollments (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    course_id uuid NOT NULL REFERENCES public.courses(id) ON DELETE CASCADE,
    status enrollment_status NOT NULL DEFAULT 'active',
    enrolled_at timestamptz NOT NULL DEFAULT public.utc_now(),
    completed_at timestamptz,
    progress_percentage numeric(5,2) NOT NULL DEFAULT 0.00,
    CONSTRAINT enrollments_unique UNIQUE (user_id, course_id),
    CONSTRAINT enrollments_progress_range CHECK (progress_percentage BETWEEN 0 AND 100)
);

CREATE TABLE IF NOT EXISTS public.content_progress (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    content_item_id uuid NOT NULL REFERENCES public.content_items(id) ON DELETE CASCADE,
    completed boolean NOT NULL DEFAULT FALSE,
    completion_percentage numeric(5,2) NOT NULL DEFAULT 0.00,
    time_spent integer NOT NULL DEFAULT 0,
    last_accessed timestamptz NOT NULL DEFAULT public.utc_now(),
    completed_at timestamptz,
    CONSTRAINT content_progress_unique UNIQUE (user_id, content_item_id),
    CONSTRAINT content_progress_percentage_range CHECK (completion_percentage BETWEEN 0 AND 100),
    CONSTRAINT content_progress_time_spent_positive CHECK (time_spent >= 0)
);

CREATE TABLE IF NOT EXISTS public.assessments (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id uuid NOT NULL REFERENCES public.courses(id) ON DELETE CASCADE,
    module_id uuid REFERENCES public.course_modules(id) ON DELETE SET NULL,
    title text NOT NULL,
    description text,
    assessment_type assessment_type NOT NULL,
    duration integer,
    total_marks numeric(6,2) NOT NULL,
    passing_marks numeric(6,2) NOT NULL,
    is_proctored boolean NOT NULL DEFAULT FALSE,
    proctoring_enabled boolean NOT NULL DEFAULT FALSE,
    proctoring_sensitivity text NOT NULL DEFAULT 'medium',
    available_from timestamptz,
    available_until timestamptz,
    max_attempts integer NOT NULL DEFAULT 1,
    shuffle_questions boolean NOT NULL DEFAULT FALSE,
    show_results_immediately boolean NOT NULL DEFAULT TRUE,
    created_at timestamptz NOT NULL DEFAULT public.utc_now(),
    updated_at timestamptz NOT NULL DEFAULT public.utc_now(),
    CONSTRAINT assessments_duration_positive CHECK (duration IS NULL OR duration > 0),
    CONSTRAINT assessments_marks_positive CHECK (total_marks > 0 AND passing_marks >= 0),
    CONSTRAINT assessments_pass_lte_total CHECK (passing_marks <= total_marks),
    CONSTRAINT assessments_attempts_positive CHECK (max_attempts > 0),
    CONSTRAINT assessments_valid_window CHECK (
        available_from IS NULL
        OR available_until IS NULL
        OR available_from <= available_until
    )
);

CREATE TABLE IF NOT EXISTS public.questions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    assessment_id uuid NOT NULL REFERENCES public.assessments(id) ON DELETE CASCADE,
    question_text text NOT NULL,
    question_type question_type NOT NULL,
    marks numeric(6,2) NOT NULL DEFAULT 1.00,
    order_index integer NOT NULL DEFAULT 0,
    explanation text,
    created_at timestamptz NOT NULL DEFAULT public.utc_now(),
    updated_at timestamptz NOT NULL DEFAULT public.utc_now(),
    CONSTRAINT questions_marks_positive CHECK (marks > 0)
);

CREATE TABLE IF NOT EXISTS public.question_options (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    question_id uuid NOT NULL REFERENCES public.questions(id) ON DELETE CASCADE,
    option_text text NOT NULL,
    is_correct boolean NOT NULL DEFAULT FALSE,
    order_index integer NOT NULL DEFAULT 0,
    created_at timestamptz NOT NULL DEFAULT public.utc_now()
);

CREATE TABLE IF NOT EXISTS public.assessment_attempts (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    assessment_id uuid NOT NULL REFERENCES public.assessments(id) ON DELETE CASCADE,
    user_id uuid NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    attempt_number integer NOT NULL,
    started_at timestamptz NOT NULL DEFAULT public.utc_now(),
    submitted_at timestamptz,
    score numeric(6,2),
    percentage numeric(6,2),
    passed boolean,
    time_taken integer,
    is_flagged boolean NOT NULL DEFAULT FALSE,
    proctoring_violations integer NOT NULL DEFAULT 0,
    CONSTRAINT assessment_attempts_unique UNIQUE (assessment_id, user_id, attempt_number),
    CONSTRAINT assessment_attempts_time_positive CHECK (time_taken IS NULL OR time_taken >= 0),
    CONSTRAINT assessment_attempts_percentage_range CHECK (percentage IS NULL OR (percentage >= 0 AND percentage <= 100))
);

CREATE TABLE IF NOT EXISTS public.student_answers (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    attempt_id uuid NOT NULL REFERENCES public.assessment_attempts(id) ON DELETE CASCADE,
    question_id uuid NOT NULL REFERENCES public.questions(id) ON DELETE CASCADE,
    answer_text text,
    selected_option_ids uuid[],
    is_correct boolean,
    marks_awarded numeric(6,2),
    feedback text,
    answered_at timestamptz NOT NULL DEFAULT public.utc_now()
);

CREATE TABLE IF NOT EXISTS public.proctoring_sessions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    attempt_id uuid NOT NULL REFERENCES public.assessment_attempts(id) ON DELETE CASCADE,
    user_id uuid NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    session_started timestamptz NOT NULL DEFAULT public.utc_now(),
    session_ended timestamptz,
    total_snapshots integer NOT NULL DEFAULT 0,
    total_alerts integer NOT NULL DEFAULT 0,
    status text NOT NULL DEFAULT 'active'
);

CREATE TABLE IF NOT EXISTS public.proctoring_snapshots (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id uuid NOT NULL REFERENCES public.proctoring_sessions(id) ON DELETE CASCADE,
    snapshot_url text NOT NULL,
    captured_at timestamptz NOT NULL DEFAULT public.utc_now(),
    faces_detected integer NOT NULL DEFAULT 0,
    analysis_result jsonb,
    has_alert boolean NOT NULL DEFAULT FALSE,
    alert_type proctoring_alert_type,
    confidence_score numeric(4,3)
);

CREATE TABLE IF NOT EXISTS public.proctoring_alerts (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id uuid NOT NULL REFERENCES public.proctoring_sessions(id) ON DELETE CASCADE,
    snapshot_id uuid REFERENCES public.proctoring_snapshots(id) ON DELETE CASCADE,
    alert_type proctoring_alert_type NOT NULL,
    severity text NOT NULL DEFAULT 'medium',
    description text,
    created_at timestamptz NOT NULL DEFAULT public.utc_now(),
    reviewed boolean NOT NULL DEFAULT FALSE,
    reviewed_by uuid REFERENCES public.users(id),
    reviewed_at timestamptz,
    action_taken text
);

CREATE TABLE IF NOT EXISTS public.grades (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    attempt_id uuid NOT NULL REFERENCES public.assessment_attempts(id) ON DELETE CASCADE,
    user_id uuid NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    assessment_id uuid NOT NULL REFERENCES public.assessments(id) ON DELETE CASCADE,
    score numeric(6,2) NOT NULL,
    max_score numeric(6,2) NOT NULL,
    percentage numeric(6,2) NOT NULL,
    grade text,
    feedback text,
    graded_by uuid REFERENCES public.users(id),
    graded_at timestamptz NOT NULL DEFAULT public.utc_now(),
    created_at timestamptz NOT NULL DEFAULT public.utc_now(),
    CONSTRAINT grades_percentage_range CHECK (percentage >= 0 AND percentage <= 100),
    CONSTRAINT grades_scores_positive CHECK (score >= 0 AND max_score > 0)
);

CREATE TABLE IF NOT EXISTS public.notifications (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    title text NOT NULL,
    message text NOT NULL,
    type text NOT NULL,
    read boolean NOT NULL DEFAULT FALSE,
    action_url text,
    created_at timestamptz NOT NULL DEFAULT public.utc_now()
);

-- Indexes -------------------------------------------------------------------

CREATE INDEX IF NOT EXISTS idx_users_email ON public.users (email);
CREATE INDEX IF NOT EXISTS idx_users_role ON public.users (role);
CREATE INDEX IF NOT EXISTS idx_courses_instructor ON public.courses (instructor_id);
CREATE INDEX IF NOT EXISTS idx_course_modules_course ON public.course_modules (course_id, order_index);
CREATE INDEX IF NOT EXISTS idx_content_items_module ON public.content_items (module_id, order_index);
CREATE INDEX IF NOT EXISTS idx_enrollments_user ON public.enrollments (user_id);
CREATE INDEX IF NOT EXISTS idx_enrollments_course ON public.enrollments (course_id);
CREATE INDEX IF NOT EXISTS idx_content_progress_user ON public.content_progress (user_id);
CREATE INDEX IF NOT EXISTS idx_assessments_course ON public.assessments (course_id);
CREATE INDEX IF NOT EXISTS idx_assessment_attempts_user ON public.assessment_attempts (user_id);
CREATE INDEX IF NOT EXISTS idx_assessment_attempts_assessment ON public.assessment_attempts (assessment_id);
CREATE INDEX IF NOT EXISTS idx_questions_assessment ON public.questions (assessment_id);
CREATE INDEX IF NOT EXISTS idx_question_options_question ON public.question_options (question_id);
CREATE INDEX IF NOT EXISTS idx_proctoring_sessions_attempt ON public.proctoring_sessions (attempt_id);
CREATE INDEX IF NOT EXISTS idx_proctoring_snapshots_session ON public.proctoring_snapshots (session_id);
CREATE INDEX IF NOT EXISTS idx_proctoring_alerts_session ON public.proctoring_alerts (session_id);
CREATE INDEX IF NOT EXISTS idx_notifications_user ON public.notifications (user_id, created_at DESC);

-- Updated_at triggers -------------------------------------------------------

CREATE TRIGGER trg_users_updated_at
BEFORE UPDATE ON public.users
FOR EACH ROW
EXECUTE FUNCTION public.set_updated_at();

CREATE TRIGGER trg_courses_updated_at
BEFORE UPDATE ON public.courses
FOR EACH ROW
EXECUTE FUNCTION public.set_updated_at();

CREATE TRIGGER trg_course_modules_updated_at
BEFORE UPDATE ON public.course_modules
FOR EACH ROW
EXECUTE FUNCTION public.set_updated_at();

CREATE TRIGGER trg_content_items_updated_at
BEFORE UPDATE ON public.content_items
FOR EACH ROW
EXECUTE FUNCTION public.set_updated_at();

CREATE TRIGGER trg_assessments_updated_at
BEFORE UPDATE ON public.assessments
FOR EACH ROW
EXECUTE FUNCTION public.set_updated_at();

CREATE TRIGGER trg_questions_updated_at
BEFORE UPDATE ON public.questions
FOR EACH ROW
EXECUTE FUNCTION public.set_updated_at();

-- Row Level Security --------------------------------------------------------

ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.courses ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.course_modules ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.content_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.enrollments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.content_progress ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.assessments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.questions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.question_options ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.assessment_attempts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.student_answers ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.proctoring_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.proctoring_snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.proctoring_alerts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.grades ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.notifications ENABLE ROW LEVEL SECURITY;

-- Users RLS
CREATE POLICY users_select_self ON public.users
FOR SELECT
USING (
  auth.role() = 'service_role'
  OR auth.uid() = auth_id
);

CREATE POLICY users_update_self ON public.users
FOR UPDATE
USING (auth.uid() = auth_id)
WITH CHECK (auth.uid() = auth_id);

CREATE POLICY users_manage_service_role ON public.users
FOR ALL
USING (auth.role() = 'service_role')
WITH CHECK (TRUE);

-- Courses RLS
CREATE POLICY courses_select_authenticated ON public.courses
FOR SELECT
USING (auth.role() IN ('authenticated', 'service_role'));

CREATE POLICY courses_manage_service_role ON public.courses
FOR ALL
USING (auth.role() = 'service_role')
WITH CHECK (TRUE);

CREATE POLICY courses_manage_instructor ON public.courses
FOR ALL
USING (
  auth.role() = 'service_role'
  OR public.has_any_role(ARRAY['admin'::user_role])
  OR (
    public.has_any_role(ARRAY['instructor'::user_role])
    AND instructor_id = public.current_app_user_id()
  )
)
WITH CHECK (
  auth.role() = 'service_role'
  OR public.has_any_role(ARRAY['admin'::user_role])
  OR (
    public.has_any_role(ARRAY['instructor'::user_role])
    AND instructor_id = public.current_app_user_id()
  )
);

-- Course modules and content items follow instructor/admin permissions
CREATE POLICY course_modules_select_authenticated ON public.course_modules
FOR SELECT
USING (auth.role() IN ('authenticated', 'service_role'));

CREATE POLICY course_modules_manage_service_role ON public.course_modules
FOR ALL
USING (auth.role() = 'service_role')
WITH CHECK (TRUE);

CREATE POLICY course_modules_manage_instructor ON public.course_modules
FOR ALL
USING (
  auth.role() = 'service_role'
  OR public.has_any_role(ARRAY['admin'::user_role])
  OR (
    public.has_any_role(ARRAY['instructor'::user_role])
    AND course_id IN (
      SELECT c.id
      FROM public.courses c
      WHERE c.id = course_modules.course_id
        AND c.instructor_id = public.current_app_user_id()
    )
  )
)
WITH CHECK (
  auth.role() = 'service_role'
  OR public.has_any_role(ARRAY['admin'::user_role])
  OR (
    public.has_any_role(ARRAY['instructor'::user_role])
    AND course_id IN (
      SELECT c.id
      FROM public.courses c
      WHERE c.id = course_modules.course_id
        AND c.instructor_id = public.current_app_user_id()
    )
  )
);

CREATE POLICY content_items_select_authenticated ON public.content_items
FOR SELECT
USING (auth.role() IN ('authenticated', 'service_role'));

CREATE POLICY content_items_manage_service_role ON public.content_items
FOR ALL
USING (auth.role() = 'service_role')
WITH CHECK (TRUE);

CREATE POLICY content_items_manage_instructor ON public.content_items
FOR ALL
USING (
  auth.role() = 'service_role'
  OR public.has_any_role(ARRAY['admin'::user_role])
  OR (
    public.has_any_role(ARRAY['instructor'::user_role])
    AND module_id IN (
      SELECT m.id
      FROM public.course_modules m
      JOIN public.courses c ON c.id = m.course_id
      WHERE m.id = content_items.module_id
        AND c.instructor_id = public.current_app_user_id()
    )
  )
)
WITH CHECK (
  auth.role() = 'service_role'
  OR public.has_any_role(ARRAY['admin'::user_role])
  OR (
    public.has_any_role(ARRAY['instructor'::user_role])
    AND module_id IN (
      SELECT m.id
      FROM public.course_modules m
      JOIN public.courses c ON c.id = m.course_id
      WHERE m.id = content_items.module_id
        AND c.instructor_id = public.current_app_user_id()
    )
  )
);

-- Enrollments and progress: students access their own, instructors/admin via role
CREATE POLICY enrollments_select_authenticated ON public.enrollments
FOR SELECT
USING (
  auth.role() = 'service_role'
  OR public.has_any_role(ARRAY['admin'::user_role])
  OR user_id = public.current_app_user_id()
);

CREATE POLICY enrollments_modify_owner ON public.enrollments
FOR UPDATE
USING (user_id = public.current_app_user_id())
WITH CHECK (user_id = public.current_app_user_id());

CREATE POLICY enrollments_manage_service_role ON public.enrollments
FOR ALL
USING (auth.role() = 'service_role')
WITH CHECK (TRUE);

CREATE POLICY content_progress_select_authenticated ON public.content_progress
FOR SELECT
USING (
  auth.role() = 'service_role'
  OR public.has_any_role(ARRAY['admin'::user_role])
  OR user_id = public.current_app_user_id()
);

CREATE POLICY content_progress_modify_owner ON public.content_progress
FOR ALL
USING (user_id = public.current_app_user_id())
WITH CHECK (user_id = public.current_app_user_id());

CREATE POLICY content_progress_manage_service_role ON public.content_progress
FOR ALL
USING (auth.role() = 'service_role')
WITH CHECK (TRUE);

-- Assessments and questions
CREATE POLICY assessments_select_authenticated ON public.assessments
FOR SELECT
USING (auth.role() IN ('authenticated', 'service_role'));

CREATE POLICY assessments_manage_service_role ON public.assessments
FOR ALL
USING (auth.role() = 'service_role')
WITH CHECK (TRUE);

CREATE POLICY assessments_manage_instructor ON public.assessments
FOR ALL
USING (
  auth.role() = 'service_role'
  OR public.has_any_role(ARRAY['admin'::user_role])
  OR (
    public.has_any_role(ARRAY['instructor'::user_role])
    AND course_id IN (
      SELECT c.id
      FROM public.courses c
      WHERE c.id = assessments.course_id
        AND c.instructor_id = public.current_app_user_id()
    )
  )
)
WITH CHECK (
  auth.role() = 'service_role'
  OR public.has_any_role(ARRAY['admin'::user_role])
  OR (
    public.has_any_role(ARRAY['instructor'::user_role])
    AND course_id IN (
      SELECT c.id
      FROM public.courses c
      WHERE c.id = assessments.course_id
        AND c.instructor_id = public.current_app_user_id()
    )
  )
);

CREATE POLICY questions_select_authenticated ON public.questions
FOR SELECT
USING (auth.role() IN ('authenticated', 'service_role'));

CREATE POLICY questions_manage_service_role ON public.questions
FOR ALL
USING (auth.role() = 'service_role')
WITH CHECK (TRUE);

CREATE POLICY questions_manage_instructor ON public.questions
FOR ALL
USING (
  auth.role() = 'service_role'
  OR public.has_any_role(ARRAY['admin'::user_role])
  OR (
    public.has_any_role(ARRAY['instructor'::user_role])
    AND assessment_id IN (
      SELECT a.id
      FROM public.assessments a
      JOIN public.courses c ON c.id = a.course_id
      WHERE a.id = questions.assessment_id
        AND c.instructor_id = public.current_app_user_id()
    )
  )
)
WITH CHECK (
  auth.role() = 'service_role'
  OR public.has_any_role(ARRAY['admin'::user_role])
  OR (
    public.has_any_role(ARRAY['instructor'::user_role])
    AND assessment_id IN (
      SELECT a.id
      FROM public.assessments a
      JOIN public.courses c ON c.id = a.course_id
      WHERE a.id = questions.assessment_id
        AND c.instructor_id = public.current_app_user_id()
    )
  )
);

CREATE POLICY question_options_select_authenticated ON public.question_options
FOR SELECT
USING (auth.role() IN ('authenticated', 'service_role'));

CREATE POLICY question_options_manage_service_role ON public.question_options
FOR ALL
USING (auth.role() = 'service_role')
WITH CHECK (TRUE);

CREATE POLICY question_options_manage_instructor ON public.question_options
FOR ALL
USING (
  auth.role() = 'service_role'
  OR public.has_any_role(ARRAY['admin'::user_role])
  OR (
    public.has_any_role(ARRAY['instructor'::user_role])
    AND question_id IN (
      SELECT q.id
      FROM public.questions q
      JOIN public.assessments a ON a.id = q.assessment_id
      JOIN public.courses c ON c.id = a.course_id
      WHERE q.id = question_options.question_id
        AND c.instructor_id = public.current_app_user_id()
    )
  )
)
WITH CHECK (
  auth.role() = 'service_role'
  OR public.has_any_role(ARRAY['admin'::user_role])
  OR (
    public.has_any_role(ARRAY['instructor'::user_role])
    AND question_id IN (
      SELECT q.id
      FROM public.questions q
      JOIN public.assessments a ON a.id = q.assessment_id
      JOIN public.courses c ON c.id = a.course_id
      WHERE q.id = question_options.question_id
        AND c.instructor_id = public.current_app_user_id()
    )
  )
);

-- Assessment attempts & student answers
CREATE POLICY assessment_attempts_select_owner ON public.assessment_attempts
FOR SELECT
USING (
  auth.role() = 'service_role'
  OR public.has_any_role(ARRAY['admin'::user_role])
  OR user_id = public.current_app_user_id()
);

CREATE POLICY assessment_attempts_insert_owner ON public.assessment_attempts
FOR INSERT
WITH CHECK (user_id = public.current_app_user_id());

CREATE POLICY assessment_attempts_manage_service_role ON public.assessment_attempts
FOR ALL
USING (auth.role() = 'service_role')
WITH CHECK (TRUE);

CREATE POLICY student_answers_select_owner ON public.student_answers
FOR SELECT
USING (
  auth.role() = 'service_role'
  OR public.has_any_role(ARRAY['admin'::user_role])
  OR attempt_id IN (
    SELECT aa.id
    FROM public.assessment_attempts aa
    WHERE aa.id = student_answers.attempt_id
      AND aa.user_id = public.current_app_user_id()
  )
);

CREATE POLICY student_answers_insert_owner ON public.student_answers
FOR INSERT
WITH CHECK (
  attempt_id IN (
    SELECT aa.id
    FROM public.assessment_attempts aa
    WHERE aa.id = student_answers.attempt_id
      AND aa.user_id = public.current_app_user_id()
  )
);

CREATE POLICY student_answers_manage_service_role ON public.student_answers
FOR ALL
USING (auth.role() = 'service_role')
WITH CHECK (TRUE);

-- Proctoring data: visible to service role, admins, owning student
CREATE POLICY proctoring_sessions_select_authenticated ON public.proctoring_sessions
FOR SELECT
USING (
  auth.role() = 'service_role'
  OR public.has_any_role(ARRAY['admin'::user_role])
  OR user_id = public.current_app_user_id()
);

CREATE POLICY proctoring_sessions_manage_service_role ON public.proctoring_sessions
FOR ALL
USING (auth.role() = 'service_role')
WITH CHECK (TRUE);

CREATE POLICY proctoring_snapshots_select_authenticated ON public.proctoring_snapshots
FOR SELECT
USING (
  auth.role() = 'service_role'
  OR public.has_any_role(ARRAY['admin'::user_role])
  OR session_id IN (
    SELECT ps.id
    FROM public.proctoring_sessions ps
    WHERE ps.id = proctoring_snapshots.session_id
      AND ps.user_id = public.current_app_user_id()
  )
);

CREATE POLICY proctoring_snapshots_manage_service_role ON public.proctoring_snapshots
FOR ALL
USING (auth.role() = 'service_role')
WITH CHECK (TRUE);

CREATE POLICY proctoring_alerts_select_authenticated ON public.proctoring_alerts
FOR SELECT
USING (
  auth.role() = 'service_role'
  OR public.has_any_role(ARRAY['admin'::user_role])
  OR session_id IN (
    SELECT ps.id
    FROM public.proctoring_sessions ps
    WHERE ps.id = proctoring_alerts.session_id
      AND ps.user_id = public.current_app_user_id()
  )
);

CREATE POLICY proctoring_alerts_manage_service_role ON public.proctoring_alerts
FOR ALL
USING (auth.role() = 'service_role')
WITH CHECK (TRUE);

-- Grades and notifications
CREATE POLICY grades_select_owner ON public.grades
FOR SELECT
USING (
  auth.role() = 'service_role'
  OR public.has_any_role(ARRAY['admin'::user_role])
  OR user_id = public.current_app_user_id()
);

CREATE POLICY grades_manage_service_role ON public.grades
FOR ALL
USING (auth.role() = 'service_role')
WITH CHECK (TRUE);

CREATE POLICY notifications_select_owner ON public.notifications
FOR SELECT
USING (
  auth.role() = 'service_role'
  OR public.has_any_role(ARRAY['admin'::user_role])
  OR user_id = public.current_app_user_id()
);

CREATE POLICY notifications_manage_owner ON public.notifications
FOR ALL
USING (user_id = public.current_app_user_id())
WITH CHECK (user_id = public.current_app_user_id());

CREATE POLICY notifications_manage_service_role ON public.notifications
FOR ALL
USING (auth.role() = 'service_role')
WITH CHECK (TRUE);

COMMIT;