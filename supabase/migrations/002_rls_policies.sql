-- ============================================================
-- LEGALBANDU: Row Level Security (RLS) Policies Migration
-- File: supabase/migrations/002_rls_policies.sql
-- ============================================================

-- Helper function to check if current user is an active participant in a deal
CREATE OR REPLACE FUNCTION public.is_deal_participant(target_deal_id UUID)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 FROM public.deals d
        WHERE d.id = target_deal_id AND d.creator_id = auth.uid()
    ) OR EXISTS (
        SELECT 1 FROM public.deal_participants dp
        WHERE dp.deal_id = target_deal_id AND dp.user_id = auth.uid()
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER STABLE;

-- 1. PROFILES RLS
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view all participant profiles"
    ON public.profiles FOR SELECT
    TO authenticated
    USING (true);

CREATE POLICY "Users can update own profile"
    ON public.profiles FOR UPDATE
    TO authenticated
    USING (id = auth.uid())
    WITH CHECK (id = auth.uid());

-- 2. DEALS RLS
ALTER TABLE public.deals ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Participants can view their deals"
    ON public.deals FOR SELECT
    TO authenticated
    USING (public.is_deal_participant(id));

CREATE POLICY "Users can create deals"
    ON public.deals FOR INSERT
    TO authenticated
    WITH CHECK (creator_id = auth.uid());

CREATE POLICY "Participants can update their deals"
    ON public.deals FOR UPDATE
    TO authenticated
    USING (public.is_deal_participant(id))
    WITH CHECK (public.is_deal_participant(id));

-- 3. DEAL PARTICIPANTS RLS
ALTER TABLE public.deal_participants ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Participants can view participants in their deals"
    ON public.deal_participants FOR SELECT
    TO authenticated
    USING (public.is_deal_participant(deal_id));

CREATE POLICY "Deal creator can add participants"
    ON public.deal_participants FOR INSERT
    TO authenticated
    WITH CHECK (public.is_deal_participant(deal_id));

CREATE POLICY "Participant can update their own record upon accepting invite"
    ON public.deal_participants FOR UPDATE
    TO authenticated
    USING (user_id = auth.uid() OR public.is_deal_participant(deal_id));

-- 4. CONVERSATIONS RLS
ALTER TABLE public.conversations ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Participants can view conversations"
    ON public.conversations FOR SELECT
    TO authenticated
    USING (public.is_deal_participant(deal_id));

CREATE POLICY "Participants can upload conversations"
    ON public.conversations FOR INSERT
    TO authenticated
    WITH CHECK (public.is_deal_participant(deal_id) AND uploaded_by = auth.uid());

-- 5. MESSAGES RLS
ALTER TABLE public.messages ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Participants can view messages"
    ON public.messages FOR SELECT
    TO authenticated
    USING (EXISTS (
        SELECT 1 FROM public.conversations c
        WHERE c.id = messages.conversation_id AND public.is_deal_participant(c.deal_id)
    ));

CREATE POLICY "Participants can insert messages"
    ON public.messages FOR INSERT
    TO authenticated
    WITH CHECK (EXISTS (
        SELECT 1 FROM public.conversations c
        WHERE c.id = messages.conversation_id AND public.is_deal_participant(c.deal_id)
    ));

-- 6. DEAL ANALYSES RLS
ALTER TABLE public.deal_analyses ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Participants can view analyses"
    ON public.deal_analyses FOR SELECT
    TO authenticated
    USING (public.is_deal_participant(deal_id));

CREATE POLICY "Participants can create analyses"
    ON public.deal_analyses FOR INSERT
    TO authenticated
    WITH CHECK (public.is_deal_participant(deal_id) AND created_by = auth.uid());

-- 7. CLARIFICATION ANSWERS RLS
ALTER TABLE public.clarification_answers ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Participants can view clarification answers"
    ON public.clarification_answers FOR SELECT
    TO authenticated
    USING (public.is_deal_participant(deal_id));

CREATE POLICY "Participants can submit clarification answers"
    ON public.clarification_answers FOR INSERT
    TO authenticated
    WITH CHECK (public.is_deal_participant(deal_id) AND answered_by = auth.uid());

CREATE POLICY "Participants can update clarification answers"
    ON public.clarification_answers FOR UPDATE
    TO authenticated
    USING (public.is_deal_participant(deal_id));

-- 8. AGREEMENT VERSIONS RLS
ALTER TABLE public.agreement_versions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Participants can view agreement versions"
    ON public.agreement_versions FOR SELECT
    TO authenticated
    USING (public.is_deal_participant(deal_id));

CREATE POLICY "Participants can create agreement versions"
    ON public.agreement_versions FOR INSERT
    TO authenticated
    WITH CHECK (public.is_deal_participant(deal_id) AND created_by = auth.uid());

CREATE POLICY "Participants can update agreement versions"
    ON public.agreement_versions FOR UPDATE
    TO authenticated
    USING (public.is_deal_participant(deal_id));

-- 9. AGREEMENT APPROVALS RLS
ALTER TABLE public.agreement_approvals ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Participants can view agreement approvals"
    ON public.agreement_approvals FOR SELECT
    TO authenticated
    USING (EXISTS (
        SELECT 1 FROM public.agreement_versions v
        WHERE v.id = agreement_approvals.agreement_version_id AND public.is_deal_participant(v.deal_id)
    ));

CREATE POLICY "Only the specific participant can submit their approval"
    ON public.agreement_approvals FOR INSERT
    TO authenticated
    WITH CHECK (EXISTS (
        SELECT 1 FROM public.deal_participants dp
        WHERE dp.id = agreement_approvals.participant_id AND dp.user_id = auth.uid()
    ));

CREATE POLICY "Only the specific participant can update their approval"
    ON public.agreement_approvals FOR UPDATE
    TO authenticated
    USING (EXISTS (
        SELECT 1 FROM public.deal_participants dp
        WHERE dp.id = agreement_approvals.participant_id AND dp.user_id = auth.uid()
    ));

-- 10. AGREEMENT COMMENTS RLS
ALTER TABLE public.agreement_comments ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Participants can view comments"
    ON public.agreement_comments FOR SELECT
    TO authenticated
    USING (EXISTS (
        SELECT 1 FROM public.agreement_versions v
        WHERE v.id = agreement_comments.agreement_version_id AND public.is_deal_participant(v.deal_id)
    ));

CREATE POLICY "Participants can submit comments"
    ON public.agreement_comments FOR INSERT
    TO authenticated
    WITH CHECK (EXISTS (
        SELECT 1 FROM public.deal_participants dp
        WHERE dp.id = agreement_comments.participant_id AND dp.user_id = auth.uid()
    ));

-- 11. AMENDMENTS RLS
ALTER TABLE public.amendments ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Participants can view amendments"
    ON public.amendments FOR SELECT
    TO authenticated
    USING (public.is_deal_participant(deal_id));

CREATE POLICY "Participants can propose amendments"
    ON public.amendments FOR INSERT
    TO authenticated
    WITH CHECK (public.is_deal_participant(deal_id) AND proposed_by = auth.uid());

CREATE POLICY "Participants can update amendments"
    ON public.amendments FOR UPDATE
    TO authenticated
    USING (public.is_deal_participant(deal_id));

-- 12. ACTIVITY LOGS RLS (Append-Only Audit Trail)
ALTER TABLE public.activity_logs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Participants can view activity logs"
    ON public.activity_logs FOR SELECT
    TO authenticated
    USING (public.is_deal_participant(deal_id));

CREATE POLICY "Participants can append activity logs"
    ON public.activity_logs FOR INSERT
    TO authenticated
    WITH CHECK (public.is_deal_participant(deal_id));

-- Notice: NO UPDATE or DELETE policies are granted for activity_logs to preserve audit integrity!

-- 13. NOTIFICATIONS RLS
ALTER TABLE public.notifications ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can only view their own notifications"
    ON public.notifications FOR SELECT
    TO authenticated
    USING (user_id = auth.uid());

CREATE POLICY "Users can only update their own notifications"
    ON public.notifications FOR UPDATE
    TO authenticated
    USING (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());
