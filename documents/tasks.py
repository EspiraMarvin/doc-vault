import os
from celery import shared_task
import logging
from .models import DocumentVersion
import boto3
from django.conf import settings
import io
import tempfile
import hashlib
import pdfplumber
import pytesseract
import clamd
from django.core.files.base import ContentFile


logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),  # Auto-retry on any exception
    retry_kwargs={'max_retries': 5},
    retry_backoff=True,  # Exponential backoff
    retry_backoff_max=600,  # Max 10 minutes between retries
    retry_jitter=True  # Add randomness to avoid thundering herd
)
def process_document_version(self, version_id):
    """entry point task, runs virus scan, OCR & indexing"""
    tmp = None
    try:
        dv = DocumentVersion.objects.get(pk=version_id)
        # download file from S3 to temp
        key = dv.file if isinstance(dv.file, str) else dv.file.name
        s3 = boto3.client(
            "s3",
            region_name=getattr(settings, "AWS_S3_REGION_NAME", None),
            aws_access_key_id=getattr(settings, "AWS_ACCESS_KEY_ID", None),
            aws_secret_access_key=getattr(settings, "AWS_SECRET_ACCESS_KEY", None),
        )
        tmp = tempfile.NamedTemporaryFile(delete=False)
        s3.download_file(settings.AWS_STORAGE_BUCKET_NAME, key, tmp.name)

        # compute hash is missing
        if not dv.file_hash:
            hasher = hashlib.sha256()
            with open(tmp.name, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    hasher.update(chunk)
            dv.file_hash = hasher.hexdigest()
            dv.save()

        # virus scan using clamd
        try:
            cd = clamd.ClamdUnixSocket()
            scan_result = cd.scan(tmp.name)

            status, virus_name = scan_result[tmp.name]

            if status == "FOUND":
                from .models import AuditLog

                AuditLog.objects.create(
                    user=None,
                    action="VIRUS_DETECTED",
                    document=dv.document,
                    version=dv,
                    extra={"virus_scan": scan_result, "virus": virus_name},
                )
                # Handle infected file (delete, quarantine, etc.)
                return
            else:
                AuditLog.objects.create(
                    user=None,
                    action="VIRUS_SCAN_PASSED",
                    document=dv.document,
                    version=dv,
                    extra={"virus_scan": scan_result},
                )
                logger.info(f"Virus scan passed for {dv.file.name}")

        except Exception as e:
            logger.error(f"Clamd scan failed: {e}")

        # OCR processing & Text extraction
        text = ""
        try:
            # For PDFs extract per page images/text via pdfplumber
            if tmp.name.lower().endswith(".pdf") or key.lower().endswith(".pdf"):
                with pdfplumber.open(tmp.name) as pdf:
                    for page in pdf.pages:
                        page_text = page.extract_text() or ""
                        text += page_text + "\n"
                    # If extracted text is empty, run OCR on page images
                    if not text.strip():
                        for page in pdf.pages:
                            im = page.to_image(resolution=300).original
                            page_ocr = pytesseract.image_to_string(im)
                            text += page_ocr + "\n"
            else:
                # try reading file bytes and run OCR if image; or python-docx for docx
                if key.lower().endswith(".docx"):
                    import docx

                    doc = docx.Document(tmp.name)
                    for p in doc.paragraphs:
                        text += p.text + "\n"
                else:
                    # try read as plain text
                    try:
                        with open(tmp.name, "r", encoding="utf-8") as f:
                            text = f.read()
                    except Exception:
                        # fallback: try OCR (if it is an image)
                        try:
                            im = Image.open(tmp.name)
                            text = pytesseract.image_to_string(im)
                        except:
                            text = ""
        except Exception as e:
            text += f"\n\n[OCR error: {e}]"

        dv.ocr_text = text
        dv.save()

        # indexing to elasticsearch
        """
        try:
            from .search import (
                index_document_version,
            )  # you can implement this using django-elasticsearch-dsl

            index_document_version(dv.id)
        except Exception:
            pass

        return True
        """
    except DocumentVersion.DoesNotExist:
        # if the document doesn't exist
        logger.error(f"DocumentVersion {version_id} not found")
        return False
    finally:
        # cleanup temp file, even if task fails or retries
        if tmp and os.path.exists(tmp.name):
            try:
                os.unlink(tmp.name)
                logger.debug(f"Cleaned up temp file: {tmp.name}")
            except Exception as e:
                logger.error(f"Failed to cleanup temp file: {e}")
