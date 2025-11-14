"""
Service for extracting images from DOCX files.

Extracts embedded images from word/media/* within .docx archive structure.
Saves images to storage and creates ReportImage records.
"""

from __future__ import annotations

import io
import logging
import zipfile
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ExtractedImage:
    """Metadata for an extracted image."""

    data: bytes
    filename: str
    page: int
    order_index: int
    format: str
    size_bytes: int


class DocxExtractionError(Exception):
    """Base error for DOCX extraction operations."""


class InvalidDocxError(DocxExtractionError):
    """Raised when file is not a valid DOCX."""


class ImageExtractionError(DocxExtractionError):
    """Raised when image extraction fails."""


class DocxImageExtractor:
    """
    Extracts images from DOCX files.

    DOCX files are ZIP archives containing images in word/media/ directory.
    This service extracts those images and returns metadata for storage.
    """

    MEDIA_PREFIX = "word/media/"
    SUPPORTED_FORMATS = {".png", ".jpg", ".jpeg", ".gif", ".bmp"}

    def __init__(self):
        pass

    def extract_images(self, docx_path: Path) -> list[ExtractedImage]:
        """
        Extract all images from a DOCX file.

        Args:
            docx_path: Path to the .docx file

        Returns:
            List of ExtractedImage with metadata

        Raises:
            InvalidDocxError: If file is not a valid DOCX
            ImageExtractionError: If extraction fails
        """
        if not docx_path.exists():
            raise InvalidDocxError(f"File not found: {docx_path}")

        try:
            with zipfile.ZipFile(docx_path, "r") as docx_zip:
                return self._extract_from_zip(docx_zip)
        except zipfile.BadZipFile as exc:
            raise InvalidDocxError(f"Not a valid ZIP/DOCX file: {docx_path}") from exc
        except Exception as exc:
            raise ImageExtractionError(f"Failed to extract images: {exc}") from exc

    def _extract_from_zip(self, docx_zip: zipfile.ZipFile) -> list[ExtractedImage]:
        """Extract images from opened ZIP archive."""
        images = []
        media_files = [
            name
            for name in docx_zip.namelist()
            if name.startswith(self.MEDIA_PREFIX) and not name.endswith("/")
        ]

        # Sort to ensure deterministic ordering
        media_files.sort()

        logger.debug(f"Found {len(media_files)} media files in DOCX archive")

        for order_index, media_path in enumerate(media_files):
            ext = Path(media_path).suffix.lower()
            if ext not in self.SUPPORTED_FORMATS:
                logger.debug(f"Skipping unsupported format: {media_path} ({ext})")
                continue

            try:
                with docx_zip.open(media_path) as img_file:
                    image_data = img_file.read()
                    image_format = self._detect_format(image_data)
                    filename = Path(media_path).name

                    logger.debug(
                        f"Extracted image {order_index}: {filename} "
                        f"({image_format}, {len(image_data)} bytes)"
                    )

                    images.append(
                        ExtractedImage(
                            data=image_data,
                            filename=filename,
                            page=0,  # DOCX doesn't have page concept, set to 0
                            order_index=order_index,
                            format=image_format,
                            size_bytes=len(image_data),
                        )
                    )
            except Exception as exc:
                # Log warning but continue with other images
                logger.warning(
                    f"Failed to extract {media_path}: {exc}",
                    exc_info=False,
                )
                continue

        logger.info(f"Successfully extracted {len(images)} images from DOCX")
        return images

    def _detect_format(self, image_data: bytes) -> str:
        """
        Detect image format using PIL.

        Args:
            image_data: Raw image bytes

        Returns:
            Format string (PNG, JPEG, etc.)
        """
        try:
            with Image.open(io.BytesIO(image_data)) as img:
                return img.format or "UNKNOWN"
        except Exception:
            return "UNKNOWN"

    def convert_to_png(self, image_data: bytes) -> bytes:
        """
        Convert image to PNG format if needed.

        Args:
            image_data: Raw image bytes

        Returns:
            PNG image bytes
        """
        try:
            with Image.open(io.BytesIO(image_data)) as img:
                # Convert to RGB if needed (for transparency handling)
                if img.mode in ("RGBA", "LA", "P"):
                    background = Image.new("RGB", img.size, (255, 255, 255))
                    if img.mode == "P":
                        img = img.convert("RGBA")
                    background.paste(
                        img, mask=img.split()[-1] if img.mode in ("RGBA", "LA") else None
                    )
                    img = background
                elif img.mode != "RGB":
                    img = img.convert("RGB")

                # Save to PNG
                output = io.BytesIO()
                img.save(output, format="PNG")
                return output.getvalue()
        except Exception as exc:
            raise ImageExtractionError(f"Failed to convert image to PNG: {exc}") from exc
