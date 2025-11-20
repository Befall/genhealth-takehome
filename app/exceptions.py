"""Custom exception classes for the application"""
from fastapi import HTTPException, status


class PDFExtractionError(HTTPException):
    """Raised when PDF extraction fails"""
    def __init__(self, detail: str = "Failed to extract information from PDF"):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail
        )


class FileValidationError(HTTPException):
    """Raised when file validation fails"""
    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail
        )


class DatabaseError(HTTPException):
    """Raised when database operations fail"""
    def __init__(self, detail: str = "Database operation failed"):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail
        )

