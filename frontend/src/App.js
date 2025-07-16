import React, { useState, useEffect } from "react";
import "./App.css";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const StockChart = ({ data, title }) => {
  const maxPrice = Math.max(...data.map(d => d.value));
  const minPrice = Math.min(...data.map(d => d.value));
  const range = maxPrice - minPrice;
  
  return (
    <div className="bg-white p-6 rounded-lg shadow-lg">
      <h3 className="text-lg font-bold mb-4">{title}</h3>
      <div className="relative h-64">
        <svg width="100%" height="100%" viewBox="0 0 800 200">
          {data.map((point, index) => {
            const x = (index / (data.length - 1)) * 800;
            const y = 200 - ((point.value - minPrice) / range) * 180;
            const nextPoint = data[index + 1];
            
            if (nextPoint) {
              const nextX = ((index + 1) / (data.length - 1)) * 800;
              const nextY = 200 - ((nextPoint.value - minPrice) / range) * 180;
              
              return (
                <line
                  key={index}
                  x1={x}
                  y1={y}
                  x2={nextX}
                  y2={nextY}
                  stroke={point.isPrediction ? "#ef4444" : "#3b82f6"}
                  strokeWidth="2"
                />
              );
            }
            return null;
          })}
          
          {/* Data points */}
          {data.map((point, index) => {
            const x = (index / (data.length - 1)) * 800;
            const y = 200 - ((point.value - minPrice) / range) * 180;
            
            return (
              <circle
                key={index}
                cx={x}
                cy={y}
                r="3"
                fill={point.isPrediction ? "#ef4444" : "#3b82f6"}
              />
            );
          })}
        </svg>
        
        {/* Legend */}
        <div className="absolute bottom-2 right-2 flex space-x-4">
          <div className="flex items-center">
            <div className="w-4 h-0.5 bg-blue-500 mr-2"></div>
            <span className="text-sm">Actual</span>
          </div>
          <div className="flex items-center">
            <div className="w-4 h-0.5 bg-red-500 mr-2"></div>
            <span className="text-sm">Predicted</span>
          </div>
        </div>
      </div>
      
      {/* Price labels */}
      <div className="flex justify-between mt-2 text-sm text-gray-600">
        <span>${minPrice.toFixed(2)}</span>
        <span>${maxPrice.toFixed(2)}</span>
      </div>
    </div>
  );
};

const MetricsCard = ({ title, value, change, isPercentage = false }) => (
  <div className="bg-white p-6 rounded-lg shadow-lg">
    <h3 className="text-sm font-medium text-gray-500 mb-2">{title}</h3>
    <div className="text-2xl font-bold text-gray-900">
      {isPercentage ? `${value.toFixed(2)}%` : `$${value.toFixed(2)}`}
    </div>
    {change !== undefined && (
      <div className={`text-sm font-medium ${change >= 0 ? 'text-green-600' : 'text-red-600'}`}>
        {change >= 0 ? '+' : ''}{change.toFixed(2)}{isPercentage ? '%' : ''}
      </div>
    )}
  </div>
);

const IndicatorCard = ({ name, value, status }) => (
  <div className="bg-white p-4 rounded-lg shadow">
    <div className="flex justify-between items-center">
      <span className="text-sm font-medium text-gray-700">{name}</span>
      <span className={`px-2 py-1 rounded text-xs font-medium ${
        status === 'BUY' ? 'bg-green-100 text-green-800' :
        status === 'SELL' ? 'bg-red-100 text-red-800' :
        'bg-yellow-100 text-yellow-800'
      }`}>
        {status}
      </span>
    </div>
    <div className="text-lg font-semibold text-gray-900 mt-1">
      {typeof value === 'number' ? value.toFixed(2) : value}
    </div>
  </div>
);

const LoadingSpinner = () => (
  <div className="flex justify-center items-center p-8">
    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
  </div>
);

function App() {
  const [selectedStock, setSelectedStock] = useState('AAPL');
  const [prediction, setPrediction] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [loading, setLoading] = useState(false);
  const [predictionDays, setPredictionDays] = useState(30);
  const [popularStocks, setPopularStocks] = useState([]);

  useEffect(() => {
    fetchPopularStocks();
  }, []);

  const fetchPopularStocks = async () => {
    try {
      const response = await axios.get(`${API}/popular-stocks`);
      setPopularStocks(response.data.symbols);
    } catch (error) {
      console.error('Error fetching popular stocks:', error);
    }
  };

  const handlePredict = async () => {
    if (!selectedStock) return;
    
    setLoading(true);
    try {
      const [predictionResponse, analysisResponse] = await Promise.all([
        axios.post(`${API}/predict`, {
          symbol: selectedStock,
          period: "5y",
          prediction_days: predictionDays
        }),
        axios.get(`${API}/analyze/${selectedStock}`)
      ]);
      
      setPrediction(predictionResponse.data);
      setAnalysis(analysisResponse.data);
    } catch (error) {
      console.error('Error:', error);
      alert('Error fetching prediction. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const getChartData = () => {
    if (!prediction) return [];
    
    const actualData = prediction.actual_prices.map((price, index) => ({
      value: price,
      date: prediction.dates[index],
      isPrediction: false
    }));
    
    const predictionData = prediction.predictions.map((price, index) => ({
      value: price,
      date: prediction.prediction_dates[index],
      isPrediction: true
    }));
    
    return [...actualData, ...predictionData];
  };

  const getRecommendationColor = (recommendation) => {
    switch (recommendation) {
      case 'BUY': return 'text-green-600 bg-green-100';
      case 'SELL': return 'text-red-600 bg-red-100';
      default: return 'text-yellow-600 bg-yellow-100';
    }
  };

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Header */}
      <div className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 py-6">
          <h1 className="text-3xl font-bold text-gray-900">Stock Price Prediction with LSTM</h1>
          <p className="text-gray-600 mt-2">AI-powered stock market predictions using deep learning</p>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Controls */}
        <div className="bg-white rounded-lg shadow-lg p-6 mb-8">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Stock Symbol</label>
              <select
                value={selectedStock}
                onChange={(e) => setSelectedStock(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {popularStocks.map(stock => (
                  <option key={stock.symbol} value={stock.symbol}>
                    {stock.symbol} - {stock.name}
                  </option>
                ))}
              </select>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Prediction Days</label>
              <select
                value={predictionDays}
                onChange={(e) => setPredictionDays(Number(e.target.value))}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value={7}>7 days</option>
                <option value={15}>15 days</option>
                <option value={30}>30 days</option>
                <option value={60}>60 days</option>
              </select>
            </div>
            
            <div className="flex items-end">
              <button
                onClick={handlePredict}
                disabled={loading}
                className="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {loading ? 'Predicting...' : 'Predict Stock Price'}
              </button>
            </div>
          </div>
        </div>

        {loading && <LoadingSpinner />}

        {/* Current Analysis */}
        {analysis && (
          <div className="mb-8">
            <h2 className="text-2xl font-bold text-gray-900 mb-4">Current Analysis - {analysis.symbol}</h2>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
              <MetricsCard 
                title="Current Price" 
                value={analysis.current_price} 
                change={analysis.change}
              />
              <MetricsCard 
                title="Change %" 
                value={analysis.change_percent} 
                isPercentage={true}
              />
              <MetricsCard 
                title="Volume" 
                value={analysis.volume / 1000000} 
                change={undefined}
              />
              <div className="bg-white p-6 rounded-lg shadow-lg">
                <h3 className="text-sm font-medium text-gray-500 mb-2">Recommendation</h3>
                <div className={`text-2xl font-bold px-3 py-1 rounded-full text-center ${getRecommendationColor(analysis.recommendation)}`}>
                  {analysis.recommendation}
                </div>
              </div>
            </div>

            {/* Technical Indicators */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <IndicatorCard 
                name="RSI (14)" 
                value={analysis.rsi} 
                status={analysis.rsi < 30 ? 'BUY' : analysis.rsi > 70 ? 'SELL' : 'HOLD'}
              />
              <IndicatorCard 
                name="MA (10)" 
                value={analysis.moving_averages.ma_10} 
                status={analysis.current_price > analysis.moving_averages.ma_10 ? 'BUY' : 'SELL'}
              />
              <IndicatorCard 
                name="MA (50)" 
                value={analysis.moving_averages.ma_50} 
                status={analysis.current_price > analysis.moving_averages.ma_50 ? 'BUY' : 'SELL'}
              />
            </div>
          </div>
        )}

        {/* Prediction Results */}
        {prediction && (
          <div className="space-y-8">
            <div>
              <h2 className="text-2xl font-bold text-gray-900 mb-4">Prediction Results</h2>
              <StockChart data={getChartData()} title={`${prediction.symbol} Price Prediction`} />
            </div>

            {/* Model Metrics */}
            <div className="bg-white rounded-lg shadow-lg p-6">
              <h3 className="text-lg font-bold mb-4">Model Performance</h3>
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div className="text-center">
                  <div className="text-2xl font-bold text-blue-600">{prediction.metrics.accuracy.toFixed(1)}%</div>
                  <div className="text-sm text-gray-600">Accuracy</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-green-600">{prediction.metrics.mae.toFixed(2)}</div>
                  <div className="text-sm text-gray-600">MAE</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-orange-600">{prediction.metrics.rmse.toFixed(2)}</div>
                  <div className="text-sm text-gray-600">RMSE</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-purple-600">{prediction.metrics.mse.toFixed(2)}</div>
                  <div className="text-sm text-gray-600">MSE</div>
                </div>
              </div>
            </div>

            {/* Key Insights */}
            <div className="bg-white rounded-lg shadow-lg p-6">
              <h3 className="text-lg font-bold mb-4">Key Insights</h3>
              <div className="space-y-3">
                <div className="flex justify-between">
                  <span className="text-gray-600">Predicted Price (Next 30 days):</span>
                  <span className="font-semibold">${prediction.predictions[prediction.predictions.length - 1].toFixed(2)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Current Price:</span>
                  <span className="font-semibold">${prediction.indicators.current_price.toFixed(2)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Expected Change:</span>
                  <span className={`font-semibold ${
                    prediction.predictions[prediction.predictions.length - 1] > prediction.indicators.current_price 
                      ? 'text-green-600' : 'text-red-600'
                  }`}>
                    {((prediction.predictions[prediction.predictions.length - 1] - prediction.indicators.current_price) / prediction.indicators.current_price * 100).toFixed(2)}%
                  </span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Empty State */}
        {!prediction && !loading && (
          <div className="text-center py-12">
            <div className="text-gray-500 text-lg">Select a stock and click "Predict Stock Price" to begin</div>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;