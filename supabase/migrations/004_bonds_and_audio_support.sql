-- ====================================================================
-- LEGALBANDU: Bonds, AI Synthetic Content Detector & Call Audio Recording
-- File: supabase/migrations/004_bonds_and_audio_support.sql
-- ====================================================================

-- 1. Support audio recording columns on conversations
ALTER TABLE public.conversations ADD COLUMN IF NOT EXISTS audio_url VARCHAR(500);
ALTER TABLE public.conversations ADD COLUMN IF NOT EXISTS audio_filename VARCHAR(255);
ALTER TABLE public.conversations ADD COLUMN IF NOT EXISTS audio_duration INTEGER;

-- 2. Drop source_type check constraint so 'call_recording' is accepted
ALTER TABLE public.conversations DROP CONSTRAINT IF EXISTS conversations_source_type_check;

-- 3. Create bond_documents table
CREATE TABLE IF NOT EXISTS public.bond_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    deal_id UUID NOT NULL REFERENCES public.deals(id) ON DELETE CASCADE,
    uploaded_by UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    filename TEXT NOT NULL,
    file_type TEXT NOT NULL DEFAULT 'pdf',
    bond_type TEXT NOT NULL DEFAULT 'Legal Bond',
    document_text TEXT NOT NULL,
    is_ai_generated BOOLEAN NOT NULL DEFAULT FALSE,
    ai_detection_score DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    ai_verdict TEXT NOT NULL DEFAULT 'Human Authored',
    ai_confidence TEXT NOT NULL DEFAULT 'medium',
    ai_markers JSONB NOT NULL DEFAULT '[]'::jsonb,
    ai_alert_triggered BOOLEAN NOT NULL DEFAULT FALSE,
    extracted_terms JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

-- Index for speedy deal room lookups
CREATE INDEX IF NOT EXISTS idx_bond_documents_deal_id ON public.bond_documents(deal_id);

-- 4. Enable Row Level Security (RLS) on bond_documents
ALTER TABLE public.bond_documents ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Participants can view bonds in their deals"
    ON public.bond_documents FOR SELECT
    TO authenticated
    USING (public.is_deal_participant(deal_id));

CREATE POLICY "Participants can upload bonds in their deals"
    ON public.bond_documents FOR INSERT
    TO authenticated
    WITH CHECK (public.is_deal_participant(deal_id) AND uploaded_by = auth.uid());

CREATE POLICY "Participants can delete bonds in their deals"
    ON public.bond_documents FOR DELETE
    TO authenticated
    USING (public.is_deal_participant(deal_id));
