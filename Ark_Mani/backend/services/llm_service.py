"""
LLM Service
Handles scenario interpretation using Hugging Face models
"""

import logging
from typing import Dict, List, Any
import json
import re

logger = logging.getLogger(__name__)

# Mock implementation - In production, this would use actual Hugging Face API
class LLMService:
    """Service for LLM-based scenario interpretation"""
    
    def __init__(self, model_name: str = "EleutherAI/gpt-j-6B"):
        self.model_name = model_name
        logger.info(f"Initializing LLM service with model: {model_name}")
        
    async def interpret_scenario(
        self,
        scenario_description: str,
        severity: float,
        portfolio_context: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Interpret natural language scenario and generate structured output
        
        Args:
            scenario_description: User's scenario description
            severity: Severity multiplier (0.1 to 3.0)
            portfolio_context: Current portfolio information
            
        Returns:
            Dictionary with structured scenario and interpretation
        """
        try:
            logger.info(f"Interpreting scenario: {scenario_description[:100]}...")
            
            # Extract asset classes from portfolio
            asset_classes = set([asset['asset_class'] for asset in portfolio_context])
            tickers = [asset['ticker'] for asset in portfolio_context]
            
            # Parse scenario using rule-based approach (simplified)
            # In production, this would use actual LLM API
            structured_scenario = self._parse_scenario(
                scenario_description,
                severity,
                asset_classes,
                tickers
            )
            
            # Generate human-readable interpretation
            interpretation = self._generate_interpretation(
                structured_scenario,
                scenario_description
            )
            
            # Generate recommendations
            recommendations = self._generate_recommendations(structured_scenario)
            
            return {
                "structured_scenario": structured_scenario,
                "interpretation": interpretation,
                "recommendations": recommendations
            }
            
        except Exception as e:
            logger.error(f"Scenario interpretation failed: {str(e)}")
            raise
    
    def _parse_scenario(
        self,
        description: str,
        severity: float,
        asset_classes: set,
        tickers: List[str]
    ) -> Dict[str, Any]:
        """Parse scenario description into structured format"""
        
        description_lower = description.lower()
        
        # Initialize scenario structure
        scenario = {
            "shock_type": "general",
            "affected_assets": [],
            "shock_magnitude": {},
            "duration_days": 90,
            "correlation_changes": {}
        }
        
        # Detect scenario type
        if any(word in description_lower for word in ["recession", "crash", "crisis", "downturn"]):
            scenario["shock_type"] = "recession"
            scenario["shock_magnitude"]["stock"] = -0.30 * severity
            scenario["shock_magnitude"]["bond"] = 0.05 * severity
            scenario["duration_days"] = 180
            
        elif any(word in description_lower for word in ["interest rate", "rates rise", "fed"]):
            scenario["shock_type"] = "interest_rate"
            scenario["shock_magnitude"]["bond"] = -0.15 * severity
            scenario["shock_magnitude"]["stock"] = -0.10 * severity
            scenario["duration_days"] = 90
            
        elif any(word in description_lower for word in ["inflation", "prices rise"]):
            scenario["shock_type"] = "inflation"
            scenario["shock_magnitude"]["commodity"] = 0.20 * severity
            scenario["shock_magnitude"]["bond"] = -0.10 * severity
            scenario["shock_magnitude"]["stock"] = -0.05 * severity
            scenario["duration_days"] = 120
            
        elif any(word in description_lower for word in ["tech", "technology"]):
            scenario["shock_type"] = "sector_specific"
            # Filter for tech stocks
            tech_stocks = [t for t in tickers if any(x in t for x in ["AAPL", "GOOGL", "MSFT", "NVDA", "TSLA", "QQQ"])]
            scenario["affected_assets"] = tech_stocks
            scenario["shock_magnitude"]["specific"] = -0.25 * severity
            scenario["duration_days"] = 60
            
        elif any(word in description_lower for word in ["rally", "bull", "boom", "surge"]):
            scenario["shock_type"] = "bull_market"
            scenario["shock_magnitude"]["stock"] = 0.25 * severity
            scenario["shock_magnitude"]["crypto"] = 0.40 * severity
            scenario["duration_days"] = 120
        
        else:
            # General market stress
            scenario["shock_magnitude"]["stock"] = -0.15 * severity
            scenario["shock_magnitude"]["bond"] = -0.05 * severity
            
        # Extract numeric values if mentioned
        numbers = re.findall(r'(\d+)%', description)
        if numbers:
            percent = float(numbers[0]) / 100
            # Apply to primary asset class
            if "stock" in scenario["shock_magnitude"]:
                scenario["shock_magnitude"]["stock"] = -percent * severity
        
        return scenario
    
    def _generate_interpretation(
        self,
        scenario: Dict[str, Any],
        original_description: str
    ) -> str:
        """Generate human-readable interpretation of the scenario"""
        
        shock_type = scenario["shock_type"]
        duration = scenario["duration_days"]
        
        interpretations = {
            "recession": f"This scenario models a recessionary environment over {duration} days. "
                        "Equities are expected to decline significantly while bonds may provide some stability. "
                        "Flight to quality typically benefits government bonds.",
            
            "interest_rate": f"This scenario simulates an interest rate increase over {duration} days. "
                           "Bond prices are expected to fall as yields rise. Equities may also face pressure "
                           "due to higher discount rates and potentially slower economic growth.",
            
            "inflation": f"This scenario models an inflationary period over {duration} days. "
                        "Commodities typically benefit from inflation, while bonds suffer from eroding purchasing power. "
                        "Real assets may outperform financial assets.",
            
            "sector_specific": f"This scenario targets specific sectors over {duration} days. "
                             f"Affected assets: {', '.join(scenario['affected_assets'][:5])}. "
                             "Other portfolio components may provide diversification benefits.",
            
            "bull_market": f"This scenario models a bull market rally over {duration} days. "
                          "Risk assets including equities and cryptocurrencies are expected to appreciate. "
                          "Defensive assets may underperform.",
            
            "general": f"This scenario applies general market stress over {duration} days. "
                      "Portfolio components will react based on their historical correlations and volatilities."
        }
        
        base_interpretation = interpretations.get(shock_type, interpretations["general"])
        
        # Add magnitude details
        magnitude_text = " Expected shocks: "
        for asset_class, magnitude in scenario["shock_magnitude"].items():
            sign = "+" if magnitude > 0 else ""
            magnitude_text += f"{asset_class}: {sign}{magnitude:.1%}, "
        
        return base_interpretation + magnitude_text.rstrip(", ") + "."
    
    def _generate_recommendations(
        self,
        scenario: Dict[str, Any]
    ) -> List[str]:
        """Generate actionable recommendations based on scenario"""
        
        recommendations = []
        shock_type = scenario["shock_type"]
        
        if shock_type == "recession":
            recommendations = [
                "Consider increasing allocation to defensive sectors (utilities, consumer staples)",
                "Evaluate increasing bond allocation for stability",
                "Review cash position for potential buying opportunities",
                "Consider quality over growth stocks during downturn"
            ]
        
        elif shock_type == "interest_rate":
            recommendations = [
                "Reduce duration in bond portfolio to minimize interest rate risk",
                "Consider floating rate securities or short-term bonds",
                "Evaluate impact on rate-sensitive sectors (REITs, utilities)",
                "Review dividend-paying stocks as bond alternatives"
            ]
        
        elif shock_type == "inflation":
            recommendations = [
                "Increase allocation to real assets (commodities, real estate)",
                "Consider Treasury Inflation-Protected Securities (TIPS)",
                "Review exposure to companies with pricing power",
                "Evaluate reducing fixed-rate bond exposure"
            ]
        
        elif shock_type == "sector_specific":
            recommendations = [
                "Review sector concentration risk in portfolio",
                "Consider rebalancing to reduce overexposure",
                "Identify uncorrelated sectors for diversification",
                "Evaluate sector-specific hedging strategies"
            ]
        
        elif shock_type == "bull_market":
            recommendations = [
                "Review profit-taking strategy for appreciated assets",
                "Maintain disciplined rebalancing to target allocations",
                "Avoid chasing performance in overextended markets",
                "Consider adding to undervalued defensive positions"
            ]
        
        else:
            recommendations = [
                "Review portfolio diversification across asset classes",
                "Ensure adequate cash reserves for rebalancing opportunities",
                "Consider stress testing other downside scenarios",
                "Verify risk metrics align with investment objectives"
            ]
        
        return recommendations
