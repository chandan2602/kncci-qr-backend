from fastapi import APIRouter
from sqlalchemy import create_engine, text
from typing import List
import os
from database import engine
from schemas import StudentPayment, PaymentKPI, PaymentResponse
 
# Create router for payment endpoints
router = APIRouter(prefix="/api/payments", tags=["Payment Status"])
 
 
# ---------------------------------------
# 1️⃣ GET PAYMENT COMPLETED STUDENTS
# ---------------------------------------
 
# @router.get("/completed")
# def get_completed_payments():
 
#     query = text("""
#         SELECT
#             q.id,
#             q.name,
#             q.email,
#             q.mobile,
#             q.user_type,
#             p.payment_amount,
#             p.payment_status,
#             p.paid_date
#         FROM public.kncci_student_payment p
#         JOIN public."KNCCI_QR_FORM" q
#         ON p.qr_form_id = q.id
#         WHERE p.payment_status = 'Paid'
#         ORDER BY p.paid_date DESC
#     """)
 
#     with engine.connect() as conn:
#         result = conn.execute(query)
#         rows = [dict(row._mapping) for row in result]
 
#     return {
#         "total_students": len(rows),
#         "data": rows
#     }
 
 
# ---------------------------------------
# 2️⃣ GET PAYMENT KPIs
# ---------------------------------------
 
@router.get("/kpis", response_model=PaymentKPI)
def get_payment_kpis():
 
    query = text("""
        SELECT
            COUNT(*) FILTER (WHERE payment_status = 'Paid')
                AS successful_transactions,
 
            COALESCE(SUM(payment_amount) FILTER
                (WHERE payment_status = 'Paid'),0)
                AS total_payment_amount,
 
            COUNT(DISTINCT email) FILTER
                (WHERE payment_status = 'Paid')
                AS students_paid
        FROM public.kncci_student_payment
    """)
 
    with engine.connect() as conn:
        result = conn.execute(query).fetchone()
 
    return {
        "total_payment_amount": float(result.total_payment_amount),
        "successful_transactions": int(result.successful_transactions),
        "students_paid": int(result.students_paid)
    }
 
 
# ---------------------------------------
# 3️⃣ OPTIONAL: FULL PAYMENT TABLE DATA
# ---------------------------------------
 
@router.get("/all", response_model=PaymentResponse)
def get_all_payments():
 
    query = text("""
        SELECT
            q.id,
            q.name,
            q.email,
            q.mobile,
            p.payment_amount,
            p.payment_status,
            p.paid_date
        FROM public.kncci_student_payment p
        JOIN public."KNCCI_QR_FORM" q
        ON p.qr_form_id = q.id
        WHERE p.payment_status = 'Paid'
        ORDER BY p.paid_date DESC
    """)
 
    with engine.connect() as conn:
        result = conn.execute(query)
        rows = [dict(row._mapping) for row in result]
 
    # Convert datetime to string
    for row in rows:
        if row.get('paid_date'):
            row['paid_date'] = row['paid_date'].isoformat()
 
    return {
        "total_payments": len(rows),
        "data": rows
    }