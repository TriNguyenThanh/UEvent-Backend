import pytest
from playwright.sync_api import Page, expect
from django.contrib.auth.models import User

@pytest.mark.django_db
def test_django_admin_login(page: Page, live_server):
    # 1. Tạo một superuser ảo trong lúc test
    User.objects.create_superuser('admin_test', 'admin@example.com', 'password123')

    # 2. Truy cập trang đăng nhập admin (live_server tự động start Django chạy ở background)
    page.goto(f"{live_server.url}/admin/login/")

    # 3. Chờ và kiểm tra Title trang đăng nhập
    expect(page).to_have_title("Log in | Django site admin")

    # 4. Điền form đăng nhập
    page.fill('input[name="username"]', 'admin_test')
    page.fill('input[name="password"]', 'password123')
    page.click('input[type="submit"]')

    # 5. Kiểm tra xem đã đăng nhập thành công chưa (vào Dashboard)
    expect(page).to_have_title("Site administration | Django site admin")
    expect(page.locator('text=Welcome, admin_test.')).to_be_visible()

@pytest.mark.django_db
def test_django_admin_login_failure(page: Page, live_server):
    # Cố tình sử dụng tài khoản không tồn tại để đăng nhập
    page.goto(f"{live_server.url}/admin/login/")
    
    # Điền form đăng nhập với thông tin sai
    page.fill('input[name="username"]', 'wrong_user')
    page.fill('input[name="password"]', 'wrong_password')
    page.click('input[type="submit"]')

    # Kiểm tra xem có xuất hiện thông báo lỗi của Django Admin không
    error_message = page.locator('.errornote')
    expect(error_message).to_be_visible()
    expect(error_message).to_contain_text("Please enter the correct username and password")
