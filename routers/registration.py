from fastapi import APIRouter, HTTPException, Depends, Form
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime
from pydantic import EmailStr

from database import get_db
from models import KNCCIQRForm, ApplicationStatus
from schemas import UserRegistration
from services.email_service import EmailService

router = APIRouter(prefix="/api", tags=["registration"])

@router.post("/register", response_model=dict)
async def register_user(user: UserRegistration, db: Session = Depends(get_db)):
    """Register a new user"""
    try:
        print(f"Registration attempt for: {user.email}")
        print(f"User type: {user.user_type}")
        
        # Test database connection first
        try:
            db.execute(text("SELECT 1"))
            print("Database connection verified")
        except Exception as db_test_error:
            print(f"Database connection test failed: {str(db_test_error)}")
            raise HTTPException(status_code=503, detail="Database connection unavailable")
        
        # Check if email already exists
        try:
            existing_user = db.query(KNCCIQRForm).filter(KNCCIQRForm.email == user.email).first()
            if existing_user:
                raise HTTPException(status_code=400, detail="Email already registered")
            print("Email availability check passed")
        except HTTPException:
            raise
        except Exception as check_error:
            print(f"Error checking existing user: {str(check_error)}")
            raise HTTPException(status_code=503, detail="Database query failed")
        
        # Generate student ID only for students (will implement after adding DB column)
        student_id = None
        
        print("Creating database record...")
        
        # Create new user
        try:
            db_user = KNCCIQRForm(
                name=user.name,
                email=user.email,
                mobile=user.mobile,
                user_type=user.user_type,
                company_name=user.company_name if user.company_name else None,
                qualification=user.qualification,
                date_of_birth=user.date_of_birth,
                appointment_date=user.appointment_date,
                slot=user.slot,
                address=user.address,
                status=ApplicationStatus.FORM_SUBMITTED
            )
            
            print("Adding to database...")
            db.add(db_user)
            db.commit()
            db.refresh(db_user)
            
            print(f"User created with ID: {db_user.id}")
            
        except Exception as db_error:
            print(f"Database insert error: {str(db_error)}")
            db.rollback()
            raise HTTPException(status_code=503, detail=f"Failed to save user data: {str(db_error)}")
        
        # Send form submitted confirmation email (this is critical for user experience)
        email_sent = False
        try:
            print("Sending form submitted confirmation email...")
            email_sent = await EmailService.form_submitted_email(user.email, user.name, student_id)
            if email_sent:
                print("✅ Form submitted confirmation email sent successfully")
            else:
                print("⚠️ Form submitted confirmation email failed to send")
        except Exception as email_error:
            print(f"❌ Failed to send form submitted email: {str(email_error)}")
            # Log the error but don't fail the registration
        
        response_data = {
            "success": True,
            "message": "Registration successful! A confirmation email has been sent to your email address.",
            "application_id": db_user.id,
            "email": user.email,
            "name": user.name,
            "email_sent": email_sent
        }
        
        # Include student ID in response if generated
        if student_id:
            response_data["student_id"] = student_id
        
        return response_data
        
    except HTTPException as he:
        print(f"HTTP Exception: {he.detail}")
        raise he
    except Exception as e:
        print(f"Unexpected registration error: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        try:
            db.rollback()
        except:
            pass
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")

@router.post("/form-submitted-email")
async def send_form_submitted_email(
    email: EmailStr = Form(...), 
    name: str = Form(...),
    student_id: str = Form(None)
):
    """Send form submitted confirmation email"""
    try:
        print(f"Sending form submitted email to: {email}")
        
        success = await EmailService.form_submitted_email(email, name, student_id)
        
        if success:
            return {
                "success": True,
                "message": f"Form submitted confirmation email sent successfully to {email}",
                "email_sent_to": email,
                "recipient_name": name
            }
        else:
            return {
                "success": False,
                "message": "Failed to send form submitted email. Check server logs for details.",
                "email_sent_to": email,
                "recipient_name": name
            }
    except Exception as e:
        print(f"Error sending form submitted email: {str(e)}")
        return {
            "success": False,
            "message": f"Error: {str(e)}",
            "email_sent_to": email if 'email' in locals() else "unknown"
        }



