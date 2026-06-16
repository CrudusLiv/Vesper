"""OCR processing for image-only slides in lectures."""

from pathlib import Path
from typing import Any, List, Optional, Tuple
from PIL import Image
import logging

logger = logging.getLogger(__name__)


def extract_slide_images(
    pdf_path: Optional[Path] = None,
    pptx_path: Optional[Path] = None
) -> List[Image.Image]:
    """
    Extract images from PDF or PPTX file.

    Args:
        pdf_path: Path to PDF file (mutually exclusive with pptx_path)
        pptx_path: Path to PPTX file (mutually exclusive with pdf_path)

    Returns:
        List of PIL Images, one per slide, in order. Returns empty list if neither
        path is provided or if extraction fails.
    """
    if not pdf_path and not pptx_path:
        return []

    if pdf_path:
        return _extract_from_pdf(pdf_path)
    else:
        return _extract_from_pptx(pptx_path)


def _extract_from_pdf(pdf_path: Path) -> List[Image.Image]:
    """Extract images from PDF file."""
    try:
        from pdf2image import convert_from_path
    except ImportError:
        logger.error("pdf2image not installed. Install with: pip install pdf2image")
        return []

    try:
        images = convert_from_path(str(pdf_path), dpi=200)
        return images
    except Exception as e:
        logger.error(f"Failed to extract images from PDF {pdf_path}: {e}")
        return []


def _extract_from_pptx(pptx_path: Path) -> List[Image.Image]:
    """Extract slide images from PPTX file."""
    try:
        from pptx import Presentation
    except ImportError:
        logger.error("python-pptx not installed. Install with: pip install python-pptx")
        return []

    try:
        prs = Presentation(str(pptx_path))
        images = []

        for slide_idx, slide in enumerate(prs.slides, 1):
            slide_image = _render_slide_to_image(slide, slide_idx)
            if slide_image:
                images.append(slide_image)

        return images
    except Exception as e:
        logger.error(f"Failed to extract images from PPTX {pptx_path}: {e}")
        return []


def _render_slide_to_image(slide: Any, slide_idx: int) -> Optional[Image.Image]:
    """Render a PPTX slide to a PIL Image.

    Args:
        slide: pptx.util.Slide object to render
        slide_idx: Index of the slide (1-based)

    Returns:
        PIL Image or None if rendering fails
    """
    # TODO: implement actual slide rendering (extract shapes, text, images from slide)
    # Create a blank image for the slide (standard 16:9 aspect ratio)
    width, height = 1280, 720
    image = Image.new('RGB', (width, height), color='white')

    return image


def run_ocr_on_image(image: Optional[Image.Image]) -> Tuple[str, float, Optional[str]]:
    """
    Run EasyOCR on a slide image to extract text.

    Args:
        image: PIL Image of slide to process

    Returns:
        Tuple of (extracted_text, confidence_score, error_message)
        - extracted_text: string of recognized text (empty string if error or no text found)
        - confidence_score: float 0-1 indicating average confidence across all detected text
        - error_message: string describing error if one occurred, None otherwise
    """
    if image is None:
        return "", 0.0, "Image is None"

    try:
        import easyocr
    except ImportError:
        logger.error("easyocr not installed. Install with: pip install easyocr")
        return "", 0.0, "easyocr not installed"

    try:
        # Initialize reader (caches model after first run)
        # gpu_device='cpu' avoids CUDA issues; silent=True suppresses progress bars
        reader = easyocr.Reader(['en'], gpu=False, verbose=False)

        # Convert PIL Image to numpy array (easyocr expects BGR or RGB numpy array)
        import numpy as np
        image_array = np.array(image)

        # Run OCR
        results = reader.readtext(image_array, detail=1)

        # Extract text and calculate average confidence
        texts = []
        confidences = []

        for (bbox, text, conf) in results:
            texts.append(text)
            confidences.append(conf)

        extracted_text = " ".join(texts)
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

        return extracted_text, avg_confidence, None

    except Exception as e:
        logger.error(f"OCR processing failed: {e}")
        return "", 0.0, str(e)
