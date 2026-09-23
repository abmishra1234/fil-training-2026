# Transfer History: Manual Test Guide

Use `GET /accounts/transfers` or its versioned equivalent, `GET /api/v1/accounts/transfers`. Both return a JSON list of transfer-history rows.

Start the API before testing:

```powershell
uvicorn app.main:app --reload
```

The response headers describe the complete result set:

| Header | Meaning |
| --- | --- |
| `X-Total-Count` | Number of records matching the filters, before pagination. |
| `X-Page` | Returned page number. |
| `X-Page-Size` | Maximum records in this response. |
| `X-Total-Pages` | Number of available pages. |

## List and paginate

```powershell
# First 20 records, newest first (the defaults are page 1 and page_size 50)
curl.exe -i "http://127.0.0.1:8000/accounts/transfers?page=1&page_size=20"

# Second page
curl.exe -i "http://127.0.0.1:8000/api/v1/accounts/transfers?page=2&page_size=20"
```

## Filter

All filters can be combined.

```powershell
# Transfers sent by account 1
curl.exe -i "http://127.0.0.1:8000/accounts/transfers?from_account_id=1"

# Transfers received by account 2, with an amount from 10 through 100
curl.exe -i "http://127.0.0.1:8000/accounts/transfers?to_account_id=2&min_amount=10&max_amount=100"

# Successful transfers within an inclusive UTC time range
curl.exe -i "http://127.0.0.1:8000/accounts/transfers?transfer_status=SUCCESS&start_timestamp=2026-09-23T00:00:00&end_timestamp=2026-09-23T23:59:59"
```

## Sort

`sort_by` accepts `transfer_id`, `timestamp`, `amount`, or `transfer_status`. `sort_order` accepts `asc` or `desc`.

```powershell
# Smallest transfers first
curl.exe -i "http://127.0.0.1:8000/accounts/transfers?sort_by=amount&sort_order=asc"

# Oldest transfers first, one page of 25 results
curl.exe -i "http://127.0.0.1:8000/accounts/transfers?sort_by=timestamp&sort_order=asc&page=1&page_size=25"
```

Invalid page numbers, page sizes above 1,000, negative amount bounds, and unsupported sort values return HTTP `422`.
