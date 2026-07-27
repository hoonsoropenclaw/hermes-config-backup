# FastAPI JWT Authentication Patterns & Pitfalls
**Created**: 2026-07-27 (Cycle 544, metacognitive-learner D3-learn)
**Status**: Active — JWT auth confirmed gap (0 sessions matched in session_search)

---

## Core Pattern: JWT + bcrypt via python-jose + passlib

```python
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional

# === CONFIG ===
SECRET_KEY = "openssl rand -hex 32"  # Generate with: openssl rand -hex 32
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# === PASSWORD HASHING ===
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

# === JWT UTILS ===
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

# === OAUTH2 SCHEME ===
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

# === DEPENDENCY ===
async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    payload = decode_token(token)
    user_id: str = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    return {"user_id": user_id}

# === ROUTES ===
@app.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    access_token = create_access_token(data={"sub": user.user_id})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/protected")
async def protected_route(current_user: dict = Depends(get_current_user)):
    return {"user": current_user, "message": "You have access!"}
```

---

## Argon2 (Prefer for New Projects — GPU-crack Resistant)

```python
from passlib.context import CryptContext
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
# Argon2 is more resistant to GPU cracking than bcrypt — use this for new projects
```

---

## Key Libraries

| Library | Purpose |
|---------|---------|
| `python-jose[cryptography]` | JWT encode/decode (HS256, RS256) |
| `passlib[bcrypt]` or `passlib[argon2]` | Password hashing (never store plaintext) |
| `fastapi.security.OAuth2PasswordBearer` | Extract Bearer token from Authorization header |

Install: `pip install "python-jose[cryptography]" "passlib[bcrypt]"`

---

## Token Storage (Frontend)

```javascript
// Store
localStorage.setItem("access_token", data.access_token)

// Use in requests
fetch("/protected", {
  headers: { "Authorization": `Bearer ${localStorage.getItem("access_token")}` }
})

// For refresh tokens: store in httpOnly cookie (never accessible to JS)
```

---

## Common Error Patterns

| Error | Cause | Fix |
|-------|-------|-----|
| `401 Unauthorized` on valid token | Token expired | Check `exp` claim; implement refresh token flow |
| `JWTError: Signature verification failed` | Wrong SECRET_KEY | Ensure same key used for encode/decode |
| `Missing token` in protected route | OAuth2PasswordBearer not injected | Add `token: str = Depends(oauth2_scheme)` param |
| `401` immediately after login | Token not returned correctly | Check `create_access_token` payload has `sub` field |

---

## Refresh Token Pattern

```python
# Login returns both access + refresh tokens
@app.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect credentials")
    access_token = create_access_token(data={"sub": user.user_id})
    refresh_token = create_access_token(
        data={"sub": user.user_id, "type": "refresh"},
        expires_delta=timedelta(days=7)
    )
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

@app.post("/refresh")
async def refresh(refresh_token: str = Depends(oauth2_scheme)):
    payload = decode_token(refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Not a refresh token")
    new_access_token = create_access_token(data={"sub": payload["sub"]})
    return {"access_token": new_access_token}
```

---

## If→Then

**If** FastAPI route needs authenticated user **then** inject `get_current_user` dependency which decodes JWT from `OAuth2PasswordBearer` header, raising 401 if token invalid or expired.

**If** storing user passwords **then** never store plain text — use `passlib.context.CryptContext(schemes=["argon2"])` for hashing and `pwd_context.verify(plain, hashed)` for verification.

**If** JWT token expires frequently **then** implement refresh token flow (store refresh token in httpOnly cookie) rather than forcing frequent re-logins.

---

## Gap Signal (Cycle 544)

session_search for "authentication JWT OAuth2 API security FastAPI" returned **0 matches** — confirmed gap. This reference file is the first documentation of this pattern for the agent.
