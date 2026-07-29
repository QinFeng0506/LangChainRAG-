"""知识库管理测试 —— 上传、列表、状态、删除、统计、权限。"""
import os
import pytest


class TestKnowledgeStats:
    """知识库统计测试。"""

    async def test_stats_empty(self, client, auth_headers):
        """空知识库应返回全零统计。"""
        resp = await client.get("/api/knowledge/stats", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_documents"] == 0
        assert data["total_chunks"] == 0
        assert data["total_size_bytes"] == 0
        assert data["documents_by_type"] == {}
        assert data["documents_by_status"] == {}

    async def test_stats_unauthorized(self, client, user_headers):
        """普通用户查看统计应被拒绝 403。"""
        resp = await client.get("/api/knowledge/stats", headers=user_headers)
        assert resp.status_code == 403

    async def test_stats_no_auth(self, client):
        """未登录查看统计应返回 401。"""
        resp = await client.get("/api/knowledge/stats")
        assert resp.status_code == 401


class TestDocumentUpload:
    """文档上传测试。"""

    async def test_upload_txt_file(self, client, auth_headers):
        """上传 TXT 文件应成功并返回文档记录。"""
        from io import BytesIO
        files = {"file": ("test.txt", BytesIO(b"test document content."), "text/plain")}
        resp = await client.post("/api/knowledge/upload", files=files, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["filename"] == "test.txt"
        assert data["file_type"] == "txt"
        assert data["status"] == "pending"  # 后台处理中

    async def test_upload_no_auth(self, client):
        """未登录上传应返回 401。"""
        from io import BytesIO
        files = {"file": ("test.txt", BytesIO(b"test"), "text/plain")}
        resp = await client.post("/api/knowledge/upload", files=files)
        assert resp.status_code == 401

    async def test_upload_not_admin(self, client, user_headers):
        """普通用户上传应返回 403。"""
        from io import BytesIO
        files = {"file": ("test.txt", BytesIO(b"test"), "text/plain")}
        resp = await client.post("/api/knowledge/upload", files=files, headers=user_headers)
        assert resp.status_code == 403

    async def test_upload_unsupported_type(self, client, auth_headers):
        """不支持的文件类型应返回 400。"""
        from io import BytesIO
        files = {"file": ("test.exe", BytesIO(b"binary"), "application/octet-stream")}
        resp = await client.post("/api/knowledge/upload", files=files, headers=auth_headers)
        assert resp.status_code == 400


class TestDocumentManagement:
    """文档管理测试 —— 列表、状态查询、删除。"""

    async def _upload_doc(self, client, auth_headers, filename="doc.txt", content=b"test content"):
        """辅助方法：上传文档并返回文档 ID。"""
        from io import BytesIO
        files = {"file": (filename, BytesIO(content), "text/plain")}
        resp = await client.post("/api/knowledge/upload", files=files, headers=auth_headers)
        return resp.json()["id"]

    async def test_list_documents(self, client, auth_headers):
        """上传多个文档后列表应正确返回所有文档。"""
        filenames = []
        for i in range(3):
            name = f"doc{i}.txt"
            filenames.append(name)
            await self._upload_doc(client, auth_headers, name)

        resp = await client.get("/api/knowledge/documents", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 3
        assert len(data["items"]) == 3
        assert data["page"] == 1
        # 所有上传的文档都应出现在列表中
        returned_names = {item["filename"] for item in data["items"]}
        assert returned_names == set(filenames)

    async def test_list_documents_pagination(self, client, auth_headers):
        """分页参数应正确生效。"""
        for i in range(30):
            await self._upload_doc(client, auth_headers, f"doc{i}.txt")

        resp = await client.get("/api/knowledge/documents?page=1&page_size=10", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 10
        assert data["total"] == 30

        # 第3页应只有10条
        resp2 = await client.get("/api/knowledge/documents?page=3&page_size=10", headers=auth_headers)
        assert resp2.json()["total"] == 30

    async def test_get_document_status(self, client, auth_headers):
        """查询文档状态应返回正确状态信息。"""
        doc_id = await self._upload_doc(client, auth_headers)

        resp = await client.get(f"/api/knowledge/documents/{doc_id}/status", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == doc_id
        assert data["filename"] == "doc.txt"
        assert data["status"] in ("pending", "parsing", "completed", "failed")

    async def test_get_document_status_not_found(self, client, auth_headers):
        """查询不存在的文档应返回 404。"""
        resp = await client.get("/api/knowledge/documents/nonexistent-id/status", headers=auth_headers)
        assert resp.status_code == 404

    async def test_delete_document(self, client, auth_headers):
        """删除文档应成功并减少文档数。"""
        doc_id = await self._upload_doc(client, auth_headers)

        # 确认存在
        list_resp = await client.get("/api/knowledge/documents", headers=auth_headers)
        assert list_resp.json()["total"] == 1

        # 删除
        resp = await client.delete(f"/api/knowledge/documents/{doc_id}", headers=auth_headers)
        assert resp.status_code == 200
        assert "已删除" in resp.json()["message"]

        # 确认已删除
        list_resp2 = await client.get("/api/knowledge/documents", headers=auth_headers)
        assert list_resp2.json()["total"] == 0

    async def test_delete_nonexistent(self, client, auth_headers):
        """删除不存在的文档应返回 404。"""
        resp = await client.delete("/api/knowledge/documents/fake-id", headers=auth_headers)
        assert resp.status_code == 404

    async def test_filter_by_status(self, client, auth_headers):
        """按状态筛选应只返回匹配的文档。"""
        await self._upload_doc(client, auth_headers, "doc1.txt")
        await self._upload_doc(client, auth_headers, "doc2.txt")

        # 按 pending 状态筛选
        resp = await client.get("/api/knowledge/documents?status=pending", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        for item in data["items"]:
            assert item["status"] == "pending"


class TestFileTypeValidation:
    """文件类型校验测试。"""

    async def test_validate_pdf(self, client, auth_headers):
        """PDF 应被允许上传。"""
        from io import BytesIO
        pdf_content = b"%PDF-1.4\n%Fake PDF content for testing\n%%EOF"
        files = {"file": ("doc.pdf", BytesIO(pdf_content), "application/pdf")}
        resp = await client.post("/api/knowledge/upload", files=files, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["file_type"] == "pdf"

    async def test_validate_image(self, client, auth_headers):
        """PNG 图片应被允许上传。"""
        from io import BytesIO
        png_content = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        files = {"file": ("photo.png", BytesIO(png_content), "image/png")}
        resp = await client.post("/api/knowledge/upload", files=files, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["file_type"] == "image"

    async def test_reject_invalid_extension(self, client, auth_headers):
        """无扩展名文件应被拒绝。"""
        from io import BytesIO
        files = {"file": ("noextension", BytesIO(b"data"), "application/octet-stream")}
        resp = await client.post("/api/knowledge/upload", files=files, headers=auth_headers)
        assert resp.status_code == 400
