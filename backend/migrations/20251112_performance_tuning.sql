-- Supabase performance tuning: add foreign key indexes and drop duplicate indexes

-- Drop duplicate indexes flagged by advisor
DROP INDEX IF EXISTS public.idx_attempts_assessment;
DROP INDEX IF EXISTS public.idx_attempts_user;
DROP INDEX IF EXISTS public.idx_proctoring_session;

-- Add covering indexes for foreign key columns
CREATE INDEX IF NOT EXISTS idx_assessments_module_id ON public.assessments(module_id);
CREATE INDEX IF NOT EXISTS idx_certificates_assessment_id ON public.certificates(assessment_id);
CREATE INDEX IF NOT EXISTS idx_certificates_course_id ON public.certificates(course_id);
CREATE INDEX IF NOT EXISTS idx_content_progress_content_item_id ON public.content_progress(content_item_id);
CREATE INDEX IF NOT EXISTS idx_exam_access_payment_order_id ON public.exam_access(payment_order_id);
CREATE INDEX IF NOT EXISTS idx_grades_assessment_id ON public.grades(assessment_id);
CREATE INDEX IF NOT EXISTS idx_grades_attempt_id ON public.grades(attempt_id);
CREATE INDEX IF NOT EXISTS idx_grades_graded_by ON public.grades(graded_by);
CREATE INDEX IF NOT EXISTS idx_grades_user_id ON public.grades(user_id);
CREATE INDEX IF NOT EXISTS idx_payment_transactions_order_id ON public.payment_transactions(payment_order_id);
CREATE INDEX IF NOT EXISTS idx_proctoring_alerts_reviewed_by ON public.proctoring_alerts(reviewed_by);
CREATE INDEX IF NOT EXISTS idx_proctoring_alerts_snapshot_id ON public.proctoring_alerts(snapshot_id);
CREATE INDEX IF NOT EXISTS idx_proctoring_sessions_user_id ON public.proctoring_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_student_answers_attempt_id ON public.student_answers(attempt_id);
CREATE INDEX IF NOT EXISTS idx_student_answers_question_id ON public.student_answers(question_id);
CREATE INDEX IF NOT EXISTS idx_user_badges_assessment_id ON public.user_badges(assessment_id);
CREATE INDEX IF NOT EXISTS idx_user_badges_certificate_id ON public.user_badges(certificate_id);

