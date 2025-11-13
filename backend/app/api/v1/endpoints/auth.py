from fastapi import APIRouter, HTTPException, status, Depends
from app.schemas.auth import (
    RegisterRequest, LoginRequest, TokenResponse,
    RefreshTokenRequest, PasswordResetRequest,
    PasswordResetConfirm, EmailVerificationRequest,
    GoogleAuthRequest, PhoneOTPRequest, PhoneLoginRequest
)
from app.core.security import (
    verify_password, get_password_hash,
    create_access_token, create_refresh_token,
    decode_token, create_email_verification_token,
    create_password_reset_token, verify_password_reset_token
)
from app.core.supabase_client import supabase_client, supabase_admin
from app.dependencies import get_current_user
from datetime import timedelta
import httpx
from app.config import settings

router = APIRouter()


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: RegisterRequest):
    """Register a new user with email and password"""
    try:
        # Check if user already exists
        existing = supabase_client.table("users").select("id").eq("email", user_data.email).execute()
        if existing.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Check phone if provided
        if user_data.phone:
            phone_check = supabase_client.table("users").select("id").eq("phone", user_data.phone).execute()
            if phone_check.data:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Phone number already registered"
                )
        
        # Create auth user in Supabase
        auth_response = supabase_admin.auth.admin.create_user({
            "email": user_data.email,
            "password": user_data.password,
            "email_confirm": False
        })
        
        if not auth_response.user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create auth user"
            )
        
        # Create user profile in database
        user_profile = {
            "auth_id": auth_response.user.id,
            "email": user_data.email,
            "full_name": user_data.full_name,
            "phone": user_data.phone,
            "role": user_data.role.value,
            "email_verified": False,
            "phone_verified": False,
            "is_active": True
        }
        
        result = supabase_client.table("users").insert(user_profile).execute()
        user = result.data[0]
        
        # Generate tokens
        access_token = create_access_token({"sub": user["id"], "role": user["role"]})
        refresh_token = create_refresh_token({"sub": user["id"]})
        
        # Send verification email (optional)
        # verification_token = create_email_verification_token(user_data.email)
        # TODO: Send email with verification link
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            user={
                "id": user["id"],
                "email": user["email"],
                "full_name": user["full_name"],
                "role": user["role"]
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )


@router.post("/login", response_model=TokenResponse)
async def login(credentials: LoginRequest):
    """Login with email and password"""
    try:
        # Authenticate with Supabase Auth
        auth_response = supabase_client.auth.sign_in_with_password({
            "email": credentials.email,
            "password": credentials.password
        })
        
        if not auth_response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Get user profile
        user_result = supabase_client.table("users").select("*").eq("auth_id", auth_response.user.id).single().execute()
        user = user_result.data
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User profile not found"
            )
        
        if not user["is_active"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is inactive"
            )
        
        # Generate tokens
        access_token = create_access_token({"sub": user["id"], "role": user["role"]})
        refresh_token = create_refresh_token({"sub": user["id"]})
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            user={
                "id": user["id"],
                "email": user["email"],
                "full_name": user["full_name"],
                "role": user["role"],
                "avatar_url": user.get("avatar_url")
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )


@router.post("/google", response_model=TokenResponse)
async def google_auth(auth_data: GoogleAuthRequest):
    """Authenticate with Google OAuth"""
    try:
        # Verify Google token
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://oauth2.googleapis.com/tokeninfo?id_token={auth_data.token}"
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid Google token"
                )
            
            google_data = response.json()
            email = google_data.get("email")
            name = google_data.get("name")
            
            if not email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email not provided by Google"
                )
        
        # Check if user exists
        user_result = supabase_client.table("users").select("*").eq("email", email).execute()
        
        if user_result.data:
            # Existing user
            user = user_result.data[0]
        else:
            # Create new user
            user_profile = {
                "email": email,
                "full_name": name or email.split("@")[0],
                "role": "student",
                "email_verified": True,
                "is_active": True
            }
            
            result = supabase_client.table("users").insert(user_profile).execute()
            user = result.data[0]
        
        # Generate tokens
        access_token = create_access_token({"sub": user["id"], "role": user["role"]})
        refresh_token = create_refresh_token({"sub": user["id"]})
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            user={
                "id": user["id"],
                "email": user["email"],
                "full_name": user["full_name"],
                "role": user["role"]
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Google authentication failed: {str(e)}"
        )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(token_data: RefreshTokenRequest):
    """Refresh access token"""
    payload = decode_token(token_data.refresh_token)
    
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    user_id = payload.get("sub")
    
    # Get user
    user_result = supabase_client.table("users").select("*").eq("id", user_id).single().execute()
    user = user_result.data
    
    if not user or not user["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    # Generate new tokens
    access_token = create_access_token({"sub": user["id"], "role": user["role"]})
    new_refresh_token = create_refresh_token({"sub": user["id"]})
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        user={
            "id": user["id"],
            "email": user["email"],
            "full_name": user["full_name"],
            "role": user["role"]
        }
    )


@router.post("/password-reset")
async def request_password_reset(request: PasswordResetRequest):
    """Request password reset email"""
    try:
        # Check if user exists
        user_result = supabase_client.table("users").select("id, email, full_name").eq("email", request.email).execute()
        
        # Always return success to prevent email enumeration
        if not user_result.data:
            return {"message": "If the email exists, a password reset link has been sent"}
        
        user = user_result.data[0]
        
        # Generate reset token
        reset_token = create_password_reset_token(request.email)
        
        # TODO: Send email with reset link
        # reset_link = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"
        
        return {"message": "If the email exists, a password reset link has been sent"}
        
    except Exception as e:
        return {"message": "If the email exists, a password reset link has been sent"}


@router.post("/password-reset/confirm")
async def confirm_password_reset(request: PasswordResetConfirm):
    """Confirm password reset with token"""
    email = verify_password_reset_token(request.token)
    
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    
    try:
        # Get user
        user_result = supabase_client.table("users").select("auth_id").eq("email", email).single().execute()
        user = user_result.data
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Update password in Supabase Auth
        supabase_admin.auth.admin.update_user_by_id(
            user["auth_id"],
            {"password": request.new_password}
        )
        
        return {"message": "Password reset successful"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Password reset failed: {str(e)}"
        )


@router.get("/me")
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """Get current authenticated user information"""
    return {
        "id": current_user["id"],
        "email": current_user["email"],
        "full_name": current_user["full_name"],
        "role": current_user["role"],
        "avatar_url": current_user.get("avatar_url"),
        "phone": current_user.get("phone"),
        "bio": current_user.get("bio"),
        "email_verified": current_user["email_verified"],
        "phone_verified": current_user.get("phone_verified", False),
        "created_at": current_user["created_at"]
    }


@router.post("/logout")
async def logout(current_user: dict = Depends(get_current_user)):
    """Logout user (client should delete tokens)"""
    # In a stateless JWT system, logout is handled client-side
    # For additional security, you could implement token blacklisting with Redis
    return {"message": "Logged out successfully"}