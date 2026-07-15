"""
pytest 配置 + 共享 fixtures
"""

import pytest_asyncio
import pytest
import sys, os, tempfile

sys.path.insert(0, os.path.dirname(__file__))

from httpx import AsyncClient, ASGITransport
from main import app


@pytest_asyncio.fixture
async def client():
    """FastAPI TestClient fixture。"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def tmp_db():
    """临时数据库路径。"""
    f = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    path = f.name
    f.close()
    yield path
    try:
        os.unlink(path)
    except OSError:
        pass
