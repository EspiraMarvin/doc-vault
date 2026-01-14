from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model

User = get_user_model()


# tags to categorize documents
class Tag(models.Model):
    name = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.name


# single document entity
class Document(models.Model):
    title = models.CharField(max_length=512)
    description = models.TextField(blank=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="documents")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    tags = models.ManyToManyField(Tag, blank=True, related_name="documents")

    # optional aggregate fields
    latest_version = models.ForeignKey(
        "DocumentVersion",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    def __str__(self):
        return self.title


# generates upload path for document versions
def upload_to_document_version(instance, filename):
    # store by document id and version number
    return f"documents/{instance.document.id}/v/{instance.version_number}/{filename}"
    # return f'documents/{instance.document.id}/versions/{filename}'


# tracks versions of a document
class DocumentVersion(models.Model):
    document = models.ForeignKey(
        Document, on_delete=models.CASCADE, related_name="versions"
    )
    file = models.FileField(upload_to=upload_to_document_version)
    version_number = models.PositiveBigIntegerField()
    uploaded_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    file_size = models.BigIntegerField(null=True, blank=True)
    content_type = models.CharField(max_length=200, blank=True)
    file_hash = models.CharField(max_length=128, blank=True)
    ocr_text = models.TextField(blank=True)
    indexed = models.BooleanField(default=False)

    class meta:
        # ensure unique version numbers per document/ prevent duplicate
        # version no.s per document
        unique_together = ("document", "version_number")
        ordering = "-version_number"  # return latest version first

    def __str__(self):
        return f"{self.document} v{self.version_number}"


# Tracks user actions for auditing
class AuditLog(models.Model):
    ACTION_CHOICES = [
        ("UPLOAD", "Upload"),
        ("DOWNLOAD", "Download"),
        ("DELETE", "Delete"),
        ("UPDATE", "Update"),
        ("TAG", "Tag"),
        ("ADDTAG", "Tag Added"),
        ("REMOVETAG", "Tag Removed"),
        ("VIRUS_DETECTED", "Virus Detected"),   
        ("VIRUS_SCAN_PASSED", "Virus Scan Passed"),
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    document = models.ForeignKey(
        Document, on_delete=models.SET_NULL, null=True, blank=True
    )
    version = models.ForeignKey(
        DocumentVersion, on_delete=models.SET_NULL, null=True, blank=True
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    details = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    extra = models.JSONField(null=True, blank=True)

    def __str__(self):
        return f"{self.user} {self.action} {self.document} @ {self.timestamp}"


# Manages sharing documents with different users and permissions
class SharedDocument(models.Model):
    PERMISSION_CHOICES = [
        ("VIEW", "View"),
        ("COMMENT", "Comment"),
        ("EDIT", "Edit"),
    ]
    document = models.ForeignKey(
        Document, on_delete=models.CASCADE, related_name="shared_with"
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="shared_documents"
    )
    permission = models.CharField(
        max_length=20, choices=PERMISSION_CHOICES, default="VIEW"
    )
    shared_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Prevents sharing the same document with the same user twice.
        unique_together = ("document", "user")
