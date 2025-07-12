import logging
import os
from fastapi.responses import HTMLResponse
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from .gemini_routes import router as gemini_router
from .openai_routes import router as openai_router
from .auth import get_credentials, get_user_project_id, onboard_user

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
    logging.info("Environment variables loaded from .env file")
except ImportError:
    logging.warning("python-dotenv not installed, .env file will not be loaded automatically")
except Exception as e:
    logging.warning(f"Could not load .env file: {e}")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

app = FastAPI()

# Add CORS middleware for preflight requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

@app.on_event("startup")
async def startup_event():
    try:
        logging.info("Starting Gemini proxy server...")
        
        # Check if credentials exist
        import os
        from .config import CREDENTIAL_FILE
        
        env_creds_json = os.getenv("GEMINI_CREDENTIALS")
        creds_file_exists = os.path.exists(CREDENTIAL_FILE)
        
        if env_creds_json or creds_file_exists:
            try:
                # Try to load existing credentials without OAuth flow first
                creds = get_credentials(allow_oauth_flow=False)
                if creds:
                    try:
                        proj_id = get_user_project_id(creds)
                        if proj_id:
                            onboard_user(creds, proj_id)
                            logging.info(f"Successfully onboarded with project ID: {proj_id}")
                        logging.info("Gemini proxy server started successfully")
                        logging.info("Authentication required - Password: see .env file")
                    except Exception as e:
                        logging.error(f"Setup failed: {str(e)}")
                        logging.warning("Server started but may not function properly until setup issues are resolved.")
                else:
                    logging.warning("Credentials file exists but could not be loaded. Server started - authentication will be required on first request.")
            except Exception as e:
                logging.error(f"Credential loading error: {str(e)}")
                logging.warning("Server started but credentials need to be set up.")
        else:
            # No credentials found - prompt user to authenticate
            logging.info("No credentials found. Starting OAuth authentication flow...")
            try:
                creds = get_credentials(allow_oauth_flow=True)
                if creds:
                    try:
                        proj_id = get_user_project_id(creds)
                        if proj_id:
                            onboard_user(creds, proj_id)
                            logging.info(f"Successfully onboarded with project ID: {proj_id}")
                        logging.info("Gemini proxy server started successfully")
                    except Exception as e:
                        logging.error(f"Setup failed: {str(e)}")
                        logging.warning("Server started but may not function properly until setup issues are resolved.")
                else:
                    logging.error("Authentication failed. Server started but will not function until credentials are provided.")
            except Exception as e:
                logging.error(f"Authentication error: {str(e)}")
                logging.warning("Server started but authentication failed.")
        
        logging.info("Authentication required - Password: see .env file")
        
    except Exception as e:
        logging.error(f"Startup error: {str(e)}")
        logging.warning("Server may not function properly.")

@app.options("/{full_path:path}")
async def handle_preflight(request: Request, full_path: str):
    """Handle CORS preflight requests without authentication."""
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, PATCH, OPTIONS",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Allow-Credentials": "true",
        }
    )

# Root endpoint - no authentication required
@app.get("/", response_class=HTMLResponse)
async def root():
    return """
    <html>
        <head>
            <title>Meihua Now</title>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body {
                    background: linear-gradient(120deg, #a1c4fd 0%, #c2e9fb 100%);
                    font-family: 'Segoe UI', Arial, sans-serif;
                    margin: 0;
                    padding: 0;
                }
                .container {
                    max-width: 480px;
                    margin: 80px auto;
                    background: rgba(255,255,255,0.95);
                    border-radius: 16px;
                    box-shadow: 0 4px 24px rgba(0,0,0,0.08);
                    padding: 40px 32px;
                    text-align: center;
                }
                h1 {
                    color: #4a90e2;
                    margin-bottom: 16px;
                }
                p {
                    color: #333;
                    font-size: 1.15em;
                    margin-bottom: 24px;
                }
                .footer {
                    margin-top: 32px;
                    color: #aaa;
                    font-size: 0.95em;
                }
                .avatar {
                    width: 80px;
                    height: 80px;
                    border-radius: 50%;
                    margin-bottom: 16px;
                    box-shadow: 0 2px 8px #ccc;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <img src="https://huggingface.co/front/assets/huggingface_logo-noborder.svg" class="avatar" alt="avatar"/>
                <h1>Meihua Now</h1>
                <p>欢迎来到 Meihua Now 主页！<br>这是一个个人项目展示页面。</p>
                <p>如需联系或了解更多，请访问 <a href="https://github.com/user/geminicli2api" target="_blank">GitHub 项目</a>。</p>
                <div class="footer">© 2024 Meihua Now</div>
            </div>
        </body>
    </html>
    """

# Health check endpoint for Docker/Hugging Face
@app.get("/health")
async def health_check():
    """Health check endpoint for container orchestration."""
    return {"status": "healthy", "service": "geminicli2api"}

app.include_router(openai_router)
app.include_router(gemini_router)
