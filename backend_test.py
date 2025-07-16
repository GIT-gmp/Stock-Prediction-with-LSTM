#!/usr/bin/env python3
"""
Comprehensive Backend API Tests for Stock Prediction System
Tests all backend endpoints with proper error handling and timeouts
"""

import requests
import json
import time
import sys
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv('/app/frontend/.env')

# Get backend URL from environment
BACKEND_URL = os.getenv('REACT_APP_BACKEND_URL', 'http://localhost:8001')
API_BASE_URL = f"{BACKEND_URL}/api"

print(f"Testing backend at: {API_BASE_URL}")

class BackendTester:
    def __init__(self):
        self.results = {
            'total_tests': 0,
            'passed': 0,
            'failed': 0,
            'errors': []
        }
        
    def log_result(self, test_name, success, message="", response_data=None):
        """Log test result"""
        self.results['total_tests'] += 1
        if success:
            self.results['passed'] += 1
            print(f"✅ {test_name}: PASSED - {message}")
        else:
            self.results['failed'] += 1
            self.results['errors'].append(f"{test_name}: {message}")
            print(f"❌ {test_name}: FAILED - {message}")
        
        if response_data:
            print(f"   Response: {json.dumps(response_data, indent=2)[:200]}...")
        print()

    def test_api_health(self):
        """Test 1: Basic API Health Check"""
        print("🔍 Testing API Health Check...")
        try:
            response = requests.get(f"{API_BASE_URL}/", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if "message" in data:
                    self.log_result("API Health Check", True, 
                                  f"API is responding (Status: {response.status_code})", data)
                    return True
                else:
                    self.log_result("API Health Check", False, 
                                  "Response missing expected 'message' field", data)
            else:
                self.log_result("API Health Check", False, 
                              f"Unexpected status code: {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            self.log_result("API Health Check", False, f"Connection error: {str(e)}")
        except Exception as e:
            self.log_result("API Health Check", False, f"Unexpected error: {str(e)}")
        
        return False

    def test_popular_stocks(self):
        """Test 2: Popular Stocks Endpoint"""
        print("🔍 Testing Popular Stocks Endpoint...")
        try:
            response = requests.get(f"{API_BASE_URL}/popular-stocks", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if "symbols" in data and isinstance(data["symbols"], list):
                    if len(data["symbols"]) > 0:
                        # Check if symbols have required fields
                        first_symbol = data["symbols"][0]
                        if "symbol" in first_symbol and "name" in first_symbol:
                            self.log_result("Popular Stocks", True, 
                                          f"Retrieved {len(data['symbols'])} stock symbols", 
                                          {"sample": first_symbol})
                            return True
                        else:
                            self.log_result("Popular Stocks", False, 
                                          "Symbol objects missing required fields")
                    else:
                        self.log_result("Popular Stocks", False, "No symbols returned")
                else:
                    self.log_result("Popular Stocks", False, 
                                  "Response missing 'symbols' array", data)
            else:
                self.log_result("Popular Stocks", False, 
                              f"Unexpected status code: {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            self.log_result("Popular Stocks", False, f"Connection error: {str(e)}")
        except Exception as e:
            self.log_result("Popular Stocks", False, f"Unexpected error: {str(e)}")
        
        return False

    def test_stock_analysis_valid(self):
        """Test 3: Stock Analysis with Valid Symbol"""
        print("🔍 Testing Stock Analysis (Valid Symbol: AAPL)...")
        try:
            response = requests.get(f"{API_BASE_URL}/analyze/AAPL", timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                required_fields = ['symbol', 'current_price', 'change', 'change_percent', 
                                 'volume', 'moving_averages', 'rsi', 'recommendation']
                
                missing_fields = [field for field in required_fields if field not in data]
                if not missing_fields:
                    self.log_result("Stock Analysis (Valid)", True, 
                                  f"Analysis for AAPL completed successfully", 
                                  {k: v for k, v in data.items() if k in ['symbol', 'current_price', 'recommendation']})
                    return True
                else:
                    self.log_result("Stock Analysis (Valid)", False, 
                                  f"Missing required fields: {missing_fields}", data)
            else:
                self.log_result("Stock Analysis (Valid)", False, 
                              f"Unexpected status code: {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            self.log_result("Stock Analysis (Valid)", False, f"Connection error: {str(e)}")
        except Exception as e:
            self.log_result("Stock Analysis (Valid)", False, f"Unexpected error: {str(e)}")
        
        return False

    def test_stock_analysis_invalid(self):
        """Test 4: Stock Analysis with Invalid Symbol"""
        print("🔍 Testing Stock Analysis (Invalid Symbol: INVALID123)...")
        try:
            response = requests.get(f"{API_BASE_URL}/analyze/INVALID123", timeout=15)
            
            # Should return error status code (400 or 500)
            if response.status_code in [400, 404, 500]:
                try:
                    data = response.json()
                    if "detail" in data:
                        self.log_result("Stock Analysis (Invalid)", True, 
                                      f"Properly handled invalid symbol (Status: {response.status_code})", 
                                      {"error": data["detail"]})
                        return True
                except:
                    pass
                
                self.log_result("Stock Analysis (Invalid)", True, 
                              f"Properly returned error status: {response.status_code}")
                return True
            else:
                self.log_result("Stock Analysis (Invalid)", False, 
                              f"Should return error status, got: {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            self.log_result("Stock Analysis (Invalid)", False, f"Connection error: {str(e)}")
        except Exception as e:
            self.log_result("Stock Analysis (Invalid)", False, f"Unexpected error: {str(e)}")
        
        return False

    def test_stock_prediction_valid(self):
        """Test 5: Stock Prediction with Valid Request (Short Period)"""
        print("🔍 Testing Stock Prediction (Valid Request - Short Period)...")
        print("⚠️  Note: ML model training may take 30-60 seconds...")
        
        try:
            payload = {
                "symbol": "AAPL",
                "period": "1y",
                "prediction_days": 7
            }
            
            # Increased timeout for ML processing
            response = requests.post(f"{API_BASE_URL}/predict", 
                                   json=payload, 
                                   timeout=120,
                                   headers={'Content-Type': 'application/json'})
            
            if response.status_code == 200:
                data = response.json()
                required_fields = ['symbol', 'predictions', 'actual_prices', 'dates', 
                                 'prediction_dates', 'metrics', 'indicators']
                
                missing_fields = [field for field in required_fields if field not in data]
                if not missing_fields:
                    # Validate data structure
                    if (isinstance(data['predictions'], list) and 
                        len(data['predictions']) == payload['prediction_days'] and
                        isinstance(data['metrics'], dict) and
                        'accuracy' in data['metrics']):
                        
                        self.log_result("Stock Prediction (Valid)", True, 
                                      f"Prediction completed for {payload['symbol']} - {len(data['predictions'])} days predicted", 
                                      {
                                          'symbol': data['symbol'],
                                          'prediction_count': len(data['predictions']),
                                          'accuracy': data['metrics'].get('accuracy', 'N/A'),
                                          'sample_prediction': data['predictions'][0] if data['predictions'] else None
                                      })
                        return True
                    else:
                        self.log_result("Stock Prediction (Valid)", False, 
                                      "Invalid data structure in response", data)
                else:
                    self.log_result("Stock Prediction (Valid)", False, 
                                  f"Missing required fields: {missing_fields}", data)
            else:
                try:
                    error_data = response.json()
                    self.log_result("Stock Prediction (Valid)", False, 
                                  f"Status: {response.status_code}, Error: {error_data.get('detail', 'Unknown error')}")
                except:
                    self.log_result("Stock Prediction (Valid)", False, 
                                  f"Status: {response.status_code}, Response: {response.text[:200]}")
                
        except requests.exceptions.Timeout:
            self.log_result("Stock Prediction (Valid)", False, 
                          "Request timed out - ML model training took too long")
        except requests.exceptions.RequestException as e:
            self.log_result("Stock Prediction (Valid)", False, f"Connection error: {str(e)}")
        except Exception as e:
            self.log_result("Stock Prediction (Valid)", False, f"Unexpected error: {str(e)}")
        
        return False

    def test_stock_prediction_invalid(self):
        """Test 6: Stock Prediction with Invalid Symbol"""
        print("🔍 Testing Stock Prediction (Invalid Symbol)...")
        try:
            payload = {
                "symbol": "INVALID123",
                "period": "1y",
                "prediction_days": 7
            }
            
            response = requests.post(f"{API_BASE_URL}/predict", 
                                   json=payload, 
                                   timeout=30,
                                   headers={'Content-Type': 'application/json'})
            
            # Should return error status code
            if response.status_code in [400, 404, 500]:
                try:
                    data = response.json()
                    if "detail" in data:
                        self.log_result("Stock Prediction (Invalid)", True, 
                                      f"Properly handled invalid symbol (Status: {response.status_code})", 
                                      {"error": data["detail"]})
                        return True
                except:
                    pass
                
                self.log_result("Stock Prediction (Invalid)", True, 
                              f"Properly returned error status: {response.status_code}")
                return True
            else:
                self.log_result("Stock Prediction (Invalid)", False, 
                              f"Should return error status, got: {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            self.log_result("Stock Prediction (Invalid)", False, f"Connection error: {str(e)}")
        except Exception as e:
            self.log_result("Stock Prediction (Invalid)", False, f"Unexpected error: {str(e)}")
        
        return False

    def test_predictions_history(self):
        """Test 7: Predictions History"""
        print("🔍 Testing Predictions History...")
        try:
            response = requests.get(f"{API_BASE_URL}/predictions", timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    self.log_result("Predictions History", True, 
                                  f"Retrieved {len(data)} prediction records", 
                                  {"count": len(data), "sample": data[0] if data else "No predictions yet"})
                    return True
                else:
                    self.log_result("Predictions History", False, 
                                  "Response should be a list", data)
            else:
                self.log_result("Predictions History", False, 
                              f"Unexpected status code: {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            self.log_result("Predictions History", False, f"Connection error: {str(e)}")
        except Exception as e:
            self.log_result("Predictions History", False, f"Unexpected error: {str(e)}")
        
        return False

    def run_all_tests(self):
        """Run all backend tests"""
        print("=" * 80)
        print("🚀 STARTING COMPREHENSIVE BACKEND API TESTS")
        print("=" * 80)
        print(f"Backend URL: {API_BASE_URL}")
        print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Run tests in order
        tests = [
            self.test_api_health,
            self.test_popular_stocks,
            self.test_stock_analysis_valid,
            self.test_stock_analysis_invalid,
            self.test_stock_prediction_valid,
            self.test_stock_prediction_invalid,
            self.test_predictions_history
        ]
        
        for test in tests:
            try:
                test()
                time.sleep(1)  # Brief pause between tests
            except Exception as e:
                print(f"❌ Test {test.__name__} crashed: {str(e)}")
                self.results['failed'] += 1
                self.results['total_tests'] += 1
        
        # Print summary
        print("=" * 80)
        print("📊 TEST SUMMARY")
        print("=" * 80)
        print(f"Total Tests: {self.results['total_tests']}")
        print(f"Passed: {self.results['passed']} ✅")
        print(f"Failed: {self.results['failed']} ❌")
        print(f"Success Rate: {(self.results['passed']/self.results['total_tests']*100):.1f}%")
        
        if self.results['errors']:
            print("\n🔍 FAILED TESTS:")
            for error in self.results['errors']:
                print(f"  • {error}")
        
        print(f"\nTest completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        
        return self.results['failed'] == 0

if __name__ == "__main__":
    tester = BackendTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)