-- Supabase security hardening: fix function search_path and enable RLS policies

-- Fix search_path for plpgsql functions flagged as mutable
ALTER FUNCTION public.has_exam_access(UUID, UUID)
    SET search_path TO public, extensions;

ALTER FUNCTION public.generate_certificate_number()
    SET search_path TO public, extensions;

ALTER FUNCTION public.award_badges_on_completion()
    SET search_path TO public, extensions;

-- Enable RLS on payment-related supporting tables
ALTER TABLE public.exam_pricing ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.badges ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.payment_transactions ENABLE ROW LEVEL SECURITY;

-- Exam pricing policies
CREATE POLICY "allow read exam pricing"
    ON public.exam_pricing
    FOR SELECT
    TO authenticated, service_role
    USING (true);

CREATE POLICY "allow manage exam pricing service"
    ON public.exam_pricing
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- Badge catalog policies
CREATE POLICY "allow read badges"
    ON public.badges
    FOR SELECT
    TO authenticated, service_role
    USING (true);

CREATE POLICY "allow manage badges service"
    ON public.badges
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- Payment transactions policies
CREATE POLICY "allow manage payment transactions service"
    ON public.payment_transactions
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);


