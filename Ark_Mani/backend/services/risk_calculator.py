"""
Risk Calculator Service
Implements comprehensive risk metrics and Monte Carlo simulations
"""

import numpy as np
import pandas as pd
from scipy import stats
from typing import Dict, List, Tuple, Any
import logging

logger = logging.getLogger(__name__)


class RiskCalculator:
    """Calculate various risk metrics for portfolio analysis"""
    
    def __init__(self):
        self.trading_days = 252  # Annual trading days
        
    def calculate_risk_metrics(
        self,
        returns: pd.DataFrame,
        weights: np.ndarray,
        confidence_level: float = 0.95
    ) -> Dict[str, float]:
        """
        Calculate comprehensive risk metrics
        
        Args:
            returns: DataFrame of asset returns
            weights: Portfolio weights
            confidence_level: Confidence level for VaR/CVaR
            
        Returns:
            Dictionary of risk metrics
        """
        try:
            # Calculate portfolio returns
            portfolio_returns = (returns * weights).sum(axis=1)
            
            # Basic statistics
            mean_return = portfolio_returns.mean() * self.trading_days
            volatility = portfolio_returns.std() * np.sqrt(self.trading_days)
            
            # Value at Risk (VaR)
            var_95 = self._calculate_var(portfolio_returns, 0.95)
            var_99 = self._calculate_var(portfolio_returns, 0.99)
            
            # Conditional VaR (Expected Shortfall)
            cvar_95 = self._calculate_cvar(portfolio_returns, 0.95)
            cvar_99 = self._calculate_cvar(portfolio_returns, 0.99)
            
            # Sharpe Ratio (assuming risk-free rate of 2%)
            risk_free_rate = 0.02
            sharpe_ratio = (mean_return - risk_free_rate) / volatility if volatility > 0 else 0
            
            # Sortino Ratio (downside risk)
            sortino_ratio = self._calculate_sortino_ratio(portfolio_returns, risk_free_rate)
            
            # Maximum Drawdown
            max_drawdown = self._calculate_max_drawdown(portfolio_returns)
            
            # Calmar Ratio
            calmar_ratio = mean_return / abs(max_drawdown) if max_drawdown != 0 else 0
            
            # Beta (relative to market - using first asset as proxy)
            beta = self._calculate_beta(portfolio_returns, returns.iloc[:, 0])
            
            # Skewness and Kurtosis
            skewness = stats.skew(portfolio_returns.dropna())
            kurtosis = stats.kurtosis(portfolio_returns.dropna())
            
            metrics = {
                'mean_return': float(mean_return),
                'volatility': float(volatility),
                'var_95': float(var_95),
                'var_99': float(var_99),
                'cvar_95': float(cvar_95),
                'cvar_99': float(cvar_99),
                'sharpe_ratio': float(sharpe_ratio),
                'sortino_ratio': float(sortino_ratio),
                'max_drawdown': float(max_drawdown),
                'calmar_ratio': float(calmar_ratio),
                'beta': float(beta),
                'skewness': float(skewness),
                'kurtosis': float(kurtosis)
            }
            
            logger.info(f"Calculated risk metrics: Sharpe={sharpe_ratio:.2f}, VaR(95%)={var_95:.2%}")
            return metrics
            
        except Exception as e:
            logger.error(f"Error calculating risk metrics: {str(e)}")
            raise
    
    def _calculate_var(self, returns: pd.Series, confidence_level: float) -> float:
        """Calculate Value at Risk using historical simulation"""
        return np.percentile(returns.dropna(), (1 - confidence_level) * 100)
    
    def _calculate_cvar(self, returns: pd.Series, confidence_level: float) -> float:
        """Calculate Conditional VaR (Expected Shortfall)"""
        var = self._calculate_var(returns, confidence_level)
        return returns[returns <= var].mean()
    
    def _calculate_sortino_ratio(self, returns: pd.Series, risk_free_rate: float) -> float:
        """Calculate Sortino Ratio (uses downside deviation)"""
        excess_returns = returns - (risk_free_rate / self.trading_days)
        downside_returns = excess_returns[excess_returns < 0]
        downside_std = downside_returns.std() * np.sqrt(self.trading_days)
        
        if downside_std == 0:
            return 0.0
        
        return (returns.mean() * self.trading_days - risk_free_rate) / downside_std
    
    def _calculate_max_drawdown(self, returns: pd.Series) -> float:
        """Calculate Maximum Drawdown"""
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        return drawdown.min()
    
    def _calculate_beta(self, portfolio_returns: pd.Series, market_returns: pd.Series) -> float:
        """Calculate portfolio beta relative to market"""
        covariance = np.cov(portfolio_returns.dropna(), market_returns.dropna())[0][1]
        market_variance = market_returns.var()
        
        if market_variance == 0:
            return 1.0
        
        return covariance / market_variance
    
    def monte_carlo_simulation(
        self,
        returns: pd.DataFrame,
        weights: np.ndarray,
        num_simulations: int = 10000,
        time_horizon: int = 252
    ) -> Dict[str, Any]:
        """
        Run Monte Carlo simulation for portfolio
        
        Args:
            returns: Historical returns
            weights: Portfolio weights
            num_simulations: Number of simulation paths
            time_horizon: Number of days to simulate
            
        Returns:
            Dictionary with simulation results
        """
        try:
            logger.info(f"Running Monte Carlo with {num_simulations} paths over {time_horizon} days")
            
            # Calculate mean and covariance of returns
            mean_returns = returns.mean()
            cov_matrix = returns.cov()
            
            # Initialize arrays
            simulation_paths = np.zeros((num_simulations, time_horizon))
            initial_value = 100000  # Starting portfolio value
            
            # Run simulations
            for i in range(num_simulations):
                # Generate correlated random returns
                random_returns = np.random.multivariate_normal(
                    mean_returns,
                    cov_matrix,
                    time_horizon
                )
                
                # Calculate portfolio returns
                portfolio_returns = np.dot(random_returns, weights)
                
                # Calculate cumulative portfolio value
                cumulative_returns = np.cumprod(1 + portfolio_returns)
                simulation_paths[i] = initial_value * cumulative_returns
            
            # Calculate statistics
            mean_path = simulation_paths.mean(axis=0)
            median_path = np.median(simulation_paths, axis=0)
            
            # Confidence intervals
            lower_ci = np.percentile(simulation_paths, 2.5, axis=0)
            upper_ci = np.percentile(simulation_paths, 97.5, axis=0)
            
            # Final value statistics
            final_values = simulation_paths[:, -1]
            expected_final = final_values.mean()
            var_95_final = np.percentile(final_values, 5)
            var_99_final = np.percentile(final_values, 1)
            
            # Calculate returns
            final_returns = (final_values - initial_value) / initial_value
            
            # Probability of loss
            prob_loss = (final_values < initial_value).sum() / num_simulations
            
            results = {
                'paths': simulation_paths.tolist(),
                'mean_path': mean_path.tolist(),
                'median_path': median_path.tolist(),
                'lower_ci': lower_ci.tolist(),
                'upper_ci': upper_ci.tolist(),
                'expected_final_value': float(expected_final),
                'var_95_final': float(var_95_final),
                'var_99_final': float(var_99_final),
                'probability_of_loss': float(prob_loss),
                'final_returns': final_returns.tolist(),
                'mean_return': float(final_returns.mean()),
                'std_return': float(final_returns.std())
            }
            
            logger.info(f"Simulation complete. Expected final value: ${expected_final:,.2f}")
            return results
            
        except Exception as e:
            logger.error(f"Monte Carlo simulation failed: {str(e)}")
            raise
    
    def stress_test(
        self,
        returns: pd.DataFrame,
        weights: np.ndarray,
        shock_magnitude: float,
        affected_assets: List[int] = None
    ) -> Dict[str, float]:
        """
        Perform stress testing with specified shocks
        
        Args:
            returns: Historical returns
            weights: Portfolio weights
            shock_magnitude: Size of shock (e.g., -0.20 for 20% drop)
            affected_assets: Indices of assets to shock (None = all)
            
        Returns:
            Dictionary with stress test results
        """
        try:
            if affected_assets is None:
                affected_assets = list(range(len(weights)))
            
            # Create shocked returns
            shocked_returns = returns.copy()
            shocked_returns.iloc[-1, affected_assets] = shock_magnitude
            
            # Calculate portfolio impact
            portfolio_returns = (shocked_returns * weights).sum(axis=1)
            shocked_value = (1 + portfolio_returns.iloc[-1])
            
            # Calculate metrics under stress
            stressed_metrics = self.calculate_risk_metrics(shocked_returns, weights)
            
            results = {
                'immediate_impact': float(shocked_value - 1),
                'stressed_var_95': stressed_metrics['var_95'],
                'stressed_volatility': stressed_metrics['volatility'],
                'stressed_sharpe': stressed_metrics['sharpe_ratio']
            }
            
            return results
            
        except Exception as e:
            logger.error(f"Stress test failed: {str(e)}")
            raise
