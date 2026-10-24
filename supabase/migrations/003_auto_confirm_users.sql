-- ====================================================================
-- Auto-Confirm Users Trigger
-- Automatically confirms email for all users upon signup
-- eliminating email verification blocks and "invalid login credentials"
-- ====================================================================

CREATE OR REPLACE FUNCTION public.auto_confirm_user_email()
RETURNS TRIGGER 
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    NEW.email_confirmed_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS on_auth_user_created_auto_confirm ON auth.users;

CREATE TRIGGER on_auth_user_created_auto_confirm
BEFORE INSERT ON auth.users
FOR EACH ROW
EXECUTE FUNCTION public.auto_confirm_user_email();

-- Ensure all existing users in auth.users are also confirmed
UPDATE auth.users 
SET email_confirmed_at = CURRENT_TIMESTAMP 
WHERE email_confirmed_at IS NULL;
