/**
 * Realtime Trading Dashboard
 *
 * 실시간 트레이딩 대시보드
 * - 실시간 가격
 * - 호가창
 * - OHLCV 차트 (향후 추가)
 */

import React, { useState } from 'react';
import { RealtimePrice } from '@/components/realtime/RealtimePrice';
import { OrderBook } from '@/components/realtime/OrderBook';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Search } from 'lucide-react';

export const RealtimePage: React.FC = () => {
  const [ticker, setTicker] = useState('AAPL');
  const [searchTicker, setSearchTicker] = useState('AAPL');

  const handleSearch = () => {
    if (searchTicker.trim()) {
      setTicker(searchTicker.trim().toUpperCase());
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      handleSearch();
    }
  };

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">실시간 트레이딩</h1>
          <p className="text-gray-500 mt-1">Real-time market data via WebSocket</p>
        </div>
      </div>

      {/* Search */}
      <Card>
        <CardHeader>
          <CardTitle>Stock Search</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-2">
            <Input
              placeholder="Enter ticker symbol (e.g., AAPL, TSLA, NVDA)"
              value={searchTicker}
              onChange={(e) => setSearchTicker(e.target.value)}
              onKeyPress={handleKeyPress}
              className="flex-1"
            />
            <Button onClick={handleSearch}>
              <Search className="h-4 w-4 mr-2" />
              Search
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Quick Access */}
      <div className="flex gap-2 flex-wrap">
        {['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'TSLA', 'META'].map((symbol) => (
          <Button
            key={symbol}
            variant={ticker === symbol ? 'default' : 'outline'}
            size="sm"
            onClick={() => {
              setTicker(symbol);
              setSearchTicker(symbol);
            }}
          >
            {symbol}
          </Button>
        ))}
      </div>

      {/* Real-time Data */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Realtime Price */}
        <RealtimePrice ticker={ticker} autoConnect={true} />

        {/* Order Book */}
        <OrderBook ticker={ticker} />
      </div>

      {/* OHLCV Chart Placeholder */}
      <Card>
        <CardHeader>
          <CardTitle>Price Chart (Coming Soon)</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-64 flex items-center justify-center bg-gray-50 rounded-lg">
            <p className="text-gray-400">OHLCV Chart will be displayed here</p>
          </div>
        </CardContent>
      </Card>

      {/* Info */}
      <Card className="bg-blue-50">
        <CardContent className="pt-6">
          <div className="space-y-2 text-sm">
            <p className="font-medium text-blue-900">💡 실시간 데이터 안내</p>
            <ul className="list-disc list-inside space-y-1 text-blue-800">
              <li>실시간 가격은 한국투자증권 WebSocket API를 통해 제공됩니다</li>
              <li>호가창은 10호가까지 표시되며 3초마다 자동 갱신됩니다</li>
              <li>차트 기능은 Phase 3에서 추가될 예정입니다</li>
            </ul>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};
