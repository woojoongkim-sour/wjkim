from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from pydantic import BaseModel, EmailStr

from app.core.database import get_db
from app.models.user import User
from app.models.email import ImapAccount, CollectedEmail
from app.models.mapping import EmailCustomerMapping, CustomerAlias
from app.services.auth import get_current_active_user, get_admin_user
from app.services.email_collector import ImapCollector

router = APIRouter(prefix="/email", tags=["Email"])


class ImapAccountCreate(BaseModel):
    email_address: str
    display_name: Optional[str] = None
    imap_host: str
    imap_port: int = 993
    use_ssl: bool = True
    username: str
    password: str
    folder: str = "INBOX"
    poll_interval_minutes: int = 15


class ImapAccountResponse(BaseModel):
    id: int
    email_address: str
    display_name: Optional[str]
    imap_host: str
    imap_port: int
    use_ssl: bool
    folder: str
    poll_interval_minutes: int
    is_active: bool
    last_sync_at: Optional[str]
    last_error: Optional[str]
    
    model_config = {"from_attributes": True}


class EmailMappingCreate(BaseModel):
    email_pattern: str
    pattern_type: str = "exact"
    customer_id: int


class CustomerAliasCreate(BaseModel):
    alias: str
    alias_type: str = "name"
    customer_id: int


@router.get("/accounts", response_model=List[ImapAccountResponse])
async def list_imap_accounts(
    customer_id: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """List IMAP accounts."""
    query = select(ImapAccount)
    if customer_id:
        query = query.where(ImapAccount.customer_id == customer_id)
    
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/accounts", response_model=ImapAccountResponse)
async def create_imap_account(
    account_data: ImapAccountCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new IMAP account."""
    from app.services.auth import get_password_hash
    
    account = ImapAccount(
        customer_id=current_user.customer_id,
        email_address=account_data.email_address,
        display_name=account_data.display_name,
        imap_host=account_data.imap_host,
        imap_port=account_data.imap_port,
        use_ssl=account_data.use_ssl,
        username=account_data.username,
        hashed_password=get_password_hash(account_data.password),
        folder=account_data.folder,
        poll_interval_minutes=account_data.poll_interval_minutes,
        created_by=current_user.username
    )
    
    db.add(account)
    await db.commit()
    await db.refresh(account)
    
    return account


@router.post("/accounts/{account_id}/test")
async def test_imap_account(
    account_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Test IMAP account connection."""
    import imaplib
    
    result = await db.execute(
        select(ImapAccount).where(ImapAccount.id == account_id)
    )
    account = result.scalar_one_or_none()
    
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    try:
        if account.use_ssl:
            mail = imaplib.IMAP4_SSL(account.imap_host, account.imap_port)
        else:
            mail = imaplib.IMAP4(account.imap_host, account.imap_port)
        
        mail.login(account.username, account.hashed_password)
        status, _ = mail.list()
        mail.logout()
        
        return {"status": "success", "message": "Connection successful"}
        
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/accounts/{account_id}/collect")
async def collect_emails(
    account_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Trigger email collection from an IMAP account."""
    collector = ImapCollector(db)
    result = await collector.collect_from_account(account_id)
    return result


@router.post("/accounts/{account_id}/sync")
async def sync_emails(
    account_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Sync emails in background."""
    collector = ImapCollector(db)
    background_tasks.add_task(collector.collect_from_account, account_id)
    return {"status": "scheduled", "message": "Email collection started"}


@router.delete("/accounts/{account_id}")
async def delete_imap_account(
    account_id: int,
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete an IMAP account (admin only)."""
    result = await db.execute(
        select(ImapAccount).where(ImapAccount.id == account_id)
    )
    account = result.scalar_one_or_none()
    
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    await db.delete(account)
    await db.commit()
    
    return {"status": "deleted"}


@router.get("/emails", response_model=List[dict])
async def list_emails(
    customer_id: Optional[int] = None,
    classification_status: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """List collected emails."""
    query = select(CollectedEmail)
    
    if customer_id:
        query = query.where(CollectedEmail.customer_id == customer_id)
    if classification_status:
        query = query.where(CollectedEmail.classification_status == classification_status)
    
    query = query.order_by(CollectedEmail.received_at.desc())
    query = query.offset(skip).limit(limit)
    
    result = await db.execute(query)
    emails = result.scalars().all()
    
    return [
        {
            "id": e.id,
            "subject": e.subject,
            "sender_email": e.sender_email,
            "sender_name": e.sender_name,
            "customer_id": e.customer_id,
            "classification_status": e.classification_status,
            "received_at": e.received_at.isoformat() if e.received_at else None,
            "attachments_count": e.attachments_count
        }
        for e in emails
    ]


@router.get("/emails/{email_id}")
async def get_email(
    email_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get email details."""
    result = await db.execute(
        select(CollectedEmail).where(CollectedEmail.id == email_id)
    )
    email = result.scalar_one_or_none()
    
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")
    
    import json
    
    return {
        "id": email.id,
        "subject": email.subject,
        "sender_email": email.sender_email,
        "sender_name": email.sender_name,
        "recipients": json.loads(email.recipients) if email.recipients else [],
        "cc_list": json.loads(email.cc_list) if email.cc_list else [],
        "body_text": email.body_text,
        "body_html": email.body_html,
        "customer_id": email.customer_id,
        "classification_status": email.classification_status,
        "received_at": email.received_at.isoformat() if email.received_at else None,
        "attachments": json.loads(email.attachments_info) if email.attachments_info else []
    }


@router.post("/mappings", status_code=201)
async def create_email_mapping(
    mapping_data: EmailMappingCreate,
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Create email-to-customer mapping."""
    mapping = EmailCustomerMapping(
        customer_id=mapping_data.customer_id,
        email_pattern=mapping_data.email_pattern,
        pattern_type=mapping_data.pattern_type
    )
    
    db.add(mapping)
    await db.commit()
    await db.refresh(mapping)
    
    return mapping


@router.post("/aliases", status_code=201)
async def create_customer_alias(
    alias_data: CustomerAliasCreate,
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Create customer alias for email classification."""
    alias = CustomerAlias(
        customer_id=alias_data.customer_id,
        alias=alias_data.alias,
        alias_type=alias_data.alias_type
    )
    
    db.add(alias)
    await db.commit()
    await db.refresh(alias)
    
    return alias
