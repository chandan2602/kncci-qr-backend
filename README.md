# KNCCI Internship Program API

A production-ready FastAPI application for managing KNCCI internship program registrations and applications.

## Project Structure

```
├── main.py                     # Main FastAPI application with error handling
├── config.py                   # Centralized configuration management
├── database.py                 # Database configuration and connection
├── models.py                   # SQLAlchemy database models
├── schemas.py                  # Pydantic schemas for request/response
├── .env                        # Environment variables (sensitive data)
├── requirements.txt            # Python dependencies
├── deploy.py                   # Production deployment script
├── start.py                    # Development server startup script
├── routers/
│   ├── __init__.py
│   ├── registration.py         # User registration endpoints
│   └── applications.py         # Application management endpoints
├── services/
│   ├── __init__.py
│   └── email_service.py         # Email service for notifications
└── utils/
    ├── __init__.py
    ├── logger.py               # Logging configuration
    └── exceptions.py           # Custom exceptions and error handlers
```

## Document Storage

The application uses file-based document storage for better performance and scalability.

### Document Upload Process

1. **File Validation**: Validates file types (PDF, JPEG, PNG, JPG)
2. **Unique Naming**: Generates unique filenames to prevent conflicts
3. **Disk Storage**: Saves files to `uploads/documents/` directory
4. **Database References**: Stores file paths in database instead of content
5. **Download Support**: Provides direct file download endpoints

### File Structure
```
uploads/
└── documents/
    ├── {application_id}_gov_id_{uuid}.pdf
    ├── {application_id}_address_proof_{uuid}.jpg
    └── {application_id}_education_cert_{uuid}.png
```

### Document Endpoints

- `POST /api/applications/{id}/documents` - Upload documents (saves to disk)
- `GET /api/applications/{id}/documents/{doc_number}` - Download document file
- `GET /api/applications/{id}/documents/status` - Check document upload status

## Production Features

- **Centralized Configuration**: Environment-based settings with validation
- **Comprehensive Logging**: File and console logging with rotation
- **Error Handling**: Custom exceptions with proper HTTP status codes
- **Database Connection Pooling**: Optimized database connections
- **Health Checks**: Endpoint for monitoring application health
- **Production Deployment**: Gunicorn support for production servers
- **Security**: Input validation, error sanitization, and secure defaults

## Quick Start

### Development Setup

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

2. **Configure environment variables in `.env`:**
```env
DATABASE_URL=postgresql://username:password@host:port/database
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USERNAME=your-email@gmail.com
EMAIL_PASSWORD=your_16_character_app_password
EMAIL_FROM=your-email@gmail.com
EMAIL_FROM_NAME=KNCCI Internship Program
DEBUG=True
```

**⚠️ Important: Gmail Setup Required**
- Enable 2-Factor Authentication on your Gmail account
- Generate an App Password: https://myaccount.google.com/apppasswords
- Use the 16-character App Password (not your regular Gmail password)

3. **Run development server:**
```bash
python start.py
```

### Production Deployment

1. **Run deployment script:**
```bash
python deploy.py
```

2. **Or manual production setup:**
```bash
# Install dependencies
pip install -r requirements.txt

# Set production environment
# Set DEBUG=False in .env

# Start with Gunicorn (recommended)
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000

# Or with Uvicorn
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

## API Endpoints

### Registration
- `POST /api/register` - Register new user
- `POST /api/form-submitted-email` - Send form submitted confirmation email

### Applications Management
- `GET /api/applications` - Get all applications
- `GET /api/applications/{id}` - Get specific application
- `GET /api/applications/status/{status}` - Get applications by status
- `GET /api/applications/search/{email}` - Search by email
- `PUT /api/applications/{id}/status` - Update application status
- `POST /api/applications/{id}/documents` - Upload documents
- `GET /api/applications/{id}/documents/{doc_number}` - Download document
- `POST /api/applications/{id}/request-documents` - Request documents from user
- `POST /api/applications/{id}/reject` - Reject application
- `POST /api/applications/{id}/send-payment-link` - Send payment request
- `POST /api/applications/{id}/confirm-payment` - Confirm payment completion

### Dashboard
- `GET /api/dashboard/stats` - Get dashboard statistics

### Health Check
- `GET /api/health` - Health check with database status

## Application Flow

1. **Registration**: User submits registration form
2. **Review**: Counselor reviews the application
3. **Documents**: If approved, counselor requests documents
4. **Document Upload**: User uploads required documents
5. **Payment**: If documents are approved, payment is requested
6. **Completion**: After payment, application is marked as completed

## Email Notifications

The system sends automated emails for:
- Registration confirmation
- Document requests
- Payment requests
- Application rejection
- Application approval

## Security Features

- Environment-based configuration
- Database connection pooling
- Input validation with Pydantic
- File type validation for uploads
- Error handling and logging

## Production Deployment

1. Set `DEBUG=False` in `.env`
2. Use a production WSGI server like Gunicorn
3. Set up proper database connection pooling
4. Configure email with app-specific passwords
5. Set up proper logging and monitoring