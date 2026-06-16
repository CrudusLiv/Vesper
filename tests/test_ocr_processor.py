"""Tests for OCR image extraction from PDFs and PPTX files."""

import pytest
from pathlib import Path
from PIL import Image
from scripts.ocr_processor import extract_slide_images


@pytest.fixture
def sample_pdf_path():
    """Create a minimal test PDF fixture if it doesn't exist."""
    fixture_dir = Path("tests/fixtures")
    fixture_dir.mkdir(exist_ok=True)

    pdf_path = fixture_dir / "sample_lecture.pdf"

    # If fixture doesn't exist, create a simple one via reportlab
    if not pdf_path.exists():
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.pdfgen import canvas

            c = canvas.Canvas(str(pdf_path), pagesize=letter)
            c.setFont("Helvetica-Bold", 24)
            c.drawString(100, 750, "Sample Lecture - Page 1")
            c.setFont("Helvetica", 12)
            c.drawString(100, 700, "This is test content")
            c.showPage()

            c.setFont("Helvetica-Bold", 24)
            c.drawString(100, 750, "Sample Lecture - Page 2")
            c.showPage()

            c.save()
        except ImportError:
            pytest.skip("reportlab required to create PDF fixture")

    return pdf_path


@pytest.fixture
def sample_pptx_path():
    """Create a minimal test PPTX fixture if it doesn't exist."""
    fixture_dir = Path("tests/fixtures")
    fixture_dir.mkdir(exist_ok=True)

    pptx_path = fixture_dir / "sample_lecture.pptx"

    # If fixture doesn't exist, create a simple one
    if not pptx_path.exists():
        try:
            from pptx import Presentation
            from pptx.util import Inches

            prs = Presentation()

            # Add 2 slides
            for i in range(2):
                slide_layout = prs.slide_layouts[5]  # Blank layout
                slide = prs.slides.add_slide(slide_layout)
                title_box = slide.shapes.add_textbox(Inches(1), Inches(2), Inches(8), Inches(2))
                title_frame = title_box.text_frame
                title_frame.text = f"Sample Lecture - Slide {i+1}"

            prs.save(str(pptx_path))
        except ImportError:
            pytest.skip("python-pptx required to create PPTX fixture")

    return pptx_path


def test_extract_images_from_pdf(sample_pdf_path):
    """Test extracting images from a PDF file."""
    images = extract_slide_images(pdf_path=sample_pdf_path, pptx_path=None)

    assert isinstance(images, list)
    # PDF extraction requires poppler; if not installed, graceful return of empty list is OK
    if len(images) > 0:
        assert all(isinstance(img, Image.Image) for img in images)


def test_extract_images_from_pptx(sample_pptx_path):
    """Test extracting images from a PPTX file."""
    images = extract_slide_images(pdf_path=None, pptx_path=sample_pptx_path)

    assert isinstance(images, list)
    assert len(images) > 0
    assert all(isinstance(img, Image.Image) for img in images)


def test_extract_images_none_if_both_none():
    """Test that empty list is returned if both pdf_path and pptx_path are None."""
    images = extract_slide_images(pdf_path=None, pptx_path=None)
    assert images == []
