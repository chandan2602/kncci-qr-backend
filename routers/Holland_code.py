from fastapi import APIRouter, HTTPException, Response, status
from typing import List, Dict, Any, Optional, Union
import os
import json
import math
import openai
import asyncpg
import psycopg2
from urllib.parse import quote_plus
from collections import Counter
from datetime import datetime, timedelta
import asyncio
from psycopg2.extras import RealDictCursor
from sqlalchemy import create_engine, text

from config import settings
from schemas import (
    StartRequest, StartResponse, NextRequest, NextResponse, 
    SummaryRequest, SummaryResponse, StartAssessmentResponse,
    UserTraits, Internship, Job, Apprenticeship, RecommendationMessage,
    CourseTagInput, CourseTagResponse
)

# Create router
router = APIRouter(prefix="/hollandcode", tags=["Holland Code"])

# Configure OpenAI client
try:
    if settings.openai_api_key:
        client = openai.OpenAI(api_key=settings.openai_api_key)
        print("✅ OpenAI client initialized successfully.")
    else:
        client = None
        print("⚠️ OpenAI API key not provided. Holland Code features will be limited.")
except openai.OpenAIError as e:
    print(f"❌ Error initializing OpenAI client: {e}")
    client = None

# Database configurations from settings
DB_USER = settings.db_user
DB_PASSWORD = settings.db_password
DB_HOST = settings.db_host
DB_PORT = settings.db_port
DB_NAME = settings.db_name

# Internship DB config from settings
IN_DB_HOST = settings.in_db_host
IN_DB_PORT = settings.in_db_port
IN_DB_NAME = settings.in_db_name
IN_DB_USER = settings.in_db_user
IN_DB_PASSWORD = settings.in_db_password

# Course DB config (SQLAlchemy)
engine = None
try:
    if all([DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME]):
        encoded_password = quote_plus(DB_PASSWORD)
        SQLALCHEMY_DATABASE_URL = f"postgresql+psycopg2://{DB_USER}:{encoded_password}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        engine = create_engine(SQLALCHEMY_DATABASE_URL)
        print("✅ SQLAlchemy engine configured for Course Recommendations.")
    else:
        print("⚠ SQLAlchemy engine not configured; missing DB variables for Course API.")
except Exception as e:
    print(f"❌ FATAL ERROR during SQLAlchemy engine setup: {e}")

# Global variables
db_pool: Optional[asyncpg.Pool] = None
preprocessed_internships = []
preprocessed_courses = []
preprocessed_jobs = []

# Holland Code constants
HOLLAND_CODES = ["R", "I", "A", "S", "E", "C"]

# Utility functions
def vectorize_traits(traits: List[str]) -> dict:
    """Converts a list of Holland Code traits into a weighted vector."""
    vector = {code: 0 for code in HOLLAND_CODES}
    weights = [9, 3, 1]
    for i, trait in enumerate(traits[:3]):
        trait_upper = trait.upper()
        if trait_upper in vector:
            vector[trait_upper] = weights[i]
    return vector

def cosine_similarity(vec1: dict, vec2: dict) -> float:
    """Calculates the cosine similarity between two trait vectors."""
    dot_product = sum(vec1[code] * vec2[code] for code in HOLLAND_CODES)
    magnitude_vec1 = math.sqrt(sum(val**2 for val in vec1.values()))
    magnitude_vec2 = math.sqrt(sum(val**2 for val in vec2.values()))
    if magnitude_vec1 == 0 or magnitude_vec2 == 0:
        return 0.0
    return dot_product / (magnitude_vec1 * magnitude_vec2)

def get_system_prompt(min_questions: int = 8, max_questions: int = 12) -> str:
    """Generates the system prompt with specified question counts."""
    return f"""
    You are an expert career counselor AI. Your goal is to identify a user's top 3 Holland Code (RIASEC) personality traits through a short, natural conversation.

    ### Core Rules:
    1. Question Variety: NEVER repeat a question within a single conversation. VARY your questions each time.
    2. Conversation Flow: Start broad, then narrow down based on user responses.
    3. Ask between {min_questions} and {max_questions} questions.
    4. Provide exactly 4 distinct options for each question.
    5. Every option must be mapped to a lowercase Holland trait.

    ### JSON Output Format:
    For questions:
    {{
      "status": "questioning",
      "question": "Your question here",
      "question_trait": "relevant trait (lowercase)",
      "options": [
        {{ "text": "Option 1", "trait": "realistic" }},
        {{ "text": "Option 2", "trait": "social" }},
        {{ "text": "Option 3", "trait": "enterprising" }},
        {{ "text": "Option 4", "trait": "conventional" }}
      ]
    }}

    For completion:
    {{
      "status": "complete",
      "closing_statement": "Thank you! I have enough information now.",
      "analysis": {{
        "top_3_traits": ["trait1", "trait2", "trait3"],
        "summary": "Brief justification."
      }}
    }}
    """

def get_ai_response(conversation_history: List[Dict[str, str]], model: str = "gpt-4o-mini") -> Optional[Dict[str, Any]]:
    """Sends a conversation to the AI and gets a parsed JSON response."""
    if not client:
        raise HTTPException(status_code=503, detail="OpenAI client is not available.")
    try:
        response = client.chat.completions.create(
            model=model,
            messages=conversation_history,
            temperature=0.8,
            response_format={"type": "json_object"}
        )
        response_content = response.choices[0].message.content
        return json.loads(response_content)
    except (json.JSONDecodeError, openai.APIError) as e:
        print(f"An API or JSON parsing error occurred: {e}")
        raise HTTPException(status_code=500, detail="Error communicating with AI or parsing its response.")

async def _generate_summary_from_code(holland_code: str) -> Dict[str, Any]:
    """Generates a personality summary by calling the AI with only a Holland Code."""
    summary_prompt = f"""
    Based on the Holland Code '{holland_code}', generate a comprehensive personality summary.
    IMPORTANT: Your entire response must be a single, valid JSON object.
    The dominant_trait MUST match the first letter of the code (R -> Realistic, I -> Investigative, etc.).
    Respond ONLY in this JSON format with the following keys: "dominant_trait", "holland_code", "profile_description", "career_paths", "work_environment", "disclaimer".
    """
    conversation = [{"role": "user", "content": summary_prompt}]
    response_data = get_ai_response(conversation)

    trait_map = {"R": "Realistic", "I": "Investigative", "A": "Artistic", "S": "Social", "E": "Enterprising", "C": "Conventional"}
    response_data["holland_code"] = holland_code.upper()
    first_letter = holland_code[0].upper()
    if first_letter in trait_map:
        response_data["dominant_trait"] = trait_map[first_letter]
    
    required_keys = ["dominant_trait", "holland_code", "profile_description", "career_paths", "work_environment", "disclaimer"]
    if not all(key in response_data for key in required_keys):
        raise HTTPException(status_code=500, detail="AI response for summary generation was missing fields.")
    return response_data

# Data loading functions
def load_and_preprocess_internships():
    """Fetches and processes internship data from the database at startup."""
    global preprocessed_internships
    conn = None
    try:
        conn = psycopg2.connect(
            host=IN_DB_HOST, port=IN_DB_PORT, dbname=IN_DB_NAME,
            user=IN_DB_USER, password=IN_DB_PASSWORD, cursor_factory=RealDictCursor
        )
        print("✅ Internship DB connection successful.")
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    courseshd_id AS "id",
                    courseshd_name AS "Title",
                    CAST(courseshd_stipend AS TEXT) AS "Stipend",
                    courseshd_traits AS "Top_Holland_Codes"
                FROM dlc_course_schedule
                WHERE courseshd_traits IS NOT NULL AND TRIM(courseshd_traits) != '';
            """)
            internships_data = cur.fetchall()
            print(f"✔ Fetched {len(internships_data)} internships from the database.")

            temp_internships = []
            for internship in internships_data:
                internship["Company"] = "OUK"
                internship["Type"] = "Remote"
                codes_data = internship.get("Top_Holland_Codes")
                final_codes = []

                if isinstance(codes_data, str):
                    clean_data = codes_data.strip().upper()
                    if ',' in clean_data:
                        final_codes = [code.strip() for code in clean_data.split(',')]
                    else:
                        final_codes = list(clean_data)

                if final_codes:
                    internship["Top_Holland_Codes"] = final_codes[:3]
                    internship["vector"] = vectorize_traits(final_codes)
                    temp_internships.append(internship)
            
            preprocessed_internships = temp_internships
            print(f"✔ Successfully preprocessed {len(preprocessed_internships)} internships.")

    except psycopg2.Error as e:
        print(f"❌ Internship database connection or query failed: {e}")
    finally:
        if conn:
            conn.close()

def load_and_preprocess_courses():
    """Fetches and processes course data from the database at startup."""
    if not engine:
        print("❌ SKIPPING COURSE DATA LOAD: Database engine is not available.")
        return

    global preprocessed_courses
    temp_courses = []

    query = text("SELECT id, apprenticeship_name, apprenticeship_category, application_fees, stipend_per_month, user_traits FROM apprenticeships WHERE user_traits IS NOT NULL AND TRIM(user_traits) != '';")

    try:
        with engine.connect() as connection:
            print("🚀 Fetching apprenticeship data from the database...")
            result = connection.execute(query)
            for row in result:
                course_dict = {
                    "course_id": row.id,
                    "Title": row.apprenticeship_name,
                    "Description": row.apprenticeship_category,
                    "Price": str(row.application_fees),
                    "course_domain": row.apprenticeship_category
                }
                if row.user_traits and isinstance(row.user_traits, str):
                    clean_data = row.user_traits.strip().upper()
                    if ',' in clean_data:
                        holland_codes_list = [code.strip() for code in clean_data.split(',')]
                    else:
                        holland_codes_list = list(clean_data)
                    
                    if holland_codes_list:
                        course_dict["Holland_Codes"] = holland_codes_list[:3]
                        course_dict["vector"] = vectorize_traits(holland_codes_list)
                        temp_courses.append(course_dict)
            preprocessed_courses = temp_courses
            print(f"✅ Successfully loaded and preprocessed {len(preprocessed_courses)} apprenticeships.")
    except Exception as e:
        print(f"⚠️  APPRENTICESHIP DATA LOAD FAILED: {e}")

def load_and_preprocess_jobs():
    """Fetches and processes job data from the database at startup."""
    global preprocessed_jobs
    conn = None
    try:
        conn = psycopg2.connect(
            host=IN_DB_HOST, port=IN_DB_PORT, dbname=IN_DB_NAME,
            user=IN_DB_USER, password=IN_DB_PASSWORD, cursor_factory=RealDictCursor
        )
        print("✅ Jobs DB connection successful.")
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    job_id AS "id",
                    job_title AS "Title",
                    (SELECT company_name FROM dlc_company WHERE company_id = internship_jobs.company_id) AS "Company",
                    CAST(job_salary_from AS TEXT) AS "Salary",
                    location AS "Location",
                    user_traits AS "Top_Holland_Codes"
                FROM internship_jobs
                WHERE user_traits IS NOT NULL AND TRIM(user_traits) != '' AND is_active = true;
            """)
            jobs_data = cur.fetchall()
            print(f"✔ Fetched {len(jobs_data)} jobs from the database.")

            temp_jobs = []
            for job in jobs_data:
                codes_data = job.get("Top_Holland_Codes")
                final_codes = []

                if isinstance(codes_data, str):
                    clean_data = codes_data.strip().upper()
                    if ',' in clean_data:
                        final_codes = [code.strip() for code in clean_data.split(',')]
                    else:
                        final_codes = list(clean_data)

                if final_codes:
                    job["Top_Holland_Codes"] = final_codes[:3]
                    job["vector"] = vectorize_traits(final_codes)
                    temp_jobs.append(job)
            
            preprocessed_jobs = temp_jobs
            print(f"✔ Successfully preprocessed {len(preprocessed_jobs)} jobs.")

    except psycopg2.Error as e:
        print(f"❌ Jobs database connection or query failed: {e}")
    finally:
        if conn:
            conn.close()

# Initialize database pool
async def init_db_pool():
    """Initialize the database connection pool."""
    global db_pool
    try:
        db_pool = await asyncpg.create_pool(
            user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT, database=DB_NAME
        )
        print("✅ Assessment DB connection pool created successfully.")
    except Exception as e:
        print(f"❌ Could not connect to the assessment database: {e}")
        db_pool = None

# Load initial data
def load_initial_data():
    """Load all initial data."""
    print("--- 🚚 Performing initial data load... ---")
    load_and_preprocess_internships()
    load_and_preprocess_courses()
    load_and_preprocess_jobs()

# API Endpoints
# Assessment API Endpoints
@router.post("/assessment/start", response_model=StartAssessmentResponse)
async def start_assessment(request: StartRequest):
    """Starts a new assessment or returns previous summary if on cooldown."""
    if not db_pool:
        raise HTTPException(status_code=503, detail="Database connection is not available.")

    try:
        async with db_pool.acquire() as conn:
            record = await conn.fetchrow(
                'SELECT user_traits, createdon FROM userprofile WHERE userid = $1',
                request.user_id
            )
        if record and record['createdon'] and record['user_traits']:
            if (datetime.utcnow() - record['createdon']) < timedelta(days=30):
                summary_dict = await _generate_summary_from_code(record['user_traits'])
                return StartAssessmentResponse(
                    status="cooldown_active_summary_returned",
                    summary_data=SummaryResponse(**summary_dict)
                )

        system_prompt = get_system_prompt()
        conversation = [{"role": "system", "content": system_prompt}]
        ai_response_data = get_ai_response(conversation)
        conversation.append({"role": "assistant", "content": json.dumps(ai_response_data)})
        
        start_response = StartResponse(
            conversation_history=conversation,
            question_data=ai_response_data
        )
        return StartAssessmentResponse(
            status="new_test_started",
            test_data=start_response
        )
    except Exception as e:
        print(f"An unexpected error occurred in /assessment/start: {e}")
        raise HTTPException(status_code=500, detail="An internal server error occurred.")

@router.post("/assessment/next", response_model=NextResponse)
async def next_question(request: NextRequest):
    """Submits a user's answer and gets the next question."""
    conversation = [msg.dict() for msg in request.conversation_history]
    user_message = f"My answer is '{request.user_selection.text}'."
    conversation.append({"role": "user", "content": user_message})
    ai_response_data = get_ai_response(conversation)
    conversation.append({"role": "assistant", "content": json.dumps(ai_response_data)})
    return NextResponse(conversation_history=conversation, question_data=ai_response_data)

@router.post("/assessment/summary", response_model=SummaryResponse)
async def get_summary(request: SummaryRequest):
    """Generates the final summary and stores the result."""
    conversation = [msg.dict() for msg in request.conversation_history]
    frequency = Counter(request.chosen_traits)
    frequency_text = "\n".join([f"- {t.capitalize()}: {c}" for t, c in frequency.items()]) or "No traits recorded."
    
    final_prompt = f"""
    Analyze the full conversation below and determine the user's top 3 Holland traits based on behavior, preferences, and personality.

    ### Frequency Data:
    {frequency_text}

    ### Instructions:
    - Respond with a single, valid JSON object.
    - Include the following keys: "dominant_trait", "holland_code", "profile_description", "career_paths", "work_environment", "disclaimer".
    - "holland_code" must be exactly 3 distinct uppercase letters (from R, I, A, S, E, C), in order of dominance.
    - "dominant_trait" must match the first letter of "holland_code".
    - Base all conclusions on the conversation and context, not just trait frequency.
    """
    conversation.append({"role": "user", "content": final_prompt})

    try:
        response_data = get_ai_response(conversation)
        
        trait_map = {"R": "Realistic", "I": "Investigative", "A": "Artistic", "S": "Social", "E": "Enterprising", "C": "Conventional"}
        holland_code = response_data.get("holland_code", "").upper()
        holland_code = holland_code[:3]
        if holland_code and holland_code[0] in trait_map:
            response_data["dominant_trait"] = trait_map[holland_code[0]]
        
        required_keys = ["dominant_trait", "holland_code", "profile_description", "career_paths", "work_environment", "disclaimer"]
        if not all(key in response_data for key in required_keys):
            raise HTTPException(status_code=500, detail="AI response missing required fields.")

        if db_pool:
            try:
                async with db_pool.acquire() as conn:
                    await conn.execute(
                        'UPDATE userprofile SET user_traits = $1, createdon = $2 WHERE userid = $3',
                        response_data["holland_code"], datetime.utcnow(), request.user_id
                    )
            except Exception as db_error:
                print(f"❌ Database update failed for user {request.user_id}: {db_error}")
        
        return SummaryResponse(**response_data)
    except openai.APIError as e:
        print(f"API error during summary generation: {e}")
        raise HTTPException(status_code=500, detail="Error generating the final summary.")

# Recommendation API Endpoints
@router.post("/internships-recommendations/", response_model=Union[List[Internship], RecommendationMessage])
def get_internship_recommendations(user_traits: UserTraits, response: Response):
    """Recommends internships based on a user's Holland Codes."""
    if not preprocessed_internships:
        raise HTTPException(status_code=503, detail="Internship data is not available.")

    user_codes = user_traits.holland_codes

    if len(user_codes) != 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid input: Please provide exactly 3 Holland codes in the list."
        )
    for code in user_codes:
        if code.strip().upper() not in HOLLAND_CODES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid Holland Code '{code}' found. Please use only R, I, A, S, E, C."
            )

    user_vector = vectorize_traits(user_codes)

    scored_internships = []
    for internship in preprocessed_internships:
        holland_score = cosine_similarity(user_vector, internship.get("vector", {})) * 100
        internship_copy = internship.copy()
        internship_copy["Match_Score"] = int(holland_score)
        del internship_copy["vector"]
        scored_internships.append(internship_copy)

    strong_recommendations = [
        internship for internship in scored_internships if internship['Match_Score'] > 90
    ]

    if not strong_recommendations:
        response.status_code = status.HTTP_404_NOT_FOUND
        return {"message": "No available internships found with a match score above 90% for your traits."}

    final_sorted_list = sorted(strong_recommendations, key=lambda x: x['Match_Score'], reverse=True)
    return final_sorted_list

@router.post("/apprenticeship-recommendations/", response_model=Union[List[Apprenticeship], RecommendationMessage])
def recommend_apprenticeships(user_traits: UserTraits, response: Response):
    """Recommends apprenticeships based on a user's Holland Codes."""
    if not preprocessed_courses:
        raise HTTPException(status_code=503, detail="Apprenticeship data is not available.")

    user_codes = user_traits.holland_codes

    if len(user_codes) != 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid input: Please provide exactly 3 Holland codes in the list."
        )
    for code in user_codes:
        if code.strip().upper() not in HOLLAND_CODES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid Holland Code '{code}' found. Please use only R, I, A, S, E, C."
            )

    user_vector = vectorize_traits(user_codes)

    scored_apprenticeships = []
    for apprenticeship in preprocessed_courses:
        holland_score = cosine_similarity(user_vector, apprenticeship.get("vector", {})) * 100
        apprenticeship_copy = apprenticeship.copy()
        apprenticeship_copy["Match_Score"] = round(holland_score, 2)
        apprenticeship_copy["id"] = apprenticeship_copy.get("course_id")
        apprenticeship_copy["Title"] = apprenticeship_copy.get("Title")
        apprenticeship_copy["Category"] = apprenticeship_copy.get("Description")
        apprenticeship_copy["Fees"] = apprenticeship_copy.get("Price")
        apprenticeship_copy["Top_Holland_Codes"] = apprenticeship_copy.get("Holland_Codes", [])
        del apprenticeship_copy["vector"]
        scored_apprenticeships.append(apprenticeship_copy)

    strong_recommendations = [
        apprenticeship for apprenticeship in scored_apprenticeships if apprenticeship['Match_Score'] > 70
    ]
    
    if not strong_recommendations:
        response.status_code = status.HTTP_404_NOT_FOUND
        return {"message": "No available apprenticeships found with a match score above 70% for your traits."}

    final_sorted_list = sorted(strong_recommendations, key=lambda x: x['Match_Score'], reverse=True)
    return final_sorted_list

@router.post("/jobs-recommendations/", response_model=Union[List[Job], RecommendationMessage])
def recommend_jobs(user_traits: UserTraits, response: Response):
    """Recommends jobs based on a user's Holland Codes."""
    if not preprocessed_jobs:
        raise HTTPException(status_code=503, detail="Job data is not available.")

    user_codes = user_traits.holland_codes

    if len(user_codes) != 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid input: Please provide exactly 3 Holland codes in the list."
        )
    for code in user_codes:
        if code.strip().upper() not in HOLLAND_CODES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid Holland Code '{code}' found. Please use only R, I, A, S, E, C."
            )

    user_vector = vectorize_traits(user_codes)

    scored_jobs = []
    for job in preprocessed_jobs:
        holland_score = cosine_similarity(user_vector, job.get("vector", {})) * 100
        job_copy = job.copy()
        job_copy["Match_Score"] = int(holland_score)
        del job_copy["vector"]
        scored_jobs.append(job_copy)

    strong_recommendations = [
        job for job in scored_jobs if job['Match_Score'] > 70
    ]

    if not strong_recommendations:
        response.status_code = status.HTTP_404_NOT_FOUND
        return {"message": "No available jobs found with a match score above 70% for your traits."}

    final_sorted_list = sorted(strong_recommendations, key=lambda x: x['Match_Score'], reverse=True)
    return final_sorted_list

@router.post("/getcoursetag", response_model=CourseTagResponse)
def get_course_tag(course_input: CourseTagInput):
    """
    Analyzes a course name and description to determine the top 3 relevant Holland Code traits and its domain.
    """
    if not client:
        raise HTTPException(status_code=503, detail="OpenAI client is not available.")
    
    system_prompt = """
    You are an expert in Holland Code (RIASEC) personality types and course categorization.
    Your task is to analyze course information, determine the top 3 most relevant Holland Code traits, and assign the most appropriate course domain.

    Holland Codes:
    - R (Realistic): Practical, hands-on, technical work with tools, machines, or physical activities
    - I (Investigative): Analytical, research-oriented, problem-solving, scientific thinking
    - A (Artistic): Creative, expressive, design-oriented, innovative
    - S (Social): Helping others, teaching, counseling, collaborative work
    - E (Enterprising): Leadership, business, persuading, managing, entrepreneurship
    - C (Conventional): Organized, detail-oriented, systematic, administrative work

    Course Domains:
    - Technology & Computer Science
    - Business & Management
    - Creative Arts & Design
    - Health & Wellness
    - Science & Engineering
    - Humanities & Social Sciences
    - Personal Development
    - Skilled Trades & Hobbies

    Instructions:
    1. Analyze the course name and description carefully.
    2. Identify the top 3 most relevant Holland Code traits in order of relevance.
    3. Select the single most relevant course domain from the list provided above.
    4. Return ONLY a valid JSON object with the format: {"course_tag": "XYZ", "Course_domain": "Domain Name"}
    5. The course_tag must be exactly 3 uppercase letters from R, I, A, S, E, C.
    6. All 3 letters in the tag must be distinct (no repeats).
    """
    
    user_message = f"""
    Course Name: {course_input.course_name}
    Course Description: {course_input.course_description}

    Determine the top 3 Holland Code traits and the most relevant course domain for this course.
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        
        response_content = response.choices[0].message.content
        result = json.loads(response_content)
        
        course_tag = result.get("course_tag", "").upper()
        Course_domain = result.get("Course_domain")
        
        if not Course_domain:
            raise ValueError("AI response did not include a Course_domain")
        
        if not course_tag or len(course_tag) != 3:
            raise ValueError("Invalid course_tag length")
        
        if not all(c in HOLLAND_CODES for c in course_tag):
            raise ValueError("Invalid Holland Code characters")
        
        if len(set(course_tag)) != 3:
            raise ValueError("Duplicate Holland Codes detected")
        
        return CourseTagResponse(course_tag=course_tag, Course_domain=Course_domain)
        
    except (json.JSONDecodeError, KeyError) as e:
        print(f"JSON parsing or key error in getcoursetag: {e}")
        raise HTTPException(status_code=500, detail="Failed to parse AI response or required key missing")
    except openai.APIError as e:
        print(f"OpenAI API error in getcoursetag: {e}")
        raise HTTPException(status_code=500, detail="Error communicating with AI service")
    except ValueError as e:
        print(f"Validation error in getcoursetag: {e}")
        raise HTTPException(status_code=500, detail=f"Invalid AI response: {str(e)}")
    except Exception as e:
        print(f"Unexpected error in getcoursetag: {e}")
        raise HTTPException(status_code=500, detail="An internal server error occurred")