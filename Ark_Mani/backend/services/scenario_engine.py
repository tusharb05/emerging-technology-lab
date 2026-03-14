"""
Scenario Engine
Applies market scenarios and runs stress tests
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)


class ScenarioEngine:
    """Engine for applying scenarios and running stress tests"""
    
    def __init__(self):
        self.trading_days = 252
    
    def run_stress_test(
        self,
        returns: pd.DataFrame,
        weights: np.ndarray,
        scenario: Dict[str, Any],
        num_simulations: int = 10000,
        duration: int = 90
    ) -> Dict[str, Any]:
        """
        Run stress test under given scenario
        
        Args:
            returns: Historical returns DataFrame
            weights: Portfolio weights
            scenario: Structured scenario dictionary
            num_simulations: Number of simulation paths
            duration: Duration in days
            
        Returns:
            Dictionary with stress test results
        """
        try:
            logger.info(f"Running stress test: {scenario['shock_type']}")
            
            # Apply shocks to returns distribution
            shocked_returns = self._apply_shocks(returns, scenario)
            
            # Calculate shocked mean and covariance
            mean_returns = shocked_returns.mean()
            cov_matrix = shocked_returns.cov()
            
            # Run simulations under stressed conditions
            simulation_paths = np.zeros((num_simulations, duration))
            initial_value = 100000
            
            for i in range(num_simulations):
                random_returns = np.random.multivariate_normal(
                    mean_returns,
                    cov_matrix,
                    duration
                )
                portfolio_returns = np.dot(random_returns, weights)
                cumulative_returns = np.cumprod(1 + portfolio_returns)
                simulation_paths[i] = initial_value * cumulative_returns
            
            results = {
                "paths": simulation_paths.tolist(),
                "scenario_type": scenario["shock_type"],
                "duration": duration
            }
            
            logger.info("Stress test completed")
            return results
            
        except Exception as e:
            logger.error(f"Stress test failed: {str(e)}")
            raise
    
    def _apply_shocks(
        self,
        returns: pd.DataFrame,
        scenario: Dict[str, Any]
    ) -> pd.DataFrame:
        """Apply scenario shocks to returns distribution"""
        
        shocked_returns = returns.copy()
        shock_magnitude = scenario.get("shock_magnitude", {})
        
        # Apply shocks based on asset class or specific assets
        for column in shocked_returns.columns:
            # Determine asset class (simplified - would need mapping in production)
            asset_class = self._infer_asset_class(column)
            
            if asset_class in shock_magnitude:
                shock = shock_magnitude[asset_class]
                # Shift mean returns
                shocked_returns[column] = shocked_returns[column] + (shock / self.trading_days)
            
            # Check if specific asset is targeted
            if column in scenario.get("affected_assets", []):
                specific_shock = shock_magnitude.get("specific", 0)
                shocked_returns[column] = shocked_returns[column] + (specific_shock / self.trading_days)
        
        return shocked_returns
    
    def _infer_asset_class(self, ticker: str) -> str:
        """Infer asset class from ticker (simplified)"""
        
        ticker_upper = ticker.upper()
        
        # Bonds
        if any(x in ticker_upper for x in ["AGG", "BND", "TLT", "BOND"]):
            return "bond"
        
        # Commodities
        if any(x in ticker_upper for x in ["GLD", "SLV", "USO", "COMMODITY"]):
            return "commodity"
        
        # Crypto
        if any(x in ticker_upper for x in ["BTC", "ETH", "CRYPTO"]):
            return "crypto"
        
        # Default to stock
        return "stock"
    
    def calculate_impact_metrics(
        self,
        scenario_results: Dict[str, Any]
    ) -> Dict[str, float]:
        """Calculate impact metrics from scenario results"""
        
        try:
            paths = np.array(scenario_results["paths"])
            initial_value = paths[0, 0]
            final_values = paths[:, -1]
            
            # Calculate metrics
            expected_loss = (final_values.mean() - initial_value) / initial_value
            worst_case = (final_values.min() - initial_value) / initial_value
            
            # Probability of various loss thresholds
            prob_loss = (final_values < initial_value).sum() / len(final_values)
            prob_large_loss = (final_values < initial_value * 0.9).sum() / len(final_values)
            
            # Recovery time (simplified)
            recovery_days = scenario_results.get("duration", 90)
            
            metrics = {
                "expected_loss": float(expected_loss),
                "worst_case": float(worst_case),
                "prob_loss": float(prob_loss * 100),
                "prob_large_loss": float(prob_large_loss * 100),
                "recovery_days": float(recovery_days)
            }
            
            return metrics
            
        except Exception as e:
            logger.error(f"Impact metrics calculation failed: {str(e)}")
            raise
    
    def calculate_asset_impact(
        self,
        returns: pd.DataFrame,
        scenario: Dict[str, Any],
        tickers: List[str]
    ) -> List[Dict[str, Any]]:
        """Calculate impact on individual assets"""
        
        try:
            asset_impacts = []
            shock_magnitude = scenario.get("shock_magnitude", {})
            
            for ticker in tickers:
                asset_class = self._infer_asset_class(ticker)
                
                # Get shock for this asset class
                shock = shock_magnitude.get(asset_class, 0)
                
                # Check if specifically targeted
                if ticker in scenario.get("affected_assets", []):
                    shock = shock_magnitude.get("specific", shock)
                
                asset_impacts.append({
                    "ticker": ticker,
                    "asset_class": asset_class,
                    "impact": float(shock)
                })
            
            return asset_impacts
            
        except Exception as e:
            logger.error(f"Asset impact calculation failed: {str(e)}")
            raise
