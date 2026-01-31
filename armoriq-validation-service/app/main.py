"""
ArmorIQ Validation Service - FastAPI Application
"""
import logging
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import structlog

from app.config import settings
from app.models import ValidationRequest, ValidationResponse, HealthResponse, MetricsResponse, ErrorResponse
from app.validation import ValidationService

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="ISO"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer() if settings.log_format == "json" else structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(
        getattr(logging, settings.log_level.upper(), logging.INFO)
    ),
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Global validation service instance
validation_service: ValidationService = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan management."""
    global validation_service
    
    # Startup
    logger.info("Starting ArmorIQ Validation Service", version=settings.service_version)
    
    try:
        validation_service = ValidationService()
        logger.info("Validation service initialized successfully")
    except Exception as e:
        logger.error("Failed to initialize validation service", error=str(e))
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down ArmorIQ Validation Service")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(
        title="ArmorIQ Validation Service",
        description="Validates LLM output through ArmorIQ workflow with credibility assessment",
        version=settings.service_version,
        lifespan=lifespan,
        docs_url="/docs" if settings.is_development else None,
        redoc_url="/redoc" if settings.is_development else None,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.is_development else [],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Request ID middleware
    @app.middleware("http")
    async def add_request_id(request: Request, call_next):
        request_id = f"req_{int(time.time())}_{hash(str(request.url))}"
        request.state.request_id = request_id
        
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = str(process_time)
        
        return response

    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        request_id = getattr(request.state, "request_id", "unknown")
        
        logger.error(
            "Unhandled exception",
            request_id=request_id,
            error=str(exc),
            path=str(request.url),
        )
        
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error="Internal server error",
                detail=str(exc) if settings.is_development else "An unexpected error occurred",
                timestamp=time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
                request_id=request_id,
            ).dict()
        )

    return app


# Create app instance
app = create_app()


@app.post("/validate", response_model=ValidationResponse, tags=["Validation"])
async def validate_llm_output(request: ValidationRequest):
    """
    Validate LLM output through ArmorIQ workflow.
    
    Processes LLM output containing tool calls through the complete ArmorIQ security workflow:
    1. Plan capture with ArmorIQ
    2. Cryptographic token generation  
    3. Secure tool execution
    4. Credibility analysis
    5. Pass/fail determination
    
    Returns detailed credibility metrics and pass/fail decision based on configurable threshold.
    """
    if validation_service is None:
        raise HTTPException(status_code=503, detail="Validation service not initialized")
    
    try:
        result = await validation_service.validate_llm_output(request)
        
        logger.info(
            "Validation completed",
            session_id=result.session_id,
            status=result.status,
            credibility=result.credibility_score,
            tools_executed=result.tools_executed,
        )
        
        return result
        
    except Exception as e:
        logger.error("Validation failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """
    Health check endpoint.
    
    Verifies service status and ArmorIQ connectivity.
    """
    if validation_service is None:
        raise HTTPException(status_code=503, detail="Validation service not initialized")
    
    try:
        health_data = await validation_service.health_check()
        
        response = HealthResponse(
            status=health_data["status"],
            service=health_data["service"],
            version=health_data["version"],
            timestamp=health_data["timestamp"],
            armoriq_connected=health_data["armoriq_connected"],
            armoriq_configured=health_data.get("armoriq_configured", True),
            mode=health_data.get("mode", "unknown"),
        )
        
        # Return 503 if unhealthy
        if health_data["status"] != "healthy":
            raise HTTPException(status_code=503, detail="Service unhealthy")
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        raise HTTPException(status_code=503, detail=f"Health check failed: {str(e)}")


@app.get("/metrics", response_model=MetricsResponse, tags=["Monitoring"])  
async def get_metrics():
    """
    Get service metrics.
    
    Returns operational metrics including validation counts, success rates, and performance data.
    """
    if validation_service is None:
        raise HTTPException(status_code=503, detail="Validation service not initialized")
    
    try:
        metrics_data = validation_service.get_metrics()
        
        return MetricsResponse(**metrics_data)
        
    except Exception as e:
        logger.error("Failed to get metrics", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get metrics: {str(e)}")


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with service information."""
    return {
        "service": settings.service_name,
        "version": settings.service_version,
        "status": "running",
        "docs_url": "/docs" if settings.is_development else None,
        "endpoints": {
            "validate": "/validate",
            "health": "/health", 
            "metrics": "/metrics",
        }
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.port,
        reload=settings.is_development,
        log_level=settings.log_level.lower(),
    )