from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.hashids import HashIdJSONResponse
from app.modules.auth.router import router as auth_router
from app.modules.files.router import router as files_router
from app.modules.jobs.router import router as jobs_router
from app.modules.test.router import router as test_router


DOCS_URL = "/docs"
API_PREFIX = "/api"

app = FastAPI(
    default_response_class=HashIdJSONResponse,
    docs_url=None,
    redoc_url=None,
    openapi_url=f"{API_PREFIX}/openapi.json",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOW_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/public", StaticFiles(directory="public"), name="public")


@app.get(DOCS_URL, include_in_schema=False)
def custom_swagger_ui_html() -> HTMLResponse:
    swagger_ui = get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=settings.APP_ENV,
        swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
        swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css",
    )
    html = swagger_ui.body.decode("utf-8")
    html = html.replace(
        "const ui = SwaggerUIBundle(",
        "const ui = window.ui = SwaggerUIBundle(",
    )
    html = html.replace(
        "</head>",
        '<style>.swagger-ui .topbar { display: none }</style></head>',
    )
    html = html.replace(
        "</body>",
        '<script src="/public/swagger-init.js"></script></body>',
    )
    return HTMLResponse(html)

app.include_router(auth_router, prefix=API_PREFIX)
app.include_router(files_router, prefix=API_PREFIX)
app.include_router(jobs_router, prefix=API_PREFIX)
app.include_router(test_router, prefix=API_PREFIX)
