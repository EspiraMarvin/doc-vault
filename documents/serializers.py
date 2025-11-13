from rest_framework import serializers
from .models import Document, DocumentVersion, Tag, AuditLog, SharedDocument
from django.contrib.auth import get_user_model

User = get_user_model()

class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['id', 'name']
        
class DocumentVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentVersion
        fields = [
            'id', 'document', 'file', 'version_number', 'uploaded_by',
            'created_at', 'file_size', 'content_type', 'file_hash']
        
class DocumentSerializer(serializers.ModelSerializer):
    versions = DocumentVersionSerializer(many=True, read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    owner = serializers.StringRelatedField(read_only=True)
    
    class Meta:
        model = Document
        fields = [
            'id', 'title', 'description', 'owner', 'created_at', 
            'updated_at', 'tags', 'versions']
        
class SimpleDocumentCreateSerializer(serializers.ModelSerializer):
    """serializer for creating document entry and requesting presigned URL"""
    title = serializers.CharField(max_length=512)
    description = serializers.CharField(allow_blank=True, required=False)

class PresignedUploadResponseSerializer(serializers.Serializer):
    url = serializers.CharField()
    fields = serializers.DictField(child=serializers.CharField(), required=False) # for POST form uploads      

class AuditLogSerializer(serializers.ModelSerializer):
    model = AuditLog
    fields = '__all__'

class SharedDocumentSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField()
    model = SharedDocument
    fields = ['id', 'document', 'user', 'permission', 'created_at']