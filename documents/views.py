from django.shortcuts import render
from rest_framework.decorators import action
from rest_framework import viewsets, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from .models import Document, DocumentVersion, Tag, AuditLog, SharedDocument
from .serializers import (
    DocumentSerializer,
    SimpleDocumentCreateSerializer,
    PresignedUploadResponseSerializer,
    DocumentVersionSerializer,
    TagSerializer,
)
from .utils import generate_presigned_post


class DocumentViewSet(viewsets.ViewSet):
    """
    A document ViewSet for:
    1. listing & retrieving documents
    2. creating document meta & request presigned URL for upload to s3
    3. notifying server about completed upload to s3 - complete upload hook
    4. server tag documents
    5. share documents
    6. download document - pre-signed
    """

    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        querySet = Document.objects.filter(owner=request.user)
        serializer = DocumentSerializer(querySet, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        doc = get_object_or_404(Document, pk=pk)
        serializer = DocumentSerializer(doc, context={"request": request})
        return Response(serializer.data)

    # custom endpoints for our ViewSet
    @action(detail=False, methods=["post"])
    def create_meta(self, request):
        """
        create a document entry and return presigned upload URL info
        Expected payload:
        {
            "title": "Document Title",
            "description": "Optional description"
             "filename": "invoice.pdf",
            "content_type": "application/pdf"
        }
        """
        payload = request.data
        title = payload.get("title")
        filename = payload.get("filename")
        content_type = payload.get("content_type", "application/octet-stream")

        if not title or not filename:
            return Response(
                {"error": "title and filename required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        doc = Document.objects.create(
            title=title, description=payload.get("description", ""), owner=request.user
        )
        # create first version record (with placeholder file path to be set
        # when backend completes upload)
        version_number = 1
        # construct 3s key
        key = f"document/{doc.id}/v{version_number}/{filename}"

        # return presigned document
        post = generate_presigned_post(key, content_type)
        # save a shadow documentversion record
        # which we update on "complete_upload" hook run
        dv = DocumentVersion.objects.create(
            document=doc,
            file=key,
            version_number=version_number,
            uploaded_by=request.user,
            file_size=0,
            content_type=content_type,
            file_hash="",
        )

        doc.latest_version = dv
        doc.save()

        # audit
        AuditLog.objects.create(
            user=request.user,
            action="UPLOAD",
            document=doc,
            document_version=dv,
            extra={"s3_key": key},
        )

        return Response(
            {
                "document_id": doc.id,
                "version_id": dv.id,
                "presigned_post": post,
            },
            status=status.HTTP_201_CREATED,
        )
