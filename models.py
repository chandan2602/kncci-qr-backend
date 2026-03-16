from sqlalchemy import Column, Integer, String, DateTime, Text, Enum, Float
from datetime import datetime
import enum
from database import Base

# Enums
class ApplicationStatus(str, enum.Enum):
    FORM_SUBMITTED = "form-submitted"
    DOCUMENTS_REQUESTED = "documents-requested"
    DOCUMENTS_UPLOADED = "documents-uploaded"
    PAYMENT_REQUESTED = "payment-requested"
    PAYMENT_COMPLETED = "payment-completed"
    REJECTED = "rejected"

class UserType(str, enum.Enum):
    STUDENT = "student"
    EMPLOYEE = "employee"

# Database Models
class KNCCIQRForm(Base):
    __tablename__ = "KNCCI_QR_FORM"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, unique=True)
    mobile = Column(String(20), nullable=False)
    user_type = Column(Enum(UserType), nullable=False)
    company_name = Column(String(255), nullable=True)
    qualification = Column(String(255), nullable=True)
    date_of_birth = Column(String(20), nullable=False)
    appointment_date = Column(String(20), nullable=False)
    slot = Column(String(50), nullable=False)
    address = Column(Text, nullable=True)
    
    # Application Status Fields
    status = Column(Enum(ApplicationStatus), default=ApplicationStatus.FORM_SUBMITTED)
    counselor_notes = Column(Text, nullable=True)
    payment_amount = Column(Float, nullable=True)
    
    # Document Fields (File paths)
    document1 = Column(String(500), nullable=True)  # Government ID file path
    document2 = Column(String(500), nullable=True)  # Address Proof file path
    document3 = Column(String(500), nullable=True)  # Educational Certificate file path
    document1_name = Column(String(255), nullable=True)
    document2_name = Column(String(255), nullable=True)
    document3_name = Column(String(255), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)