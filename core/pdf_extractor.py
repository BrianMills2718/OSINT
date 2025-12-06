#!/usr/bin/env python3
"""
PDF extraction utility for document-heavy sources.

Provides async-safe PDF downloading and text extraction using PyMuPDF.
Used by integrations like FBI Vault, GovInfo, CourtListener, Federal Register.
"""

import asyncio
import hashlib
import logging
import tempfile
from pathlib import Path
from typing import Optional, Tuple
from urllib.parse import urlparse

import aiohttp

logger = logging.getLogger(__name__)

# Cache directory for downloaded PDFs
PDF_CACHE_DIR = Path("data/pdf_cache")


class PDFExtractor:
    """
    Async-safe PDF text extraction.

    Features:
    - Downloads PDFs asynchronously
    - Extracts text using PyMuPDF (fitz)
    - Caches PDFs locally by URL hash
    - Configurable max pages and size limits
    - Graceful error handling
    """

    def __init__(
        self,
        cache_dir: Path = PDF_CACHE_DIR,
        max_size_mb: float = 50.0,
        max_pages: int = 100,
        timeout_seconds: int = 30
    ):
        """
        Initialize PDF extractor.

        Args:
            cache_dir: Directory to cache downloaded PDFs
            max_size_mb: Maximum PDF size to download (MB)
            max_pages: Maximum pages to extract text from
            timeout_seconds: Download timeout
        """
        self.cache_dir = cache_dir
        self.max_size_bytes = int(max_size_mb * 1024 * 1024)
        self.max_pages = max_pages
        self.timeout = aiohttp.ClientTimeout(total=timeout_seconds)

        # Ensure cache directory exists
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _url_to_cache_path(self, url: str) -> Path:
        """Convert URL to cache file path using hash."""
        url_hash = hashlib.md5(url.encode()).hexdigest()
        return self.cache_dir / f"{url_hash}.pdf"

    async def download_pdf(self, url: str) -> Optional[Path]:
        """
        Download PDF from URL, using cache if available.

        Args:
            url: PDF URL to download

        Returns:
            Path to downloaded PDF, or None if failed
        """
        cache_path = self._url_to_cache_path(url)

        # Return cached version if exists
        if cache_path.exists():
            logger.debug(f"Using cached PDF: {cache_path}")
            return cache_path

        try:
            # Headers to avoid bot detection
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "application/pdf,*/*"
            }

            # Allow redirects
            async with aiohttp.ClientSession(timeout=self.timeout, headers=headers) as session:
                async with session.get(url, allow_redirects=True) as response:
                    if response.status != 200:
                        logger.warning(f"PDF download failed: HTTP {response.status} for {url}")
                        return None

                    # Check content length
                    content_length = response.headers.get('Content-Length')
                    if content_length and int(content_length) > self.max_size_bytes:
                        logger.warning(f"PDF too large: {int(content_length) / 1024 / 1024:.1f}MB > {self.max_size_bytes / 1024 / 1024:.1f}MB limit")
                        return None

                    # Check content type
                    content_type = response.headers.get('Content-Type', '')
                    if 'pdf' not in content_type.lower() and not url.lower().endswith('.pdf'):
                        logger.warning(f"URL does not appear to be PDF: {content_type}")
                        # Continue anyway - some servers don't set content type correctly

                    # Download to cache
                    content = await response.read()

                    if len(content) > self.max_size_bytes:
                        logger.warning(f"PDF content too large: {len(content) / 1024 / 1024:.1f}MB")
                        return None

                    cache_path.write_bytes(content)
                    logger.info(f"Downloaded PDF: {url} -> {cache_path}")
                    return cache_path

        except asyncio.TimeoutError:
            logger.warning(f"PDF download timeout: {url}")
            return None
        except Exception as e:
            logger.error(f"PDF download failed: {e}", exc_info=True)
            return None

    def extract_text(self, pdf_path: Path) -> Tuple[str, int]:
        """
        Extract text from PDF file.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Tuple of (extracted_text, page_count)
        """
        try:
            import fitz  # PyMuPDF
        except ImportError:
            logger.error("PyMuPDF not installed. Run: pip install PyMuPDF")
            return "", 0

        try:
            doc = fitz.open(pdf_path)
            text_parts = []
            page_count = min(len(doc), self.max_pages)

            for page_num in range(page_count):
                page = doc[page_num]
                text = page.get_text()
                if text.strip():
                    text_parts.append(f"[Page {page_num + 1}]\n{text}")

            doc.close()

            full_text = "\n\n".join(text_parts)
            logger.debug(f"Extracted {len(full_text)} chars from {page_count} pages")
            return full_text, page_count

        except Exception as e:
            logger.error(f"PDF extraction failed for {pdf_path}: {e}", exc_info=True)
            return "", 0

    async def extract_from_url(self, url: str) -> Tuple[str, dict]:
        """
        Download and extract text from PDF URL.

        Args:
            url: PDF URL

        Returns:
            Tuple of (extracted_text, metadata_dict)
        """
        metadata = {
            "url": url,
            "success": False,
            "page_count": 0,
            "char_count": 0,
            "cached": False,
            "error": None
        }

        # Check cache
        cache_path = self._url_to_cache_path(url)
        metadata["cached"] = cache_path.exists()

        # Download
        pdf_path = await self.download_pdf(url)
        if not pdf_path:
            metadata["error"] = "Download failed"
            return "", metadata

        # Extract - run in thread to avoid blocking
        text, page_count = await asyncio.to_thread(self.extract_text, pdf_path)

        metadata["success"] = bool(text)
        metadata["page_count"] = page_count
        metadata["char_count"] = len(text)

        return text, metadata

    def clear_cache(self, older_than_days: int = 7):
        """
        Clear old cached PDFs.

        Args:
            older_than_days: Delete files older than this many days
        """
        import time

        cutoff = time.time() - (older_than_days * 24 * 60 * 60)
        deleted = 0

        for pdf_file in self.cache_dir.glob("*.pdf"):
            if pdf_file.stat().st_mtime < cutoff:
                pdf_file.unlink()
                deleted += 1

        logger.info(f"Cleared {deleted} cached PDFs older than {older_than_days} days")


# Singleton instance
_extractor: Optional[PDFExtractor] = None


def get_pdf_extractor() -> PDFExtractor:
    """Get or create singleton PDF extractor instance."""
    global _extractor
    if _extractor is None:
        _extractor = PDFExtractor()
    return _extractor


async def extract_pdf_text(url: str) -> Tuple[str, dict]:
    """
    Convenience function to extract text from PDF URL.

    Args:
        url: PDF URL

    Returns:
        Tuple of (extracted_text, metadata_dict)
    """
    extractor = get_pdf_extractor()
    return await extractor.extract_from_url(url)
