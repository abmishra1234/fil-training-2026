# Aceranker.ai Privacy and Record Classes (SEC-PROC-RECORD)

## Record classification
Classify a record before applying retention or deletion. Identity verification evidence, transaction journals, application logs and support conversations belong to different record classes. One customer account may reference several classes with different deletion dates.

## KYC document access
Only authorised identity operations staff may access unmasked KYC documents. Development teams use masked test fixtures. Access permission does not shorten the KYC retention period or permit downloading documents to a personal device.

## Marketing consent deletion
An optional marketing mailing-list entry is removed within 7 days of a verified opt-out. Retain only the minimal suppression marker needed to respect that preference. This process does not delete payment transaction records subject to retention requirements.

## Recruitment records
Unsuccessful candidate interview notes are retained for 6 months after the hiring decision unless a documented hold applies. The recruiting team owns the deletion queue. Candidate notes are not KYC onboarding records or employee payroll records.

## Temporary export files
Approved operational exports expire after 7 days in managed storage. Delete the export earlier when its purpose is complete. Deleting a temporary export does not delete the authoritative transaction journal or alter its record retention requirement.

## Legal hold
The legal team may place a documented hold on a specified record set. Suspend scheduled deletion for those records until the hold is released. The hold must identify its scope and owner; a vague team request to retain everything is insufficient.

## Verified deletion request
Verify requester identity before processing a customer deletion request. List records eligible for deletion separately from records still under retention or legal hold. Explain the remaining record categories without exposing another customer's information.

## Backup deletion propagation
Deletion workflows record when removal from active systems is complete and how expired backup copies age out. Restrict any restored backup before it returns to service and reapply completed deletion instructions. Backup recovery must not silently reactivate a deleted marketing profile.
