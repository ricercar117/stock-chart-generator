import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import webbrowser
import os
import math
import json
import argparse
from typing import List, TypedDict

# Define the shape of our configuration objects for clarity and safety
class StockInfo(TypedDict):
    ticker: str
    name: str

class LayoutSettings(TypedDict):
    template: str
    height: int
    volume_bar_color: str

class ChartSettings(TypedDict):
    data_range_days: int
    ema_windows: List[int]
    ema_colors: List[str]
    layout_settings: LayoutSettings

def create_chart_traces(data, ema_windows, ema_colors, volume_bar_color):
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
        marker_color=volume_bar_color,
        showlegend=False
    )
    
    ema_traces = []
    
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

def generate_chart_for_stock(stock_info: StockInfo, chart_settings: ChartSettings):
    """
    単一の銘柄情報に基づいてチャートを生成・保存する
    :param stock_info: A dictionary containing the stock's ticker and name.
    :param chart_settings: A dictionary containing chart rendering settings.
    """
    ticker = stock_info['ticker']
    ticker_name = stock_info['name']
    ema_windows = chart_settings['ema_windows']
    ema_colors = chart_settings['ema_colors']
    data_range_days = chart_settings['data_range_days']
    layout_settings = chart_settings['layout_settings']
    
    # --- 2. データの取得 ---
    end_date = datetime.now()
    start_date_full = end_date - timedelta(days=data_range_days)

    print(f"'{ticker_name}' ({ticker}) のデータを取得しています...")
    df = yf.download(ticker, start=start_date_full, end=end_date)

    if df.empty:
        print(f"エラー: {ticker} のデータ取得に失敗しました。ティッカーが正しいか確認してください。")
        return # 次の銘柄へ

    # --- 3. データの前処理 ---
    try:
        # yfinanceのマルチレベルカラムをフラット化
        df.columns = df.columns.droplevel(1)
    except (AttributeError, KeyError):
        pass # 既にフラットな場合は何もしない

    column_mapping = {
        'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'
    }
    df = df.rename(columns={c: column_mapping.get(c.lower(), c) for c in df.columns})
    df = df[['Open', 'High', 'Low', 'Close', 'Volume']]

    for window in ema_windows:
        df[f'EMA{window}'] = df['Close'].ewm(span=window, adjust=False).mean()

    # --- 4. チャートの描画 ---
    candlestick_trace, ema_traces, volume_trace = create_chart_traces(df, ema_windows, ema_colors, layout_settings['volume_bar_color'])

    if all([candlestick_trace, ema_traces, volume_trace]):
        fig = make_subplots(
            rows=2, cols=1, shared_xaxes=True, 
            vertical_spacing=0.05, row_heights=[0.7, 0.3]
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
            template=layout_settings['template'], height=layout_settings['height'], showlegend=False,
            title_text=f"<b>{ticker} {ticker_name} - 日足</b>",
            xaxis_rangeslider_visible=False,
            yaxis=dict(title_text="株価", type="log", side="right", range=[y_range_min, y_range_max]),
            xaxis=dict(
                rangebreaks=[dict(bounds=["sat", "mon"])],
                dtick="M1", tickformat="%d/%m",
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
        fig.update_xaxes(range=[end_date - timedelta(days=180), end_date])

        # --- 5. ファイルの保存と表示 ---
        # スクリプトの場所を基準に出力先を決定
        script_dir = os.path.dirname(os.path.abspath(__file__))
        output_dir = os.path.join(script_dir, "charts")
        os.makedirs(output_dir, exist_ok=True)
        
        # ファイル名に銘柄コードを含めて一意にする
        file_name = f"{ticker}_{ticker_name}_chart.html"
        file_path = os.path.join(output_dir, file_name)

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
            # file://プロトコルを明示して、ブラウザで正しく開けるようにする
            webbrowser.open(f"file://{os.path.abspath(file_path)}")
            print(f"チャートは {file_path} に保存され、ブラウザで開かれました。")
        except Exception as e:
            print(f"ブラウザを開く際にエラーが発生しました: {e}")
            print(f"ファイルは {file_path} に保存されました。手動で開いてください。")

def main():
    """
    設定ファイルを読み込み、指定された全銘柄のチャートを生成する
    """
    parser = argparse.ArgumentParser(description="指定された銘柄の株価チャートを生成します。")
    parser.add_argument(
        "-t", "--ticker", 
        type=str, 
        help="config.json内の特定の銘柄コード（例: 9434.T）だけを生成します。"
    )
    args = parser.parse_args()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, 'config.json')

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except FileNotFoundError:
        print(f"エラー: 設定ファイルが見つかりません: {config_path}")
        return
    except json.JSONDecodeError:
        print(f"エラー: 設定ファイルの形式が正しくありません: {config_path}")
        return

    stocks_to_process = config.get('stocks_to_analyze', [])

    # コマンドライン引数でティッカーが指定された場合、リストをフィルタリング
    if args.ticker:
        stocks_to_process = [s for s in stocks_to_process if s['ticker'] == args.ticker]
        if not stocks_to_process:
            print(f"エラー: 指定されたティッカー '{args.ticker}' はconfig.jsonに見つかりません。")
            return

    for stock in stocks_to_process:
        generate_chart_for_stock(stock, config.get('chart_settings', {}))

if __name__ == "__main__":
    main()