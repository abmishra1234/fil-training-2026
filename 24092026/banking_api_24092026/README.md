# bank_api – Extension 6 STARTER (Authentication & Authorization)

This is the Extension 5 solution plus the scaffolding for Extension 6.
Follow **Ext6_Lab_Guide.docx**. Search the code for `TODO` to find every place you must edit:

    grep -rn "TODO" app/          # Windows PowerShell:  Select-String -Path app\*\*.py -Pattern TODO

    pip install -r requirements.txt
    del bank.db  /  rm bank.db     # once: the accounts table gets a new column
    uvicorn app.main:app --reload  # http://127.0.0.1:8000/docs
    pytest tests/test_auth1_users.py -v     # work task by task
    pytest -v                               # finish line: 108 passed

Already provided for you: `config.py` (JWT settings), `.env`, `models/user.py`,
`repositories/user_repository.py`, the new error classes in `core/errors.py`,
wiring in `main.py` and `api/v1/__init__.py`, and all acceptance tests.
