# Information Security Basics (SEC-POL-01)

## Passwords
Passwords must be at least 14 characters long. Passphrases are encouraged. Passwords are not force-rotated on a schedule; they must be changed immediately if a compromise is suspected. Reusing your NovaPay password on any other website is not allowed.

## Multi-factor authentication
MFA through the "NovaAuth" authenticator app is mandatory for email, VPN, the code repository and the cloud console. SMS codes are not accepted for engineering systems.

## Secrets in code
API keys, client secrets, passwords and tokens must never be committed to git, pasted into chat tools, or shared in screenshots. Use the secrets manager "VaultNova". A leaked secret must be reported to security@novapay.example within 1 hour and rotated.

## Phishing
Report suspicious emails with the "Report Phish" button. Security runs simulated phishing campaigns every quarter; employees who click are assigned a 20-minute refresher course.

## Customer data
Production customer data must never be copied to laptops or lower environments. Use the masked datasets in the "sandbox" environment for development and testing.
