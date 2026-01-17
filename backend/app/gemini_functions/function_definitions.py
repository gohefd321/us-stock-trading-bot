"""
Gemini Function Definitions
8 trading functions for Gemini AI function calling
"""

from typing import List, Dict

# Function schemas for Gemini function calling
TRADING_FUNCTIONS: List[Dict] = [
    {
        "name": "check_balance",
        "description": "Get current account balance including cash and total asset value",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "get_current_price",
        "description": "Get current market price for a specific US stock ticker",
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "US stock ticker symbol (e.g., AAPL, TSLA, NVDA)"
                }
            },
            "required": ["ticker"]
        }
    },
    {
        "name": "get_portfolio_status",
        "description": "Get comprehensive portfolio status including all positions, P/L, and exposure",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "execute_trade",
        "description": "Execute a trade (buy or sell) for a US stock. This will place an actual order through the broker.",
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "US stock ticker symbol"
                },
                "action": {
                    "type": "string",
                    "enum": ["BUY", "SELL"],
                    "description": "Trade action - BUY to open/increase position, SELL to close/decrease position"
                },
                "quantity": {
                    "type": "integer",
                    "description": "Number of shares to trade"
                },
                "order_type": {
                    "type": "string",
                    "enum": ["MARKET", "LIMIT"],
                    "description": "Order type - MARKET for immediate execution, LIMIT for specific price"
                },
                "limit_price": {
                    "type": "number",
                    "description": "Limit price for LIMIT orders (optional, only used if order_type is LIMIT)"
                }
            },
            "required": ["ticker", "action", "quantity", "order_type"]
        }
    },
    {
        "name": "analyze_signals",
        "description": "Get aggregated market signals for a ticker from WallStreetBets, Yahoo Finance, and TipRanks",
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "US stock ticker symbol"
                },
                "hours_back": {
                    "type": "integer",
                    "description": "Number of hours to look back for recent signals (default: 24)"
                }
            },
            "required": ["ticker"]
        }
    },
    {
        "name": "calculate_position_size",
        "description": "Calculate optimal position size based on confidence level, current price, and risk limits",
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "US stock ticker symbol"
                },
                "confidence": {
                    "type": "number",
                    "description": "Confidence level from 0.0 to 1.0 for this trade"
                },
                "price": {
                    "type": "number",
                    "description": "Current or expected price per share"
                }
            },
            "required": ["ticker", "confidence", "price"]
        }
    },
    {
        "name": "check_stop_loss_triggers",
        "description": "Check if any positions have triggered stop-loss levels (-30% from purchase price)",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "get_trading_history",
        "description": "Get recent trading history to understand past decisions and performance",
        "parameters": {
            "type": "object",
            "properties": {
                "days_back": {
                    "type": "integer",
                    "description": "Number of days to look back for trading history (default: 7)"
                }
            },
            "required": []
        }
    }
]
