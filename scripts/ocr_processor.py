"""OCR processing for image-only slides in lectures."""

from pathlib import Path
from typing import Any, List, Optional
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
