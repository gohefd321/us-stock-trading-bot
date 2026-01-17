-- US Stock Trading Bot Database Schema
-- SQLite Database for storing trading data, AI decisions, and signals

-- API Keys table: Encrypted API key storage
CREATE TABLE IF NOT EXISTS api_keys (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key_name TEXT NOT NULL UNIQUE,  -- 'korea_investment_key', 'korea_investment_secret', etc.
    encrypted_value TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Trades table: All executed trades
CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_id TEXT UNIQUE,  -- Broker's trade ID
    ticker TEXT NOT NULL,
    action TEXT NOT NULL CHECK(action IN ('BUY', 'SELL')),
    quantity INTEGER NOT NULL,
    price REAL NOT NULL,
    total_value REAL NOT NULL,  -- In KRW
    order_type TEXT DEFAULT 'MARKET' CHECK(order_type IN ('MARKET', 'LIMIT')),
    status TEXT DEFAULT 'PENDING' CHECK(status IN ('PENDING', 'FILLED', 'CANCELLED', 'FAILED')),
    executed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    broker_response TEXT,  -- JSON response from broker
    llm_decision_id INTEGER,  -- Link to decision that triggered this trade
    FOREIGN KEY (llm_decision_id) REFERENCES llm_decisions(id)
);

-- LLM Decisions table: All LLM decision logs
CREATE TABLE IF NOT EXISTS llm_decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    decision_type TEXT NOT NULL,  -- 'PRE_MARKET', 'MID_SESSION', 'PRE_CLOSE', 'CHAT_QUERY'
    prompt TEXT NOT NULL,
    response TEXT NOT NULL,
    reasoning TEXT,  -- Extracted reasoning from LLM
    confidence_score REAL,  -- 0-1 confidence score
    function_calls TEXT,  -- JSON array of function calls made
    signals_used TEXT,  -- JSON of signals that influenced decision
    portfolio_state TEXT,  -- JSON snapshot of portfolio at decision time
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    execution_time_ms INTEGER
);

-- Signals table: Market signals from all sources
CREATE TABLE IF NOT EXISTS signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    source TEXT NOT NULL CHECK(source IN ('WSB', 'YAHOO', 'TIPRANKS')),
    signal_type TEXT NOT NULL,  -- 'SENTIMENT', 'NEWS', 'ANALYST_RATING', 'PRICE_ALERT'
    signal_data TEXT NOT NULL,  -- JSON data specific to signal type
    sentiment_score REAL,  -- -1 to 1
    strength REAL,  -- 0 to 1
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    is_active BOOLEAN DEFAULT 1
);

-- Portfolio Snapshots table: Daily portfolio state
CREATE TABLE IF NOT EXISTS portfolio_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_date DATE NOT NULL UNIQUE,
    cash_balance REAL NOT NULL,
    total_holdings_value REAL NOT NULL,
    total_value REAL NOT NULL,
    daily_pnl REAL,
    daily_pnl_pct REAL,
    total_pnl REAL,
    total_pnl_pct REAL,
    holdings_json TEXT NOT NULL,  -- JSON of all positions
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- User Preferences table: System configuration
CREATE TABLE IF NOT EXISTS user_preferences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT NOT NULL UNIQUE,
    value TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Initial user preferences
INSERT OR IGNORE INTO user_preferences (key, value) VALUES
    ('initial_capital_krw', '1000000'),
    ('max_position_size_pct', '40'),
    ('daily_loss_limit_pct', '20'),
    ('stop_loss_pct', '30'),
    ('trading_enabled', 'true'),
    ('notification_enabled', 'false'),
    ('gemini_model', 'gemini-2.0-flash-exp'),
    ('google_search_grounding', 'true');

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_trades_ticker ON trades(ticker);
CREATE INDEX IF NOT EXISTS idx_trades_created_at ON trades(created_at);
CREATE INDEX IF NOT EXISTS idx_trades_status ON trades(status);
CREATE INDEX IF NOT EXISTS idx_signals_ticker ON signals(ticker);
CREATE INDEX IF NOT EXISTS idx_signals_source ON signals(source);
CREATE INDEX IF NOT EXISTS idx_signals_created_at ON signals(created_at);
CREATE INDEX IF NOT EXISTS idx_signals_active ON signals(is_active);
CREATE INDEX IF NOT EXISTS idx_llm_decisions_created_at ON llm_decisions(created_at);
CREATE INDEX IF NOT EXISTS idx_llm_decisions_type ON llm_decisions(decision_type);
