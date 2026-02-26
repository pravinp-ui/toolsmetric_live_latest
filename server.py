from fastapi import FastAPI, APIRouter, HTTPException, Depends, UploadFile, File, Request, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
import uuid
from datetime import datetime, timezone, timedelta
import jwt
from passlib.context import CryptContext
import base64


# Load environment variables BEFORE importing email_service
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Import email service (must be after load_dotenv to read SMTP credentials)
from email_service import (
    send_welcome_email,
    send_login_notification,
    send_submission_received,
    send_tool_approved,
    send_tool_rejected,
    send_review_posted,
    send_admin_new_submission
)

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Security
SECRET_KEY = os.environ.get('JWT_SECRET', 'toolsmetric-secret-key-2025')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

# Default admin credentials (will be created on first run)
DEFAULT_ADMIN_EMAIL = "admin@toolsmetric.com"
DEFAULT_ADMIN_PASSWORD = "admin123"


# Define Models
class StatusCheck(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class StatusCheckCreate(BaseModel):
    client_name: str

# Auth Models
class AdminLogin(BaseModel):
    email: str
    password: str

class AdminUser(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: str
    password_hash: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

# Tool Models
class ToolCreate(BaseModel):
    name: str
    slug: str
    logo: str
    website: str = ""
    description: str
    category: str
    categorySlug: str
    pricing: str
    priceType: str = "freemium"
    rating: float = 4.5
    reviews: int = 0
    features: List[str] = []
    trending: bool = False
    verified: bool = True

class ToolUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    logo: Optional[str] = None
    website: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    categorySlug: Optional[str] = None
    pricing: Optional[str] = None
    priceType: Optional[str] = None
    rating: Optional[float] = None
    reviews: Optional[int] = None
    features: Optional[List[str]] = None
    trending: Optional[bool] = None
    verified: Optional[bool] = None

class Tool(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    slug: str
    logo: str
    website: str = ""
    description: str
    category: str
    categorySlug: str
    pricing: str
    priceType: str = "freemium"
    rating: float = 4.5
    reviews: int = 0
    features: List[str] = []
    trending: bool = False
    verified: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Blog Models
class BlogCreate(BaseModel):
    title: str
    slug: str
    excerpt: str
    content: str
    image: str
    category: str
    author: str
    authorAvatar: str
    readTime: str

class BlogUpdate(BaseModel):
    title: Optional[str] = None
    slug: Optional[str] = None
    excerpt: Optional[str] = None
    content: Optional[str] = None
    image: Optional[str] = None
    category: Optional[str] = None
    author: Optional[str] = None
    authorAvatar: Optional[str] = None
    readTime: Optional[str] = None

class Blog(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    slug: str
    excerpt: str
    content: str
    image: str
    category: str
    author: str
    authorAvatar: str
    readTime: str
    date: str = Field(default_factory=lambda: datetime.now(timezone.utc).strftime("%b %d, %Y"))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# Tool Submission Models
class ToolSubmission(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    slug: str
    logo: str
    description: str
    category: str
    categorySlug: str
    pricing: str
    priceType: str = "freemium"
    features: List[str] = []
    website_url: str = ""
    submitter_name: str
    submitter_email: str
    status: str = "pending"  # pending, approved, rejected
    admin_notes: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ToolSubmissionCreate(BaseModel):
    name: str
    slug: str
    logo: str
    description: str
    category: str
    categorySlug: str
    pricing: str
    priceType: str = "freemium"
    features: List[str] = []
    website_url: str = ""
    submitter_name: str
    submitter_email: str

class ToolSubmissionReview(BaseModel):
    status: str  # approved or rejected
    admin_notes: str = ""


# User Models (for reviews)
class UserCreate(BaseModel):
    name: str
    email: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    email: str
    password_hash: str
    avatar: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    avatar: str

# Review Models
class ReviewCreate(BaseModel):
    tool_id: str
    tool_slug: str
    rating: int = Field(ge=1, le=5)
    content: str

class ReviewUpdate(BaseModel):
    rating: Optional[int] = Field(default=None, ge=1, le=5)
    content: Optional[str] = None

class Review(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tool_id: str
    tool_slug: str
    user_id: str
    user_name: str
    user_avatar: str = ""
    rating: int
    content: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# Helper Functions
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_admin(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        admin = await db.admins.find_one({"email": email})
        if admin is None:
            raise HTTPException(status_code=401, detail="Admin not found")
        return admin
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        user_type = payload.get("type", "user")
        
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        user = await db.users.find_one({"email": email})
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

async def get_optional_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))):
    if credentials is None:
        return None
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if email is None:
            return None
        user = await db.users.find_one({"email": email})
        return user
    except:
        return None


# Initialize default admin on startup
@app.on_event("startup")
async def create_default_admin():
    existing_admin = await db.admins.find_one({"email": DEFAULT_ADMIN_EMAIL})
    if not existing_admin:
        admin = AdminUser(
            email=DEFAULT_ADMIN_EMAIL,
            password_hash=get_password_hash(DEFAULT_ADMIN_PASSWORD)
        )
        doc = admin.model_dump()
        doc['created_at'] = doc['created_at'].isoformat()
        await db.admins.insert_one(doc)
        logger.info(f"Default admin created: {DEFAULT_ADMIN_EMAIL}")


# Base routes
@api_router.get("/")
async def root():
    return {"message": "Hello World"}

@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    status_dict = input.model_dump()
    status_obj = StatusCheck(**status_dict)
    doc = status_obj.model_dump()
    doc['timestamp'] = doc['timestamp'].isoformat()
    _ = await db.status_checks.insert_one(doc)
    return status_obj

@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    status_checks = await db.status_checks.find({}, {"_id": 0}).to_list(1000)
    for check in status_checks:
        if isinstance(check['timestamp'], str):
            check['timestamp'] = datetime.fromisoformat(check['timestamp'])
    return status_checks


# Auth Routes
@api_router.post("/admin/login", response_model=Token)
async def admin_login(login_data: AdminLogin):
    admin = await db.admins.find_one({"email": login_data.email})
    if not admin:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if not verify_password(login_data.password, admin["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token = create_access_token(data={"sub": admin["email"]})
    return Token(access_token=access_token)

@api_router.get("/admin/me")
async def get_admin_me(current_admin: dict = Depends(get_current_admin)):
    return {"email": current_admin["email"], "id": current_admin["id"]}


# Tool Routes
@api_router.get("/tools", response_model=List[Tool])
async def get_tools():
    tools = await db.tools.find({}, {"_id": 0}).to_list(1000)
    for tool in tools:
        if isinstance(tool.get('created_at'), str):
            tool['created_at'] = datetime.fromisoformat(tool['created_at'])
    return tools

@api_router.get("/tools/{slug}")
async def get_tool(slug: str):
    tool = await db.tools.find_one({"slug": slug}, {"_id": 0})
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")
    if isinstance(tool.get('created_at'), str):
        tool['created_at'] = datetime.fromisoformat(tool['created_at'])
    return tool

@api_router.post("/admin/tools", response_model=Tool)
async def create_tool(tool_data: ToolCreate, current_admin: dict = Depends(get_current_admin)):
    # Check if slug already exists
    existing = await db.tools.find_one({"slug": tool_data.slug})
    if existing:
        raise HTTPException(status_code=400, detail="Tool with this slug already exists")
    
    tool = Tool(**tool_data.model_dump())
    doc = tool.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.tools.insert_one(doc)
    return tool

@api_router.put("/admin/tools/{tool_id}", response_model=Tool)
async def update_tool(tool_id: str, tool_data: ToolUpdate, current_admin: dict = Depends(get_current_admin)):
    existing = await db.tools.find_one({"id": tool_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Tool not found")
    
    update_data = {k: v for k, v in tool_data.model_dump().items() if v is not None}
    if update_data:
        await db.tools.update_one({"id": tool_id}, {"$set": update_data})
    
    updated = await db.tools.find_one({"id": tool_id}, {"_id": 0})
    if isinstance(updated.get('created_at'), str):
        updated['created_at'] = datetime.fromisoformat(updated['created_at'])
    return updated

@api_router.delete("/admin/tools/{tool_id}")
async def delete_tool(tool_id: str, current_admin: dict = Depends(get_current_admin)):
    result = await db.tools.delete_one({"id": tool_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Tool not found")
    return {"message": "Tool deleted successfully"}


# Blog Routes
@api_router.get("/blogs", response_model=List[Blog])
async def get_blogs():
    blogs = await db.blogs.find({}, {"_id": 0}).to_list(1000)
    for blog in blogs:
        if isinstance(blog.get('created_at'), str):
            blog['created_at'] = datetime.fromisoformat(blog['created_at'])
    return sorted(blogs, key=lambda x: x.get('created_at', datetime.min), reverse=True)

@api_router.get("/blogs/{slug}")
async def get_blog(slug: str):
    blog = await db.blogs.find_one({"slug": slug}, {"_id": 0})
    if not blog:
        raise HTTPException(status_code=404, detail="Blog not found")
    if isinstance(blog.get('created_at'), str):
        blog['created_at'] = datetime.fromisoformat(blog['created_at'])
    return blog

@api_router.post("/admin/blogs", response_model=Blog)
async def create_blog(blog_data: BlogCreate, current_admin: dict = Depends(get_current_admin)):
    # Check if slug already exists
    existing = await db.blogs.find_one({"slug": blog_data.slug})
    if existing:
        raise HTTPException(status_code=400, detail="Blog with this slug already exists")
    
    blog = Blog(**blog_data.model_dump())
    doc = blog.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.blogs.insert_one(doc)
    return blog

@api_router.put("/admin/blogs/{blog_id}", response_model=Blog)
async def update_blog(blog_id: str, blog_data: BlogUpdate, current_admin: dict = Depends(get_current_admin)):
    existing = await db.blogs.find_one({"id": blog_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Blog not found")
    
    update_data = {k: v for k, v in blog_data.model_dump().items() if v is not None}
    if update_data:
        await db.blogs.update_one({"id": blog_id}, {"$set": update_data})
    
    updated = await db.blogs.find_one({"id": blog_id}, {"_id": 0})
    if isinstance(updated.get('created_at'), str):
        updated['created_at'] = datetime.fromisoformat(updated['created_at'])
    return updated

@api_router.delete("/admin/blogs/{blog_id}")
async def delete_blog(blog_id: str, current_admin: dict = Depends(get_current_admin)):
    result = await db.blogs.delete_one({"id": blog_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Blog not found")
    return {"message": "Blog deleted successfully"}


# Tool Submission Routes (Public)
@api_router.post("/submissions", response_model=ToolSubmission)
async def submit_tool(submission_data: ToolSubmissionCreate, background_tasks: BackgroundTasks):
    # Check if slug already exists in tools or submissions
    existing_tool = await db.tools.find_one({"slug": submission_data.slug})
    existing_submission = await db.tool_submissions.find_one({"slug": submission_data.slug, "status": "pending"})
    
    if existing_tool:
        raise HTTPException(status_code=400, detail="A tool with this slug already exists")
    if existing_submission:
        raise HTTPException(status_code=400, detail="A submission with this slug is already pending review")
    
    submission = ToolSubmission(**submission_data.model_dump())
    doc = submission.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.tool_submissions.insert_one(doc)
    
    # Send confirmation email to submitter
    background_tasks.add_task(
        send_submission_received,
        submission_data.submitter_email,
        submission_data.submitter_name,
        submission_data.name,
        submission.id
    )
    
    # Notify admin of new submission
    background_tasks.add_task(
        send_admin_new_submission,
        submission_data.name,
        submission_data.submitter_name,
        submission_data.submitter_email,
        submission.id
    )
    
    return submission

@api_router.get("/submissions/{submission_id}")
async def get_submission_status(submission_id: str):
    submission = await db.tool_submissions.find_one({"id": submission_id}, {"_id": 0})
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    return {"id": submission["id"], "name": submission["name"], "status": submission["status"]}


# Tool Submission Admin Routes
@api_router.get("/admin/submissions", response_model=List[ToolSubmission])
async def get_all_submissions(current_admin: dict = Depends(get_current_admin)):
    submissions = await db.tool_submissions.find({}, {"_id": 0}).to_list(1000)
    for sub in submissions:
        if isinstance(sub.get('created_at'), str):
            sub['created_at'] = datetime.fromisoformat(sub['created_at'])
    return sorted(submissions, key=lambda x: x.get('created_at', datetime.min), reverse=True)

@api_router.get("/admin/submissions/pending", response_model=List[ToolSubmission])
async def get_pending_submissions(current_admin: dict = Depends(get_current_admin)):
    submissions = await db.tool_submissions.find({"status": "pending"}, {"_id": 0}).to_list(1000)
    for sub in submissions:
        if isinstance(sub.get('created_at'), str):
            sub['created_at'] = datetime.fromisoformat(sub['created_at'])
    return sorted(submissions, key=lambda x: x.get('created_at', datetime.min), reverse=True)

@api_router.put("/admin/submissions/{submission_id}/review")
async def review_submission(submission_id: str, review: ToolSubmissionReview, background_tasks: BackgroundTasks, current_admin: dict = Depends(get_current_admin)):
    submission = await db.tool_submissions.find_one({"id": submission_id})
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    if review.status not in ["approved", "rejected"]:
        raise HTTPException(status_code=400, detail="Status must be 'approved' or 'rejected'")
    
    # Update submission status
    await db.tool_submissions.update_one(
        {"id": submission_id},
        {"$set": {"status": review.status, "admin_notes": review.admin_notes}}
    )
    
    # If approved, create the tool and notify submitter
    if review.status == "approved":
        tool_data = {
            "id": str(uuid.uuid4()),
            "name": submission["name"],
            "slug": submission["slug"],
            "logo": submission["logo"],
            "website": submission.get("website", submission.get("website_url", "")),
            "description": submission["description"],
            "category": submission["category"],
            "categorySlug": submission["categorySlug"],
            "pricing": submission["pricing"],
            "priceType": submission.get("priceType", "freemium"),
            "rating": 4.5,
            "reviews": 0,
            "features": submission.get("features", []),
            "trending": False,
            "verified": True,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.tools.insert_one(tool_data)
        
        # Send approval email to submitter
        background_tasks.add_task(
            send_tool_approved,
            submission["submitter_email"],
            submission["submitter_name"],
            submission["name"],
            submission["slug"]
        )
        
        return {"message": "Submission approved and tool created", "tool_id": tool_data["id"]}
    
    # If rejected, notify submitter
    background_tasks.add_task(
        send_tool_rejected,
        submission["submitter_email"],
        submission["submitter_name"],
        submission["name"],
        review.admin_notes
    )
    
    return {"message": "Submission rejected"}

@api_router.delete("/admin/submissions/{submission_id}")
async def delete_submission(submission_id: str, current_admin: dict = Depends(get_current_admin)):
    result = await db.tool_submissions.delete_one({"id": submission_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Submission not found")
    return {"message": "Submission deleted successfully"}


# User Auth Routes
@api_router.post("/auth/register", response_model=Token)
async def register_user(user_data: UserCreate, background_tasks: BackgroundTasks):
    # Check if email already exists
    existing = await db.users.find_one({"email": user_data.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user = User(
        name=user_data.name,
        email=user_data.email,
        password_hash=get_password_hash(user_data.password),
        avatar=f"https://ui-avatars.com/api/?name={user_data.name.replace(' ', '+')}&background=10b981&color=fff"
    )
    doc = user.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.users.insert_one(doc)
    
    # Send welcome email in background
    background_tasks.add_task(send_welcome_email, user_data.email, user_data.name)
    
    access_token = create_access_token(data={"sub": user.email, "type": "user"})
    return Token(access_token=access_token)

@api_router.post("/auth/login", response_model=Token)
async def login_user(login_data: UserLogin, background_tasks: BackgroundTasks, request: Request):
    user = await db.users.find_one({"email": login_data.email})
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if not verify_password(login_data.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Send login notification in background
    login_time = datetime.now(timezone.utc).strftime("%B %d, %Y at %I:%M %p UTC")
    client_ip = request.client.host if request.client else "Unknown"
    background_tasks.add_task(send_login_notification, user["email"], user["name"], login_time, client_ip)
    
    access_token = create_access_token(data={"sub": user["email"], "type": "user"})
    return Token(access_token=access_token)

@api_router.get("/auth/me", response_model=UserResponse)
async def get_user_me(current_user: dict = Depends(get_current_user)):
    return UserResponse(
        id=current_user["id"],
        name=current_user["name"],
        email=current_user["email"],
        avatar=current_user.get("avatar", "")
    )


# Review Routes (Public - Get reviews)
@api_router.get("/reviews/{tool_slug}", response_model=List[Review])
async def get_tool_reviews(tool_slug: str):
    reviews = await db.reviews.find({"tool_slug": tool_slug}, {"_id": 0}).to_list(1000)
    for review in reviews:
        if isinstance(review.get('created_at'), str):
            review['created_at'] = datetime.fromisoformat(review['created_at'])
    return sorted(reviews, key=lambda x: x.get('created_at', datetime.min), reverse=True)

# Review Routes (User - Create review)
@api_router.post("/reviews", response_model=Review)
async def create_review(review_data: ReviewCreate, current_user: dict = Depends(get_current_user)):
    # Check if user already reviewed this tool
    existing = await db.reviews.find_one({
        "tool_slug": review_data.tool_slug,
        "user_id": current_user["id"]
    })
    if existing:
        raise HTTPException(status_code=400, detail="You have already reviewed this tool")
    
    review = Review(
        tool_id=review_data.tool_id,
        tool_slug=review_data.tool_slug,
        user_id=current_user["id"],
        user_name=current_user["name"],
        user_avatar=current_user.get("avatar", ""),
        rating=review_data.rating,
        content=review_data.content
    )
    doc = review.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.reviews.insert_one(doc)
    
    # Update tool's review count and rating
    all_reviews = await db.reviews.find({"tool_slug": review_data.tool_slug}, {"_id": 0}).to_list(1000)
    total_ratings = sum(r["rating"] for r in all_reviews)
    avg_rating = round(total_ratings / len(all_reviews), 1) if all_reviews else 4.5
    
    await db.tools.update_one(
        {"slug": review_data.tool_slug},
        {"$set": {"reviews": len(all_reviews), "rating": avg_rating}}
    )
    
    return review

# Review Routes (User - Update own review)
@api_router.put("/reviews/{review_id}", response_model=Review)
async def update_review(review_id: str, review_data: ReviewUpdate, current_user: dict = Depends(get_current_user)):
    existing = await db.reviews.find_one({"id": review_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Review not found")
    
    if existing["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="You can only update your own reviews")
    
    update_data = {k: v for k, v in review_data.model_dump().items() if v is not None}
    if update_data:
        await db.reviews.update_one({"id": review_id}, {"$set": update_data})
    
    updated = await db.reviews.find_one({"id": review_id}, {"_id": 0})
    if isinstance(updated.get('created_at'), str):
        updated['created_at'] = datetime.fromisoformat(updated['created_at'])
    
    # Recalculate tool's rating
    all_reviews = await db.reviews.find({"tool_slug": updated["tool_slug"]}, {"_id": 0}).to_list(1000)
    total_ratings = sum(r["rating"] for r in all_reviews)
    avg_rating = round(total_ratings / len(all_reviews), 1) if all_reviews else 4.5
    await db.tools.update_one(
        {"slug": updated["tool_slug"]},
        {"$set": {"rating": avg_rating}}
    )
    
    return updated

# Review Routes (User - Delete own review)
@api_router.delete("/reviews/{review_id}")
async def delete_own_review(review_id: str, current_user: dict = Depends(get_current_user)):
    existing = await db.reviews.find_one({"id": review_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Review not found")
    
    if existing["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="You can only delete your own reviews")
    
    tool_slug = existing["tool_slug"]
    await db.reviews.delete_one({"id": review_id})
    
    # Recalculate tool's review count and rating
    all_reviews = await db.reviews.find({"tool_slug": tool_slug}, {"_id": 0}).to_list(1000)
    if all_reviews:
        total_ratings = sum(r["rating"] for r in all_reviews)
        avg_rating = round(total_ratings / len(all_reviews), 1)
    else:
        avg_rating = 4.5
    
    await db.tools.update_one(
        {"slug": tool_slug},
        {"$set": {"reviews": len(all_reviews), "rating": avg_rating}}
    )
    
    return {"message": "Review deleted successfully"}


# Admin Review Routes
@api_router.get("/admin/reviews", response_model=List[Review])
async def get_all_reviews(current_admin: dict = Depends(get_current_admin)):
    reviews = await db.reviews.find({}, {"_id": 0}).to_list(1000)
    for review in reviews:
        if isinstance(review.get('created_at'), str):
            review['created_at'] = datetime.fromisoformat(review['created_at'])
    return sorted(reviews, key=lambda x: x.get('created_at', datetime.min), reverse=True)

@api_router.put("/admin/reviews/{review_id}", response_model=Review)
async def admin_update_review(review_id: str, review_data: ReviewUpdate, current_admin: dict = Depends(get_current_admin)):
    existing = await db.reviews.find_one({"id": review_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Review not found")
    
    update_data = {k: v for k, v in review_data.model_dump().items() if v is not None}
    if update_data:
        await db.reviews.update_one({"id": review_id}, {"$set": update_data})
    
    updated = await db.reviews.find_one({"id": review_id}, {"_id": 0})
    if isinstance(updated.get('created_at'), str):
        updated['created_at'] = datetime.fromisoformat(updated['created_at'])
    
    # Recalculate tool's rating
    all_reviews = await db.reviews.find({"tool_slug": updated["tool_slug"]}, {"_id": 0}).to_list(1000)
    total_ratings = sum(r["rating"] for r in all_reviews)
    avg_rating = round(total_ratings / len(all_reviews), 1) if all_reviews else 4.5
    await db.tools.update_one(
        {"slug": updated["tool_slug"]},
        {"$set": {"rating": avg_rating}}
    )
    
    return updated

@api_router.delete("/admin/reviews/{review_id}")
async def admin_delete_review(review_id: str, current_admin: dict = Depends(get_current_admin)):
    existing = await db.reviews.find_one({"id": review_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Review not found")
    
    tool_slug = existing["tool_slug"]
    await db.reviews.delete_one({"id": review_id})
    
    # Recalculate tool's review count and rating
    all_reviews = await db.reviews.find({"tool_slug": tool_slug}, {"_id": 0}).to_list(1000)
    if all_reviews:
        total_ratings = sum(r["rating"] for r in all_reviews)
        avg_rating = round(total_ratings / len(all_reviews), 1)
    else:
        avg_rating = 4.5
    
    await db.tools.update_one(
        {"slug": tool_slug},
        {"$set": {"reviews": len(all_reviews), "rating": avg_rating}}
    )
    
    return {"message": "Review deleted successfully"}


# Image upload (base64)
@api_router.post("/admin/upload")
async def upload_image(current_admin: dict = Depends(get_current_admin), file: UploadFile = File(...)):
    contents = await file.read()
    base64_image = base64.b64encode(contents).decode('utf-8')
    content_type = file.content_type or 'image/jpeg'
    data_url = f"data:{content_type};base64,{base64_image}"
    return {"url": data_url, "filename": file.filename}

@app.get("/")
async def main_root():
    return {"message": "ToolsMetric API is running"}
# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
