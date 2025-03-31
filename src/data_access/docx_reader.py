# src/data_access/docx_reader.py
"""Module for reading data from DOCX files."""
import logging
from pathlib import Path
from typing import Optional
from docx import Document
from docx.opc.exceptions import PackageNotFoundError

# Import core type if needed for return type hint, otherwise return str
# from src.core import MyOwnCompanyBusinessData

logger = logging.getLogger(__name__)

def read_skyfend_business(docx_file_path: Path) -> str | None:
    """
    Read and extract text from a DOCX file, handling various edge cases.
    
    Args:
        docx_file_path: Path to the DOCX file
        
    Returns:
        str: Extracted text from the document, or None if there was an error
    """
    try:
        if not docx_file_path.is_file():
            logger.error(f"File not found: {docx_file_path}")
            return None
            
        doc = Document(docx_file_path)
        
        # Process paragraphs with robust error handling
        paras_text = []
        for para in doc.paragraphs:
            # Skip paragraphs with None text or empty after stripping
            if para.text is None or not para.text.strip():
                continue
            paras_text.append(para.text)
            
        full_text = "\n".join(paras_text)
        logger.info(f"Successfully read {len(paras_text)} paragraphs from {docx_file_path}")
        return full_text
        
    except PackageNotFoundError as e:
        logger.error(f"Invalid or corrupted DOCX file '{docx_file_path}': {e}")
        return None
    except Exception as e:
        logger.error(f"Error reading DOCX document '{docx_file_path}': {e}")
        return None