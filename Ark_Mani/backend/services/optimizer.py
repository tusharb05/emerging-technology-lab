"""
Portfolio Optimizer Service
Implements various optimization strategies using CVXPY
"""

import numpy as np
import pandas as pd
import cvxpy as cp
from typing import Dict, Tuple, List, Any
import logging

logger = logging.getLogger(__name__)


class PortfolioOptimizer:
    """Portfolio optimization using modern portfolio theory"""
    
    def __init__(self, risk_free_rate: float = 0.02):
        self.risk_free_rate = risk_free_rate
        self.trading_days = 252
    
    def optimize(
        self,
        returns: pd.DataFrame,
        objective: str = "Maximize Sharpe Ratio",
        constraints: Dict[str, Any] = None
    ) -> Tuple[np.ndarray, Dict[str, float]]:
        """
        Optimize portfolio based on specified objective
        
        Args:
            returns: Historical returns DataFrame
            objective: Optimization objective
            constraints: Dictionary of constraints
            
        Returns:
            Tuple of (optimized_weights, metrics)
        """
        try:
            if constraints is None:
                constraints = {}
            
            # Select optimization method
            if objective == "Minimize Variance":
                weights = self._minimize_variance(returns, constraints)
            elif objective == "Maximize Sharpe Ratio":
                weights = self._maximize_sharpe(returns, constraints)
            elif objective == "Risk Parity":
                weights = self._risk_parity(returns, constraints)
            elif objective == "Custom":
                weights = self._custom_optimization(returns, constraints)
            else:
                raise ValueError(f"Unknown objective: {objective}")
            
            # Calculate metrics for optimized portfolio
            metrics = self.calculate_portfolio_metrics(returns, weights)
            
            logger.info(f"Optimization complete: {objective}, Sharpe={metrics['sharpe']:.2f}")
            return weights, metrics
            
        except Exception as e:
            logger.error(f"Optimization failed: {str(e)}")
            raise
    
    def _minimize_variance(
        self,
        returns: pd.DataFrame,
        constraints: Dict[str, Any]
    ) -> np.ndarray:
        """Minimize portfolio variance"""
        try:
            n_assets = len(returns.columns)
            
            # Calculate expected returns and covariance
            mean_returns = returns.mean().values
            cov_matrix = returns.cov().values
            
            # Define optimization variables
            weights = cp.Variable(n_assets)
            
            # Objective: minimize variance
            portfolio_variance = cp.quad_form(weights, cov_matrix)
            objective = cp.Minimize(portfolio_variance)
            
            # Constraints
            constraint_list = [
                cp.sum(weights) == 1,  # Weights sum to 1
                weights >= constraints.get('min_weight', 0.0),  # Minimum weight
                weights <= constraints.get('max_weight', 1.0)   # Maximum weight
            ]
            
            # Target return constraint if specified
            if 'target_return' in constraints:
                target_return = constraints['target_return'] / self.trading_days
                constraint_list.append(weights @ mean_returns >= target_return)
            
            # Sector constraints
            if 'sector_limits' in constraints:
                # This would require sector mapping - simplified version
                pass
            
            # Solve optimization problem
            problem = cp.Problem(objective, constraint_list)
            problem.solve(solver=cp.ECOS)
            
            if problem.status not in ["optimal", "optimal_inaccurate"]:
                raise ValueError(f"Optimization failed: {problem.status}")
            
            return weights.value
            
        except Exception as e:
            logger.error(f"Variance minimization failed: {str(e)}")
            raise
    
    def _maximize_sharpe(
        self,
        returns: pd.DataFrame,
        constraints: Dict[str, Any]
    ) -> np.ndarray:
        """Maximize Sharpe Ratio"""
        try:
            n_assets = len(returns.columns)
            
            # Calculate parameters
            mean_returns = returns.mean().values * self.trading_days
            cov_matrix = returns.cov().values * self.trading_days
            
            # Define variables
            weights = cp.Variable(n_assets)
            
            # Portfolio return and risk
            portfolio_return = weights @ mean_returns
            portfolio_risk = cp.quad_form(weights, cov_matrix)
            
            # Objective: maximize Sharpe ratio
            # We maximize (return - risk_free) / sqrt(variance)
            # Equivalently: minimize variance / (return - risk_free)
            objective = cp.Minimize(portfolio_risk)
            
            # Constraints
            constraint_list = [
                cp.sum(weights) == 1,
                weights >= constraints.get('min_weight', 0.0),
                weights <= constraints.get('max_weight', 1.0),
                portfolio_return - self.risk_free_rate >= 0.01  # Minimum excess return
            ]
            
            # Solve
            problem = cp.Problem(objective, constraint_list)
            problem.solve(solver=cp.ECOS)
            
            if problem.status not in ["optimal", "optimal_inaccurate"]:
                # Fallback to equal weights
                logger.warning("Sharpe optimization failed, using equal weights")
                return np.ones(n_assets) / n_assets
            
            return weights.value
            
        except Exception as e:
            logger.error(f"Sharpe maximization failed: {str(e)}")
            # Return equal weights as fallback
            return np.ones(len(returns.columns)) / len(returns.columns)
    
    def _risk_parity(
        self,
        returns: pd.DataFrame,
        constraints: Dict[str, Any]
    ) -> np.ndarray:
        """
        Risk parity allocation
        Each asset contributes equally to portfolio risk
        """
        try:
            cov_matrix = returns.cov().values
            n_assets = len(returns.columns)
            
            # Initialize with equal weights
            weights = np.ones(n_assets) / n_assets
            
            # Iterative algorithm for risk parity
            for iteration in range(100):
                portfolio_vol = np.sqrt(weights @ cov_matrix @ weights)
                marginal_contrib = cov_matrix @ weights / portfolio_vol
                risk_contrib = weights * marginal_contrib
                
                # Target risk contribution
                target_risk = risk_contrib.sum() / n_assets
                
                # Update weights
                weights = weights * (target_risk / risk_contrib)
                weights = weights / weights.sum()  # Normalize
                
                # Check convergence
                if np.allclose(risk_contrib, target_risk, rtol=0.01):
                    break
            
            # Apply constraints
            min_weight = constraints.get('min_weight', 0.0)
            max_weight = constraints.get('max_weight', 1.0)
            weights = np.clip(weights, min_weight, max_weight)
            weights = weights / weights.sum()  # Re-normalize
            
            return weights
            
        except Exception as e:
            logger.error(f"Risk parity optimization failed: {str(e)}")
            raise
    
    def _custom_optimization(
        self,
        returns: pd.DataFrame,
        constraints: Dict[str, Any]
    ) -> np.ndarray:
        """Custom optimization with user-defined constraints"""
        # Placeholder for custom optimization
        return self._maximize_sharpe(returns, constraints)
    
    def calculate_portfolio_metrics(
        self,
        returns: pd.DataFrame,
        weights: np.ndarray
    ) -> Dict[str, float]:
        """Calculate portfolio performance metrics"""
        try:
            # Annualized return
            mean_returns = returns.mean().values
            portfolio_return = (weights @ mean_returns) * self.trading_days
            
            # Annualized volatility
            cov_matrix = returns.cov().values
            portfolio_variance = weights @ cov_matrix @ weights
            portfolio_volatility = np.sqrt(portfolio_variance * self.trading_days)
            
            # Sharpe ratio
            sharpe_ratio = (portfolio_return - self.risk_free_rate) / portfolio_volatility
            
            return {
                'return': float(portfolio_return),
                'volatility': float(portfolio_volatility),
                'sharpe': float(sharpe_ratio),
                'variance': float(portfolio_variance * self.trading_days)
            }
            
        except Exception as e:
            logger.error(f"Metrics calculation failed: {str(e)}")
            raise
    
    def generate_efficient_frontier(
        self,
        returns: pd.DataFrame,
        num_points: int = 50
    ) -> Dict[str, List[float]]:
        """
        Generate efficient frontier points
        
        Args:
            returns: Historical returns
            num_points: Number of frontier points
            
        Returns:
            Dictionary with returns and volatility arrays
        """
        try:
            mean_returns = returns.mean().values * self.trading_days
            cov_matrix = returns.cov().values * self.trading_days
            n_assets = len(returns.columns)
            
            # Define range of target returns
            min_return = mean_returns.min()
            max_return = mean_returns.max()
            target_returns = np.linspace(min_return, max_return, num_points)
            
            frontier_returns = []
            frontier_volatility = []
            
            for target in target_returns:
                try:
                    # Optimization variables
                    weights = cp.Variable(n_assets)
                    portfolio_return = weights @ mean_returns
                    portfolio_variance = cp.quad_form(weights, cov_matrix)
                    
                    # Minimize variance for target return
                    objective = cp.Minimize(portfolio_variance)
                    constraints = [
                        cp.sum(weights) == 1,
                        weights >= 0,
                        portfolio_return >= target
                    ]
                    
                    problem = cp.Problem(objective, constraints)
                    problem.solve(solver=cp.ECOS, verbose=False)
                    
                    if problem.status == "optimal":
                        frontier_returns.append(float(target))
                        frontier_volatility.append(float(np.sqrt(portfolio_variance.value)))
                        
                except:
                    continue
            
            return {
                'returns': frontier_returns,
                'volatility': frontier_volatility
            }
            
        except Exception as e:
            logger.error(f"Efficient frontier generation failed: {str(e)}")
            return {'returns': [], 'volatility': []}
