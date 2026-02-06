import { Routes, Route } from 'react-router-dom'
import { Box } from '@mui/material'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Trading from './pages/Trading'
import Portfolio from './pages/Portfolio'
import Signals from './pages/Signals'
import Settings from './pages/Settings'
import { SystemControlPage } from './pages/SystemControlPage'
import { OrderManagementPage } from './pages/OrderManagementPage'
import { PortfolioOptimizerPage } from './pages/PortfolioOptimizerPage'

function App() {
  return (
    <Box sx={{ display: 'flex', minHeight: '100vh' }}>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/trading" element={<Trading />} />
          <Route path="/portfolio" element={<Portfolio />} />
          <Route path="/signals" element={<Signals />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="/system" element={<SystemControlPage />} />
          <Route path="/orders" element={<OrderManagementPage />} />
          <Route path="/optimizer" element={<PortfolioOptimizerPage />} />
        </Routes>
      </Layout>
    </Box>
  )
}

export default App
