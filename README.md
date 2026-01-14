### Doc Vault

#### Features:

- [ ] File versioning and diffing
- [ ] OCR integration for scanned PDFs
- [ ] Presigned S3 uploads
- [ ] User permissions and audit logs
- [ ] Full-text search (ElasticSearch)
- [ ] Indexing & virus scanning (Celery)

#### ERD

![Entity Relationship Diagram](assets/DMS_Models_Relationship.png)

##### run celery worker

```bash
celery -A dms_project worker -l info
```

##### monitor tasks (celery)

```bash
celery -A doc_vault flower
# Open browser to http://localhost:5555
```

##### Clean files

```bash
make clean
```
