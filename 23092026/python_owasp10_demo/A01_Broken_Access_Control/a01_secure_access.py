from typing import Annotated
from fastapi import FastAPI, HTTPException, Depends # type: ignore

app = FastAPI(title="A01 Broken Access Control - Secure")

# Dummy user data and a dependency to simulate an authenticated user
users = {
    '1': {'name': 'Abinash', 'email': 'abinash@example.com'},
    '2': {'name': 'Rahul', 'email': 'rahul@example.com'}
}

async def get_current_user_id():
    # In a real app, this would come from a token/session
    return "1"

@app.get("/user/{user_id}")
async def get_user(user_id: str, current_user_id: Annotated[str, Depends(get_current_user_id)]):
    # Secure: Ensure requested resource belongs to the current user
    if user_id != current_user_id:
        raise HTTPException(status_code=403, detail="Unauthorized")
    if user_id in users:
        return users[user_id]
    raise HTTPException(status_code=404, detail="User not found")
