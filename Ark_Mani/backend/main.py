from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
from typing import List, Dict, Optional, Any
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Portfolio Risk Assessment API",
    description="AI-powered portfolio risk analysis and optimization",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic Models
class Asset(BaseModel):
    ticker: str = Field(..., description="Asset ticker symbol")
    weight: float = Field(..., ge=0.0, le=1.0, description="Portfolio weight")
    asset_class: str = Field(..., description="Asset class (stock, bond, crypto, etc.)")

class Portfolio(BaseModel):
    assets: List[Asset]
    
    @validator('assets')
    def validate_weights(cls, v):
        total_weight = sum(asset.weight for asset in v)
        if not (0.99 <= total_weight <= 1.01):
            raise ValueError(f"Portfolio weights must sum to 1.0, got {total_weight}")
        return v

class AnalysisRequest(BaseModel):
    portfolio: List[Dict[str, Any]]
    confidence_level: float = Field(0.95, ge=0.5, le=0.99)
    simulation_paths: int = Field(10000, ge=100, le=100000)
    time_horizon: int = Field(252, ge=1, le=365)

class OptimizationRequest(BaseModel):
    portfolio: List[Dict[str, Any]]
    objective: str = Field("Maximize Sharpe Ratio", description="Optimization objective")
    constraints: Dict[str, Any] = Field(default_factory=dict)

class ScenarioRequest(BaseModel):
    portfolio: List[Dict[str, Any]]
    scenario_description: str = Field(..., min_length=10)
    severity: float = Field(1.0, ge=0.1, le=3.0)
    duration: int = Field(90, ge=1, le=365)
    simulation_paths: int = Field(10000, ge=100, le=100000)

class ReportRequest(BaseModel):
    portfolio: List[Dict[str, Any]]
    analysis_results: Dict[str, Any]
    report_type: str
    include_charts: bool = True
    include_raw_data: bool = False
    format: str = "PDF"

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for Kubernetes liveness probe"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "backend-api"
    }

# Readiness check
@app.get("/ready")
async def readiness_check():
    """Readiness check for Kubernetes readiness probe"""
    # Add checks for database, redis, etc.
    return {
        "status": "ready",
        "timestamp": datetime.utcnow().isoformat(),
        "dependencies": {
            "database": "connected",
            "redis": "connected",
            "llm_service": "available"
        }
    }

# Metrics endpoint for Prometheus
@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    # This would typically use prometheus_client library
    return {"message": "Metrics endpoint - integrate with prometheus_client"}

# Main analysis endpoint
@app.post("/api/v1/analyze")
async def analyze_portfolio(request: AnalysisRequest):
    """
    Perform comprehensive risk analysis on portfolio
    
    - Fetches historical market data
    - Calculates risk metrics (VaR, CVaR, Sharpe, etc.)
    - Runs Monte Carlo simulations
    - Returns detailed analysis results
    """
    try:
        logger.info(f"Starting analysis for portfolio with {len(request.portfolio)} assets")
        
        # Import risk calculation modules
        from services.risk_calculator import RiskCalculator
        from services.market_data import MarketDataService
        
        # Initialize services
        market_data_service = MarketDataService()
        risk_calculator = RiskCalculator()
        
        # Extract tickers
        tickers = [asset['ticker'] for asset in request.portfolio]
        weights = np.array([asset['weight'] for asset in request.portfolio])
        
        # Fetch historical data
        logger.info(f"Fetching market data for {len(tickers)} tickers")
        price_data = await market_data_service.fetch_historical_prices(
            tickers=tickers,
            period="2y"  # 2 years of data
        )
        
        if price_data.empty:
            raise HTTPException(status_code=400, detail="Failed to fetch market data")
        
        # Calculate returns
        returns = price_data.pct_change().dropna()
        
        # Calculate risk metrics
        logger.info("Calculating risk metrics")
        risk_metrics = risk_calculator.calculate_risk_metrics(
            returns=returns,
            weights=weights,
            confidence_level=request.confidence_level
        )
        
        # Run Monte Carlo simulation
        logger.info(f"Running Monte Carlo simulation with {request.simulation_paths} paths")
        simulation_results = risk_calculator.monte_carlo_simulation(
            returns=returns,
            weights=weights,
            num_simulations=request.simulation_paths,
            time_horizon=request.time_horizon
        )
        
        # Calculate correlation matrix
        correlation_matrix = returns.corr().round(3).to_dict()
        
        # Prepare response
        response = {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "portfolio_size": len(tickers),
            "risk_metrics": risk_metrics,
            "simulation_results": simulation_results,
            "correlation_matrix": correlation_matrix,
            "metadata": {
                "confidence_level": request.confidence_level,
                "simulation_paths": request.simulation_paths,
                "time_horizon": request.time_horizon,
                "data_period": "2 years"
            }
        }
        
        logger.info("Analysis completed successfully")
        return response
        
    except Exception as e:
        logger.error(f"Analysis failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

# Portfolio optimization endpoint
@app.post("/api/v1/optimize")
async def optimize_portfolio(request: OptimizationRequest):
    """
    Optimize portfolio allocations based on specified objective
    
    Supported objectives:
    - Minimize Variance
    - Maximize Sharpe Ratio
    - Risk Parity
    - Custom constraints
    """
    try:
        logger.info(f"Starting optimization with objective: {request.objective}")
        
        from services.optimizer import PortfolioOptimizer
        from services.market_data import MarketDataService
        
        # Initialize services
        market_data_service = MarketDataService()
        optimizer = PortfolioOptimizer()
        
        # Extract tickers and current weights
        tickers = [asset['ticker'] for asset in request.portfolio]
        current_weights = np.array([asset['weight'] for asset in request.portfolio])
        
        # Fetch historical data
        price_data = await market_data_service.fetch_historical_prices(tickers, period="2y")
        returns = price_data.pct_change().dropna()
        
        # Calculate original portfolio metrics
        original_metrics = optimizer.calculate_portfolio_metrics(returns, current_weights)
        
        # Run optimization
        logger.info("Running portfolio optimization")
        optimized_weights, optimized_metrics = optimizer.optimize(
            returns=returns,
            objective=request.objective,
            constraints=request.constraints
        )
        
        # Generate efficient frontier
        efficient_frontier = optimizer.generate_efficient_frontier(returns)
        
        # Prepare optimized portfolio
        optimized_portfolio = [
            {
                "ticker": ticker,
                "old_weight": float(old_weight),
                "new_weight": float(new_weight),
                "change": float(new_weight - old_weight)
            }
            for ticker, old_weight, new_weight in zip(tickers, current_weights, optimized_weights)
        ]
        
        response = {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "original_metrics": original_metrics,
            "optimized_metrics": optimized_metrics,
            "optimized_weights": optimized_portfolio,
            "efficient_frontier": efficient_frontier,
            "improvement": {
                "return_increase": optimized_metrics['return'] - original_metrics['return'],
                "risk_reduction": original_metrics['volatility'] - optimized_metrics['volatility'],
                "sharpe_improvement": optimized_metrics['sharpe'] - original_metrics['sharpe']
            }
        }
        
        logger.info("Optimization completed successfully")
        return response
        
    except Exception as e:
        logger.error(f"Optimization failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Optimization failed: {str(e)}")

# LLM-powered scenario analysis
@app.post("/api/v1/scenario/analyze")
async def analyze_scenario(request: ScenarioRequest):
    """
    Use LLM to interpret scenario description and simulate impact
    
    - Sends scenario description to LLM service
    - LLM generates structured market shocks
    - Applies shocks to portfolio
    - Runs stress test simulations
    """
    try:
        logger.info(f"Analyzing scenario: {request.scenario_description[:100]}...")
        
        from services.llm_service import LLMService
        from services.scenario_engine import ScenarioEngine
        from services.market_data import MarketDataService
        
        # Initialize services
        llm_service = LLMService()
        scenario_engine = ScenarioEngine()
        market_data_service = MarketDataService()
        
        # Get LLM interpretation
        logger.info("Sending scenario to LLM for interpretation")
        llm_response = await llm_service.interpret_scenario(
            scenario_description=request.scenario_description,
            severity=request.severity,
            portfolio_context=request.portfolio
        )
        
        # Extract structured scenario
        structured_scenario = llm_response['structured_scenario']
        interpretation = llm_response['interpretation']
        
        # Fetch market data
        tickers = [asset['ticker'] for asset in request.portfolio]
        weights = np.array([asset['weight'] for asset in request.portfolio])
        
        price_data = await market_data_service.fetch_historical_prices(tickers, period="2y")
        returns = price_data.pct_change().dropna()
        
        # Apply scenario and run stress test
        logger.info("Running scenario stress test")
        scenario_results = scenario_engine.run_stress_test(
            returns=returns,
            weights=weights,
            scenario=structured_scenario,
            num_simulations=request.simulation_paths,
            duration=request.duration
        )
        
        # Calculate impact metrics
        impact_metrics = scenario_engine.calculate_impact_metrics(scenario_results)
        
        # Asset-level impact
        asset_impact = scenario_engine.calculate_asset_impact(
            returns=returns,
            scenario=structured_scenario,
            tickers=tickers
        )
        
        response = {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "llm_interpretation": interpretation,
            "structured_scenario": structured_scenario,
            "impact_metrics": impact_metrics,
            "scenario_paths": scenario_results['paths'][:100],  # Return subset
            "asset_impact": asset_impact,
            "recommendations": llm_response.get('recommendations', [])
        }
        
        logger.info("Scenario analysis completed")
        return response
        
    except Exception as e:
        logger.error(f"Scenario analysis failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Scenario analysis failed: {str(e)}")

# Report generation endpoint
@app.post("/api/v1/reports/generate")
async def generate_report(request: ReportRequest, background_tasks: BackgroundTasks):
    """
    Generate comprehensive risk assessment report
    
    Supports multiple formats:
    - PDF: Full report with charts
    - Excel: Detailed data tables
    - JSON: Programmatic access
    """
    try:
        logger.info(f"Generating {request.format} report of type: {request.report_type}")
        
        from services.report_generator import ReportGenerator
        
        report_generator = ReportGenerator()
        
        # Generate report
        report_data = report_generator.generate(
            portfolio=request.portfolio,
            analysis_results=request.analysis_results,
            report_type=request.report_type,
            include_charts=request.include_charts,
            include_raw_data=request.include_raw_data,
            output_format=request.format
        )
        
        response = {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "report_type": request.report_type,
            "format": request.format,
            "file_size_kb": len(report_data.get('content', b'')) / 1024,
            "download_url": report_data.get('url'),
            "expires_at": (datetime.utcnow() + timedelta(hours=24)).isoformat()
        }
        
        logger.info(f"Report generated successfully: {response['file_size_kb']:.2f} KB")
        return response
        
    except Exception as e:
        logger.error(f"Report generation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Report generation failed: {str(e)}")

# Upload portfolio file
@app.post("/api/v1/portfolio/upload")
async def upload_portfolio(file: UploadFile = File(...)):
    """
    Upload portfolio from CSV file
    
    Expected columns: ticker, weight, asset_class
    """
    try:
        # Read file content
        content = await file.read()
        
        # Parse CSV
        import io
        df = pd.read_csv(io.StringIO(content.decode('utf-8')))
        
        # Validate required columns
        required_columns = ['ticker', 'weight', 'asset_class']
        if not all(col in df.columns for col in required_columns):
            raise HTTPException(
                status_code=400,
                detail=f"CSV must contain columns: {required_columns}"
            )
        
        # Validate weights
        total_weight = df['weight'].sum()
        if not (0.99 <= total_weight <= 1.01):
            # Normalize weights
            df['weight'] = df['weight'] / total_weight
        
        portfolio_data = df.to_dict('records')
        
        return {
            "status": "success",
            "portfolio": portfolio_data,
            "num_assets": len(portfolio_data),
            "message": "Portfolio uploaded successfully"
        }
        
    except Exception as e:
        logger.error(f"Portfolio upload failed: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Failed to parse portfolio: {str(e)}")

# Exception handler
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "timestamp": datetime.utcnow().isoformat()
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
