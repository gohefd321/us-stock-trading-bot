/**
 * Order Management Page
 *
 * 주문 관리 대시보드
 * - 매수/매도 주문 생성
 * - 활성 주문 조회
 * - 주문 히스토리
 * - 포지션 조회
 */

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { ArrowUp, ArrowDown, TrendingUp, DollarSign, Activity, RefreshCw, AlertTriangle, CheckCircle } from 'lucide-react';

interface Order {
  order_id: number;
  order_number: string;
  ticker: string;
  order_type: string;
  order_quantity: number;
  filled_quantity: number;
  status: string;
  submitted_at: string;
  filled_at?: string;
}

interface Position {
  ticker: string;
  quantity: number;
  avg_buy_price: number;
  current_price: number;
  current_value: number;
  unrealized_pnl: number;
  unrealized_pnl_pct: number;
  portfolio_weight: number;
}

export const OrderManagementPage: React.FC = () => {
  const [ticker, setTicker] = useState('AAPL');
  const [quantity, setQuantity] = useState('10');
  const [orderMethod, setOrderMethod] = useState('MARKET');
  const [price, setPrice] = useState('');
  const [stopLossPct, setStopLossPct] = useState('5');
  const [takeProfitPct, setTakeProfitPct] = useState('10');

  const [activeOrders, setActiveOrders] = useState<Order[]>([]);
  const [orderHistory, setOrderHistory] = useState<Order[]>([]);
  const [positions, setPositions] = useState<Position[]>([]);

  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');

  // Fetch data
  const fetchActiveOrders = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/orders/active');
      if (response.ok) {
        const data = await response.json();
        setActiveOrders(data.orders);
      }
    } catch (error) {
      console.error('Failed to fetch active orders:', error);
    }
  };

  const fetchOrderHistory = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/orders/history?limit=20');
      if (response.ok) {
        const data = await response.json();
        setOrderHistory(data.orders);
      }
    } catch (error) {
      console.error('Failed to fetch order history:', error);
    }
  };

  const fetchPositions = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/portfolio/positions');
      if (response.ok) {
        const data = await response.json();
        setPositions(data.positions);
      }
    } catch (error) {
      console.error('Failed to fetch positions:', error);
    }
  };

  useEffect(() => {
    fetchActiveOrders();
    fetchOrderHistory();
    fetchPositions();

    // Refresh every 30 seconds
    const interval = setInterval(() => {
      fetchActiveOrders();
      fetchPositions();
    }, 30000);

    return () => clearInterval(interval);
  }, []);

  // Create buy order
  const handleBuyOrder = async () => {
    setLoading(true);
    setMessage('');

    try {
      const response = await fetch('http://localhost:8000/api/orders/buy', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ticker: ticker,
          quantity: parseInt(quantity),
          order_method: orderMethod,
          price: price ? parseFloat(price) : 0,
          stop_loss_pct: stopLossPct ? parseFloat(stopLossPct) : null,
          take_profit_pct: takeProfitPct ? parseFloat(takeProfitPct) : null,
        }),
      });

      const data = await response.json();

      if (response.ok) {
        setMessage(`✓ Buy order created: ${data.order_number}`);
        fetchActiveOrders();
        fetchPositions();
      } else {
        setMessage(`✗ Error: ${data.detail}`);
      }
    } catch (error) {
      setMessage(`✗ Failed to create order: ${error}`);
    } finally {
      setLoading(false);
    }
  };

  // Create sell order
  const handleSellOrder = async () => {
    setLoading(true);
    setMessage('');

    try {
      const response = await fetch('http://localhost:8000/api/orders/sell', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ticker: ticker,
          quantity: parseInt(quantity),
          order_method: orderMethod,
          price: price ? parseFloat(price) : 0,
        }),
      });

      const data = await response.json();

      if (response.ok) {
        setMessage(`✓ Sell order created: ${data.order_number}`);
        fetchActiveOrders();
        fetchPositions();
      } else {
        setMessage(`✗ Error: ${data.detail}`);
      }
    } catch (error) {
      setMessage(`✗ Failed to create order: ${error}`);
    } finally {
      setLoading(false);
    }
  };

  // Check stop loss / take profit
  const handleCheckStopLoss = async () => {
    setLoading(true);
    try {
      const response = await fetch('http://localhost:8000/api/orders/check-stop-loss-take-profit', {
        method: 'POST',
      });

      if (response.ok) {
        const data = await response.json();
        setMessage(`✓ Checked stop loss/take profit: ${data.count} orders triggered`);
        fetchActiveOrders();
        fetchPositions();
      }
    } catch (error) {
      setMessage(`✗ Failed to check: ${error}`);
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadge = (status: string) => {
    const colorMap: { [key: string]: string } = {
      SUBMITTED: 'bg-blue-500',
      PENDING: 'bg-yellow-500',
      PARTIAL_FILLED: 'bg-orange-500',
      FILLED: 'bg-green-500',
      CANCELLED: 'bg-gray-500',
      REJECTED: 'bg-red-500',
    };

    return (
      <Badge className={colorMap[status] || 'bg-gray-500'}>
        {status}
      </Badge>
    );
  };

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">주문 관리</h1>
          <p className="text-gray-500 mt-1">Order Management & Portfolio Positions</p>
        </div>
        <Button onClick={handleCheckStopLoss} disabled={loading}>
          <AlertTriangle className="h-4 w-4 mr-2" />
          Check Stop Loss/Take Profit
        </Button>
      </div>

      {/* Message */}
      {message && (
        <Card className={message.startsWith('✓') ? 'bg-green-50' : 'bg-red-50'}>
          <CardContent className="py-3">
            <p className={message.startsWith('✓') ? 'text-green-700' : 'text-red-700'}>
              {message}
            </p>
          </CardContent>
        </Card>
      )}

      {/* Order Creation */}
      <Card>
        <CardHeader>
          <CardTitle>주문 생성</CardTitle>
          <CardDescription>Create Buy/Sell Order</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <Label>Ticker</Label>
              <Input
                placeholder="AAPL"
                value={ticker}
                onChange={(e) => setTicker(e.target.value.toUpperCase())}
              />
            </div>
            <div>
              <Label>Quantity</Label>
              <Input
                type="number"
                placeholder="10"
                value={quantity}
                onChange={(e) => setQuantity(e.target.value)}
              />
            </div>
            <div>
              <Label>Order Method</Label>
              <Select value={orderMethod} onValueChange={setOrderMethod}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="MARKET">Market</SelectItem>
                  <SelectItem value="LIMIT">Limit</SelectItem>
                </SelectContent>
              </Select>
            </div>
            {orderMethod === 'LIMIT' && (
              <div>
                <Label>Price</Label>
                <Input
                  type="number"
                  placeholder="150.00"
                  value={price}
                  onChange={(e) => setPrice(e.target.value)}
                />
              </div>
            )}
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label>Stop Loss (%)</Label>
              <Input
                type="number"
                placeholder="5"
                value={stopLossPct}
                onChange={(e) => setStopLossPct(e.target.value)}
              />
            </div>
            <div>
              <Label>Take Profit (%)</Label>
              <Input
                type="number"
                placeholder="10"
                value={takeProfitPct}
                onChange={(e) => setTakeProfitPct(e.target.value)}
              />
            </div>
          </div>

          <div className="flex gap-2">
            <Button onClick={handleBuyOrder} disabled={loading} className="flex-1 bg-green-600 hover:bg-green-700">
              <ArrowUp className="h-4 w-4 mr-2" />
              Buy
            </Button>
            <Button onClick={handleSellOrder} disabled={loading} className="flex-1 bg-red-600 hover:bg-red-700">
              <ArrowDown className="h-4 w-4 mr-2" />
              Sell
            </Button>
          </div>
        </CardContent>
      </Card>

      <Tabs defaultValue="positions" className="w-full">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="positions">Positions</TabsTrigger>
          <TabsTrigger value="active">Active Orders</TabsTrigger>
          <TabsTrigger value="history">Order History</TabsTrigger>
        </TabsList>

        {/* Positions */}
        <TabsContent value="positions" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Portfolio Positions</CardTitle>
              <CardDescription>Current holdings and P&L</CardDescription>
            </CardHeader>
            <CardContent>
              {positions.length > 0 ? (
                <div className="space-y-3">
                  {positions.map((pos) => (
                    <div key={pos.ticker} className="p-4 border rounded-lg">
                      <div className="flex justify-between items-center">
                        <div>
                          <h3 className="font-bold text-lg">{pos.ticker}</h3>
                          <p className="text-sm text-gray-500">
                            {pos.quantity} shares @ ${pos.avg_buy_price?.toFixed(2)}
                          </p>
                        </div>
                        <div className="text-right">
                          <p className="text-lg font-semibold">
                            ${pos.current_value?.toFixed(2)}
                          </p>
                          <Badge variant={pos.unrealized_pnl >= 0 ? 'default' : 'destructive'}>
                            {pos.unrealized_pnl >= 0 ? '+' : ''}
                            ${pos.unrealized_pnl?.toFixed(2)} ({pos.unrealized_pnl_pct?.toFixed(2)}%)
                          </Badge>
                        </div>
                      </div>
                      <div className="mt-2 grid grid-cols-3 gap-2 text-sm">
                        <div>
                          <p className="text-gray-500">Current Price</p>
                          <p className="font-medium">${pos.current_price?.toFixed(2)}</p>
                        </div>
                        <div>
                          <p className="text-gray-500">Portfolio Weight</p>
                          <p className="font-medium">{pos.portfolio_weight?.toFixed(1)}%</p>
                        </div>
                        <div>
                          <p className="text-gray-500">Value</p>
                          <p className="font-medium">${pos.current_value?.toFixed(2)}</p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-center text-gray-400 py-8">No positions</p>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Active Orders */}
        <TabsContent value="active" className="space-y-4">
          <Card>
            <CardHeader>
              <div className="flex justify-between items-center">
                <CardTitle>Active Orders</CardTitle>
                <Button size="sm" variant="outline" onClick={fetchActiveOrders}>
                  <RefreshCw className="h-4 w-4" />
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {activeOrders.length > 0 ? (
                <div className="space-y-2">
                  {activeOrders.map((order) => (
                    <div key={order.order_id} className="p-3 border rounded flex justify-between items-center">
                      <div>
                        <div className="flex items-center gap-2">
                          <Badge variant={order.order_type === 'BUY' ? 'default' : 'destructive'}>
                            {order.order_type}
                          </Badge>
                          <span className="font-semibold">{order.ticker}</span>
                        </div>
                        <p className="text-sm text-gray-500 mt-1">
                          {order.filled_quantity}/{order.order_quantity} filled
                        </p>
                      </div>
                      <div className="text-right">
                        {getStatusBadge(order.status)}
                        <p className="text-xs text-gray-500 mt-1">
                          {new Date(order.submitted_at).toLocaleString()}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-center text-gray-400 py-8">No active orders</p>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Order History */}
        <TabsContent value="history" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Order History</CardTitle>
            </CardHeader>
            <CardContent>
              {orderHistory.length > 0 ? (
                <div className="space-y-2">
                  {orderHistory.map((order) => (
                    <div key={order.order_id} className="p-3 border rounded">
                      <div className="flex justify-between items-center">
                        <div className="flex items-center gap-2">
                          <Badge variant={order.order_type === 'BUY' ? 'default' : 'destructive'}>
                            {order.order_type}
                          </Badge>
                          <span className="font-semibold">{order.ticker}</span>
                          <span className="text-sm text-gray-500">x{order.order_quantity}</span>
                        </div>
                        <div className="text-right">
                          {getStatusBadge(order.status)}
                        </div>
                      </div>
                      <p className="text-xs text-gray-500 mt-2">
                        Submitted: {new Date(order.submitted_at).toLocaleString()}
                        {order.filled_at && ` | Filled: ${new Date(order.filled_at).toLocaleString()}`}
                      </p>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-center text-gray-400 py-8">No order history</p>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};
