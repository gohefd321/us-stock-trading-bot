/**
 * Algorithm Dashboard
 *
 * 알고리즘 트레이딩 대시보드
 * - 기술적 지표
 * - 트레이딩 전략
 * - 실시간 신호
 * - 백테스팅 결과
 */

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { TrendingUp, TrendingDown, Activity, BarChart3, Zap, RefreshCw } from 'lucide-react';

interface TradingSignal {
  ticker: string;
  signal_type: string;
  strength: number;
  confidence: number;
  strategy_name: string;
  reason: string;
  created_at: string;
}

interface BacktestResult {
  id: number;
  ticker: string;
  strategy: string;
  metrics: {
    total_return: number;
    sharpe_ratio: number;
    max_drawdown: number;
    win_rate: number;
  };
  created_at: string;
}

export const AlgorithmDashboard: React.FC = () => {
  const [ticker, setTicker] = useState('AAPL');
  const [latestSignal, setLatestSignal] = useState<TradingSignal | null>(null);
  const [backtestResults, setBacktestResults] = useState<BacktestResult[]>([]);
  const [schedulerStatus, setSchedulerStatus] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  // 최신 신호 조회
  const fetchLatestSignal = async () => {
    try {
      const response = await fetch(`http://localhost:8000/api/signals/${ticker}/latest`);
      if (response.ok) {
        const data = await response.json();
        setLatestSignal(data);
      }
    } catch (error) {
      console.error('Failed to fetch signal:', error);
    }
  };

  // 백테스트 결과 조회
  const fetchBacktestResults = async () => {
    try {
      const response = await fetch(`http://localhost:8000/api/backtest/results?limit=5`);
      if (response.ok) {
        const data = await response.json();
        setBacktestResults(data.results);
      }
    } catch (error) {
      console.error('Failed to fetch backtest results:', error);
    }
  };

  // 스케줄러 상태 조회
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

  // 신호 생성
  const generateSignal = async () => {
    setLoading(true);
    try {
      const response = await fetch('http://localhost:8000/api/signals/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ticker: ticker,
          timeframe: '1h',
          strategy_names: ['MA_CROSS', 'RSI', 'MACD'],
        }),
      });

      if (response.ok) {
        await fetchLatestSignal();
      }
    } catch (error) {
      console.error('Failed to generate signal:', error);
    } finally {
      setLoading(false);
    }
  };

  // 스케줄러 시작
  const startScheduler = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/scheduler/start', {
        method: 'POST',
      });
      if (response.ok) {
        await fetchSchedulerStatus();
      }
    } catch (error) {
      console.error('Failed to start scheduler:', error);
    }
  };

  useEffect(() => {
    fetchLatestSignal();
    fetchBacktestResults();
    fetchSchedulerStatus();
  }, [ticker]);

  const getSignalColor = (signalType: string) => {
    if (signalType === 'BUY') return 'bg-green-500';
    if (signalType === 'SELL') return 'bg-red-500';
    return 'bg-gray-500';
  };

  const getSignalIcon = (signalType: string) => {
    if (signalType === 'BUY') return <TrendingUp className="h-4 w-4" />;
    if (signalType === 'SELL') return <TrendingDown className="h-4 w-4" />;
    return <Activity className="h-4 w-4" />;
  };

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">알고리즘 트레이딩 대시보드</h1>
          <p className="text-gray-500 mt-1">Quantitative Trading Algorithm Dashboard</p>
        </div>

        {schedulerStatus && (
          <Badge variant={schedulerStatus.is_running ? 'default' : 'secondary'}>
            Scheduler: {schedulerStatus.is_running ? 'Running' : 'Stopped'}
          </Badge>
        )}
      </div>

      {/* Ticker Search */}
      <Card>
        <CardHeader>
          <CardTitle>종목 검색</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-2">
            <Input
              placeholder="Enter ticker symbol (e.g., AAPL)"
              value={ticker}
              onChange={(e) => setTicker(e.target.value.toUpperCase())}
              className="flex-1"
            />
            <Button onClick={generateSignal} disabled={loading}>
              <Zap className="h-4 w-4 mr-2" />
              Generate Signal
            </Button>
          </div>
        </CardContent>
      </Card>

      <Tabs defaultValue="signals" className="w-full">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="signals">트레이딩 신호</TabsTrigger>
          <TabsTrigger value="backtest">백테스트 결과</TabsTrigger>
          <TabsTrigger value="scheduler">스케줄러</TabsTrigger>
        </TabsList>

        {/* Trading Signals */}
        <TabsContent value="signals" className="space-y-4">
          {latestSignal ? (
            <Card>
              <CardHeader>
                <div className="flex justify-between items-center">
                  <div>
                    <CardTitle className="text-2xl">{latestSignal.ticker}</CardTitle>
                    <CardDescription>Latest Trading Signal</CardDescription>
                  </div>
                  <Badge className={getSignalColor(latestSignal.signal_type)}>
                    {getSignalIcon(latestSignal.signal_type)}
                    <span className="ml-2">{latestSignal.signal_type}</span>
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Signal Metrics */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm text-gray-500">Signal Strength</p>
                    <div className="flex items-center gap-2 mt-1">
                      <div className="flex-1 bg-gray-200 rounded-full h-2">
                        <div
                          className="bg-blue-600 h-2 rounded-full"
                          style={{ width: `${latestSignal.strength * 100}%` }}
                        />
                      </div>
                      <span className="text-sm font-medium">
                        {(latestSignal.strength * 100).toFixed(0)}%
                      </span>
                    </div>
                  </div>
                  <div>
                    <p className="text-sm text-gray-500">Confidence</p>
                    <div className="flex items-center gap-2 mt-1">
                      <div className="flex-1 bg-gray-200 rounded-full h-2">
                        <div
                          className="bg-green-600 h-2 rounded-full"
                          style={{ width: `${latestSignal.confidence * 100}%` }}
                        />
                      </div>
                      <span className="text-sm font-medium">
                        {(latestSignal.confidence * 100).toFixed(0)}%
                      </span>
                    </div>
                  </div>
                </div>

                {/* Reason */}
                <div>
                  <p className="text-sm text-gray-500">Reason</p>
                  <p className="mt-1">{latestSignal.reason}</p>
                </div>

                {/* Strategy & Time */}
                <div className="grid grid-cols-2 gap-4 pt-4 border-t">
                  <div>
                    <p className="text-sm text-gray-500">Strategy</p>
                    <p className="font-medium">{latestSignal.strategy_name}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-500">Generated At</p>
                    <p className="font-medium">
                      {new Date(latestSignal.created_at).toLocaleString()}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          ) : (
            <Card>
              <CardContent className="py-12 text-center text-gray-400">
                No signal data available. Generate a signal to see results.
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* Backtest Results */}
        <TabsContent value="backtest" className="space-y-4">
          <div className="grid grid-cols-1 gap-4">
            {backtestResults.map((result) => (
              <Card key={result.id}>
                <CardHeader>
                  <div className="flex justify-between items-center">
                    <div>
                      <CardTitle>{result.ticker}</CardTitle>
                      <CardDescription>{result.strategy}</CardDescription>
                    </div>
                    <Badge
                      variant={result.metrics.total_return > 0 ? 'default' : 'destructive'}
                    >
                      {result.metrics.total_return > 0 ? '+' : ''}
                      {result.metrics.total_return.toFixed(2)}%
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-4 gap-4 text-sm">
                    <div>
                      <p className="text-gray-500">Sharpe Ratio</p>
                      <p className="font-medium text-lg">
                        {result.metrics.sharpe_ratio.toFixed(2)}
                      </p>
                    </div>
                    <div>
                      <p className="text-gray-500">Max Drawdown</p>
                      <p className="font-medium text-lg text-red-600">
                        {result.metrics.max_drawdown.toFixed(2)}%
                      </p>
                    </div>
                    <div>
                      <p className="text-gray-500">Win Rate</p>
                      <p className="font-medium text-lg">
                        {result.metrics.win_rate.toFixed(2)}%
                      </p>
                    </div>
                    <div>
                      <p className="text-gray-500">Date</p>
                      <p className="font-medium text-sm">
                        {new Date(result.created_at).toLocaleDateString()}
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        {/* Scheduler */}
        <TabsContent value="scheduler" className="space-y-4">
          <Card>
            <CardHeader>
              <div className="flex justify-between items-center">
                <CardTitle>Integrated Scheduler</CardTitle>
                {schedulerStatus && (
                  <Button
                    onClick={startScheduler}
                    disabled={schedulerStatus.is_running}
                    size="sm"
                  >
                    {schedulerStatus.is_running ? 'Running' : 'Start Scheduler'}
                  </Button>
                )}
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              {schedulerStatus && (
                <>
                  <div className="grid grid-cols-3 gap-4">
                    <div>
                      <p className="text-sm text-gray-500">Status</p>
                      <Badge variant={schedulerStatus.is_running ? 'default' : 'secondary'}>
                        {schedulerStatus.is_running ? 'Active' : 'Inactive'}
                      </Badge>
                    </div>
                    <div>
                      <p className="text-sm text-gray-500">Watchlist</p>
                      <p className="font-medium">{schedulerStatus.watchlist_count} stocks</p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-500">Scheduled Jobs</p>
                      <p className="font-medium">{schedulerStatus.scheduled_jobs} jobs</p>
                    </div>
                  </div>

                  {/* Scheduled Jobs */}
                  <div className="border-t pt-4">
                    <p className="font-medium mb-3">Scheduled Jobs:</p>
                    <div className="space-y-2">
                      {schedulerStatus.jobs?.map((job: any) => (
                        <div
                          key={job.id}
                          className="flex justify-between items-center p-3 bg-gray-50 rounded"
                        >
                          <div>
                            <p className="font-medium">{job.name}</p>
                            <p className="text-sm text-gray-500">ID: {job.id}</p>
                          </div>
                          {job.next_run && (
                            <p className="text-sm">
                              Next: {new Date(job.next_run).toLocaleString()}
                            </p>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                </>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};
