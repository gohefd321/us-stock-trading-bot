/**
 * Portfolio Optimizer Page
 *
 * 포트폴리오 최적화 대시보드
 * - Modern Portfolio Theory (MPT)
 * - Efficient Frontier
 * - 리밸런싱 추천
 */

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { PieChart, TrendingUp, RefreshCw, Target, BarChart3 } from 'lucide-react';

interface OptimizationResult {
  portfolio_weights: { [key: string]: number };
  expected_return: number;
  expected_volatility: number;
  sharpe_ratio: number;
  efficient_frontier: Array<{
    return: number;
    volatility: number;
    sharpe_ratio: number;
  }>;
}

interface RebalanceAction {
  ticker: string;
  current_weight: number;
  target_weight: number;
  weight_diff: number;
  action: string;
  quantity: number;
  value: number;
}

interface PortfolioMetrics {
  total_invested: number;
  total_value: number;
  total_unrealized_pnl: number;
  total_return_pct: number;
  portfolio_volatility: number;
  position_count: number;
  position_weights: Array<{
    ticker: string;
    weight: number;
    value: number;
    unrealized_pnl: number;
  }>;
}

export const PortfolioOptimizerPage: React.FC = () => {
  const [tickers, setTickers] = useState('AAPL,MSFT,GOOGL,AMZN,NVDA');
  const [method, setMethod] = useState('sharpe');
  const [lookbackDays, setLookbackDays] = useState('252');
  const [riskFreeRate, setRiskFreeRate] = useState('0.04');

  const [optimizationResult, setOptimizationResult] = useState<OptimizationResult | null>(null);
  const [rebalanceActions, setRebalanceActions] = useState<RebalanceAction[]>([]);
  const [portfolioMetrics, setPortfolioMetrics] = useState<PortfolioMetrics | null>(null);

  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');

  // Fetch portfolio metrics
  const fetchPortfolioMetrics = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/portfolio/metrics');
      if (response.ok) {
        const data = await response.json();
        setPortfolioMetrics(data);
      }
    } catch (error) {
      console.error('Failed to fetch portfolio metrics:', error);
    }
  };

  useEffect(() => {
    fetchPortfolioMetrics();
  }, []);

  // Optimize portfolio
  const handleOptimize = async () => {
    setLoading(true);
    setMessage('');

    try {
      const tickerList = tickers.split(',').map((t) => t.trim());

      const response = await fetch('http://localhost:8000/api/portfolio/optimize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          tickers: tickerList,
          method: method,
          lookback_days: parseInt(lookbackDays),
          risk_free_rate: parseFloat(riskFreeRate),
        }),
      });

      const data = await response.json();

      if (response.ok) {
        setOptimizationResult(data);
        setMessage('✓ Portfolio optimization completed');
      } else {
        setMessage(`✗ Error: ${data.error}`);
      }
    } catch (error) {
      setMessage(`✗ Failed to optimize: ${error}`);
    } finally {
      setLoading(false);
    }
  };

  // Get rebalancing recommendations
  const handleRebalancing = async () => {
    if (!optimizationResult || !portfolioMetrics) {
      setMessage('✗ Please optimize portfolio first');
      return;
    }

    setLoading(true);
    setMessage('');

    try {
      // Convert weights from 0-1 to 0-100
      const targetWeights: { [key: string]: number } = {};
      Object.keys(optimizationResult.portfolio_weights).forEach((ticker) => {
        targetWeights[ticker] = optimizationResult.portfolio_weights[ticker] * 100;
      });

      const response = await fetch('http://localhost:8000/api/portfolio/rebalancing', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          target_weights: targetWeights,
          total_value: portfolioMetrics.total_value,
          tolerance: 5.0,
        }),
      });

      const data = await response.json();

      if (response.ok) {
        setRebalanceActions(data.actions);
        setMessage(
          data.rebalancing_needed
            ? `✓ Rebalancing needed: ${data.actions.length} actions`
            : '✓ Portfolio is balanced'
        );
      } else {
        setMessage(`✗ Error: ${data.error}`);
      }
    } catch (error) {
      setMessage(`✗ Failed to get rebalancing: ${error}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold">포트폴리오 최적화</h1>
        <p className="text-gray-500 mt-1">Modern Portfolio Theory & Efficient Frontier</p>
      </div>

      {/* Message */}
      {message && (
        <Card className={message.startsWith('✓') ? 'bg-green-50' : 'bg-red-50'}>
          <CardContent className="py-3">
            <p className={message.startsWith('✓') ? 'text-green-700' : 'text-red-700'}>{message}</p>
          </CardContent>
        </Card>
      )}

      {/* Portfolio Metrics */}
      {portfolioMetrics && (
        <Card>
          <CardHeader>
            <CardTitle>Current Portfolio Metrics</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div>
                <p className="text-sm text-gray-500">Total Value</p>
                <p className="text-2xl font-bold">${portfolioMetrics.total_value.toFixed(2)}</p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Total Return</p>
                <Badge variant={portfolioMetrics.total_return_pct >= 0 ? 'default' : 'destructive'}>
                  {portfolioMetrics.total_return_pct >= 0 ? '+' : ''}
                  {portfolioMetrics.total_return_pct.toFixed(2)}%
                </Badge>
              </div>
              <div>
                <p className="text-sm text-gray-500">Volatility</p>
                <p className="text-lg font-semibold">
                  {portfolioMetrics.portfolio_volatility
                    ? `${(portfolioMetrics.portfolio_volatility * 100).toFixed(1)}%`
                    : 'N/A'}
                </p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Positions</p>
                <p className="text-lg font-semibold">{portfolioMetrics.position_count}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Optimization Settings */}
      <Card>
        <CardHeader>
          <CardTitle>Optimization Settings</CardTitle>
          <CardDescription>Modern Portfolio Theory (MPT)</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <Label>Tickers (comma-separated)</Label>
            <Input
              placeholder="AAPL,MSFT,GOOGL,AMZN,NVDA"
              value={tickers}
              onChange={(e) => setTickers(e.target.value.toUpperCase())}
            />
          </div>

          <div className="grid grid-cols-3 gap-4">
            <div>
              <Label>Method</Label>
              <Select value={method} onValueChange={setMethod}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="sharpe">Sharpe Ratio (Recommended)</SelectItem>
                  <SelectItem value="min_variance">Minimum Variance</SelectItem>
                  <SelectItem value="max_return">Maximum Return</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Lookback Days</Label>
              <Input
                type="number"
                placeholder="252"
                value={lookbackDays}
                onChange={(e) => setLookbackDays(e.target.value)}
              />
            </div>
            <div>
              <Label>Risk-Free Rate</Label>
              <Input
                type="number"
                step="0.01"
                placeholder="0.04"
                value={riskFreeRate}
                onChange={(e) => setRiskFreeRate(e.target.value)}
              />
            </div>
          </div>

          <div className="flex gap-2">
            <Button onClick={handleOptimize} disabled={loading} className="flex-1">
              <Target className="h-4 w-4 mr-2" />
              Optimize Portfolio
            </Button>
            <Button
              onClick={handleRebalancing}
              disabled={loading || !optimizationResult}
              variant="outline"
              className="flex-1"
            >
              <BarChart3 className="h-4 w-4 mr-2" />
              Get Rebalancing
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Optimization Result */}
      {optimizationResult && (
        <Card>
          <CardHeader>
            <CardTitle>Optimal Portfolio Weights</CardTitle>
            <CardDescription>
              Expected Return: {(optimizationResult.expected_return * 100).toFixed(2)}% | Volatility:{' '}
              {(optimizationResult.expected_volatility * 100).toFixed(2)}% | Sharpe Ratio:{' '}
              {optimizationResult.sharpe_ratio.toFixed(2)}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {Object.entries(optimizationResult.portfolio_weights).map(([ticker, weight]) => (
                <div key={ticker} className="flex items-center gap-4">
                  <span className="font-semibold w-16">{ticker}</span>
                  <div className="flex-1 bg-gray-200 rounded-full h-4">
                    <div
                      className="bg-blue-600 h-4 rounded-full"
                      style={{ width: `${weight * 100}%` }}
                    />
                  </div>
                  <span className="font-medium w-16 text-right">{(weight * 100).toFixed(1)}%</span>
                </div>
              ))}
            </div>

            {/* Performance Metrics */}
            <div className="mt-6 grid grid-cols-3 gap-4 pt-4 border-t">
              <div className="text-center">
                <p className="text-sm text-gray-500">Expected Return</p>
                <p className="text-xl font-bold text-green-600">
                  {(optimizationResult.expected_return * 100).toFixed(2)}%
                </p>
              </div>
              <div className="text-center">
                <p className="text-sm text-gray-500">Expected Volatility</p>
                <p className="text-xl font-bold">
                  {(optimizationResult.expected_volatility * 100).toFixed(2)}%
                </p>
              </div>
              <div className="text-center">
                <p className="text-sm text-gray-500">Sharpe Ratio</p>
                <p className="text-xl font-bold text-blue-600">
                  {optimizationResult.sharpe_ratio.toFixed(2)}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Rebalancing Actions */}
      {rebalanceActions.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Rebalancing Actions</CardTitle>
            <CardDescription>{rebalanceActions.length} actions needed</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {rebalanceActions.map((action, index) => (
                <div key={index} className="p-4 border rounded-lg">
                  <div className="flex justify-between items-center">
                    <div>
                      <div className="flex items-center gap-2">
                        <Badge variant={action.action === 'BUY' ? 'default' : 'destructive'}>
                          {action.action}
                        </Badge>
                        <span className="font-semibold text-lg">{action.ticker}</span>
                      </div>
                      <p className="text-sm text-gray-500 mt-1">
                        {action.current_weight.toFixed(1)}% → {action.target_weight.toFixed(1)}% (
                        {action.weight_diff > 0 ? '+' : ''}
                        {action.weight_diff.toFixed(1)}%)
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-lg font-bold">{action.quantity} shares</p>
                      <p className="text-sm text-gray-500">${action.value.toFixed(2)}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            <div className="mt-4 pt-4 border-t">
              <p className="text-sm text-gray-500">
                💡 Tip: These actions will bring your portfolio closer to the optimal allocation based on
                Modern Portfolio Theory.
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Efficient Frontier Chart */}
      {optimizationResult && optimizationResult.efficient_frontier.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Efficient Frontier</CardTitle>
            <CardDescription>Risk-Return Trade-off</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-64 flex items-center justify-center bg-gray-50 rounded">
              <p className="text-gray-400">
                📊 Chart visualization: Efficient Frontier
                <br />
                <span className="text-sm">
                  (Connect with Chart.js or Recharts for visual representation)
                </span>
              </p>
            </div>
            <div className="mt-4 text-sm text-gray-600">
              <p>
                <strong>Efficient Frontier:</strong> The set of optimal portfolios offering the highest
                expected return for a given level of risk.
              </p>
              <p className="mt-2">
                Data Points: {optimizationResult.efficient_frontier.length} portfolios calculated
              </p>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};
