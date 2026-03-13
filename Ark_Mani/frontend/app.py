import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import requests
from datetime import datetime, timedelta
import json
import os

# Configuration
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# Page config
st.set_page_config(
    page_title="Portfolio Risk Assessment",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 0.5rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .risk-high {
        color: #d62728;
        font-weight: bold;
    }
    .risk-medium {
        color: #ff7f0e;
        font-weight: bold;
    }
    .risk-low {
        color: #2ca02c;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'portfolio_data' not in st.session_state:
    st.session_state.portfolio_data = None
if 'analysis_results' not in st.session_state:
    st.session_state.analysis_results = None
if 'scenario_history' not in st.session_state:
    st.session_state.scenario_history = []

# Sidebar
with st.sidebar:
    st.image("https://via.placeholder.com/150x50/1f77b4/ffffff?text=Portfolio+Risk", use_container_width=True)
    st.markdown("### Navigation")
    page = st.radio(
        "Select Page",
        ["Portfolio Input", "Risk Analysis", "Optimization", "Scenario Testing", "Reports"],
        label_visibility="collapsed"
    )
    
    st.markdown("---")
    st.markdown("### Settings")
    confidence_level = st.selectbox("VaR Confidence Level", [0.90, 0.95, 0.99], index=1)
    simulation_paths = st.number_input("Monte Carlo Paths", min_value=1000, max_value=100000, value=10000, step=1000)
    time_horizon = st.number_input("Time Horizon (days)", min_value=1, max_value=365, value=252)
    
    st.markdown("---")
    st.markdown("### About")
    st.info("AI-powered portfolio risk assessment using LLMs and advanced quantitative methods.")

# Helper functions
def call_backend(endpoint, method="GET", data=None, files=None):
    """Make API calls to backend"""
    url = f"{BACKEND_URL}/{endpoint}"
    try:
        if method == "GET":
            response = requests.get(url, params=data)
        elif method == "POST":
            if files:
                response = requests.post(url, files=files, data=data)
            else:
                response = requests.post(url, json=data)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"API Error: {str(e)}")
        return None

def create_portfolio_composition_chart(portfolio_df):
    """Create portfolio composition pie chart"""
    fig = px.pie(
        portfolio_df,
        values='weight',
        names='ticker',
        title='Portfolio Composition',
        color_discrete_sequence=px.colors.qualitative.Set3
    )
    fig.update_traces(textposition='inside', textinfo='percent+label')
    return fig

def create_risk_metrics_chart(metrics):
    """Create risk metrics bar chart"""
    fig = go.Figure()
    
    metric_names = ['VaR 95%', 'CVaR 95%', 'Max Drawdown', 'Volatility']
    metric_values = [
        abs(metrics.get('var_95', 0)) * 100,
        abs(metrics.get('cvar_95', 0)) * 100,
        abs(metrics.get('max_drawdown', 0)) * 100,
        metrics.get('volatility', 0) * 100
    ]
    
    colors = ['#d62728', '#ff7f0e', '#ff9896', '#ffbb78']
    
    fig.add_trace(go.Bar(
        x=metric_names,
        y=metric_values,
        marker_color=colors,
        text=[f'{v:.2f}%' for v in metric_values],
        textposition='auto',
    ))
    
    fig.update_layout(
        title='Risk Metrics Overview',
        yaxis_title='Value (%)',
        showlegend=False,
        height=400
    )
    
    return fig

def create_monte_carlo_chart(simulation_results):
    """Create Monte Carlo simulation visualization"""
    fig = go.Figure()
    
    # Plot multiple paths
    for i, path in enumerate(simulation_results['paths'][:100]):
        fig.add_trace(go.Scatter(
            y=path,
            mode='lines',
            line=dict(width=0.5, color='rgba(100,100,100,0.1)'),
            showlegend=False,
            hoverinfo='skip'
        ))
    
    # Add mean path
    mean_path = simulation_results['mean_path']
    fig.add_trace(go.Scatter(
        y=mean_path,
        mode='lines',
        name='Mean Path',
        line=dict(width=3, color='blue')
    ))
    
    # Add confidence intervals
    upper_ci = simulation_results['upper_ci']
    lower_ci = simulation_results['lower_ci']
    
    fig.add_trace(go.Scatter(
        y=upper_ci,
        mode='lines',
        name='95% CI Upper',
        line=dict(width=2, color='green', dash='dash')
    ))
    
    fig.add_trace(go.Scatter(
        y=lower_ci,
        mode='lines',
        name='95% CI Lower',
        line=dict(width=2, color='red', dash='dash')
    ))
    
    fig.update_layout(
        title='Monte Carlo Simulation - Portfolio Value Paths',
        xaxis_title='Time (days)',
        yaxis_title='Portfolio Value',
        height=500,
        hovermode='x unified'
    )
    
    return fig

# Page 1: Portfolio Input
if page == "Portfolio Input":
    st.markdown('<p class="main-header">Portfolio Input</p>', unsafe_allow_html=True)
    
    tab1, tab2, tab3 = st.tabs(["Upload CSV", "Manual Entry", "Sample Portfolio"])
    
    with tab1:
        st.markdown("### Upload Portfolio Data")
        st.markdown("Upload a CSV file with columns: `ticker`, `weight`, `asset_class`")
        
        uploaded_file = st.file_uploader("Choose a CSV file", type=['csv'])
        
        if uploaded_file:
            try:
                portfolio_df = pd.read_csv(uploaded_file)
                
                # Validate columns
                required_cols = ['ticker', 'weight', 'asset_class']
                if all(col in portfolio_df.columns for col in required_cols):
                    # Normalize weights
                    total_weight = portfolio_df['weight'].sum()
                    if abs(total_weight - 1.0) > 0.01:
                        st.warning(f"Weights sum to {total_weight:.2f}. Normalizing to 1.0...")
                        portfolio_df['weight'] = portfolio_df['weight'] / total_weight
                    
                    st.session_state.portfolio_data = portfolio_df
                    st.success(f"Portfolio loaded successfully! {len(portfolio_df)} assets")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.dataframe(portfolio_df, use_container_width=True)
                    with col2:
                        st.plotly_chart(create_portfolio_composition_chart(portfolio_df), use_container_width=True)
                else:
                    st.error(f"Missing required columns. Found: {list(portfolio_df.columns)}")
            except Exception as e:
                st.error(f"Error reading file: {str(e)}")
    
    with tab2:
        st.markdown("### Manual Portfolio Entry")
        
        num_assets = st.number_input("Number of assets", min_value=1, max_value=50, value=5)
        
        manual_data = []
        for i in range(num_assets):
            col1, col2, col3 = st.columns(3)
            with col1:
                ticker = st.text_input(f"Asset {i+1} Ticker", value=f"STOCK{i+1}", key=f"ticker_{i}")
            with col2:
                weight = st.number_input(f"Weight", min_value=0.0, max_value=1.0, value=1/num_assets, key=f"weight_{i}")
            with col3:
                asset_class = st.selectbox(f"Asset Class", ["stock", "bond", "crypto", "commodity"], key=f"class_{i}")
            
            manual_data.append({"ticker": ticker, "weight": weight, "asset_class": asset_class})
        
        if st.button("Create Portfolio"):
            portfolio_df = pd.DataFrame(manual_data)
            # Normalize weights
            portfolio_df['weight'] = portfolio_df['weight'] / portfolio_df['weight'].sum()
            st.session_state.portfolio_data = portfolio_df
            st.success(" Portfolio created!")
            st.dataframe(portfolio_df)
    
    with tab3:
        st.markdown("### Sample Portfolio")
        st.markdown("Load a pre-configured sample portfolio for testing")
        
        sample_portfolios = {
            "Balanced": pd.DataFrame({
                'ticker': ['SPY', 'AGG', 'GLD', 'VNQ', 'BTC-USD'],
                'weight': [0.40, 0.30, 0.15, 0.10, 0.05],
                'asset_class': ['stock', 'bond', 'commodity', 'stock', 'crypto']
            }),
            "Aggressive Growth": pd.DataFrame({
                'ticker': ['QQQ', 'ARKK', 'TSLA', 'NVDA', 'ETH-USD'],
                'weight': [0.30, 0.25, 0.20, 0.15, 0.10],
                'asset_class': ['stock', 'stock', 'stock', 'stock', 'crypto']
            }),
            "Conservative": pd.DataFrame({
                'ticker': ['AGG', 'BND', 'TLT', 'GLD', 'SPY'],
                'weight': [0.40, 0.30, 0.15, 0.10, 0.05],
                'asset_class': ['bond', 'bond', 'bond', 'commodity', 'stock']
            })
        }
        
        selected_sample = st.selectbox("Select Sample Portfolio", list(sample_portfolios.keys()))
        
        if st.button("Load Sample"):
            st.session_state.portfolio_data = sample_portfolios[selected_sample]
            st.success(f" Loaded {selected_sample} portfolio!")
            
            col1, col2 = st.columns(2)
            with col1:
                st.dataframe(st.session_state.portfolio_data)
            with col2:
                st.plotly_chart(create_portfolio_composition_chart(st.session_state.portfolio_data), use_container_width=True)

# Page 2: Risk Analysis
elif page == "Risk Analysis":
    st.markdown('<p class="main-header">Risk Analysis</p>', unsafe_allow_html=True)
    
    if st.session_state.portfolio_data is None:
        st.warning(" Please upload or create a portfolio first!")
        st.stop()
    
    st.markdown("### Current Portfolio")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Assets", len(st.session_state.portfolio_data))
    with col2:
        asset_classes = st.session_state.portfolio_data['asset_class'].nunique()
        st.metric("Asset Classes", asset_classes)
    with col3:
        st.metric("Total Weight", f"{st.session_state.portfolio_data['weight'].sum():.2%}")
    
    if st.button(" Run Risk Analysis", type="primary"):
        with st.spinner("Fetching market data and running simulations..."):
            # Call backend API
            analysis_data = {
                "portfolio": st.session_state.portfolio_data.to_dict('records'),
                "confidence_level": confidence_level,
                "simulation_paths": simulation_paths,
                "time_horizon": time_horizon
            }
            
            results = call_backend("api/v1/analyze", method="POST", data=analysis_data)
            
            if results:
                st.session_state.analysis_results = results
                st.success(" Analysis complete!")
    
    if st.session_state.analysis_results:
        results = st.session_state.analysis_results
        
        st.markdown("---")
        st.markdown("### Risk Metrics")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            var_95 = results.get('risk_metrics', {}).get('var_95', 0)
            st.metric(
                "VaR (95%)",
                f"{abs(var_95):.2%}",
                delta=f"{var_95:.2%}",
                delta_color="inverse"
            )
        
        with col2:
            cvar_95 = results.get('risk_metrics', {}).get('cvar_95', 0)
            st.metric(
                "CVaR (95%)",
                f"{abs(cvar_95):.2%}",
                delta=f"{cvar_95:.2%}",
                delta_color="inverse"
            )
        
        with col3:
            sharpe = results.get('risk_metrics', {}).get('sharpe_ratio', 0)
            st.metric(
                "Sharpe Ratio",
                f"{sharpe:.2f}",
                delta="Good" if sharpe > 1 else "Poor"
            )
        
        with col4:
            max_dd = results.get('risk_metrics', {}).get('max_drawdown', 0)
            st.metric(
                "Max Drawdown",
                f"{abs(max_dd):.2%}",
                delta=f"{max_dd:.2%}",
                delta_color="inverse"
            )
        
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.plotly_chart(create_risk_metrics_chart(results.get('risk_metrics', {})), use_container_width=True)
        
        with col2:
            # Correlation matrix
            if 'correlation_matrix' in results:
                corr_df = pd.DataFrame(results['correlation_matrix'])
                fig = px.imshow(
                    corr_df,
                    title='Asset Correlation Matrix',
                    color_continuous_scale='RdBu_r',
                    aspect='auto'
                )
                st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("---")
        st.markdown("### Monte Carlo Simulation Results")
        
        if 'simulation_results' in results:
            st.plotly_chart(create_monte_carlo_chart(results['simulation_results']), use_container_width=True)
            
            # Distribution of returns
            returns = results['simulation_results'].get('final_returns', [])
            fig = go.Figure()
            fig.add_trace(go.Histogram(x=returns, nbinsx=50, name='Return Distribution'))
            fig.update_layout(
                title='Distribution of Simulated Returns',
                xaxis_title='Return (%)',
                yaxis_title='Frequency',
                height=400
            )
            st.plotly_chart(fig, use_container_width=True)

# Page 3: Optimization
elif page == "Optimization":
    st.markdown('<p class="main-header">Portfolio Optimization</p>', unsafe_allow_html=True)
    
    if st.session_state.portfolio_data is None:
        st.warning(" Please upload or create a portfolio first!")
        st.stop()
    
    st.markdown("### Optimization Objectives")
    
    col1, col2 = st.columns(2)
    
    with col1:
        objective = st.selectbox(
            "Select Objective",
            ["Minimize Variance", "Maximize Sharpe Ratio", "Risk Parity", "Custom"]
        )
        
        st.markdown("### Constraints")
        max_weight = st.slider("Maximum Asset Weight", 0.0, 1.0, 0.4)
        min_weight = st.slider("Minimum Asset Weight", 0.0, 0.5, 0.0)
        target_return = st.number_input("Target Return (annual %)", 0.0, 50.0, 10.0) / 100
    
    with col2:
        st.markdown("### Sector Constraints")
        sector_limits = {}
        for asset_class in st.session_state.portfolio_data['asset_class'].unique():
            limit = st.slider(f"Max {asset_class} allocation", 0.0, 1.0, 0.6, key=f"sector_{asset_class}")
            sector_limits[asset_class] = limit
    
    if st.button(" Optimize Portfolio", type="primary"):
        with st.spinner("Running optimization..."):
            optimization_data = {
                "portfolio": st.session_state.portfolio_data.to_dict('records'),
                "objective": objective,
                "constraints": {
                    "max_weight": max_weight,
                    "min_weight": min_weight,
                    "target_return": target_return,
                    "sector_limits": sector_limits
                }
            }
            
            results = call_backend("api/v1/optimize", method="POST", data=optimization_data)
            
            if results:
                st.success(" Optimization complete!")
                
                # Compare original vs optimized
                st.markdown("### Results Comparison")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("#### Original Portfolio")
                    st.dataframe(st.session_state.portfolio_data)
                    
                    orig_metrics = results.get('original_metrics', {})
                    st.metric("Expected Return", f"{orig_metrics.get('return', 0):.2%}")
                    st.metric("Volatility", f"{orig_metrics.get('volatility', 0):.2%}")
                    st.metric("Sharpe Ratio", f"{orig_metrics.get('sharpe', 0):.2f}")
                
                with col2:
                    st.markdown("#### Optimized Portfolio")
                    optimized_df = pd.DataFrame(results.get('optimized_weights', []))
                    st.dataframe(optimized_df)
                    
                    opt_metrics = results.get('optimized_metrics', {})
                    st.metric("Expected Return", f"{opt_metrics.get('return', 0):.2%}")
                    st.metric("Volatility", f"{opt_metrics.get('volatility', 0):.2%}")
                    st.metric("Sharpe Ratio", f"{opt_metrics.get('sharpe', 0):.2f}")
                
                # Efficient frontier
                if 'efficient_frontier' in results:
                    fig = go.Figure()
                    
                    frontier = results['efficient_frontier']
                    fig.add_trace(go.Scatter(
                        x=frontier['volatility'],
                        y=frontier['returns'],
                        mode='lines',
                        name='Efficient Frontier',
                        line=dict(color='blue', width=2)
                    ))
                    
                    # Original portfolio
                    fig.add_trace(go.Scatter(
                        x=[orig_metrics.get('volatility', 0)],
                        y=[orig_metrics.get('return', 0)],
                        mode='markers',
                        name='Original',
                        marker=dict(size=15, color='red', symbol='circle')
                    ))
                    
                    # Optimized portfolio
                    fig.add_trace(go.Scatter(
                        x=[opt_metrics.get('volatility', 0)],
                        y=[opt_metrics.get('return', 0)],
                        mode='markers',
                        name='Optimized',
                        marker=dict(size=15, color='green', symbol='star')
                    ))
                    
                    fig.update_layout(
                        title='Efficient Frontier',
                        xaxis_title='Volatility (Risk)',
                        yaxis_title='Expected Return',
                        height=500
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)

# Page 4: Scenario Testing
elif page == "Scenario Testing":
    st.markdown('<p class="main-header">Scenario Testing</p>', unsafe_allow_html=True)
    
    if st.session_state.portfolio_data is None:
        st.warning(" Please upload or create a portfolio first!")
        st.stop()
    
    st.markdown("### AI-Powered Scenario Generation")
    st.markdown("Use natural language to describe market scenarios. The LLM will interpret and simulate the impact.")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        scenario_prompt = st.text_area(
            "Describe your scenario",
            placeholder="Example: What if interest rates rise by 2% and tech stocks drop 20%?",
            height=100
        )
        
        st.markdown("#### Or select a pre-defined scenario:")
        preset_scenarios = {
            "Recession": "Model a recession with 30% equity decline, 10% increase in bonds",
            "Tech Crash": "Simulate a 40% decline in technology sector stocks",
            "Interest Rate Hike": "Model impact of 2% interest rate increase",
            "Inflation Spike": "Simulate 5% inflation with commodity price surge",
            "Market Rally": "Model a bull market with 25% equity gains"
        }
        
        selected_preset = st.selectbox("Choose preset", ["Custom"] + list(preset_scenarios.keys()))
        
        if selected_preset != "Custom":
            scenario_prompt = preset_scenarios[selected_preset]
    
    with col2:
        st.markdown("#### Scenario Parameters")
        severity = st.slider("Severity", 0.5, 2.0, 1.0, 0.1)
        duration = st.number_input("Duration (days)", 30, 365, 90)
    
    if st.button(" Run Scenario Analysis", type="primary"):
        with st.spinner("AI is interpreting your scenario and running simulations..."):
            scenario_data = {
                "portfolio": st.session_state.portfolio_data.to_dict('records'),
                "scenario_description": scenario_prompt,
                "severity": severity,
                "duration": duration,
                "simulation_paths": simulation_paths
            }
            
            results = call_backend("api/v1/scenario/analyze", method="POST", data=scenario_data)
            
            if results:
                st.success(" Scenario analysis complete!")
                
                # Add to history
                st.session_state.scenario_history.append({
                    "timestamp": datetime.now(),
                    "description": scenario_prompt,
                    "results": results
                })
                
                st.markdown("---")
                st.markdown("### AI Interpretation")
                st.info(results.get('llm_interpretation', 'No interpretation available'))
                
                st.markdown("### Impact Analysis")
                
                col1, col2, col3, col4 = st.columns(4)
                
                impact = results.get('impact_metrics', {})
                
                with col1:
                    st.metric("Expected Loss", f"{abs(impact.get('expected_loss', 0)):.2%}")
                with col2:
                    st.metric("Worst Case Loss", f"{abs(impact.get('worst_case', 0)):.2%}")
                with col3:
                    st.metric("Probability of Loss > 10%", f"{impact.get('prob_large_loss', 0):.1%}")
                with col4:
                    st.metric("Recovery Time", f"{impact.get('recovery_days', 0):.0f} days")
                
                # Simulation paths under scenario
                if 'scenario_paths' in results:
                    fig = go.Figure()
                    
                    for path in results['scenario_paths'][:50]:
                        fig.add_trace(go.Scatter(
                            y=path,
                            mode='lines',
                            line=dict(width=0.5, color='rgba(200,100,100,0.2)'),
                            showlegend=False
                        ))
                    
                    fig.update_layout(
                        title='Portfolio Value Under Scenario',
                        xaxis_title='Days',
                        yaxis_title='Portfolio Value',
                        height=400
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                
                # Asset-level impact
                if 'asset_impact' in results:
                    st.markdown("### Asset-Level Impact")
                    impact_df = pd.DataFrame(results['asset_impact'])
                    
                    fig = px.bar(
                        impact_df,
                        x='ticker',
                        y='impact',
                        color='impact',
                        title='Impact by Asset',
                        color_continuous_scale='RdYlGn_r'
                    )
                    st.plotly_chart(fig, use_container_width=True)
    
    # Scenario history
    if st.session_state.scenario_history:
        st.markdown("---")
        st.markdown("### Scenario History")
        
        for idx, scenario in enumerate(reversed(st.session_state.scenario_history[-5:])):
            with st.expander(f" {scenario['timestamp'].strftime('%Y-%m-%d %H:%M')} - {scenario['description'][:50]}..."):
                st.write(f"**Description:** {scenario['description']}")
                impact = scenario['results'].get('impact_metrics', {})
                st.write(f"**Expected Loss:** {abs(impact.get('expected_loss', 0)):.2%}")
                st.write(f"**Worst Case:** {abs(impact.get('worst_case', 0)):.2%}")

# Page 5: Reports
elif page == "Reports":
    st.markdown('<p class="main-header">Reports & Export</p>', unsafe_allow_html=True)
    
    if st.session_state.analysis_results is None:
        st.warning(" Please run a risk analysis first!")
        st.stop()
    
    st.markdown("### Generate Reports")
    
    col1, col2 = st.columns(2)
    
    with col1:
        report_type = st.selectbox(
            "Report Type",
            ["Comprehensive Risk Report", "Executive Summary", "Optimization Report", "Scenario Analysis"]
        )
        
        include_charts = st.checkbox("Include Charts", value=True)
        include_raw_data = st.checkbox("Include Raw Data", value=False)
    
    with col2:
        export_format = st.selectbox("Export Format", ["PDF", "Excel", "JSON"])
        
        if st.button(" Generate Report", type="primary"):
            with st.spinner("Generating report..."):
                report_data = {
                    "portfolio": st.session_state.portfolio_data.to_dict('records'),
                    "analysis_results": st.session_state.analysis_results,
                    "report_type": report_type,
                    "include_charts": include_charts,
                    "include_raw_data": include_raw_data,
                    "format": export_format
                }
                
                response = call_backend("api/v1/reports/generate", method="POST", data=report_data)
                
                if response:
                    st.success(" Report generated successfully!")
                    
                    # Download button
                    report_url = response.get('download_url')
                    if report_url:
                        st.download_button(
                            label=f" Download {export_format} Report",
                            data=response.get('file_content', ''),
                            file_name=f"portfolio_report_{datetime.now().strftime('%Y%m%d')}.{export_format.lower()}",
                            mime=f"application/{export_format.lower()}"
                        )
    
    st.markdown("---")
    st.markdown("### Quick Metrics Summary")
    
    if st.session_state.analysis_results:
        metrics = st.session_state.analysis_results.get('risk_metrics', {})
        
        summary_df = pd.DataFrame({
            'Metric': ['VaR 95%', 'CVaR 95%', 'Sharpe Ratio', 'Max Drawdown', 'Volatility'],
            'Value': [
                f"{abs(metrics.get('var_95', 0)):.2%}",
                f"{abs(metrics.get('cvar_95', 0)):.2%}",
                f"{metrics.get('sharpe_ratio', 0):.2f}",
                f"{abs(metrics.get('max_drawdown', 0)):.2%}",
                f"{metrics.get('volatility', 0):.2%}"
            ]
        })
        
        st.dataframe(summary_df, use_container_width=True, hide_index=True)

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #666;'>
        <p>Automated Risk Assessment Tool | Powered by AI & Kubernetes</p>
        <p> This tool is for educational purposes. Not financial advice.</p>
    </div>
    """,
    unsafe_allow_html=True
)
