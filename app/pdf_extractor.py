import pdfplumber
import PyPDF2
import re
from datetime import datetime, date
from typing import Optional, Tuple
from fastapi import UploadFile, HTTPException, status
import io
import logging

logger = logging.getLogger(__name__)

# Try to import OCR libraries (optional)
try:
    from pdf2image import convert_from_bytes
    from pytesseract import image_to_string
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    logger.warning("OCR libraries not available. Install pdf2image and pytesseract for image-based PDF support.")


def extract_text_with_ocr(file_content: bytes) -> str:
    """Extract text from PDF using OCR (for image-based PDFs) - processes all pages"""
    if not OCR_AVAILABLE:
        return ""
    
    try:
        logger.info("Converting PDF pages to images for OCR...")
        # Convert PDF pages to images
        images = convert_from_bytes(file_content, dpi=300)
        logger.info(f"Converted {len(images)} pages to images")
        
        text = ""
        for i, image in enumerate(images):
            logger.info(f"Running OCR on page {i+1}...")
            # Run OCR on each image
            page_text = image_to_string(image, lang='eng')
            if page_text:
                text += page_text + "\n"
                logger.info(f"Page {i+1} OCR text length: {len(page_text)}")
            else:
                logger.warning(f"No text extracted from page {i+1} via OCR")
        
        return text
    except Exception as e:
        logger.error(f"OCR extraction failed: {str(e)}", exc_info=True)
        return ""


def extract_order_info_with_ocr_page_by_page(file_content: bytes) -> Optional[Tuple[str, str, date]]:
    """Extract order info from PDF using OCR, processing page by page and stopping early if all info found"""
    if not OCR_AVAILABLE:
        return None
    
    try:
        logger.info("Converting PDF pages to images for OCR...")
        # Convert PDF pages to images
        images = convert_from_bytes(file_content, dpi=300)
        logger.info(f"Converted {len(images)} pages to images")
        
        for i, image in enumerate(images):
            logger.info(f"Running OCR on page {i+1}...")
            # Run OCR on each image
            page_text = image_to_string(image, lang='eng')
            if not page_text:
                logger.warning(f"No text extracted from page {i+1} via OCR")
                continue
            
            logger.info(f"Page {i+1} OCR text length: {len(page_text)}")
            logger.debug(f"Page {i+1} text (first 500 chars): {page_text[:500]}")
            
            # Try to extract all three pieces of information from this page
            name_result = extract_patient_name(page_text)
            dob = extract_date_of_birth(page_text)
            
            logger.info(f"Page {i+1} extraction results: name={name_result is not None}, dob={dob is not None}")
            if name_result:
                logger.info(f"Page {i+1} extracted name: {name_result[0]} {name_result[1]}")
            if dob:
                logger.info(f"Page {i+1} extracted DOB: {dob.date()}")
            
            # If we found all three pieces, we're done!
            if name_result and dob:
                first_name, last_name = name_result
                logger.info(f"✓ Found all required information on page {i+1}, stopping OCR early")
                return (first_name, last_name, dob.date())
            else:
                logger.info(f"Page {i+1}: Missing info, continuing to next page...")
        
        # If we get here, we didn't find all info on any single page
        logger.warning("Could not find all required information on any single page")
        return None
        
    except Exception as e:
        logger.error(f"OCR extraction failed: {str(e)}", exc_info=True)
        return None


def extract_patient_name(text: str) -> Optional[Tuple[str, str]]:
    """Extract first name and last name from PDF text"""
    # Pattern for format: "Patient Name and Address Patient Date of Birth\nMarie Curie 12/05/1900"
    # Look for the header line, then capture the next line which has name and date
    pattern = r"Patient\s+Name\s+and\s+Address.*?Date\s+of\s+Birth\s*\n\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\s+(\d{1,2}/\d{1,2}/\d{2,4})"
    match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
    if match:
        name_part = match.group(1).strip()
        name_parts = name_part.split()
        if len(name_parts) >= 2:
            first_name = name_parts[0]
            last_name = " ".join(name_parts[1:])
            logger.info("Extracted name: %s %s", first_name, last_name)
            return (first_name, last_name)
    
    # Fallback: Look for name on a line after "Patient Name" or similar headers
    # Pattern: "Patient Name" or "Name" followed by name on same or next line
    patterns = [
        r"(?:Patient\s+Name|Name)[:\s]+\s*([A-Z][a-z]+)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
        r"Patient\s+Name\s+and\s+Address\s*\n\s*([A-Z][a-z]+)\s+([A-Z][a-z]+)",
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            first_name = match.group(1).strip()
            last_name = match.group(2).strip()
            logger.info("Extracted name (fallback): %s %s", first_name, last_name)
            return (first_name, last_name)
    
    return None


def extract_date_of_birth(text: str) -> Optional[datetime]:
    """Extract date of birth from PDF text"""
    # Pattern for format: "Patient Name and Address Patient Date of Birth\nMarie Curie 12/05/1900"
    # Look for date on the same line as the name after the header
    pattern = r"Patient\s+Name\s+and\s+Address.*?Date\s+of\s+Birth\s*\n\s*[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\s+(\d{1,2}/\d{1,2}/\d{2,4})"
    match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
    if match:
        date_str = match.group(1)
        try:
            parsed_date = datetime.strptime(date_str, "%m/%d/%Y")
            if parsed_date.year > 1900 and parsed_date.year <= datetime.now().year:
                logger.info("Extracted date of birth: %s", parsed_date.date())
                return parsed_date
        except ValueError:
            pass
    
    # Fallback: Look for patterns like "Date of Birth: MM/DD/YYYY" or "DOB: MM/DD/YYYY"
    patterns = [
        r"(?:Date\s+of\s+Birth|DOB|D\.O\.B\.)[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
        r"(\d{1,2})/(\d{1,2})/(\d{4})",  # MM/DD/YYYY format
    ]
    
    for pattern in patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            if match.lastindex == 3:
                # Reconstruct date from groups
                month, day, year = match.groups()
                date_str = f"{month}/{day}/{year}"
            else:
                date_str = match.group(1) if match.lastindex >= 1 else match.group(0)
            
            # Try to parse the date
            for fmt in ["%m/%d/%Y", "%m-%d-%Y", "%m/%d/%y", "%m-%d-%y"]:
                try:
                    parsed_date = datetime.strptime(date_str, fmt)
                    # Validate it's a reasonable date (not in the future, not too old)
                    if parsed_date.year > 1900 and parsed_date.year <= datetime.now().year:
                        logger.info("Extracted date of birth (fallback): %s", parsed_date.date())
                        return parsed_date
                except ValueError:
                    continue
    
    return None


def extract_order_info_from_text_pdf_page_by_page(file_content: bytes) -> Optional[Tuple[str, str, date]]:
    """Extract order info from text-based PDF, processing page by page and stopping early if all info found"""
    try:
        logger.info("Processing text-based PDF page by page...")
        with pdfplumber.open(io.BytesIO(file_content)) as pdf:
            logger.info(f"Number of pages: {len(pdf.pages)}")
            
            for i, page in enumerate(pdf.pages):
                logger.info(f"Extracting text from page {i+1}...")
                
                # Try different extraction methods
                page_text = page.extract_text()
                if not page_text:
                    page_text = page.extract_text(layout=True)
                if not page_text:
                    words = page.extract_words()
                    if words:
                        page_text = " ".join([w.get('text', '') for w in words if w.get('text')])
                
                if not page_text:
                    logger.warning(f"No text extracted from page {i+1}")
                    continue
                
                logger.info(page_text[:500])
                # Try to extract all three pieces of information from this page
                name_result = extract_patient_name(page_text)
                dob = extract_date_of_birth(page_text)
                
                logger.info(f"Page {i+1} extraction results: name={name_result is not None}, dob={dob is not None}")
                if name_result:
                    logger.info(f"Page {i+1} extracted name: {name_result[0]} {name_result[1]}")
                if dob:
                    logger.info(f"Page {i+1} extracted DOB: {dob.date()}")
                
                # If we found all three pieces, we're done!
                if name_result and dob:
                    first_name, last_name = name_result
                    logger.info(f"✓ Found all required information on page {i+1}, stopping text extraction early")
                    return (first_name, last_name, dob.date())
                else:
                    logger.info(f"Page {i+1}: Missing info, continuing to next page...")
            
            # If we get here, we didn't find all info on any single page
            logger.warning("Could not find all required information on any single page")
            return None
            
    except Exception as e:
        logger.warning(f"pdfplumber extraction failed: {str(e)}")
        # Try PyPDF2 as fallback
        try:
            logger.info("Trying PyPDF2 as fallback...")
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_content))
            logger.info(f"Number of pages (PyPDF2): {len(pdf_reader.pages)}")
            
            for i, page in enumerate(pdf_reader.pages):
                logger.info(f"Extracting text from page {i+1} (PyPDF2)...")
                page_text = page.extract_text()
                
                if not page_text:
                    logger.warning(f"No text extracted from page {i+1} (PyPDF2)")
                    continue
                
                logger.info(f"Page {i+1} text length (PyPDF2): {len(page_text)}")
                
                # Try to extract all three pieces of information from this page
                name_result = extract_patient_name(page_text)
                dob = extract_date_of_birth(page_text)
                
                logger.info(f"Page {i+1} extraction results: name={name_result is not None}, dob={dob is not None}")
                
                # If we found all three pieces, we're done!
                if name_result and dob:
                    first_name, last_name = name_result
                    logger.info(f"✓ Found all required information on page {i+1}, stopping text extraction early")
                    return (first_name, last_name, dob.date())
                else:
                    logger.info(f"Page {i+1}: Missing info, continuing to next page...")
            
            return None
        except Exception as e2:
            logger.error(f"PyPDF2 extraction also failed: {str(e2)}")
            return None


def extract_order_info_from_pdf(file: UploadFile) -> Tuple[str, str, date]:
    """Extract first name, last name, and date of birth from a PDF file"""
    try:
        # Read the file content
        file_content = file.file.read()
        file.file.seek(0)  # Reset file pointer
    except Exception as e:
        logger.error(f"Error reading PDF file: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error reading PDF file. Please ensure the file is not corrupted."
        )
    
    # Try text-based PDF extraction page by page first
    logger.info("Attempting text-based PDF extraction page by page...")
    try:
        result = extract_order_info_from_text_pdf_page_by_page(file_content)
        if result:
            return result
    except Exception as e:
        logger.warning(f"Text extraction failed: {str(e)}")
    
    # If text extraction didn't work, try OCR page by page
    if OCR_AVAILABLE:
        logger.info("Text extraction didn't find all info, attempting OCR extraction page by page...")
        try:
            result = extract_order_info_with_ocr_page_by_page(file_content)
            if result:
                return result
        except Exception as e:
            logger.error(f"OCR extraction failed: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to extract information using OCR. The PDF may be corrupted or unreadable."
            )
    else:
        logger.warning("OCR not available, cannot process image-based PDFs")
    
    # If we get here, extraction failed
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=(
            "Could not extract patient name and date of birth from PDF. "
            "Please ensure the PDF contains readable text with 'Patient Name' and 'Date of Birth' fields."
        )
    )

