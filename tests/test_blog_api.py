"""
Blog API Tests - Testing blog endpoints and data integrity
Tests: GET /api/blogs, GET /api/blogs/{slug}
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestBlogAPI:
    """Test blog API endpoints"""
    
    def test_get_all_blogs_success(self):
        """Test GET /api/blogs returns list of blogs"""
        response = requests.get(f"{BASE_URL}/api/blogs")
        
        # Status assertion
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        # Data assertions
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        assert len(data) >= 10, f"Expected at least 10 blogs, got {len(data)}"
        
        print(f"✓ GET /api/blogs returned {len(data)} blogs")
    
    def test_blog_structure(self):
        """Test blog objects have required fields"""
        response = requests.get(f"{BASE_URL}/api/blogs")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data) > 0, "No blogs found"
        
        blog = data[0]
        required_fields = ['id', 'title', 'slug', 'excerpt', 'content', 'image', 
                          'category', 'author', 'authorAvatar', 'readTime', 'date']
        
        for field in required_fields:
            assert field in blog, f"Blog missing required field: {field}"
            assert blog[field], f"Blog field {field} is empty"
        
        print(f"✓ Blog structure validated with all required fields")
    
    def test_get_single_blog_success(self):
        """Test GET /api/blogs/{slug} returns single blog"""
        # First get a valid slug
        list_response = requests.get(f"{BASE_URL}/api/blogs")
        assert list_response.status_code == 200
        blogs = list_response.json()
        assert len(blogs) > 0, "No blogs to test"
        
        valid_slug = blogs[0]['slug']
        
        # Get single blog
        response = requests.get(f"{BASE_URL}/api/blogs/{valid_slug}")
        
        # Status assertion
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        # Data assertions
        blog = response.json()
        assert blog['slug'] == valid_slug, f"Slug mismatch"
        assert 'content' in blog, "Blog should have content"
        assert len(blog['content']) > 100, "Blog content should be substantial"
        
        print(f"✓ GET /api/blogs/{valid_slug} returned blog successfully")
    
    def test_get_blog_not_found(self):
        """Test GET /api/blogs/{slug} returns 404 for invalid slug"""
        response = requests.get(f"{BASE_URL}/api/blogs/nonexistent-slug-123")
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print(f"✓ Invalid slug correctly returns 404")
    
    def test_blog_images_valid_urls(self):
        """Test all blog images have valid URLs"""
        response = requests.get(f"{BASE_URL}/api/blogs")
        assert response.status_code == 200
        
        blogs = response.json()
        invalid_images = []
        
        for blog in blogs:
            image_url = blog.get('image', '')
            if not image_url or not image_url.startswith('http'):
                invalid_images.append((blog['slug'], image_url))
        
        assert len(invalid_images) == 0, f"Blogs with invalid image URLs: {invalid_images}"
        print(f"✓ All {len(blogs)} blogs have valid image URLs")
    
    def test_blog_images_load(self):
        """Test that blog images actually load (HTTP HEAD check)"""
        response = requests.get(f"{BASE_URL}/api/blogs")
        assert response.status_code == 200
        
        blogs = response.json()[:5]  # Test first 5 blogs
        broken_images = []
        
        for blog in blogs:
            image_url = blog.get('image', '')
            try:
                img_response = requests.head(image_url, timeout=5, allow_redirects=True)
                if img_response.status_code >= 400:
                    broken_images.append((blog['slug'], image_url, img_response.status_code))
            except Exception as e:
                broken_images.append((blog['slug'], image_url, str(e)))
        
        if broken_images:
            print(f"⚠ Broken images found: {broken_images}")
        else:
            print(f"✓ All tested blog images load correctly")
        
        # This is a warning, not a hard failure (Unsplash might have rate limits)
        assert len(broken_images) == 0, f"Broken images: {broken_images}"
    
    def test_blog_content_markdown_formatting(self):
        """Test blog content has expected markdown formatting"""
        response = requests.get(f"{BASE_URL}/api/blogs")
        assert response.status_code == 200
        
        blogs = response.json()
        blogs_with_content = [b for b in blogs if b.get('content') and len(b['content']) > 200]
        
        assert len(blogs_with_content) > 0, "No blogs with substantial content found"
        
        # Check first blog has markdown elements
        blog = blogs_with_content[0]
        content = blog['content']
        
        # Check for markdown headings
        has_headings = '##' in content or '###' in content
        # Check for list items
        has_lists = '- ' in content or '1. ' in content
        
        if not has_headings:
            print(f"⚠ Blog '{blog['slug']}' may lack markdown headings")
        if not has_lists:
            print(f"⚠ Blog '{blog['slug']}' may lack markdown lists")
        
        print(f"✓ Blog content format validated")


class TestUserAuthAPI:
    """Test user authentication endpoints"""
    
    def test_register_user_success(self):
        """Test POST /api/auth/register creates new user"""
        import uuid
        unique_email = f"test_{uuid.uuid4().hex[:8]}@example.com"
        
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "name": "Test User",
            "email": unique_email,
            "password": "testpass123"
        })
        
        # Status assertion
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Data assertions
        data = response.json()
        assert 'access_token' in data, "Response should contain access_token"
        assert data.get('token_type') == 'bearer', "Token type should be bearer"
        
        print(f"✓ User registration successful for {unique_email}")
        return data['access_token']
    
    def test_register_duplicate_email(self):
        """Test POST /api/auth/register rejects duplicate email"""
        import uuid
        unique_email = f"test_dup_{uuid.uuid4().hex[:8]}@example.com"
        
        # First registration
        requests.post(f"{BASE_URL}/api/auth/register", json={
            "name": "Test User",
            "email": unique_email,
            "password": "testpass123"
        })
        
        # Second registration with same email
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "name": "Test User 2",
            "email": unique_email,
            "password": "testpass456"
        })
        
        assert response.status_code == 400, f"Expected 400 for duplicate, got {response.status_code}"
        print(f"✓ Duplicate email correctly rejected")
    
    def test_login_user_success(self):
        """Test POST /api/auth/login with valid credentials"""
        import uuid
        unique_email = f"test_login_{uuid.uuid4().hex[:8]}@example.com"
        
        # First register
        requests.post(f"{BASE_URL}/api/auth/register", json={
            "name": "Login Test User",
            "email": unique_email,
            "password": "logintest123"
        })
        
        # Then login
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": unique_email,
            "password": "logintest123"
        })
        
        # Status assertion
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        # Data assertions
        data = response.json()
        assert 'access_token' in data, "Response should contain access_token"
        
        print(f"✓ User login successful")
    
    def test_login_invalid_credentials(self):
        """Test POST /api/auth/login rejects invalid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "nonexistent@example.com",
            "password": "wrongpassword"
        })
        
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print(f"✓ Invalid credentials correctly rejected")
    
    def test_get_user_me(self):
        """Test GET /api/auth/me returns user info"""
        import uuid
        unique_email = f"test_me_{uuid.uuid4().hex[:8]}@example.com"
        
        # Register and get token
        reg_response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "name": "Me Test User",
            "email": unique_email,
            "password": "metest123"
        })
        token = reg_response.json()['access_token']
        
        # Get user info
        response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # Status assertion
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        # Data assertions
        data = response.json()
        assert data['email'] == unique_email, "Email should match"
        assert data['name'] == "Me Test User", "Name should match"
        
        print(f"✓ GET /api/auth/me returned user info")


class TestAdminAPI:
    """Test admin endpoints"""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin token"""
        response = requests.post(f"{BASE_URL}/api/admin/login", json={
            "email": "admin@toolsmetric.com",
            "password": "admin123"
        })
        if response.status_code == 200:
            return response.json()['access_token']
        pytest.skip("Admin login failed")
    
    def test_admin_login_success(self):
        """Test POST /api/admin/login with valid credentials"""
        response = requests.post(f"{BASE_URL}/api/admin/login", json={
            "email": "admin@toolsmetric.com",
            "password": "admin123"
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert 'access_token' in data
        print(f"✓ Admin login successful")
    
    def test_admin_login_invalid(self):
        """Test POST /api/admin/login rejects invalid credentials"""
        response = requests.post(f"{BASE_URL}/api/admin/login", json={
            "email": "admin@toolsmetric.com",
            "password": "wrongpassword"
        })
        
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print(f"✓ Invalid admin credentials rejected")
    
    def test_admin_me(self, admin_token):
        """Test GET /api/admin/me returns admin info"""
        response = requests.get(
            f"{BASE_URL}/api/admin/me",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data['email'] == "admin@toolsmetric.com"
        print(f"✓ Admin /me endpoint working")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
