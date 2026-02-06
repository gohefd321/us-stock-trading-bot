/**
 * Order Book Component
 *
 * 실시간 호가창 (10호가)
 */

import React, { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface OrderBookEntry {
  price: number;
  volume: number;
}

interface OrderBookData {
  ticker: string;
  asks: OrderBookEntry[];
  bids: OrderBookEntry[];
  total_ask_volume: number;
  total_bid_volume: number;
  updated_at: string;
}

interface OrderBookProps {
  ticker: string;
}

export const OrderBook: React.FC<OrderBookProps> = ({ ticker }) => {
  const [orderBook, setOrderBook] = useState<OrderBookData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchOrderBook = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`http://localhost:8000/api/realtime/orderbook/${ticker}/latest`);

      if (!response.ok) {
        throw new Error('Failed to fetch order book');
      }

      const data = await response.json();
      setOrderBook(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (ticker) {
      fetchOrderBook();

      // Auto-refresh every 3 seconds
      const interval = setInterval(fetchOrderBook, 3000);
      return () => clearInterval(interval);
    }
  }, [ticker]);

  const getVolumeBarWidth = (volume: number, maxVolume: number) => {
    return (volume / maxVolume) * 100;
  };

  const maxAskVolume = orderBook ? Math.max(...orderBook.asks.map(a => a.volume || 0)) : 0;
  const maxBidVolume = orderBook ? Math.max(...orderBook.bids.map(b => b.volume || 0)) : 0;

  return (
    <Card>
      <CardHeader>
        <div className="flex justify-between items-center">
          <CardTitle>Order Book - {ticker}</CardTitle>
          <Button size="sm" variant="outline" onClick={fetchOrderBook} disabled={loading}>
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          </Button>
        </div>
      </CardHeader>

      <CardContent>
        {error && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
            {error}
          </div>
        )}

        {orderBook ? (
          <div className="space-y-4">
            {/* Asks (매도) */}
            <div>
              <div className="flex justify-between text-xs font-medium text-gray-500 mb-2">
                <span>Ask Price</span>
                <span>Volume</span>
              </div>

              <div className="space-y-1">
                {orderBook.asks.slice(0, 10).reverse().map((ask, idx) => (
                  <div key={idx} className="relative">
                    {/* Volume bar */}
                    <div
                      className="absolute top-0 right-0 h-full bg-red-100 transition-all"
                      style={{ width: `${getVolumeBarWidth(ask.volume, maxAskVolume)}%` }}
                    />

                    {/* Price and Volume */}
                    <div className="relative flex justify-between text-sm py-1 px-2">
                      <span className="font-medium text-red-600">
                        ${ask.price?.toFixed(2) || 'N/A'}
                      </span>
                      <span className="text-gray-700">
                        {ask.volume?.toLocaleString() || 'N/A'}
                      </span>
                    </div>
                  </div>
                ))}
              </div>

              <div className="text-xs text-gray-500 mt-2">
                Total Ask: {orderBook.total_ask_volume.toLocaleString()}
              </div>
            </div>

            {/* Spread */}
            <div className="border-t border-b border-gray-300 py-2 text-center">
              <span className="text-sm font-medium text-gray-600">
                Spread: ${((orderBook.asks[0]?.price || 0) - (orderBook.bids[0]?.price || 0)).toFixed(2)}
              </span>
            </div>

            {/* Bids (매수) */}
            <div>
              <div className="flex justify-between text-xs font-medium text-gray-500 mb-2">
                <span>Bid Price</span>
                <span>Volume</span>
              </div>

              <div className="space-y-1">
                {orderBook.bids.slice(0, 10).map((bid, idx) => (
                  <div key={idx} className="relative">
                    {/* Volume bar */}
                    <div
                      className="absolute top-0 right-0 h-full bg-green-100 transition-all"
                      style={{ width: `${getVolumeBarWidth(bid.volume, maxBidVolume)}%` }}
                    />

                    {/* Price and Volume */}
                    <div className="relative flex justify-between text-sm py-1 px-2">
                      <span className="font-medium text-green-600">
                        ${bid.price?.toFixed(2) || 'N/A'}
                      </span>
                      <span className="text-gray-700">
                        {bid.volume?.toLocaleString() || 'N/A'}
                      </span>
                    </div>
                  </div>
                ))}
              </div>

              <div className="text-xs text-gray-500 mt-2">
                Total Bid: {orderBook.total_bid_volume.toLocaleString()}
              </div>
            </div>

            {/* Last Update */}
            <div className="text-xs text-gray-400 text-center">
              Last update: {new Date(orderBook.updated_at).toLocaleTimeString()}
            </div>
          </div>
        ) : (
          <div className="text-center py-8 text-gray-400">
            {loading ? 'Loading...' : 'No data available'}
          </div>
        )}
      </CardContent>
    </Card>
  );
};
