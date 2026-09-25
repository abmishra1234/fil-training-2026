# Authentication and Authorization in Swagger UI

This guide walks through registering a customer, signing in, authorizing Swagger, and using protected banking endpoints. Open Swagger at **http://127.0.0.1:8000/docs** while the API is running.

## 1. Start the API

From the `banking_api` project directory, install requirements and start the server:

```bash
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

Wait for `Application startup complete` in the terminal, then open the Swagger URL above.

## 2. Register a customer

1. Expand **POST `/api/v1/auth/register`** under **Auth**.
2. Select **Try it out**.
3. Enter a username (3–32 characters; letters, numbers, `_`, `.`, and `-` are allowed) and a password (15–128 characters).

   ```json
   {
     "username": "asha.k",
     "password": "Correct-Horse-Battery-9"
   }
   ```

4. Select **Execute**. A successful response is `201` and includes the user's ID, username, role, active status, and creation time. New registrations always receive the `CUSTOMER` role; do not include a role in the request.

If you already registered, skip this step and sign in with that account.

## 3. Sign in and get a JWT

1. Expand **POST `/api/v1/auth/token`** under **Auth** and select **Try it out**.
2. Enter your username and password in the form fields. This endpoint uses form data, not a JSON request body.
3. Select **Execute**. A successful response contains an `access_token`, `token_type` (`bearer`), and `expires_in` (seconds). The default token lifetime is 15 minutes.
4. Copy the complete value of `access_token` from the response.

## 4. Authorize Swagger

1. Select **Authorize** near the top of the Swagger page.
2. In the OAuth2 password-flow dialog, enter the same username and password used to sign in.
3. Select **Authorize**, then close the dialog.

Swagger requests a token from `/api/v1/auth/token` and attaches it as `Authorization: Bearer <token>` to protected calls. You do not need to paste the word `Bearer` into the username or password fields. When the token expires, select **Authorize** again and sign in again.

## 5. Confirm the signed-in identity

Expand **GET `/api/v1/auth/me`**, select **Try it out**, then **Execute**. The response should show your account and `CUSTOMER` role. If you see `401`, authorize again or sign in with valid credentials.

## 6. Try customer endpoints

With Swagger authorized as a customer:

1. Use **POST `/api/v1/accounts/`** to create an account. Example body:

   ```json
   { "owner_name": "Asha Kumar" }
   ```

2. Use **GET `/api/v1/accounts/`** to list your accounts and note an account `id`.
3. Use **POST `/api/v1/accounts/{account_id}/deposit`** with that ID and body `{"amount": 100}` to deposit.
4. Use **GET `/api/v1/accounts/{account_id}`** to view the account.

Customers must be authenticated for account and money operations. They can view and operate only accounts they own. Accessing another customer's account is hidden as `404`; an unauthenticated request returns `401`.

## 7. Try ADMIN-only operations (optional)

The local development configuration can create a bootstrap administrator at startup when `ADMIN_USERNAME` and `ADMIN_PASSWORD` are configured in `.env`. The sample project's development values are:

- Username: `bank.admin`
- Password: `Admin-Passphrase-2026!`

Use your configured values if they differ. Treat these sample credentials as development-only and change them before using a shared or deployed environment.

To use the administrator in Swagger, select **Authorize**, sign in with the admin credentials, then try:

- **GET `/api/v1/admin/users`** to list users.
- **PATCH `/api/v1/admin/users/{user_id}`** with `{"is_active": false}` to disable a user, or `true` to enable one.
- **PUT `/api/v1/accounts/{account_id}/kyc-status`** with `{"kyc_compliant": true}` to update an account's KYC status.

These operations require the `ADMIN` role. A customer receives `403` if they try an admin-only operation. An administrator can view all accounts, but cannot move money from a customer's account.

## Common responses

| Status | Meaning | What to do |
|---|---|---|
| `200` / `201` | Request succeeded | Review the response body. |
| `401` | Missing, invalid, or expired token; or incorrect login | Use **Authorize** and sign in again. |
| `403` | Signed-in user lacks the required role | Sign in with an administrator account if the operation is admin-only. |
| `404` | Resource does not exist or is not visible to this customer | Check the ID and account ownership. |
| `409` | Username already registered | Choose a different username or sign in to the existing account. |
| `422` | Request fields failed validation | Check the schema, required fields, and formats shown in Swagger. |

## Notes

- Use the versioned `/api/v1/...` endpoints shown above. Legacy `/accounts/...` routes are protected too, but `/api/v1` is the recommended API.
- Swagger's **Authorize** button manages the bearer token for protected endpoints. Registration is public and does not sign you in automatically.
- Passwords are stored as hashes. The API does not return passwords or password hashes.
- Account ownership is checked by the server on each request. Changing a token's contents or role does not grant access.
