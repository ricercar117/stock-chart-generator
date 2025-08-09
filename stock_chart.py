import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import webbrowser
import os
import math

# 銘柄と名前の定義
ticker = '9434.T'
ticker_name = 'ソフトバンク'

# データの取得
end_date = datetime.now()
start_date_full = end_date - timedelta(days=365 * 2) 

df = yf.download(ticker, start=start_date_full, end=end_date)

# 列名をPlotlyが認識できる形式にリネーム
try:
    df.columns = df.columns.droplevel(1)
except (AttributeError, KeyError):
    pass

column_mapping = {
    'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume',
    'Open': 'Open', 'High': 'High', 'Low': 'Low', 'Close': 'Close', 'Volume': 'Volume',
    ('Open',): 'Open', ('High',): 'High', ('Low',): 'Low', ('Close',): 'Close', ('Volume',): 'Volume',
}
df = df.rename(columns=column_mapping)
df = df[['Open', 'High', 'Low', 'Close', 'Volume']]

ema_windows = [5, 13, 25, 75, 130, 260]
for window in ema_windows:
    df[f'EMA{window}'] = df['Close'].ewm(span=window, adjust=False).mean()

def create_chart_traces(data):
    if data.empty:
        return None, None, None

    candlestick_trace = go.Candlestick(
        x=data.index,
        open=data['Open'],
        high=data['High'],
        low=data['Low'],
        close=data['Close'],
        showlegend=False
    )
    
    volume_trace = go.Bar(
        x=data.index,
        y=data['Volume'],
        marker_color='rgba(255, 255, 255, 0.5)',
        showlegend=False
    )
    
    ema_colors = ['blue', 'yellow', 'orange', 'green', 'purple', 'red']
    ema_traces = []
    ema_windows = [5, 13, 25, 75, 130, 260]
    
    for window, color in zip(ema_windows, ema_colors):
        ema_trace = go.Scatter(
            x=data.index, 
            y=data[f'EMA{window}'], 
            mode='lines', 
            line=dict(color=color), 
            showlegend=False,
            name=f'EMA{window}'
        )
        ema_traces.append(ema_trace)

    return candlestick_trace, ema_traces, volume_trace

candlestick_trace, ema_traces, volume_trace = create_chart_traces(df)

if all([candlestick_trace, ema_traces, volume_trace]):
    fig = make_subplots(
        rows=2, 
        cols=1, 
        shared_xaxes=True, 
        vertical_spacing=0.05, 
        row_heights=[0.7, 0.3]
    )

    fig.add_trace(candlestick_trace, row=1, col=1)
    for trace in ema_traces:
        fig.add_trace(trace, row=1, col=1)

    fig.add_trace(volume_trace, row=2, col=1)
    
    df_initial_view = df.loc[end_date - timedelta(days=180):]
    y_max_value = df_initial_view['High'].max() * 1.1 
    y_min_value = df_initial_view['Low'].min() * 0.9

    y_range_min = math.log10(y_min_value)
    y_range_max = math.log10(y_max_value)

    fig.update_layout(
        template='plotly_dark',
        height=700,
        showlegend=False,
        title_text=f"<b>{ticker} {ticker_name} - 日足</b>",
        xaxis_rangeslider_visible=False,
        yaxis=dict(
            title_text="株価",
            type="log",
            side="right",
            range=[y_range_min, y_range_max]
        ),
        # --- 修正箇所：rangeselectorをここに移動 ---
        xaxis=dict(
            rangebreaks=[dict(bounds=["sat", "mon"])],
            dtick="M1",
            tickformat="%d/%m",
            rangeselector=dict(
                buttons=list([
                    dict(count=1, label="1m", step="month", stepmode="backward"),
                    dict(count=6, label="6m", step="month", stepmode="backward"),
                    dict(count=1, label="1y", step="year", stepmode="backward"),
                    dict(step="all")
                ])
            )
        )
    )
    
    fig.update_yaxes(title_text="出来高", row=2, col=1, side="right")
    
    # --- update_xaxesからrangeselectorを削除 ---
    fig.update_xaxes(
        range=[end_date - timedelta(days=180), end_date]
    )

    folder_path = "D:\\VS code\\動的html"
    file_name = "stock_charts_day.html"
    file_path = os.path.join(folder_path, file_name)
    
    os.makedirs(folder_path, exist_ok=True)

    fig.write_html(
        file_path, 
        config={
            'displayModeBar': True,
            'modeBarButtonsToRemove': [
                'zoom2d', 'pan2d', 'select2d', 'lasso2d', 'autoscale', 'resetscale',
                'hoverclosest', 'hovercompare', 'togglehover', 'togglespikelines'
            ],
            'modeBarActiveColor': 'orange',
            'dragmode': 'zoom'
        }
    )

    try:
        webbrowser.open(file_path)
        print(f"チャートは {file_path} に保存され、ブラウザで開かれました。")
    except Exception as e:
        print(f"ブラウザを開く際にエラーが発生しました: {e}")
        print(f"ファイルは {file_path} に保存されました。手動で開いてください。")