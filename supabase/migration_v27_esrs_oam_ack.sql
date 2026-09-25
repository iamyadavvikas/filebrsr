-- Migration V27: CSRD / ESRS filing — OAM acknowledgment protocol & channel
-- ==========================================================================
-- Tracks the regulator's acknowledgment of a submitted ESEF package: when the
-- OAM answers the manifest webhook with a JSON receipt { submission_ref,
-- received_at, ... }, the submission records the acknowledgment reference and
-- payload, plus the transport channel used (local_queue | oam_webhook |
-- sandbox). Retains the plain-text receipts of earlier submissions.
-- Idempotent. Run AFTER migration_v26_esrs_validator.sql.
-- ==========================================================================

alter table public.esrs_submissions
  add column if not exists sent_at          timestamptz,
  add column if not exists channel          text,
  add column if not exists ack_ref          text,
  add column if not exists acknowledged_at  timestamptz,
  add column if not exists ack_payload      jsonb;

-- Backfill channel from the pre-ack status vocabulary.
update public.esrs_submissions
   set channel = case
         when status like 'webhook_failed:%' then 'oam_webhook'
         when status = 'submitted'           then 'oam_webhook'
         else                                     'local_queue'
       end
 where channel is null;

drop index if exists esrs_submissions_channel_idx;
create index if not exists esrs_submissions_channel_idx
  on public.esrs_submissions(channel, acknowledged_at desc);

comment on column public.esrs_submissions.channel is
  'How the package reached the OAM: local_queue (no endpoint configured), oam_webhook (manifest webhook), sandbox (simulated receipt).';
comment on column public.esrs_submissions.ack_ref is
  'Regulator submission reference from the acknowledgment receipt.';