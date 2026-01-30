"""Document downloader for Finlex Open Data."""

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from lxml import etree

from .client import FinlexClient
from .logging_config import logger
from .urls import DocumentInfo, parse_akn_uri, build_api_path


@dataclass
class DownloadResult:
    """Result of a single download operation."""

    akn_uri: str
    status: str  # success, skipped, error
    timestamp: str
    files: list[str] = field(default_factory=list)
    error: Optional[str] = None


@dataclass
class DownloadOptions:
    """Options for downloading documents."""

    output_dir: Path
    fetch_pdf: bool = False
    fetch_zip: bool = False
    fetch_media: bool = False
    force: bool = False
    dry_run: bool = False


# Akoma Ntoso namespace
AKN_NS = {"akn": "http://docs.oasis-open.org/legaldocml/ns/akn/3.0"}


def download_document(
    client: FinlexClient,
    akn_uri: str,
    options: DownloadOptions,
) -> DownloadResult:
    """Download a single document and its assets.
    
    Args:
        client: HTTP client instance.
        akn_uri: Document URI from list endpoint.
        options: Download options.
    
    Returns:
        DownloadResult with status and file paths.
    """
    result = DownloadResult(
        akn_uri=akn_uri,
        status="error",
        timestamp=datetime.now().isoformat(),
    )

    # Parse URI to get document info
    info = parse_akn_uri(akn_uri)
    if not info:
        result.error = f"Failed to parse URI: {akn_uri}"
        logger.error(result.error)
        return result

    # Create output directory
    doc_dir = options.output_dir / info.folder_path
    xml_path = doc_dir / "main.xml"

    # Check if already exists
    if xml_path.exists() and not options.force:
        result.status = "skipped"
        result.files.append(str(xml_path))
        logger.info(f"Skipping existing: {xml_path}")
        return result

    if options.dry_run:
        result.status = "dry-run"
        logger.info(f"[DRY-RUN] Would download: {akn_uri}")
        logger.info(f"[DRY-RUN] To: {doc_dir}")
        return result

    # Create directory
    doc_dir.mkdir(parents=True, exist_ok=True)

    # Fetch XML
    api_path = build_api_path(info)
    try:
        response = client.get_xml(api_path)
        if response.status_code != 200:
            result.error = f"HTTP {response.status_code} fetching XML"
            logger.error(result.error)
            return result

        xml_content = response.content
        xml_path.write_bytes(xml_content)
        result.files.append(str(xml_path))
        logger.info(f"Downloaded XML: {xml_path}")

    except Exception as e:
        result.error = f"Failed to fetch XML: {e}"
        logger.error(result.error)
        return result

    # Fetch PDF if requested
    if options.fetch_pdf:
        pdf_path = doc_dir / "main.pdf"
        try:
            response = client.get_pdf(f"{api_path}/main.pdf")
            if response.status_code == 200:
                pdf_path.write_bytes(response.content)
                result.files.append(str(pdf_path))
                logger.info(f"Downloaded PDF: {pdf_path}")
            elif response.status_code != 404:
                logger.warning(f"PDF fetch returned HTTP {response.status_code}")
        except Exception as e:
            logger.warning(f"Failed to fetch PDF: {e}")

    # Fetch ZIP if requested
    if options.fetch_zip:
        zip_path = doc_dir / "main.zip"
        try:
            response = client.get_zip(f"{api_path}/main.akn")
            if response.status_code == 200:
                zip_path.write_bytes(response.content)
                result.files.append(str(zip_path))
                logger.info(f"Downloaded ZIP: {zip_path}")
            elif response.status_code != 404:
                logger.warning(f"ZIP fetch returned HTTP {response.status_code}")
        except Exception as e:
            logger.warning(f"Failed to fetch ZIP: {e}")

    # Fetch media if requested
    if options.fetch_media:
        media_links = extract_media_links(xml_content)
        if media_links:
            media_dir = doc_dir / "media"
            media_dir.mkdir(exist_ok=True)
            for link in media_links:
                media_path = media_dir / Path(link).name
                try:
                    response = client.get(f"{api_path}/{link}")
                    if response.status_code == 200:
                        media_path.write_bytes(response.content)
                        result.files.append(str(media_path))
                        logger.info(f"Downloaded media: {media_path}")
                except Exception as e:
                    logger.warning(f"Failed to fetch media {link}: {e}")

    result.status = "success"
    return result


def extract_media_links(xml_content: bytes) -> list[str]:
    """Extract media file links from Akoma Ntoso XML.
    
    Args:
        xml_content: Raw XML bytes.
    
    Returns:
        List of relative media paths (e.g., ["media/123.gif"]).
    """
    links = []
    try:
        tree = etree.fromstring(xml_content)
        
        # Look for img elements
        for img in tree.xpath("//akn:img/@src", namespaces=AKN_NS):
            if img.startswith("media/"):
                links.append(img)
        
        # Look for attachments with href
        for href in tree.xpath("//akn:attachment//@href", namespaces=AKN_NS):
            if href.startswith("media/"):
                links.append(href)
        
        # Look for ref elements pointing to media
        for ref in tree.xpath("//akn:ref/@href", namespaces=AKN_NS):
            if ref.startswith("media/"):
                links.append(ref)

    except Exception as e:
        logger.warning(f"Failed to parse XML for media links: {e}")

    return list(set(links))  # Deduplicate
