import os
import uuid
import shutil
from sqlalchemy.orm import Session
from database import FileRecord, VaultMessage, new_uuid, now_utc
from config import settings

def upload_file_service(file, current_user, db: Session):
    file_id = new_uuid()
    message_id = new_uuid()
    ext = os.path.splitext(file.filename)[1]
    
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    save_path = os.path.join(settings.UPLOAD_DIR, f"{file_id}{ext}")
    
    with open(save_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    vault_msg = VaultMessage(
        id=message_id,
        sender_id=current_user.id,
        message_type="file_upload",
        payload_summary=f"Uploaded file: {file.filename}",
        created_at=now_utc()
    )
    db.add(vault_msg)
    
    file_record = FileRecord(
        id=file_id,
        owner_id=current_user.id,
        message_id=message_id,
        original_name=file.filename,
        file_size=os.path.getsize(save_path),
        mime_type=file.content_type,
        extension=ext,
        storage_path=save_path,
        created_at=now_utc()
    )
    db.add(file_record)
    
    db.commit()
    db.refresh(file_record)
    return file_record

def list_files_service(current_user, db: Session, skip=0, limit=100, filter_ext=None):
    query = db.query(FileRecord).filter(
        FileRecord.owner_id == current_user.id, 
        FileRecord.is_deleted == False
    )
    
    if filter_ext:
        query = query.filter(FileRecord.extension == filter_ext)
    
    total = query.count()
    files = query.offset(skip).limit(limit).all()
    return total, files

def get_vault_messages_service(current_user, db: Session, skip=0, limit=50):
    query = db.query(VaultMessage).filter(
        VaultMessage.sender_id == current_user.id
    ).order_by(VaultMessage.created_at.desc())
    
    total = query.count()
    messages = query.offset(skip).limit(limit).all()
    return total, messages

def delete_file_service(file_id, current_user, db: Session):
    record = db.query(FileRecord).filter(
        FileRecord.id == file_id, 
        FileRecord.owner_id == current_user.id
    ).first()
    
    if record:
        record.is_deleted = True
        record.deleted_at = now_utc()
        db.commit()

def download_file_service(file_id, current_user, db: Session):
    # Find the file record
    record = db.query(FileRecord).filter(
        FileRecord.id == file_id, 
        FileRecord.owner_id == current_user.id
    ).first()
    return record