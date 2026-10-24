-- ============================================================
-- LEGALBANDU: Database Schema Migration
-- File: supabase/migrations/001_initial_schema.sql
-- ============================================================

-- Enable pgcrypto extension for UUID generation and hashing
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- 1. PROFILES
CREATE TABLE IF NOT EXISTS public.profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    full_name TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

-- Trigger to create profile when auth.users is created
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.profiles (id, full_name, created_at, updated_at)
    VALUES (
        new.id,
        COALESCE(new.raw_user_meta_data->>'full_name', split_part(new.email, '@', 1)),
        now(),
        now()
    )
    ON CONFLICT (id) DO UPDATE
    SET full_name = EXCLUDED.full_name,
        updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- 2. DEALS
CREATE TABLE IF NOT EXISTS public.deals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    creator_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'Services',
    description TEXT NOT NULL DEFAULT '',
    currency TEXT NOT NULL DEFAULT 'INR',
    status TEXT NOT NULL DEFAULT 'draft',
    current_version_id UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

-- 3. DEAL PARTICIPANTS
CREATE TABLE IF NOT EXISTS public.deal_participants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    deal_id UUID NOT NULL REFERENCES public.deals(id) ON DELETE CASCADE,
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    role TEXT NOT NULL CHECK (role IN ('creator', 'counterparty')),
    invitation_email TEXT,
    invitation_token_hash TEXT,
    invitation_expires_at TIMESTAMPTZ,
    joined_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    CONSTRAINT uq_deal_user UNIQUE NULLS NOT DISTINCT (deal_id, user_id)
);

-- 4. CONVERSATIONS
CREATE TABLE IF NOT EXISTS public.conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    deal_id UUID NOT NULL REFERENCES public.deals(id) ON DELETE CASCADE,
    uploaded_by UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    source_type TEXT NOT NULL CHECK (source_type IN ('paste', 'file_upload')),
    original_content TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

-- 5. MESSAGES
CREATE TABLE IF NOT EXISTS public.messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES public.conversations(id) ON DELETE CASCADE,
    speaker_label TEXT NOT NULL DEFAULT 'Participant',
    message_text TEXT NOT NULL,
    message_timestamp TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

-- 6. DEAL ANALYSES
CREATE TABLE IF NOT EXISTS public.deal_analyses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    deal_id UUID NOT NULL REFERENCES public.deals(id) ON DELETE CASCADE,
    conversation_id UUID REFERENCES public.conversations(id) ON DELETE SET NULL,
    analysis_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_by UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

-- 7. CLARIFICATION ANSWERS
CREATE TABLE IF NOT EXISTS public.clarification_answers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    deal_id UUID NOT NULL REFERENCES public.deals(id) ON DELETE CASCADE,
    field_name TEXT NOT NULL,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    answered_by UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

-- 8. AGREEMENT VERSIONS
CREATE TABLE IF NOT EXISTS public.agreement_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    deal_id UUID NOT NULL REFERENCES public.deals(id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,
    agreement_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    agreement_text TEXT NOT NULL DEFAULT '',
    created_by UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    superseded_at TIMESTAMPTZ,
    CONSTRAINT uq_deal_version UNIQUE (deal_id, version_number)
);

-- Foreign key from deals to current_version_id
ALTER TABLE public.deals 
    DROP CONSTRAINT IF EXISTS fk_deals_current_version;
ALTER TABLE public.deals 
    ADD CONSTRAINT fk_deals_current_version 
    FOREIGN KEY (current_version_id) 
    REFERENCES public.agreement_versions(id) 
    ON DELETE SET NULL;

-- 9. AGREEMENT APPROVALS
CREATE TABLE IF NOT EXISTS public.agreement_approvals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agreement_version_id UUID NOT NULL REFERENCES public.agreement_versions(id) ON DELETE CASCADE,
    participant_id UUID NOT NULL REFERENCES public.deal_participants(id) ON DELETE CASCADE,
    status TEXT NOT NULL CHECK (status IN ('approved', 'changes_requested', 'pending')),
    comment TEXT,
    confirmed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    CONSTRAINT uq_version_participant UNIQUE (agreement_version_id, participant_id)
);

-- 10. AGREEMENT COMMENTS
CREATE TABLE IF NOT EXISTS public.agreement_comments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agreement_version_id UUID NOT NULL REFERENCES public.agreement_versions(id) ON DELETE CASCADE,
    participant_id UUID NOT NULL REFERENCES public.deal_participants(id) ON DELETE CASCADE,
    field_name TEXT NOT NULL DEFAULT 'general',
    comment_text TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

-- 11. AMENDMENTS
CREATE TABLE IF NOT EXISTS public.amendments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    deal_id UUID NOT NULL REFERENCES public.deals(id) ON DELETE CASCADE,
    proposed_by UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    field_name TEXT NOT NULL,
    original_value TEXT NOT NULL DEFAULT '',
    proposed_value TEXT NOT NULL DEFAULT '',
    reason TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'proposed' CHECK (status IN ('proposed', 'confirmed', 'rejected')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

-- 12. ACTIVITY LOGS (Tamper-Evident SHA-256 Hash Chain)
CREATE TABLE IF NOT EXISTS public.activity_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    deal_id UUID NOT NULL REFERENCES public.deals(id) ON DELETE CASCADE,
    actor_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    event_type TEXT NOT NULL,
    event_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    previous_hash TEXT NOT NULL,
    event_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

-- 13. NOTIFICATIONS
CREATE TABLE IF NOT EXISTS public.notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    deal_id UUID REFERENCES public.deals(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    is_read BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_deals_creator ON public.deals(creator_id);
CREATE INDEX IF NOT EXISTS idx_deals_updated ON public.deals(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_participants_deal ON public.deal_participants(deal_id);
CREATE INDEX IF NOT EXISTS idx_participants_user ON public.deal_participants(user_id);
CREATE INDEX IF NOT EXISTS idx_participants_token ON public.deal_participants(invitation_token_hash);
CREATE INDEX IF NOT EXISTS idx_conversations_deal ON public.conversations(deal_id);
CREATE INDEX IF NOT EXISTS idx_messages_conv ON public.messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_analyses_deal ON public.deal_analyses(deal_id);
CREATE INDEX IF NOT EXISTS idx_clarifications_deal ON public.clarification_answers(deal_id);
CREATE INDEX IF NOT EXISTS idx_versions_deal ON public.agreement_versions(deal_id);
CREATE INDEX IF NOT EXISTS idx_approvals_version ON public.agreement_approvals(agreement_version_id);
CREATE INDEX IF NOT EXISTS idx_comments_version ON public.agreement_comments(agreement_version_id);
CREATE INDEX IF NOT EXISTS idx_activity_deal ON public.activity_logs(deal_id, created_at ASC);
CREATE INDEX IF NOT EXISTS idx_notifications_user ON public.notifications(user_id, created_at DESC);
