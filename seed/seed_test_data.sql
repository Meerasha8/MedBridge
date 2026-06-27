-- ============================================================================
-- MEDBRIDGE — TEST SEED DATA
-- ============================================================================
-- Run this in the Supabase SQL Editor AFTER running the main schema file.
-- Creates fake auth.users + profiles + doctors + patients + a nurse + an
-- admin, plus a couple of sample appointments/documents so the app has
-- something to show immediately.
--
-- ⚠️  TEST DATA ONLY. Do not run this against a production project.
-- It inserts directly into auth.users, which is only safe to do from the
-- SQL Editor (running as postgres / service role) — never do this from
-- client code or with the anon key.
--
-- All seeded accounts share the same password so you can log in immediately:
--   Password: Test@1234
--
-- Re-running this script is safe — every insert uses a fixed UUID and
-- ON CONFLICT DO NOTHING, so existing rows are left untouched.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 0. Helper: create an auth.users row for one fake person
-- ----------------------------------------------------------------------------
-- Supabase's auth.users has several required system columns. This inserts
-- the minimum needed for password login to work, with email already
-- "confirmed" so you don't need to click a confirmation link.
create or replace function seed_create_auth_user(
  p_id uuid,
  p_email text,
  p_password text
) returns void
language plpgsql
as $$
begin
  insert into auth.users (
    instance_id, id, aud, role, email, encrypted_password,
    email_confirmed_at, created_at, updated_at,
    confirmation_token, recovery_token, email_change_token_new, email_change,
    raw_app_meta_data, raw_user_meta_data, is_super_admin, is_sso_user
  ) values (
    '00000000-0000-0000-0000-000000000000',
    p_id, 'authenticated', 'authenticated', p_email,
    crypt(p_password, gen_salt('bf')),
    now(), now(), now(),
    '', '', '', '',
    '{"provider":"email","providers":["email"]}'::jsonb,
    '{}'::jsonb,
    false, false
  )
  on conflict (id) do nothing;

  -- Supabase also expects a matching identity row for email/password login.
  insert into auth.identities (
    id, provider_id, user_id, identity_data, provider, last_sign_in_at, created_at, updated_at
  ) values (
    gen_random_uuid(), p_id::text, p_id,
    jsonb_build_object('sub', p_id::text, 'email', p_email),
    'email', now(), now(), now()
  )
  on conflict do nothing;
end;
$$;


-- ----------------------------------------------------------------------------
-- 1. DOCTORS (6, spread around Chennai / Puducherry for distance testing)
-- ----------------------------------------------------------------------------
-- id columns are fixed uuids so the script is idempotent and so you can
-- reference these doctors easily while testing (e.g. in Postman / curl).

select seed_create_auth_user('a0000000-0000-0000-0000-000000000001', 'dr.arun.cardio@test.medbridge.dev', 'Test@1234');
select seed_create_auth_user('a0000000-0000-0000-0000-000000000002', 'dr.priya.derma@test.medbridge.dev', 'Test@1234');
select seed_create_auth_user('a0000000-0000-0000-0000-000000000003', 'dr.suresh.ortho@test.medbridge.dev', 'Test@1234');
select seed_create_auth_user('a0000000-0000-0000-0000-000000000004', 'dr.lakshmi.peds@test.medbridge.dev', 'Test@1234');
select seed_create_auth_user('a0000000-0000-0000-0000-000000000005', 'dr.karthik.gp@test.medbridge.dev', 'Test@1234');
select seed_create_auth_user('a0000000-0000-0000-0000-000000000006', 'dr.fathima.gyn@test.medbridge.dev', 'Test@1234');

insert into profiles (id, email, full_name, phone, language_preference, role)
values
  ('a0000000-0000-0000-0000-000000000001', 'dr.arun.cardio@test.medbridge.dev', 'Dr. Arun Kumar', '+91 9840011111', 'en', 'doctor'),
  ('a0000000-0000-0000-0000-000000000002', 'dr.priya.derma@test.medbridge.dev', 'Dr. Priya Raman', '+91 9840022222', 'ta', 'doctor'),
  ('a0000000-0000-0000-0000-000000000003', 'dr.suresh.ortho@test.medbridge.dev', 'Dr. Suresh Babu', '+91 9840033333', 'en', 'doctor'),
  ('a0000000-0000-0000-0000-000000000004', 'dr.lakshmi.peds@test.medbridge.dev', 'Dr. Lakshmi Narayanan', '+91 9840044444', 'ta', 'doctor'),
  ('a0000000-0000-0000-0000-000000000005', 'dr.karthik.gp@test.medbridge.dev', 'Dr. Karthik Subramaniam', '+91 9840055555', 'en', 'doctor'),
  ('a0000000-0000-0000-0000-000000000006', 'dr.fathima.gyn@test.medbridge.dev', 'Dr. Fathima Begum', '+91 9840066666', 'ta', 'doctor')
on conflict (id) do nothing;

insert into doctors (
  id, profile_id, registration_number, specialization, clinic_name, clinic_address,
  lat, lng, languages_spoken, experience_years, consultation_fee, is_verified
)
values
  ('b0000000-0000-0000-0000-000000000001', 'a0000000-0000-0000-0000-000000000001',
   'TN-MED-10001', 'Cardiologist', 'Apollo Heart Clinic', 'Anna Nagar, Chennai',
   13.0850, 80.2101, array['Tamil','English'], 14, 700, true),

  ('b0000000-0000-0000-0000-000000000002', 'a0000000-0000-0000-0000-000000000002',
   'TN-MED-10002', 'Dermatologist', 'SkinCare Clinic', 'T. Nagar, Chennai',
   13.0418, 80.2341, array['Tamil','English','Hindi'], 9, 500, true),

  ('b0000000-0000-0000-0000-000000000003', 'a0000000-0000-0000-0000-000000000003',
   'TN-MED-10003', 'Orthopedic', 'Bone & Joint Care Center', 'Velachery, Chennai',
   12.9815, 80.2180, array['Tamil','English'], 20, 800, true),

  ('b0000000-0000-0000-0000-000000000004', 'a0000000-0000-0000-0000-000000000004',
   'TN-MED-10004', 'Pediatrician', 'Little Stars Children Clinic', 'Adyar, Chennai',
   13.0067, 80.2570, array['Tamil','English','Telugu'], 11, 600, true),

  -- This one lives in Puducherry so it shows up when searching from there.
  ('b0000000-0000-0000-0000-000000000005', 'a0000000-0000-0000-0000-000000000005',
   'PY-MED-20001', 'General Physician', 'Sunrise General Clinic', 'White Town, Puducherry',
   11.9340, 79.8300, array['Tamil','English','French'], 7, 350, true),

  -- This one is NOT verified yet, to test the admin verification flow.
  ('b0000000-0000-0000-0000-000000000006', 'a0000000-0000-0000-0000-000000000006',
   'PY-MED-20002', 'Gynecologist', 'Women''s Wellness Clinic', 'Lawspet, Puducherry',
   11.9420, 79.8190, array['Tamil','English'], 5, 450, false)
on conflict (id) do nothing;


-- ----------------------------------------------------------------------------
-- 2. PATIENTS (3)
-- ----------------------------------------------------------------------------
select seed_create_auth_user('c0000000-0000-0000-0000-000000000001', 'patient.ravi@test.medbridge.dev', 'Test@1234');
select seed_create_auth_user('c0000000-0000-0000-0000-000000000002', 'patient.meena@test.medbridge.dev', 'Test@1234');
select seed_create_auth_user('c0000000-0000-0000-0000-000000000003', 'patient.john@test.medbridge.dev', 'Test@1234');

insert into profiles (id, email, full_name, phone, language_preference, role)
values
  ('c0000000-0000-0000-0000-000000000001', 'patient.ravi@test.medbridge.dev', 'Ravi Shankar', '+91 9940011111', 'ta', 'patient'),
  ('c0000000-0000-0000-0000-000000000002', 'patient.meena@test.medbridge.dev', 'Meena Kandasamy', '+91 9940022222', 'ta', 'patient'),
  ('c0000000-0000-0000-0000-000000000003', 'patient.john@test.medbridge.dev', 'John Mathew', '+91 9940033333', 'en', 'patient')
on conflict (id) do nothing;

insert into patients (
  id, profile_id, date_of_birth, blood_group,
  emergency_contact_name, emergency_contact_phone, allergies
)
values
  ('d0000000-0000-0000-0000-000000000001', 'c0000000-0000-0000-0000-000000000001',
   '1990-04-12', 'B+', 'Geetha Shankar', '+91 9940099111', array['Penicillin']),

  ('d0000000-0000-0000-0000-000000000002', 'c0000000-0000-0000-0000-000000000002',
   '1985-11-02', 'O+', 'Karthik Kandasamy', '+91 9940099222', array[]::text[]),

  ('d0000000-0000-0000-0000-000000000003', 'c0000000-0000-0000-0000-000000000003',
   '1998-07-23', 'A-', 'Anna Mathew', '+91 9940099333', array['Dust','Peanuts'])
on conflict (id) do nothing;


-- ----------------------------------------------------------------------------
-- 3. NURSE (sub-account under Dr. Arun Kumar) + ADMIN
-- ----------------------------------------------------------------------------
select seed_create_auth_user('e0000000-0000-0000-0000-000000000001', 'nurse.kavitha@test.medbridge.dev', 'Test@1234');
select seed_create_auth_user('f0000000-0000-0000-0000-000000000001', 'admin@test.medbridge.dev', 'Test@1234');

insert into profiles (id, email, full_name, phone, language_preference, role)
values
  ('e0000000-0000-0000-0000-000000000001', 'nurse.kavitha@test.medbridge.dev', 'Kavitha Nurse', '+91 9950011111', 'ta', 'nurse'),
  ('f0000000-0000-0000-0000-000000000001', 'admin@test.medbridge.dev', 'MedBridge Admin', '+91 9000000000', 'en', 'admin')
on conflict (id) do nothing;

insert into sub_accounts (id, doctor_id, profile_id, role, is_active)
values
  ('11100000-0000-0000-0000-000000000001', 'b0000000-0000-0000-0000-000000000001',
   'e0000000-0000-0000-0000-000000000001', 'nurse', true)
on conflict (id) do nothing;


-- ----------------------------------------------------------------------------
-- 4. SAMPLE APPOINTMENTS (mix of upcoming + one completed for testing
--    reviews/prescriptions)
-- ----------------------------------------------------------------------------
insert into appointments (
  id, patient_id, doctor_id, scheduled_at, status, symptoms_text, symptoms_language, is_urgent
)
values
  -- upcoming, pending
  ('22200000-0000-0000-0000-000000000001',
   'd0000000-0000-0000-0000-000000000001', 'b0000000-0000-0000-0000-000000000001',
   now() + interval '2 days' + interval '10 hours', 'pending',
   'Chest pain and shortness of breath when climbing stairs.', 'en', true),

  -- upcoming, confirmed
  ('22200000-0000-0000-0000-000000000002',
   'd0000000-0000-0000-0000-000000000002', 'b0000000-0000-0000-0000-000000000005',
   now() + interval '1 day' + interval '15 hours', 'confirmed',
   'Fever and cough for the last 3 days.', 'ta', false),

  -- already completed, so you can test reviews + prescriptions
  ('22200000-0000-0000-0000-000000000003',
   'd0000000-0000-0000-0000-000000000003', 'b0000000-0000-0000-0000-000000000004',
   now() - interval '5 days', 'completed',
   'Child has a mild skin rash and itching.', 'en', false)
on conflict (id) do nothing;

-- backfill completed_at for the completed appointment above (the schema's
-- trigger only fires on UPDATE, not on this direct INSERT)
update appointments
set completed_at = now() - interval '5 days' + interval '30 minutes'
where id = '22200000-0000-0000-0000-000000000003' and completed_at is null;


-- ----------------------------------------------------------------------------
-- 5. SAMPLE DOCUMENT (so /patient/documents has something to show)
-- ----------------------------------------------------------------------------
insert into documents (id, patient_id, uploaded_by, appointment_id, doc_type, file_url, file_name, description)
values
  ('33300000-0000-0000-0000-000000000001',
   'd0000000-0000-0000-0000-000000000001', 'c0000000-0000-0000-0000-000000000001', null,
   'lab_report', 'https://example.com/sample-files/cbc_report.pdf', 'cbc_report.pdf',
   'CBC blood test report from June 2025')
on conflict (id) do nothing;


-- ----------------------------------------------------------------------------
-- 6. CLEANUP — drop the helper function (optional, keeps schema tidy)
-- ----------------------------------------------------------------------------
drop function if exists seed_create_auth_user(uuid, text, text);


-- ============================================================================
-- DONE. Test login credentials (password for ALL accounts: Test@1234)
-- ============================================================================
-- Doctors:
--   dr.arun.cardio@test.medbridge.dev     (Cardiologist, Chennai, verified)
--   dr.priya.derma@test.medbridge.dev     (Dermatologist, Chennai, verified)
--   dr.suresh.ortho@test.medbridge.dev    (Orthopedic, Chennai, verified)
--   dr.lakshmi.peds@test.medbridge.dev    (Pediatrician, Chennai, verified)
--   dr.karthik.gp@test.medbridge.dev      (General Physician, Puducherry, verified)
--   dr.fathima.gyn@test.medbridge.dev     (Gynecologist, Puducherry, NOT verified — test /admin/dashboard)
--
-- Patients:
--   patient.ravi@test.medbridge.dev
--   patient.meena@test.medbridge.dev
--   patient.john@test.medbridge.dev       (has a completed appointment w/ Dr. Lakshmi — test reviews/prescriptions)
--
-- Staff:
--   nurse.kavitha@test.medbridge.dev      (nurse under Dr. Arun Kumar)
--   admin@test.medbridge.dev              (admin)
-- ============================================================================
