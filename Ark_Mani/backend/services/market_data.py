"""
Market Data Service
Fetches and processes market data using yFinance
"""

import yfinance as yf
import pandas as pd
import numpy as np
from typing import List, Optional
from datetime import datetime, timedelta
import logging
import asyncio
from functools import lru_cache

logger = logging.getLogger(__name__)


class MarketDataService:
    """Service for fetching and caching market data"""
    
    def __init__(self, cache_duration: int = 3600):
        self.cache_duration = cache_duration  # Cache for 1 hour
        self._cache = {}
    
    async def fetch_historical_prices(
        self,
        tickers: List[str],
        period: str = "2y",
        interval: str = "1d"
    ) -> pd.DataFrame:
        """
        Fetch historical price data for multiple tickers
        
        Args:
            tickers: List of ticker symbols
            period: Data period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
            interval: Data interval (1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo)
            
        Returns:
            DataFrame with adjusted close prices
        """
        try:
            logger.info(f"Fetching historical data for {len(tickers)} tickers")
            
            # Check cache
            cache_key = f"{','.join(sorted(tickers))}_{period}_{interval}"
            if cache_key in self._cache:
                cache_time, data = self._cache[cache_key]
                if (datetime.now() - cache_time).seconds < self.cache_duration:
                    logger.info("Returning cached data")
                    return data
            
            # Download data
            data = await asyncio.to_thread(
                self._download_data,
                tickers,
                period,
                interval
            )
            
            # Cache the result
            self._cache[cache_key] = (datetime.now(), data)
            
            logger.info(f"Downloaded {len(data)} rows of data")
            return data
            
        except Exception as e:
            logger.error(f"Failed to fetch market data: {str(e)}")
            raise
    
    def _download_data(
        self,
        tickers: List[str],
        period: str,
        interval: str
    ) -> pd.DataFrame:
        """Internal method to download data using yfinance"""
        try:
            # Download data for all tickers
            data = yf.download(
                tickers=tickers,
                period=period,
                interval=interval,
                progress=False,
                threads=True
            )
            
            # Handle single vs multiple tickers
            if len(tickers) == 1:
                prices = data['Adj Close'].to_frame()
                prices.columns = tickers
            else:
                prices = data['Adj Close']
            
            # Remove any NaN values
            prices = prices.dropna()
            
            if prices.empty:
                raise ValueError("No data retrieved for specified tickers")
            
            return prices
            
        except Exception as e:
            logger.error(f"Download failed: {str(e)}")
            raise
    
    async def get_current_prices(self, tickers: List[str]) -> Dict[str, float]:
        """
        Get current prices for tickers
        
        Args:
            tickers: List of ticker symbols
            
        Returns:
            Dictionary of ticker: price
        """
        try:
            prices = {}
            
            for ticker in tickers:
                try:
                    stock = yf.Ticker(ticker)
                    info = stock.info
                    current_price = info.get('currentPrice') or info.get('regularMarketPrice')
                    
                    if current_price:
                        prices[ticker] = float(current_price)
                    else:
                        logger.warning(f"No current price available for {ticker}")
                        prices[ticker] = None
                        
                except Exception as e:
                    logger.warning(f"Failed to get price for {ticker}: {str(e)}")
                    prices[ticker] = None
            
            return prices
            
        except Exception as e:
            logger.error(f"Failed to get current prices: {str(e)}")
            raise
    
    async def get_asset_info(self, ticker: str) -> dict:
        """
        Get detailed information about an asset
        
        Args:
            ticker: Ticker symbol
            
        Returns:
            Dictionary with asset information
        """
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            return {
                'symbol': ticker,
                'name': info.get('longName', ticker),
                'sector': info.get('sector', 'Unknown'),
                'industry': info.get('industry', 'Unknown'),
                'market_cap': info.get('marketCap'),
                'beta': info.get('beta'),
                'pe_ratio': info.get('trailingPE'),
                'dividend_yield': info.get('dividendYield'),
                '52_week_high': info.get('fiftyTwoWeekHigh'),
                '52_week_low': info.get('fiftyTwoWeekLow')
            }
            
        except Exception as e:
            logger.error(f"Failed to get info for {ticker}: {str(e)}")
            return {'symbol': ticker, 'error': str(e)}
    
    def calculate_correlation(
        self,
        prices: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Calculate correlation matrix from prices
        
        Args:
            prices: DataFrame of prices
            
        Returns:
            Correlation matrix
        """
        returns = prices.pct_change().dropna()
        return returns.corr()
    
    def detect_regime_change(
        self,
        prices: pd.DataFrame,
        window: int = 30
    ) -> pd.DataFrame:
        """
        Detect market regime changes using volatility clustering
        
        Args:
            prices: Price data
            window: Rolling window for volatility calculation
            
        Returns:
            DataFrame with regime indicators
        """
        try:
            returns = prices.pct_change().dropna()
            
            # Calculate rolling volatility
            rolling_vol = returns.rolling(window=window).std()
            
            # Calculate regime threshold (high vs low volatility)
            median_vol = rolling_vol.median(axis=1)
            high_vol_regime = (rolling_vol.T > median_vol * 1.5).T
            
            return high_vol_regime
            
        except Exception as e:
            logger.error(f"Regime detection failed: {str(e)}")
            raise
