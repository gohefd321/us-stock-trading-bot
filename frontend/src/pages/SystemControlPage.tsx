/**
 * System Control Page
 *
 * 시스템 제어 대시보드
 * - 스케줄러 시작/중지
 * - 워치리스트 관리
 * - 초기 데이터 수집
 */

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Label } from '@/components/ui/label';
import { Play, Square, RefreshCw, Plus, Trash2, Database, TrendingUp, AlertCircle } from 'lucide-react';

interface SchedulerStatus {
  is_running: boolean;
  jobs: Array<{
    id: string;
    name: string;
    next_run_time: string;
  }>;
}

export const SystemControlPage: React.FC = () => {
  const [schedulerStatus, setSchedulerStatus] = useState<SchedulerStatus | null>(null);
  const [watchlist, setWatchlist] = useState<string[]>([]);
  const [newTicker, setNewTicker] = useState('');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');

  // Fetch scheduler status
  const fetchSchedulerStatus = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/scheduler/status');
      if (response.ok) {
        const data = await response.json();
        setSchedulerStatus(data);
      }
    } catch (error) {
      console.error('Failed to fetch scheduler status:', error);
    }
  };

  // Fetch watchlist
  const fetchWatchlist = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/scheduler/watchlist');
      if (response.ok) {
        const data = await response.json();
        setWatchlist(data.watchlist || []);
      }
    } catch (error) {
      console.error('Failed to fetch watchlist:', error);
    }
  };

  useEffect(() => {
    fetchSchedulerStatus();
    fetchWatchlist();

    // Refresh every 10 seconds
    const interval = setInterval(() => {
      fetchSchedulerStatus();
    }, 10000);

    return () => clearInterval(interval);
  }, []);

  // Start scheduler
  const handleStartScheduler = async () => {
    setLoading(true);
    setMessage('');
    try {
      const response = await fetch('http://localhost:8000/api/scheduler/start', {
        method: 'POST',
      });
      const data = await response.json();
      if (response.ok) {
        setMessage('✓ Scheduler started successfully');
        fetchSchedulerStatus();
      } else {
        setMessage(`✗ Error: ${data.detail}`);
      }
    } catch (error) {
      setMessage(`✗ Failed to start scheduler: ${error}`);
    } finally {
      setLoading(false);
    }
  };

  // Stop scheduler
  const handleStopScheduler = async () => {
    setLoading(true);
    setMessage('');
    try {
      const response = await fetch('http://localhost:8000/api/scheduler/stop', {
        method: 'POST',
      });
      const data = await response.json();
      if (response.ok) {
        setMessage('✓ Scheduler stopped successfully');
        fetchSchedulerStatus();
      } else {
        setMessage(`✗ Error: ${data.detail}`);
      }
    } catch (error) {
      setMessage(`✗ Failed to stop scheduler: ${error}`);
    } finally {
      setLoading(false);
    }
  };

  // Add to watchlist
  const handleAddToWatchlist = async () => {
    if (!newTicker.trim()) return;

    setLoading(true);
    setMessage('');
    try {
      const response = await fetch('http://localhost:8000/api/scheduler/watchlist/add', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ticker: newTicker.toUpperCase() }),
      });
      const data = await response.json();
      if (response.ok) {
        setMessage(`✓ ${newTicker.toUpperCase()} added to watchlist`);
        setNewTicker('');
        fetchWatchlist();
      } else {
        setMessage(`✗ Error: ${data.detail}`);
      }
    } catch (error) {
      setMessage(`✗ Failed to add ticker: ${error}`);
    } finally {
      setLoading(false);
    }
  };

  // Remove from watchlist
  const handleRemoveFromWatchlist = async (ticker: string) => {
    setLoading(true);
    setMessage('');
    try {
      const response = await fetch(`http://localhost:8000/api/scheduler/watchlist/remove/${ticker}`, {
        method: 'DELETE',
      });
      const data = await response.json();
      if (response.ok) {
        setMessage(`✓ ${ticker} removed from watchlist`);
        fetchWatchlist();
      } else {
        setMessage(`✗ Error: ${data.detail}`);
      }
    } catch (error) {
      setMessage(`✗ Failed to remove ticker: ${error}`);
    } finally {
      setLoading(false);
    }
  };

  // Manual data collection
  const handleManualDataCollection = async () => {
    setLoading(true);
    setMessage('');
    try {
      // Run market screener
      await fetch('http://localhost:8000/api/screener/scan', { method: 'POST' });

      // Run signal generation for watchlist
      for (const ticker of watchlist.slice(0, 5)) {
        await fetch('http://localhost:8000/api/signals/generate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            ticker: ticker,
            timeframe: '1h',
            strategy_names: ['MA_CROSS', 'RSI', 'MACD'],
          }),
        });
      }

      setMessage('✓ Manual data collection completed');
    } catch (error) {
      setMessage(`✗ Failed to collect data: ${error}`);
    } finally {
      setLoading(false);
    }
  };

  // Generate daily report
  const handleGenerateDailyReport = async () => {
    setLoading(true);
    setMessage('');
    try {
      const response = await fetch('http://localhost:8000/api/daily-report/generate', {
        method: 'POST',
      });
      const data = await response.json();
      if (response.ok) {
        setMessage('✓ Daily report generated successfully');
      } else {
        setMessage(`✗ Error: ${data.detail || data.error}`);
      }
    } catch (error) {
      setMessage(`✗ Failed to generate report: ${error}`);
    } finally {
      setLoading(false);
    }
  };

  // Calculate indicators for all watchlist
  const handleCalculateIndicators = async () => {
    setLoading(true);
    setMessage('');
    try {
      let successCount = 0;
      for (const ticker of watchlist) {
        const response = await fetch(`http://localhost:8000/api/indicators/calculate/${ticker}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            timeframe: '1h',
            lookback_periods: 200,
          }),
        });
        if (response.ok) successCount++;
      }
      setMessage(`✓ Indicators calculated for ${successCount}/${watchlist.length} tickers`);
    } catch (error) {
      setMessage(`✗ Failed to calculate indicators: ${error}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold">시스템 제어</h1>
        <p className="text-gray-500 mt-1">System Control & Configuration</p>
      </div>

      {/* Message */}
      {message && (
        <Card className={message.startsWith('✓') ? 'bg-green-50' : 'bg-red-50'}>
          <CardContent className="py-3">
            <p className={message.startsWith('✓') ? 'text-green-700' : 'text-red-700'}>{message}</p>
          </CardContent>
        </Card>
      )}

      {/* Scheduler Control */}
      <Card>
        <CardHeader>
          <CardTitle>스케줄러 제어</CardTitle>
          <CardDescription>Automated data collection and signal generation</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium">Status</p>
              <Badge variant={schedulerStatus?.is_running ? 'default' : 'secondary'}>
                {schedulerStatus?.is_running ? '🟢 Running' : '🔴 Stopped'}
              </Badge>
            </div>
            <div className="flex gap-2">
              <Button
                onClick={handleStartScheduler}
                disabled={loading || schedulerStatus?.is_running}
                className="bg-green-600 hover:bg-green-700"
              >
                <Play className="h-4 w-4 mr-2" />
                Start
              </Button>
              <Button
                onClick={handleStopScheduler}
                disabled={loading || !schedulerStatus?.is_running}
                variant="destructive"
              >
                <Square className="h-4 w-4 mr-2" />
                Stop
              </Button>
            </div>
          </div>

          {schedulerStatus?.jobs && schedulerStatus.jobs.length > 0 && (
            <div className="mt-4 space-y-2">
              <p className="font-medium text-sm text-gray-600">Scheduled Jobs:</p>
              <div className="space-y-1">
                {schedulerStatus.jobs.map((job) => (
                  <div key={job.id} className="flex justify-between items-center text-sm p-2 bg-gray-50 rounded">
                    <span>{job.name}</span>
                    <span className="text-gray-500">
                      Next: {job.next_run_time ? new Date(job.next_run_time).toLocaleString() : 'N/A'}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Watchlist Management */}
      <Card>
        <CardHeader>
          <CardTitle>워치리스트 관리</CardTitle>
          <CardDescription>Manage tickers to monitor</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex gap-2">
            <Input
              placeholder="Enter ticker (e.g., AAPL)"
              value={newTicker}
              onChange={(e) => setNewTicker(e.target.value.toUpperCase())}
              onKeyPress={(e) => e.key === 'Enter' && handleAddToWatchlist()}
            />
            <Button onClick={handleAddToWatchlist} disabled={loading || !newTicker.trim()}>
              <Plus className="h-4 w-4 mr-2" />
              Add
            </Button>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
            {watchlist.map((ticker) => (
              <div
                key={ticker}
                className="flex items-center justify-between p-3 border rounded-lg bg-gray-50"
              >
                <span className="font-semibold">{ticker}</span>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => handleRemoveFromWatchlist(ticker)}
                  disabled={loading}
                >
                  <Trash2 className="h-4 w-4 text-red-500" />
                </Button>
              </div>
            ))}
          </div>

          {watchlist.length === 0 && (
            <p className="text-center text-gray-400 py-8">No tickers in watchlist</p>
          )}
        </CardContent>
      </Card>

      {/* Manual Actions */}
      <Card>
        <CardHeader>
          <CardTitle>수동 작업</CardTitle>
          <CardDescription>Manual data collection and processing</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <Button onClick={handleManualDataCollection} disabled={loading} variant="outline">
              <Database className="h-4 w-4 mr-2" />
              Collect Market Data
            </Button>

            <Button onClick={handleCalculateIndicators} disabled={loading || watchlist.length === 0} variant="outline">
              <TrendingUp className="h-4 w-4 mr-2" />
              Calculate Indicators
            </Button>

            <Button onClick={handleGenerateDailyReport} disabled={loading} variant="outline">
              <RefreshCw className="h-4 w-4 mr-2" />
              Generate Daily Report
            </Button>

            <Button
              onClick={() => window.location.href = 'http://localhost:8000/docs'}
              variant="outline"
            >
              <AlertCircle className="h-4 w-4 mr-2" />
              API Documentation
            </Button>
          </div>

          <div className="mt-4 p-4 bg-blue-50 rounded-lg">
            <p className="text-sm text-blue-700">
              💡 <strong>Tip:</strong> Start the scheduler for automatic data collection every 15-30 minutes.
              Add tickers to watchlist to monitor specific stocks.
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Quick Setup Guide */}
      <Card>
        <CardHeader>
          <CardTitle>빠른 시작 가이드</CardTitle>
        </CardHeader>
        <CardContent>
          <ol className="space-y-3 text-sm">
            <li className="flex gap-3">
              <span className="font-bold text-blue-600">1.</span>
              <span>워치리스트에 모니터링할 종목 추가 (예: AAPL, MSFT, GOOGL)</span>
            </li>
            <li className="flex gap-3">
              <span className="font-bold text-blue-600">2.</span>
              <span>"Calculate Indicators" 버튼 클릭하여 초기 지표 계산</span>
            </li>
            <li className="flex gap-3">
              <span className="font-bold text-blue-600">3.</span>
              <span>"Start" 버튼 클릭하여 스케줄러 시작 (자동 데이터 수집)</span>
            </li>
            <li className="flex gap-3">
              <span className="font-bold text-blue-600">4.</span>
              <span>알고리즘 대시보드(/algorithm)에서 신호 확인</span>
            </li>
            <li className="flex gap-3">
              <span className="font-bold text-blue-600">5.</span>
              <span>주문 관리(/orders)에서 실제 매매 실행</span>
            </li>
          </ol>
        </CardContent>
      </Card>
    </div>
  );
};
