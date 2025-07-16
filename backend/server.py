from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timedelta
import yfinance as yf
import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
from tensorflow.keras.callbacks import EarlyStopping
import ta
import json
import asyncio
from concurrent.futures import ThreadPoolExecutor
import warnings
warnings.filterwarnings('ignore')

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Thread pool for ML operations
executor = ThreadPoolExecutor(max_workers=4)

# Define Models
class StockRequest(BaseModel):
    symbol: str
    period: str = "5y"  # Default to 5 years
    prediction_days: int = 30

class StockPrediction(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    symbol: str
    predictions: List[float]
    actual_prices: List[float]
    dates: List[str]
    prediction_dates: List[str]
    metrics: Dict[str, float]
    indicators: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class StockAnalysis(BaseModel):
    symbol: str
    current_price: float
    change: float
    change_percent: float
    volume: int
    market_cap: Optional[float] = None
    pe_ratio: Optional[float] = None
    moving_averages: Dict[str, float]
    rsi: float
    recommendation: str

# Stock data processing functions
def fetch_stock_data(symbol: str, period: str = "5y"):
    """Fetch stock data from Yahoo Finance"""
    try:
        ticker = yf.Ticker(symbol)
        data = ticker.history(period=period)
        info = ticker.info
        
        if data.empty:
            raise ValueError(f"No data found for symbol {symbol}")
        
        return data, info
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error fetching data for {symbol}: {str(e)}")

def add_technical_indicators(data):
    """Add technical indicators to the data"""
    # Moving averages
    data['MA_10'] = data['Close'].rolling(window=10).mean()
    data['MA_50'] = data['Close'].rolling(window=50).mean()
    data['MA_200'] = data['Close'].rolling(window=200).mean()
    
    # RSI
    data['RSI'] = ta.momentum.rsi(data['Close'], window=14)
    
    # MACD
    macd = ta.trend.MACD(data['Close'])
    data['MACD'] = macd.macd()
    data['MACD_signal'] = macd.macd_signal()
    data['MACD_histogram'] = macd.macd_diff()
    
    # Bollinger Bands
    bollinger = ta.volatility.BollingerBands(data['Close'])
    data['BB_upper'] = bollinger.bollinger_hband()
    data['BB_middle'] = bollinger.bollinger_mavg()
    data['BB_lower'] = bollinger.bollinger_lband()
    
    return data

def create_sequences(data, sequence_length=60):
    """Create sequences for LSTM training"""
    sequences = []
    targets = []
    
    for i in range(sequence_length, len(data)):
        sequences.append(data[i-sequence_length:i])
        targets.append(data[i])
    
    return np.array(sequences), np.array(targets)

def build_lstm_model(input_shape):
    """Build LSTM model for stock prediction"""
    model = Sequential([
        LSTM(50, return_sequences=True, input_shape=input_shape),
        Dropout(0.2),
        LSTM(50, return_sequences=True),
        Dropout(0.2),
        LSTM(50),
        Dropout(0.2),
        Dense(25),
        Dense(1)
    ])
    
    model.compile(optimizer='adam', loss='mean_squared_error')
    return model

def train_and_predict(symbol: str, period: str = "5y", prediction_days: int = 30):
    """Train LSTM model and make predictions"""
    try:
        # Fetch data
        data, info = fetch_stock_data(symbol, period)
        
        # Add technical indicators
        data = add_technical_indicators(data)
        
        # Prepare data for LSTM
        price_data = data['Close'].values.reshape(-1, 1)
        
        # Scale the data
        scaler = MinMaxScaler(feature_range=(0, 1))
        scaled_data = scaler.fit_transform(price_data)
        
        # Create sequences
        sequence_length = 60
        X, y = create_sequences(scaled_data, sequence_length)
        
        # Split data
        split_ratio = 0.8
        split_index = int(len(X) * split_ratio)
        X_train, X_test = X[:split_index], X[split_index:]
        y_train, y_test = y[:split_index], y[split_index:]
        
        # Build and train model
        model = build_lstm_model((X_train.shape[1], 1))
        
        early_stopping = EarlyStopping(monitor='loss', patience=10, restore_best_weights=True)
        model.fit(X_train, y_train, epochs=50, batch_size=32, 
                 callbacks=[early_stopping], verbose=0)
        
        # Make predictions on test set
        test_predictions = model.predict(X_test)
        test_predictions = scaler.inverse_transform(test_predictions)
        actual_test_prices = scaler.inverse_transform(y_test.reshape(-1, 1))
        
        # Calculate metrics
        mse = mean_squared_error(actual_test_prices, test_predictions)
        mae = mean_absolute_error(actual_test_prices, test_predictions)
        rmse = np.sqrt(mse)
        
        # Make future predictions
        last_sequence = scaled_data[-sequence_length:]
        future_predictions = []
        
        for _ in range(prediction_days):
            prediction = model.predict(last_sequence.reshape(1, sequence_length, 1), verbose=0)
            future_predictions.append(prediction[0, 0])
            last_sequence = np.append(last_sequence[1:], prediction[0, 0])
        
        # Inverse transform future predictions
        future_predictions = scaler.inverse_transform(np.array(future_predictions).reshape(-1, 1))
        future_predictions = future_predictions.flatten().tolist()
        
        # Get recent actual prices for comparison
        recent_prices = data['Close'].tail(60).values.tolist()
        recent_dates = data.index[-60:].strftime('%Y-%m-%d').tolist()
        
        # Generate future dates
        last_date = data.index[-1]
        future_dates = []
        for i in range(1, prediction_days + 1):
            future_date = last_date + timedelta(days=i)
            # Skip weekends (assuming markets are closed)
            while future_date.weekday() >= 5:
                future_date += timedelta(days=1)
            future_dates.append(future_date.strftime('%Y-%m-%d'))
        
        # Get current indicators
        current_indicators = {
            'ma_10': float(data['MA_10'].iloc[-1]) if not pd.isna(data['MA_10'].iloc[-1]) else 0,
            'ma_50': float(data['MA_50'].iloc[-1]) if not pd.isna(data['MA_50'].iloc[-1]) else 0,
            'ma_200': float(data['MA_200'].iloc[-1]) if not pd.isna(data['MA_200'].iloc[-1]) else 0,
            'rsi': float(data['RSI'].iloc[-1]) if not pd.isna(data['RSI'].iloc[-1]) else 50,
            'macd': float(data['MACD'].iloc[-1]) if not pd.isna(data['MACD'].iloc[-1]) else 0,
            'bb_upper': float(data['BB_upper'].iloc[-1]) if not pd.isna(data['BB_upper'].iloc[-1]) else 0,
            'bb_lower': float(data['BB_lower'].iloc[-1]) if not pd.isna(data['BB_lower'].iloc[-1]) else 0,
            'volume': int(data['Volume'].iloc[-1]),
            'current_price': float(data['Close'].iloc[-1])
        }
        
        return {
            'symbol': symbol,
            'predictions': future_predictions,
            'actual_prices': recent_prices,
            'dates': recent_dates,
            'prediction_dates': future_dates,
            'metrics': {
                'mse': float(mse),
                'mae': float(mae),
                'rmse': float(rmse),
                'accuracy': float(max(0, 100 - (mae / np.mean(actual_test_prices) * 100)))
            },
            'indicators': current_indicators,
            'info': {
                'market_cap': info.get('marketCap'),
                'pe_ratio': info.get('trailingPE'),
                'company_name': info.get('longName', symbol)
            }
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in prediction: {str(e)}")

def get_stock_analysis(symbol: str):
    """Get current stock analysis"""
    try:
        data, info = fetch_stock_data(symbol, "1y")
        data = add_technical_indicators(data)
        
        current_price = float(data['Close'].iloc[-1])
        prev_price = float(data['Close'].iloc[-2])
        change = current_price - prev_price
        change_percent = (change / prev_price) * 100
        
        # Generate recommendation based on indicators
        rsi = float(data['RSI'].iloc[-1]) if not pd.isna(data['RSI'].iloc[-1]) else 50
        ma_10 = float(data['MA_10'].iloc[-1]) if not pd.isna(data['MA_10'].iloc[-1]) else current_price
        ma_50 = float(data['MA_50'].iloc[-1]) if not pd.isna(data['MA_50'].iloc[-1]) else current_price
        
        if rsi < 30 and current_price > ma_10 > ma_50:
            recommendation = "BUY"
        elif rsi > 70 and current_price < ma_10 < ma_50:
            recommendation = "SELL"
        else:
            recommendation = "HOLD"
        
        return StockAnalysis(
            symbol=symbol,
            current_price=current_price,
            change=change,
            change_percent=change_percent,
            volume=int(data['Volume'].iloc[-1]),
            market_cap=info.get('marketCap'),
            pe_ratio=info.get('trailingPE'),
            moving_averages={
                'ma_10': ma_10,
                'ma_50': ma_50,
                'ma_200': float(data['MA_200'].iloc[-1]) if not pd.isna(data['MA_200'].iloc[-1]) else current_price
            },
            rsi=rsi,
            recommendation=recommendation
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in analysis: {str(e)}")

# API Routes
@api_router.get("/")
async def root():
    return {"message": "Stock Price Prediction API"}

@api_router.post("/predict", response_model=StockPrediction)
async def predict_stock(request: StockRequest):
    """Predict stock prices using LSTM"""
    try:
        # Run prediction in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            executor, 
            train_and_predict, 
            request.symbol.upper(), 
            request.period, 
            request.prediction_days
        )
        
        # Save prediction to database
        prediction = StockPrediction(**result)
        await db.predictions.insert_one(prediction.dict())
        
        return prediction
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/analyze/{symbol}")
async def analyze_stock(symbol: str):
    """Get current stock analysis"""
    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(executor, get_stock_analysis, symbol.upper())
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/predictions", response_model=List[StockPrediction])
async def get_predictions(limit: int = 10):
    """Get recent predictions"""
    predictions = await db.predictions.find().sort("timestamp", -1).limit(limit).to_list(limit)
    return [StockPrediction(**pred) for pred in predictions]

@api_router.get("/popular-stocks")
async def get_popular_stocks():
    """Get popular stock symbols"""
    return {
        "symbols": [
            {"symbol": "AAPL", "name": "Apple Inc."},
            {"symbol": "GOOGL", "name": "Alphabet Inc."},
            {"symbol": "MSFT", "name": "Microsoft Corporation"},
            {"symbol": "TSLA", "name": "Tesla, Inc."},
            {"symbol": "AMZN", "name": "Amazon.com, Inc."},
            {"symbol": "META", "name": "Meta Platforms, Inc."},
            {"symbol": "NFLX", "name": "Netflix, Inc."},
            {"symbol": "NVDA", "name": "NVIDIA Corporation"},
            {"symbol": "SPY", "name": "SPDR S&P 500 ETF Trust"},
            {"symbol": "QQQ", "name": "Invesco QQQ Trust"}
        ]
    }

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
    executor.shutdown(wait=True)