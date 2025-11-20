# Order Management API

A FastAPI-based REST API for managing orders with CRUD operations.

## Features

- Create, Read, Update, and Delete operations for Orders
- **User authentication** with JWT tokens
- **Activity logging** - all API requests are logged to the database
- PDF file upload with automatic extraction of patient information
- **OCR support** for image-based/scanned PDFs (requires Tesseract)
- SQLite database (local, file-based)
- Automatic API documentation (Swagger UI)
- Input validation using Pydantic

## Order Model

Each Order has the following fields:
- **ID**: Primary key (auto-generated)
- **First Name**: Required string
- **Last Name**: Required string
- **Date of Birth**: Required date

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. **Configure environment variables** (optional but recommended):
   - Copy `.env.example` to `.env`: `cp .env.example .env`
   - Edit `.env` and set your `SECRET_KEY` (use a strong, random string)
   - For production, set environment variables in your deployment platform (Railway, Heroku, etc.)
   
   **Important**: Never commit `.env` to version control. It's already in `.gitignore`.

3. **For image-based PDFs (scanned documents)**, install Tesseract OCR:
   - **macOS**: `brew install tesseract`
   - **Ubuntu/Debian**: `sudo apt-get install tesseract-ocr`
   - **Windows**: Download from [GitHub](https://github.com/UB-Mannheim/tesseract/wiki)
   
   Also install poppler (required for pdf2image):
   - **macOS**: `brew install poppler`
   - **Ubuntu/Debian**: `sudo apt-get install poppler-utils`
   - **Windows**: Download from [poppler-windows](https://github.com/oschwartz10612/poppler-windows/releases/)

4. Run the application:
```bash
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`

**Note**: The API automatically uses OCR for image-based PDFs. If Tesseract is not installed, text-based PDFs will still work, but scanned/image-based PDFs will fail.

## Live Deployment

A live version of this API is available at:

**https://genhealth-takehome-production.up.railway.app**

You can interact with the live API using **Swagger UI**: https://genhealth-takehome-production.up.railway.app/docs

## API Documentation

For local development, once the server is running, you can access **Swagger UI**: http://localhost:8000/docs

## API Endpoints

### Public Endpoints
- `GET /` - Root endpoint
- `GET /health` - Health check
- `POST /auth/register` - Register a new user
- `POST /auth/login` - Login and get access token

### Protected Endpoints (require authentication)
- `POST /order/` - Create a new order from a PDF file
- `GET /order/` - Get all orders (with pagination: `?skip=0&limit=100`)
- `GET /order/{order_id}` - Get a specific order by ID
- `PUT /order/{order_id}` - Update an existing order
- `DELETE /order/{order_id}` - Delete an order
- `GET /auth/me` - Get current user information

All protected endpoints require a Bearer token in the `Authorization` header.

## Example Usage

All examples below use `http://localhost:8000` for local development. For the live deployment, replace with `https://genhealth-takehome-production.up.railway.app`.

**Note**: All `/order/*` endpoints require authentication. First register a user and login to get a Bearer token (see Authentication section below).

### Authentication

#### Register a new user:
```bash
curl -X POST "http://localhost:8000/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "password": "password123"
  }'
```

#### Login to get access token:
```bash
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=testuser&password=password123"
```

Use the returned `access_token` in subsequent requests with the `Authorization: Bearer <token>` header.

### Create an Order from PDF
```bash
curl -X POST "http://localhost:8000/order/" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -F "file=@path/to/prescription.pdf"
```

The PDF should contain patient information including:
- Patient Name (First Name and Last Name)
- Date of Birth

The API will automatically extract this information and create the order.

### Get All Orders
```bash
curl -X GET "http://localhost:8000/order/" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

### Get Order by ID
```bash
curl -X GET "http://localhost:8000/order/1" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

### Update an Order
```bash
curl -X PUT "http://localhost:8000/order/1" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "Jane",
    "last_name": "Smith"
  }'
```

### Delete an Order
```bash
curl -X DELETE "http://localhost:8000/order/1" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

## Database

The SQLite database file (`orders.db`) will be created automatically in the project root when you first run the application.

