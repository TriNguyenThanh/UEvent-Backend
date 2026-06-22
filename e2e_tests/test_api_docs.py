import pytest
from playwright.sync_api import Page, expect

def test_swagger_docs_load(page: Page, live_server):
    """Kiểm tra xem trang tài liệu API Swagger có hoạt động không"""
    # 1. Truy cập trang Swagger UI
    page.goto(f"{live_server.url}/swagger/")
    
    # 2. Chờ trang render xong giao diện Swagger
    expect(page).to_have_title("Swagger UI")
    
    # 3. Kiểm tra xem phần tử chính của giao diện (như tiêu đề API) có hiển thị không
    swagger_title = page.locator('.title')
    expect(swagger_title).to_be_visible()

def test_redoc_docs_load(page: Page, live_server):
    """Kiểm tra xem trang tài liệu API ReDoc có hoạt động không"""
    page.goto(f"{live_server.url}/redoc/")
    
    # Kiểm tra Redoc tag có được render thành công không
    redoc_container = page.locator('redoc')
    expect(redoc_container).to_be_visible()
