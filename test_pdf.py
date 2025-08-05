import PyPDF2
import tempfile
import os

def test_pdf_reading(pdf_path):
    """Test if we can read the PDF properly"""
    try:
        with open(pdf_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            print(f"✅ Successfully read PDF with {len(reader.pages)} pages")
            
            # Try to access the first page
            if len(reader.pages) > 0:
                first_page = reader.pages[0]
                print(f"✅ Successfully accessed first page")
                return True
            else:
                print("❌ PDF has no pages")
                return False
    except Exception as e:
        print(f"❌ Error reading PDF: {e}")
        return False

def test_pdf_creation():
    """Test if we can create a simple PDF"""
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            c = canvas.Canvas(tmp_file.name, pagesize=letter)
            c.drawString(100, 100, "Test")
            c.save()
            
            # Try to read it back
            with open(tmp_file.name, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                print(f"✅ Successfully created and read test PDF")
            
            os.unlink(tmp_file.name)
            return True
    except Exception as e:
        print(f"❌ Error creating test PDF: {e}")
        return False

if __name__ == "__main__":
    print("Testing PDF capabilities...")
    test_pdf_creation()
    
    # If you have a PDF file, uncomment this:
    # test_pdf_reading("your_pdf_file.pdf") 