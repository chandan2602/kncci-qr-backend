from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
import os
import uuid
import shutil
from pathlib import Path

from database import get_db
from models import KNCCIQRForm, ApplicationStatus
from schemas import ApplicationUpdate, ApplicationResponse, DashboardStats
from services.email_service import EmailService

router = APIRouter(prefix="/api", tags=["applications"])

# Ensure uploads directory exists
UPLOAD_DIR = Path("uploads/documents")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

async def save_uploaded_file(file: UploadFile, application_id: int, doc_type: str) -> str:
    """Save uploaded file to disk and return the file path"""
    # Generate unique filename
    file_extension = Path(file.filename).suffix
    unique_filename = f"{application_id}_{doc_type}_{uuid.uuid4().hex}{file_extension}"
    file_path = UPLOAD_DIR / unique_filename
    
    # Save file to disk
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    return str(file_path)

@router.get("/applications", response_model=List[ApplicationResponse])
async def get_all_applications(db: Session = Depends(get_db)):
    """Get all applications for counselor dashboard"""
    try:
        applications = db.query(KNCCIQRForm).order_by(KNCCIQRForm.created_at.desc()).all()
        return applications
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/applications/status/{status}")
async def get_applications_by_status(status: ApplicationStatus, db: Session = Depends(get_db)):
    """Get applications by status"""
    try:
        applications = db.query(KNCCIQRForm).filter(
            KNCCIQRForm.status == status
        ).order_by(KNCCIQRForm.created_at.desc()).all()
        return applications
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/applications/{application_id}", response_model=ApplicationResponse)
async def get_application(application_id: int, db: Session = Depends(get_db)):
    """Get specific application details"""
    try:
        application = db.query(KNCCIQRForm).filter(KNCCIQRForm.id == application_id).first()
        if not application:
            raise HTTPException(status_code=404, detail="Application not found")
        return application
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/applications/search/{email}")
async def search_application_by_email(email: str, db: Session = Depends(get_db)):
    """Search application by email"""
    try:
        application = db.query(KNCCIQRForm).filter(KNCCIQRForm.email == email).first()
        if not application:
            raise HTTPException(status_code=404, detail="Application not found")
        return application
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/applications/{application_id}/status")
async def update_application_status(
    application_id: int, 
    update: ApplicationUpdate, 
    db: Session = Depends(get_db)
):
    """Update application status (counselor actions)"""
    try:
        application = db.query(KNCCIQRForm).filter(KNCCIQRForm.id == application_id).first()
        if not application:
            raise HTTPException(status_code=404, detail="Application not found")
        
        application.status = update.status
        if update.counselor_notes:
            application.counselor_notes = update.counselor_notes
        if update.payment_amount:
            application.payment_amount = update.payment_amount
        application.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(application)
        
        return {
            "success": True,
            "message": f"Application status updated to {update.status}",
            "application": application
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/applications/{application_id}/documents")
async def upload_documents(
    application_id: int,
    document1: UploadFile = File(...),
    document2: UploadFile = File(...),
    document3: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload documents for an application"""
    try:
        application = db.query(KNCCIQRForm).filter(KNCCIQRForm.id == application_id).first()
        if not application:
            raise HTTPException(status_code=404, detail="Application not found")
        
        # Validate file types
        allowed_types = ["application/pdf", "image/jpeg", "image/png", "image/jpg"]
        for doc in [document1, document2, document3]:
            if doc.content_type not in allowed_types:
                raise HTTPException(status_code=400, detail=f"Invalid file type: {doc.content_type}")
        
        # Save files to disk and get file paths
        doc1_path = await save_uploaded_file(document1, application_id, "gov_id")
        doc2_path = await save_uploaded_file(document2, application_id, "address_proof")
        doc3_path = await save_uploaded_file(document3, application_id, "education_cert")
        
        # Store file paths in database
        application.document1 = doc1_path
        application.document2 = doc2_path
        application.document3 = doc3_path
        application.document1_name = document1.filename
        application.document2_name = document2.filename
        application.document3_name = document3.filename
        application.status = ApplicationStatus.DOCUMENTS_UPLOADED
        application.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(application)
        
        return {
            "success": True,
            "message": "Documents uploaded successfully",
            "application_id": application_id,
            "files_saved": {
                "document1": doc1_path,
                "document2": doc2_path,
                "document3": doc3_path
            }
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/applications/{application_id}/documents/{doc_number}")
async def download_document(application_id: int, doc_number: int, db: Session = Depends(get_db)):
    """Download a specific document"""
    try:
        application = db.query(KNCCIQRForm).filter(KNCCIQRForm.id == application_id).first()
        if not application:
            raise HTTPException(status_code=404, detail="Application not found")
        
        doc_path = None
        doc_name = None
        
        if doc_number == 1:
            doc_path = application.document1
            doc_name = application.document1_name
        elif doc_number == 2:
            doc_path = application.document2
            doc_name = application.document2_name
        elif doc_number == 3:
            doc_path = application.document3
            doc_name = application.document3_name
        else:
            raise HTTPException(status_code=400, detail="Invalid document number")
        
        if not doc_path or not os.path.exists(doc_path):
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Return file response for download
        return FileResponse(
            path=doc_path,
            filename=doc_name,
            media_type='application/octet-stream'
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/applications/{application_id}/documents/status")
async def get_document_status(application_id: int, db: Session = Depends(get_db)):
    """Get document upload status for an application"""
    try:
        application = db.query(KNCCIQRForm).filter(KNCCIQRForm.id == application_id).first()
        if not application:
            raise HTTPException(status_code=404, detail="Application not found")
        
        documents_status = {
            "document1": {
                "uploaded": bool(application.document1),
                "filename": application.document1_name,
                "exists_on_disk": bool(application.document1 and os.path.exists(application.document1))
            },
            "document2": {
                "uploaded": bool(application.document2),
                "filename": application.document2_name,
                "exists_on_disk": bool(application.document2 and os.path.exists(application.document2))
            },
            "document3": {
                "uploaded": bool(application.document3),
                "filename": application.document3_name,
                "exists_on_disk": bool(application.document3 and os.path.exists(application.document3))
            }
        }
        
        return {
            "application_id": application_id,
            "status": application.status,
            "documents": documents_status
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
@router.post("/applications/{application_id}/request-documents")
async def request_documents(application_id: int, notes: str = Form(...), db: Session = Depends(get_db)):
    """Counselor requests documents from user"""
    try:
        application = db.query(KNCCIQRForm).filter(KNCCIQRForm.id == application_id).first()
        if not application:
            raise HTTPException(status_code=404, detail="Application not found")
        
        print(f"Found application: ID={application.id}, Email={application.email}, Name={application.name}")
        
        application.status = ApplicationStatus.DOCUMENTS_REQUESTED
        application.counselor_notes = notes
        application.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(application)
        
        # Send document request email with detailed logging
        email_sent = False
        try:
            print(f"Attempting to send email to: {application.email}")
            email_sent = await EmailService.send_document_request_email(application.email, application.name, notes)
            print(f"Email send result: {email_sent}")
        except Exception as email_error:
            print(f"Failed to send document request email: {str(email_error)}")
            print(f"Error type: {type(email_error).__name__}")
        
        return {
            "success": True,
            "message": "Documents requested successfully",
            "email_sent_to": application.email,
            "email_sent_successfully": email_sent,
            "application_name": application.name,
            "notes_sent": notes
        }
    except Exception as e:
        db.rollback()
        print(f"Database error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/applications/{application_id}/reject")
async def reject_application(application_id: int, reason: str = Form(...), db: Session = Depends(get_db)):
    """Counselor rejects an application"""
    try:
        application = db.query(KNCCIQRForm).filter(KNCCIQRForm.id == application_id).first()
        if not application:
            raise HTTPException(status_code=404, detail="Application not found")
        
        application.status = ApplicationStatus.REJECTED
        application.counselor_notes = reason
        application.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(application)
        
        # Send rejection email
        try:
            await EmailService.send_rejection_email(application.email, application.name, reason)
        except Exception as email_error:
            print(f"Failed to send rejection email: {str(email_error)}")
        
        return {
            "success": True,
            "message": "Application rejected",
            "email_sent_to": application.email
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/applications/{application_id}/send-payment-link")
async def send_payment_link(application_id: int, amount: float = Form(299.0), db: Session = Depends(get_db)):
    """Send payment link to user"""
    try:
        application = db.query(KNCCIQRForm).filter(KNCCIQRForm.id == application_id).first()
        if not application:
            raise HTTPException(status_code=404, detail="Application not found")
        
        application.status = ApplicationStatus.PAYMENT_REQUESTED
        application.payment_amount = amount
        application.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(application)
        
        # Send payment request email
        try:
            await EmailService.send_payment_request_email(application.email, application.name, amount)
        except Exception as email_error:
            print(f"Failed to send payment request email: {str(email_error)}")
        
        return {
            "success": True,
            "message": "Payment link sent successfully",
            "amount": amount,
            "email_sent_to": application.email
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/applications/{application_id}/confirm-payment")
async def confirm_payment(application_id: int, db: Session = Depends(get_db)):
    """Counselor confirms payment completion"""
    try:
        application = db.query(KNCCIQRForm).filter(KNCCIQRForm.id == application_id).first()
        if not application:
            raise HTTPException(status_code=404, detail="Application not found")
        
        application.status = ApplicationStatus.PAYMENT_COMPLETED
        application.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(application)
        
        # Send approval email
        try:
            await EmailService.send_approval_email(application.email, application.name, None)
        except Exception as email_error:
            print(f"Failed to send approval email: {str(email_error)}")
        
        return {
            "success": True,
            "message": "Payment confirmed - Application approved",
            "application_id": application_id
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/dashboard/stats", response_model=DashboardStats)
async def get_dashboard_stats(db: Session = Depends(get_db)):
    """Get dashboard statistics"""
    try:
        total_applications = db.query(KNCCIQRForm).count()
        pending_review = db.query(KNCCIQRForm).filter(
            KNCCIQRForm.status == ApplicationStatus.FORM_SUBMITTED
        ).count()
        document_review = db.query(KNCCIQRForm).filter(
            KNCCIQRForm.status.in_([
                ApplicationStatus.DOCUMENTS_REQUESTED,
                ApplicationStatus.DOCUMENTS_UPLOADED,
                ApplicationStatus.PAYMENT_REQUESTED
            ])
        ).count()
        approved = db.query(KNCCIQRForm).filter(
            KNCCIQRForm.status == ApplicationStatus.PAYMENT_COMPLETED
        ).count()
        rejected = db.query(KNCCIQRForm).filter(
            KNCCIQRForm.status == ApplicationStatus.REJECTED
        ).count()
        
        return DashboardStats(
            total_applications=total_applications,
            pending_review=pending_review,
            document_review=document_review,
            approved=approved,
            rejected=rejected
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/applications/{application_id}/debug")
async def debug_application(application_id: int, db: Session = Depends(get_db)):
    """Debug endpoint to check application details"""
    try:
        application = db.query(KNCCIQRForm).filter(KNCCIQRForm.id == application_id).first()
        if not application:
            raise HTTPException(status_code=404, detail="Application not found")
        
        return {
            "application_id": application.id,
            "name": application.name,
            "email": application.email,
            "mobile": application.mobile,
            "status": application.status,
            "created_at": application.created_at
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))