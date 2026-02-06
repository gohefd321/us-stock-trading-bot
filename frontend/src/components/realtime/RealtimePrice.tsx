/**
 * Realtime Price Component
 *
 * WebSocket을 통한 실시간 가격 표시
 */

import React, { useEffect, useState, useCallback } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { TrendingUp, TrendingDown, Minus, RefreshCw } from 'lucide-react';

interface RealtimePriceData {
  ticker: string;
  price: number;
  change: number;
  change_rate: number;
  volume: number;
  time: string;
}

interface RealtimePriceProps {
  ticker: string;
  autoConnect?: boolean;
}

export const RealtimePrice: React.FC<RealtimePriceProps> = ({
  ticker,
  autoConnect = true
}) => {
  const [priceData, setPriceData] = useState<RealtimePriceData | null>(null);
  const [ws, setWs] = useState<WebSocket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const connectWebSocket = useCallback(() => {
    if (ws) {
      ws.close();
    }

    setError(null);

    // WebSocket 연결
    const wsUrl = `ws://localhost:8000/api/realtime/ws/${ticker}`;
    const newWs = new WebSocket(wsUrl);

    newWs.onopen = () => {
      console.log(`WebSocket connected for ${ticker}`);
      setIsConnected(true);
      setError(null);
    };

    newWs.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'realtime_price') {
          setPriceData(data);
        }
      } catch (err) {
        console.error('Failed to parse WebSocket message:', err);
      }
    };

    newWs.onerror = (event) => {
      console.error('WebSocket error:', event);
      setError('WebSocket connection error');
      setIsConnected(false);
    };

    newWs.onclose = () => {
      console.log(`WebSocket disconnected for ${ticker}`);
      setIsConnected(false);
    };

    setWs(newWs);
  }, [ticker, ws]);

  const disconnectWebSocket = useCallback(() => {
    if (ws) {
      ws.close();
      setWs(null);
      setIsConnected(false);
    }
  }, [ws]);

  useEffect(() => {
    if (autoConnect && ticker) {
      connectWebSocket();
    }

    return () => {
      if (ws) {
        ws.close();
      }
    };
  }, [ticker, autoConnect]);

  const getTrendIcon = () => {
    if (!priceData || priceData.change === 0) return <Minus className="h-4 w-4" />;
    return priceData.change > 0
      ? <TrendingUp className="h-4 w-4" />
      : <TrendingDown className="h-4 w-4" />;
  };

  const getTrendColor = () => {
    if (!priceData) return 'text-gray-500';
    if (priceData.change > 0) return 'text-green-600';
    if (priceData.change < 0) return 'text-red-600';
    return 'text-gray-500';
  };

  const getBackgroundColor = () => {
    if (!priceData) return 'bg-white';
    if (priceData.change > 0) return 'bg-green-50';
    if (priceData.change < 0) return 'bg-red-50';
    return 'bg-white';
  };

  return (
    <Card className={`transition-colors duration-300 ${getBackgroundColor()}`}>
      <CardHeader>
        <div className="flex justify-between items-center">
          <div>
            <CardTitle className="text-2xl font-bold">{ticker}</CardTitle>
            <CardDescription>Real-time Price</CardDescription>
          </div>
          <div className="flex gap-2">
            {isConnected ? (
              <Badge variant="default" className="bg-green-500">Live</Badge>
            ) : (
              <Badge variant="secondary">Disconnected</Badge>
            )}
            <Button
              size="sm"
              variant="outline"
              onClick={isConnected ? disconnectWebSocket : connectWebSocket}
            >
              <RefreshCw className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </CardHeader>

      <CardContent>
        {error && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
            {error}
          </div>
        )}

        {priceData ? (
          <div className="space-y-4">
            {/* Current Price */}
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-gray-500">Current Price</span>
              <div className="flex items-center gap-2">
                <span className={`text-3xl font-bold ${getTrendColor()}`}>
                  ${priceData.price.toFixed(2)}
                </span>
                {getTrendIcon()}
              </div>
            </div>

            {/* Change */}
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-gray-500">Change</span>
              <div className="text-right">
                <div className={`text-lg font-semibold ${getTrendColor()}`}>
                  {priceData.change > 0 ? '+' : ''}{priceData.change.toFixed(2)}
                </div>
                <div className={`text-sm ${getTrendColor()}`}>
                  ({priceData.change_rate > 0 ? '+' : ''}{priceData.change_rate.toFixed(2)}%)
                </div>
              </div>
            </div>

            {/* Volume */}
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-gray-500">Volume</span>
              <span className="text-lg font-semibold">
                {priceData.volume.toLocaleString()}
              </span>
            </div>

            {/* Last Update */}
            <div className="flex items-center justify-between text-xs text-gray-400">
              <span>Last Update</span>
              <span>{new Date(priceData.time).toLocaleTimeString()}</span>
            </div>
          </div>
        ) : (
          <div className="text-center py-8 text-gray-400">
            {isConnected ? 'Waiting for data...' : 'Not connected'}
          </div>
        )}
      </CardContent>
    </Card>
  );
};
