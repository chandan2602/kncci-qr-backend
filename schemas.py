from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
from models import UserType, ApplicationStatus

# Pydantic Models
class UserRegistration(BaseModel):
    name: str
    email: EmailStr
    mobile: str
    user_type: UserType
    company_name: Optional[str] = None
    qualification: Optional[str] = None
    date_of_birth: str
    appointment_date: str
    slot: str
    address: Optional[str] = None

class ApplicationUpdate(BaseModel):
    status: ApplicationStatus
    counselor_notes: Optional[str] = None
    payment_amount: Optional[float] = None

class ApplicationResponse(BaseModel):
    id: int
    name: str
    email: str
    mobile: str
    user_type: str
    company_name: Optional[str]
    qualification: Optional[str]
    date_of_birth: str
    appointment_date: str
    slot: str
    address: Optional[str]
    status: str
    counselor_notes: Optional[str]
    payment_amount: Optional[float]
    document1_name: Optional[str]
    document2_name: Optional[str]
    document3_name: Optional[str]
    created_at: datetime
    updated_at: datetime

class EmailTestRequest(BaseModel):
    email: str

class DashboardStats(BaseModel):
    total_applications: int
    pending_review: int
    document_review: int
    approved: int
    rejected: int
# Holland Code Assessment Schemas
from typing import List, Dict, Any, Union
from pydantic import Field

class AssessmentMessage(BaseModel):
    role: str
    content: str

class UserSelection(BaseModel):
    text: str
    trait: str

class StartRequest(BaseModel):
    user_id: int

class StartResponse(BaseModel):
    conversation_history: List[AssessmentMessage]
    question_data: Dict[str, Any]

class NextRequest(BaseModel):
    conversation_history: List[AssessmentMessage]
    user_selection: UserSelection

class NextResponse(BaseModel):
    conversation_history: List[AssessmentMessage]
    question_data: Dict[str, Any]

class SummaryRequest(BaseModel):
    user_id: int
    conversation_history: List[AssessmentMessage]
    chosen_traits: List[str]

class SummaryResponse(BaseModel):
    dominant_trait: str
    holland_code: str
    profile_description: str
    career_paths: List[str]
    work_environment: str
    disclaimer: str

class StartAssessmentResponse(BaseModel):
    status: str
    test_data: Optional[StartResponse] = None
    summary_data: Optional[SummaryResponse] = None

# Holland Code Recommendation Schemas
class UserTraits(BaseModel):
    holland_codes: List[str]

class Internship(BaseModel):
    id: int
    Title: str
    Company: str
    Stipend: str
    Type: str
    Top_Holland_Codes: List[str]
    Match_Score: int

class Job(BaseModel):
    id: int
    Title: str
    Company: str
    Salary: str
    Location: str
    Top_Holland_Codes: List[str]
    Match_Score: int

class Apprenticeship(BaseModel):
    id: int
    Title: str
    Category: str
    Fees: str
    Top_Holland_Codes: List[str]
    Match_Score: float

class RecommendationMessage(BaseModel):
    message: str

class Course(BaseModel):
    course_id: int
    Title: str
    Description: Optional[str]
    Match_Score: float
    Price: Optional[str]
    Holland_Codes: List[str]
    course_domain: Optional[str]

class HollandCodeInput(BaseModel):
    holland_code: str = Field(..., example="RIA", description="A string of 1 to 3 Holland codes.")

class CourseTagInput(BaseModel):
    course_name: str = Field(..., description="Name of the course")
    course_description: str = Field(..., description="Description of the course")

class CourseTagResponse(BaseModel):
    course_tag: str = Field(..., description="Top 3 Holland codes (e.g., 'SIA')")
    Course_domain: str = Field(..., description="The general domain of the course")


# Payment Schemas
class StudentPayment(BaseModel):
    id: int
    name: str
    email: str
    mobile: str
    user_type: Optional[str] = None
    payment_amount: Optional[float] = None
    payment_status: str
    paid_date: Optional[str] = None

class PaymentKPI(BaseModel):
    total_payment_amount: float
    successful_transactions: int
    students_paid: int

class PaymentResponse(BaseModel):
    total_payments: int
    data: List[StudentPayment]