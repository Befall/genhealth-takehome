# Order Management API

A FastAPI-based REST API for managing orders with CRUD operations.

## Features

- Create, Read, Update, and Delete operations for Orders
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

2. **For image-based PDFs (scanned documents)**, install Tesseract OCR:
   - **macOS**: `brew install tesseract`
   - **Ubuntu/Debian**: `sudo apt-get install tesseract-ocr`
   - **Windows**: Download from [GitHub](https://github.com/UB-Mannheim/tesseract/wiki)
   
   Also install poppler (required for pdf2image):
   - **macOS**: `brew install poppler`
   - **Ubuntu/Debian**: `sudo apt-get install poppler-utils`
   - **Windows**: Download from [poppler-windows](https://github.com/oschwartz10612/poppler-windows/releases/)

3. Run the application:
```bash
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`

**Note**: The API automatically uses OCR for image-based PDFs. If Tesseract is not installed, text-based PDFs will still work, but scanned/image-based PDFs will fail.

## API Documentation

Once the server is running, you can access:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## API Endpoints

- `GET /` - Root endpoint
- `GET /health` - Health check
- `POST /order/` - Create a new order from a PDF file
- `GET /order/` - Get all orders (with pagination: `?skip=0&limit=100`)
- `GET /order/{order_id}` - Get a specific order by ID
- `PUT /order/{order_id}` - Update an existing order
- `DELETE /order/{order_id}` - Delete an order

## Example Usage

### Create an Order from PDF
```bash
curl -X POST "http://localhost:8000/order/" \
  -F "file=@path/to/prescription.pdf"
```

The PDF should contain patient information including:
- Patient Name (First Name and Last Name)
- Date of Birth

The API will automatically extract this information and create the order.

### Get All Orders
```bash
curl "http://localhost:8000/order/"
```

### Get Order by ID
```bash
curl "http://localhost:8000/order/1"
```

### Update an Order
```bash
curl -X PUT "http://localhost:8000/order/1" \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "Jane",
    "last_name": "Smith"
  }'
```

### Delete an Order
```bash
curl -X DELETE "http://localhost:8000/order/1"
```

## Database

The SQLite database file (`orders.db`) will be created automatically in the project root when you first run the application.

