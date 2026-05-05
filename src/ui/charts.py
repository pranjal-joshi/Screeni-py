"""
Plotly chart utilities for Screeni-py Streamlit UI.
Provides OHLC candlestick charts, RSI panels, and screening summary charts.
"""
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np


def plot_ohlc_chart(df: pd.DataFrame, stock_name: str) -> go.Figure:
    """
    Candlestick chart with volume subplot and SMA/EMA overlays.
    
    Args:
        df: OHLCV DataFrame with columns: Open, High, Low, Close, Volume
            Optionally: SMA (50-day), LMA (200-day), RSI
        stock_name: Display name for the chart title
        
    Returns:
        Plotly Figure object
    """
    # Reverse if needed (some screener data is most-recent-first)
    if not df.empty and df.index[0] > df.index[-1] if hasattr(df.index[0], '__gt__') else False:
        df = df[::-1]

    # Build subplot layout: candlestick + volume
    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        row_heights=[0.75, 0.25],
        subplot_titles=[f"{stock_name} — OHLC", "Volume"],
    )

    # Candlestick chart
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df['Open'],
            high=df['High'],
            low=df['Low'],
            close=df['Close'],
            name='Price',
            increasing_line_color='#26a69a',
            decreasing_line_color='#ef5350',
        ),
        row=1, col=1,
    )

    # SMA overlay (50-day)
    if 'SMA' in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df['SMA'],
                mode='lines',
                name='SMA 50',
                line=dict(color='#2196f3', width=1.5),
            ),
            row=1, col=1,
        )

    # LMA overlay (200-day)
    if 'LMA' in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df['LMA'],
                mode='lines',
                name='SMA 200',
                line=dict(color='#ff9800', width=1.5),
            ),
            row=1, col=1,
        )

    # Volume bars
    if 'Volume' in df.columns:
        colors = ['#26a69a' if c >= o else '#ef5350'
                  for c, o in zip(df['Close'], df['Open'])]
        fig.add_trace(
            go.Bar(
                x=df.index,
                y=df['Volume'],
                name='Volume',
                marker_color=colors,
                opacity=0.7,
            ),
            row=2, col=1,
        )

        # Volume MA
        if 'VolMA' in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=df['VolMA'],
                    mode='lines',
                    name='Vol MA 20',
                    line=dict(color='#9c27b0', width=1.5),
                ),
                row=2, col=1,
            )

    fig.update_layout(
        title=f"{stock_name} — Technical Analysis",
        xaxis_rangeslider_visible=False,
        template='plotly_dark',
        height=600,
        showlegend=True,
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
    )
    fig.update_xaxes(showgrid=True, gridwidth=0.5, gridcolor='rgba(128,128,128,0.2)')
    fig.update_yaxes(showgrid=True, gridwidth=0.5, gridcolor='rgba(128,128,128,0.2)')

    return fig


def plot_rsi_chart(df: pd.DataFrame, stock_name: str) -> go.Figure:
    """
    RSI indicator panel (14-period) with overbought/oversold zones.
    
    Args:
        df: DataFrame with 'RSI' column (computed by screener preprocessData)
        stock_name: Display name for the chart title
        
    Returns:
        Plotly Figure object
    """
    fig = go.Figure()

    if 'RSI' not in df.columns:
        fig.add_annotation(
            text="RSI data not available",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
        )
        return fig

    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df['RSI'],
            mode='lines',
            name='RSI (14)',
            line=dict(color='#00bcd4', width=2),
        )
    )

    # Overbought line
    fig.add_hline(y=70, line_dash='dash', line_color='#ef5350', annotation_text='Overbought (70)')
    # Midline
    fig.add_hline(y=50, line_dash='dot', line_color='#9e9e9e', annotation_text='50')
    # Oversold line
    fig.add_hline(y=30, line_dash='dash', line_color='#26a69a', annotation_text='Oversold (30)')

    # Fill overbought/oversold regions
    fig.add_hrect(y0=70, y1=100, fillcolor='rgba(239,83,80,0.1)', line_width=0)
    fig.add_hrect(y0=0, y1=30, fillcolor='rgba(38,166,154,0.1)', line_width=0)

    fig.update_layout(
        title=f"{stock_name} — RSI (14)",
        template='plotly_dark',
        height=300,
        yaxis=dict(range=[0, 100], title='RSI'),
        showlegend=True,
    )

    return fig


def plot_screening_summary(results_df: pd.DataFrame) -> go.Figure:
    """
    Bar chart summary of screened results by sector or pattern criteria.
    Shows distribution of stocks by key metrics.
    
    Args:
        results_df: DataFrame of screening results (from Screener)
        
    Returns:
        Plotly Figure object
    """
    fig = go.Figure()

    if results_df is None or results_df.empty:
        fig.add_annotation(
            text="No screening results to display",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16),
        )
        fig.update_layout(template='plotly_dark', height=300)
        return fig

    # Try to show trend distribution
    if 'Trend (30Days)' in results_df.columns or any('Trend' in c for c in results_df.columns):
        trend_col = next((c for c in results_df.columns if 'Trend' in c), None)
        if trend_col:
            # Clean ANSI color codes for display
            trend_clean = results_df[trend_col].astype(str).str.replace(r'\x1b\[[0-9;]*m', '', regex=True)
            trend_counts = trend_clean.value_counts().reset_index()
            trend_counts.columns = ['Trend', 'Count']

            fig.add_trace(
                go.Bar(
                    x=trend_counts['Trend'],
                    y=trend_counts['Count'],
                    name='Trend Distribution',
                    marker_color='#2196f3',
                )
            )
            fig.update_layout(
                title="Screened Stocks — Trend Distribution",
                template='plotly_dark',
                height=350,
                xaxis_title='Trend',
                yaxis_title='Stock Count',
            )
            return fig

    # Fallback: just show count
    fig.add_trace(
        go.Bar(
            x=['Total Matches'],
            y=[len(results_df)],
            marker_color='#26a69a',
            name='Stocks Found',
        )
    )
    fig.update_layout(
        title=f"Screening Results: {len(results_df)} stocks found",
        template='plotly_dark',
        height=300,
    )
    return fig
