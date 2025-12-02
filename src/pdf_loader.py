"""
PDF Loader - Extract and process course PDFs
"""
from pathlib import Path
from typing import List
from pypdf import PdfReader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from src.config import config

class PDFLoader:
    """Load and process PDF files"""
    
    def __init__(self):
        """Initialize PDF loader"""
        self.pdf_folder = Path(config.PDF_FOLDER_PATH)
        self.chunk_size = 1000  # Characters per chunk
        self.chunk_overlap = 200  # Overlap between chunks
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=["\n\n", "\n", " ", ""]
        )
    
    def load_all_pdfs(self) -> List[dict]:
        """
        Load all PDFs from the PDF folder
        
        Returns:
            List of documents with metadata
        """
        documents = []
        
        # Get all PDF files
        pdf_files = list(self.pdf_folder.glob("*.pdf"))
        
        if not pdf_files:
            print(f"⚠️  No PDFs found in {self.pdf_folder}")
            return documents
        
        print(f"📚 Found {len(pdf_files)} PDF(s)")
        
        for pdf_path in pdf_files:
            print(f"📖 Processing: {pdf_path.name}")
            try:
                docs = self._load_pdf(pdf_path)
                documents.extend(docs)
                print(f"   ✅ Extracted {len(docs)} chunks")
            except Exception as e:
                print(f"   ❌ Error processing {pdf_path.name}: {e}")
        
        print(f"\n✅ Total chunks created: {len(documents)}")
        return documents
    
    def _load_pdf(self, pdf_path: Path) -> List[dict]:
        """
        Load a single PDF file
        
        Args:
            pdf_path: Path to PDF file
        
        Returns:
            List of text chunks with metadata
        """
        documents = []
        
        # Read PDF
        pdf_reader = PdfReader(pdf_path)
        pdf_name = pdf_path.stem  # Filename without extension
        
        # Extract text from all pages
        full_text = ""
        for page_num, page in enumerate(pdf_reader.pages):
            text = page.extract_text()
            full_text += text + "\n"
        
        # Split into chunks
        chunks = self.text_splitter.split_text(full_text)
        
        # Create documents with metadata
        for chunk_idx, chunk in enumerate(chunks):
            doc = {
                "content": chunk,
                "metadata": {
                    "source": pdf_name,
                    "chunk_index": chunk_idx,
                    "file_path": str(pdf_path)
                }
            }
            documents.append(doc)
        
        return documents


# Global instance
pdf_loader = PDFLoader()
