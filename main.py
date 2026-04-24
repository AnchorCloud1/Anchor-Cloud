import os
import uuid
import io
from fastapi import Request
from datetime import datetime
from typing import Optional

from fastapi import (
    FastAPI, Depends, HTTPException, UploadFile, File,
    Query, status
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.config import settings
from database import get_db, init_db, User, FileRecord, VaultMessage
from backend.auth import (
    create_access_token, authenticate_user,
    get_current_user, get_google_auth_url, exchange_google_code,
)
from crypto import hash_password
from file_service import (
    upload_file_service, download_file_service,
    delete_file_service, list_files_service,
    get_vault_messages_service,
)
from schemas import (
    RegisterRequest, LoginRequest, TokenResponse,
    UserProfile, FileUploadResponse, FileListResponse,
    FileListItem, FileDeleteResponse,
    VaultMessageOut, VaultMessageListResponse,
    HealthResponse,
)

# ── App ──────────────────────────────────────────────────────
app = FastAPI(
    title       = "Anchor Cloud API",
    description = "Zero-Knowledge Secure File Vault",
    version     = "1.0.0",
    docs_url    = "/api/docs",
    redoc_url   = "/api/redoc",
    openapi_url = "/api/openapi.json",
)

# ── CORS ─────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins     = ["*"],
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)

# ── Static files ─────────────────────────────────────────────
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# ── Startup ──────────────────────────────────────────────────
@app.on_event("startup")
def on_startup():
    print(f"[Anchor Cloud] Starting in '{settings.APP_ENV}' mode...")
    init_db()
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    print(f"[Anchor Cloud] Ready → http://localhost:{settings.APP_PORT}/")
    print(f"[Anchor Cloud] API docs → http://localhost:{settings.APP_PORT}/api/docs")


# ── Frontend ─────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def serve_frontend():
    html_path = os.path.join(os.path.dirname(__file__), "index.html")
    if os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>Anchor Cloud — frontend not found.</h1>", status_code=404)


# ════════════════════════════════════════════════════════════
# SYSTEM
# ════════════════════════════════════════════════════════════

@app.get("/api/health", response_model=HealthResponse, tags=["System"])
def health_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception:
        db_status = "error"
    return HealthResponse(status="ok", version="1.0.0", db=db_status)


# ════════════════════════════════════════════════════════════
# AUTH
# ════════════════════════════════════════════════════════════

@app.post("/api/auth/register", response_model=TokenResponse, tags=["Auth"])
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    identifier = body.identifier.strip()
    is_email   = "@" in identifier

    if is_email:
        existing = db.query(User).filter(User.email == identifier.lower()).first()
    else:
        existing = db.query(User).filter(User.phone == identifier).first()

    if existing:
        field = "email address" if is_email else "phone number"
        raise HTTPException(status_code=409, detail=f"Account with this {field} already exists.")

    user = User(
        id              = str(uuid.uuid4()),
        name            = body.name.strip(),
        email           = identifier.lower() if is_email else None,
        phone           = identifier if not is_email else None,
        hashed_password = hash_password(body.password),
        is_active       = True,
        plan            = "free",
        created_at      = datetime.utcnow(),
    )
    db.add(user)

    welcome = VaultMessage(
        id              = str(uuid.uuid4()),
        sender_id       = user.id,
        message_type    = "system",
        payload_summary = f"Welcome to Anchor Cloud, {user.name}! Your vault is ready.",
        created_at      = datetime.utcnow(),
    )
    db.add(welcome)
    db.commit()
    db.refresh(user)

    token = create_access_token(user.id, {"name": user.name})
    return TokenResponse(
        token=token, user_id=user.id, name=user.name,
        email=user.email, avatar_url=user.avatar_url, plan=user.plan,
    )


@app.post("/api/auth/login", response_model=TokenResponse, tags=["Auth"])
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = authenticate_user(db, body.identifier.strip(), body.password)
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect credentials.")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account deactivated.")

    user.last_login = datetime.utcnow()
    db.commit()

    token = create_access_token(user.id, {"name": user.name})
    return TokenResponse(
        token=token, user_id=user.id, name=user.name,
        email=user.email, avatar_url=user.avatar_url, plan=user.plan,
    )


@app.get("/api/auth/google", tags=["Auth"])
def google_login():
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=501, detail="Google OAuth not configured.")
    return RedirectResponse(url=get_google_auth_url())


@app.get("/api/auth/google/callback", tags=["Auth"])
async def google_callback(code: str = Query(...), state: str = Query(""), db: Session = Depends(get_db)):
    info      = await exchange_google_code(code)
    google_id = info["google_id"]
    email     = info["email"]
    name      = info["name"]
    avatar    = info["avatar_url"]

    user = db.query(User).filter(User.google_id == google_id).first()
    if not user and email:
        user = db.query(User).filter(User.email == email.lower()).first()
        if user:
            user.google_id  = google_id
            user.avatar_url = avatar or user.avatar_url

    if not user:
        user = User(
            id           = str(uuid.uuid4()),
            name         = name,
            email        = email.lower() if email else None,
            google_id    = google_id,
            google_email = email,
            avatar_url   = avatar,
            is_active    = True,
            plan         = "free",
            created_at   = datetime.utcnow(),
        )
        db.add(user)
        db.add(VaultMessage(
            id=str(uuid.uuid4()), sender_id=user.id,
            message_type="system",
            payload_summary=f"Welcome to Anchor Cloud, {name}! Signed in via Google.",
            created_at=datetime.utcnow(),
        ))

    user.last_login = datetime.utcnow()
    db.commit()
    db.refresh(user)

    token = create_access_token(user.id, {"name": user.name})
    return RedirectResponse(url=f"/?token={token}&name={user.name}")


# ── User ─────────────────────────────────────────────────────

@app.get("/api/user/me", response_model=UserProfile, tags=["User"])
def get_profile(current_user: User = Depends(get_current_user)):
    return current_user


# ════════════════════════════════════════════════════════════
# FILES
# ════════════════════════════════════════════════════════════

@app.post("/api/files/upload", response_model=FileUploadResponse, tags=["Files"])
async def upload_file(
    file        : UploadFile    = File(...),
    current_user: User          = Depends(get_current_user),
    db          : Session       = Depends(get_db),
):
    record = await upload_file_service(file, current_user, db)
    return FileUploadResponse(
        uuid=record.id, name=record.original_name, size=record.file_size,
        mime_type=record.mime_type, extension=record.extension,
        encryption_algo=record.encryption_algo, is_encrypted=record.is_encrypted,
        message_id=record.message_id, uploaded_at=record.created_at,
    )


@app.get("/api/files", response_model=FileListResponse, tags=["Files"])
def list_files(
    skip        : int           = Query(0, ge=0),
    limit       : int           = Query(100, ge=1, le=500),
    ext         : Optional[str] = Query(None),
    current_user: User          = Depends(get_current_user),
    db          : Session       = Depends(get_db),
):
    total, files = list_files_service(current_user, db, skip=skip, limit=limit, filter_ext=ext)
    items = [
        FileListItem(
            uuid=f.id, name=f.original_name, size=f.file_size,
            mime_type=f.mime_type, extension=f.extension,
            encryption_algo=f.encryption_algo, is_encrypted=f.is_encrypted,
            uploaded_at=f.created_at,
        ) for f in files
    ]
    return FileListResponse(total=total, files=items)


@app.get("/api/files/download/{file_id}", tags=["Files"])
def download_file(
    file_id     : str,
    current_user: User    = Depends(get_current_user),
    db          : Session = Depends(get_db),
):
    plaintext, filename, mime_type = download_file_service(file_id, current_user, db)
    return StreamingResponse(
        content    = io.BytesIO(plaintext),
        media_type = mime_type,
        headers    = {
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length"     : str(len(plaintext)),
            "X-Anchor-UUID"      : file_id,
        }
    )


@app.delete("/api/files/{file_id}", response_model=FileDeleteResponse, tags=["Files"])
def delete_file(
    file_id     : str,
    current_user: User    = Depends(get_current_user),
    db          : Session = Depends(get_db),
):
    delete_file_service(file_id, current_user, db)
    return FileDeleteResponse(detail="File permanently deleted from vault.", uuid=file_id)


@app.get("/api/files/{file_id}/info", response_model=FileListItem, tags=["Files"])
def get_file_info(
    file_id     : str,
    current_user: User    = Depends(get_current_user),
    db          : Session = Depends(get_db),
):
    record = db.query(FileRecord).filter(
        FileRecord.id == file_id,
        FileRecord.owner_id == current_user.id,
        FileRecord.is_deleted == False,
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="File not found.")
    return FileListItem(
        uuid=record.id, name=record.original_name, size=record.file_size,
        mime_type=record.mime_type, extension=record.extension,
        encryption_algo=record.encryption_algo, is_encrypted=record.is_encrypted,
        uploaded_at=record.created_at,
    )


# ════════════════════════════════════════════════════════════
# VAULT MESSAGES
# ════════════════════════════════════════════════════════════

@app.get("/api/vault/messages", response_model=VaultMessageListResponse, tags=["Vault"])
def get_vault_messages(
    skip        : int     = Query(0, ge=0),
    limit       : int     = Query(50, ge=1, le=200),
    current_user: User    = Depends(get_current_user),
    db          : Session = Depends(get_db),
):
    total, messages = get_vault_messages_service(current_user, db, skip=skip, limit=limit)
    out = []
    for msg in messages:
        fr = msg.file_record
        out.append(VaultMessageOut(
            id=msg.id, message_type=msg.message_type,
            payload_summary=msg.payload_summary,
            file_uuid = fr.id           if fr and not fr.is_deleted else None,
            file_name = fr.original_name if fr and not fr.is_deleted else None,
            file_size = fr.file_size     if fr and not fr.is_deleted else None,
            created_at=msg.created_at,
        ))
    return VaultMessageListResponse(total=total, messages=out)


# ════════════════════════════════════════════════════════════
# DEV ONLY
# ════════════════════════════════════════════════════════════

if settings.APP_ENV == "development":

    @app.get("/api/dev/users", tags=["Dev"])
    def dev_list_users(db: Session = Depends(get_db)):
        users = db.query(User).all()
        return [{"id": u.id, "name": u.name, "email": u.email, "plan": u.plan} for u in users]

    @app.delete("/api/dev/reset", tags=["Dev"])
    def dev_reset(db: Session = Depends(get_db)):
        db.query(VaultMessage).delete()
        db.query(FileRecord).delete()
        db.query(User).delete()
        db.commit()
        return {"detail": "Database wiped."}

    @app.post("/process-mock-payment", tags=["Dev"])
    def process_mock_payment(request: Request, db: Session = Depends(get_db)):
        return {"status": "success", "message": "Pro features unlocked"}
    

    @app.route('/process-mock-payment', methods=['POST'])
    def process_mock_payment():
    # Simulate a delay (for the 'pro' feel)
        import time
        time.sleep(1.5) 
        try:
            return jsonify({"status": "success", "message": "Pro features unlocked"}), 200
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500
        
    @app.route('/process-mock-payment', methods=['POST'])
    def process_mock_payment():
        data = request.get_json()
        method = data.get('method')
        plan = data.get('plan')
    
        import time
        time.sleep(2)
    
        print(f"--- DEMO MODE: Processing {plan} payment via {method} ---")
    
        return jsonify({"status": "success", "message": f"Processed via {method}"}), 200