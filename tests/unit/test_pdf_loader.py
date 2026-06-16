import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
from src.document_processing.pdf_loader import PDFLoader

def test_pdf_loader_initialization():
    loader = PDFLoader()
    assert loader.chunk_size == 1000
    assert loader.chunk_overlap == 200
    assert loader.text_splitter is not None

@patch('src.document_processing.pdf_loader.PDFLoader._extract_with_pypdf')
def test_load_pdf_success(mock_pypdf_extract):
    mock_pypdf_extract.return_value = "This is page one content.\nThis is page two content."
    loader = PDFLoader()
    
    pdf_path = Path("test_document.pdf")
    docs = loader._load_pdf(pdf_path)
    
    assert len(docs) > 0
    assert docs[0]["content"] == "This is page one content.\nThis is page two content."
    assert docs[0]["metadata"]["source"] == "test_document"
    assert docs[0]["metadata"]["chunk_index"] == 0
    assert docs[0]["metadata"]["file_path"] == str(pdf_path)

@patch('src.document_processing.pdf_loader.PDFLoader._extract_with_pypdf')
@patch('src.document_processing.pdf_loader.PDFLoader._extract_with_pymupdf')
def test_load_pdf_fallback(mock_pymupdf_extract, mock_pypdf_extract):
    # Mock pypdf to fail, and pymupdf to succeed
    mock_pypdf_extract.side_effect = Exception("pypdf error")
    mock_pymupdf_extract.return_value = "Pymupdf fallback content"
    
    loader = PDFLoader()
    pdf_path = Path("fallback_doc.pdf")
    docs = loader._load_pdf(pdf_path)
    
    assert len(docs) == 1
    assert docs[0]["content"] == "Pymupdf fallback content"
    assert docs[0]["metadata"]["source"] == "fallback_doc"

@patch('src.document_processing.pdf_loader.PDFLoader._load_pdf')
@patch('pathlib.Path.glob')
def test_load_all_pdfs(mock_glob, mock_load_pdf):
    # Mock glob to return two PDF paths
    mock_glob.return_value = [Path("doc1.pdf"), Path("doc2.pdf")]
    
    mock_load_pdf.side_effect = [
        [{"content": "chunk1", "metadata": {"source": "doc1", "chunk_index": 0, "file_path": "doc1.pdf"}}],
        [{"content": "chunk2", "metadata": {"source": "doc2", "chunk_index": 0, "file_path": "doc2.pdf"}}]
    ]
    
    loader = PDFLoader()
    all_docs = loader.load_all_pdfs()
    
    assert len(all_docs) == 2
    assert all_docs[0]["content"] == "chunk1"
    assert all_docs[1]["content"] == "chunk2"
    assert mock_load_pdf.call_count == 2
