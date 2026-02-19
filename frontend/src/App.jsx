import { useState, useEffect } from 'react'
import useWebSocket from './hooks/useWebSocket'
import SupplierPanel from './components/SupplierPanel'
import CustomerPanel from './components/CustomerPanel'
import DispatchPanel from './components/DispatchPanel'
import OrdersPanel from './components/OrdersPanel'
import DeliveryTracker from './components/DeliveryTracker'
import SystemDashboard from './components/SystemDashboard'

function App() {
  const [orders, setOrders] = useState([])
  const [trackingOrderId, setTrackingOrderId] = useState(null)
  const [currentView, setCurrentView] = useState('marketplace') // 'marketplace' or 'dashboard'
  
  const { isConnected } = useWebSocket((event) => {
    setOrders(prev => {
      const existing = prev.findIndex(o => o.order.id === event.order.id)
      if (existing >= 0) {
        const updated = [...prev]
        updated[existing] = event
        return updated
      }
      return [event, ...prev]
    })
  })

  // Load existing orders on mount
  useEffect(() => {
    const loadOrders = async () => {
      try {
        const response = await fetch('http://localhost:8000/api/orders')
        const existingOrders = await response.json()
        
        // Convert to event format
        const orderEvents = existingOrders.map(order => ({
          event_type: `order.${order.status}`,
          order: order,
          timestamp: order.updated_at || order.created_at
        }))
        
        setOrders(orderEvents)
        console.log('Loaded existing orders:', orderEvents.length)
      } catch (error) {
        console.error('Failed to load orders:', error)
      }
    }
    
    loadOrders()
  }, [])

  return (
    <div style={{ fontFamily: 'sans-serif' }}>
      {/* Navigation Bar */}
      <nav style={{
        background: '#1f2937',
        padding: '0 20px',
        boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
        position: 'sticky',
        top: 0,
        zIndex: 100
      }}>
        <div style={{
          maxWidth: '1600px',
          margin: '0 auto',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          height: '60px'
        }}>
          <h1 style={{ margin: 0, fontSize: '20px', color: 'white' }}>
            🍕 Pizza Delivery Platform
          </h1>
          
          <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
            <button
              onClick={() => setCurrentView('marketplace')}
              style={{
                padding: '8px 16px',
                background: currentView === 'marketplace' ? '#3b82f6' : 'transparent',
                color: 'white',
                border: '1px solid #4b5563',
                borderRadius: '6px',
                cursor: 'pointer',
                fontSize: '14px',
                fontWeight: '500',
                transition: 'all 0.2s'
              }}
            >
              🏪 Marketplace
            </button>
            
            <button
              onClick={() => setCurrentView('dashboard')}
              style={{
                padding: '8px 16px',
                background: currentView === 'dashboard' ? '#3b82f6' : 'transparent',
                color: 'white',
                border: '1px solid #4b5563',
                borderRadius: '6px',
                cursor: 'pointer',
                fontSize: '14px',
                fontWeight: '500',
                transition: 'all 0.2s'
              }}
            >
              📊 Dashboard
            </button>
            
            <div style={{
              padding: '6px 12px',
              background: isConnected ? '#10b981' : '#ef4444',
              borderRadius: '20px',
              fontSize: '12px',
              color: 'white',
              fontWeight: '500'
            }}>
              {isConnected ? '🟢 Connected' : '🔴 Disconnected'}
            </div>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <div style={{ padding: '20px', maxWidth: '1600px', margin: '0 auto' }}>
        {currentView === 'marketplace' ? (
          <>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '20px', marginBottom: '30px' }}>
              <SupplierPanel orders={orders} />
              <CustomerPanel orders={orders} />
              <DispatchPanel orders={orders} />
            </div>

            <OrdersPanel orders={orders} onTrackDelivery={setTrackingOrderId} />
          </>
        ) : (
          <SystemDashboard />
        )}
      </div>

      {/* Delivery Tracker Modal */}
      {trackingOrderId && (
        <DeliveryTracker
          orderId={trackingOrderId}
          onClose={() => setTrackingOrderId(null)}
        />
      )}
    </div>
  )
}

export default App
