import { useState, useEffect } from 'react'
import useWebSocket from './hooks/useWebSocket'
import SupplierPanel from './components/SupplierPanel'
import CustomerPanel from './components/CustomerPanel'
import DispatchPanel from './components/DispatchPanel'
import OrdersPanel from './components/OrdersPanel'

function App() {
  const [orders, setOrders] = useState([])
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
    <div style={{ padding: '20px', fontFamily: 'sans-serif', maxWidth: '1600px', margin: '0 auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '30px' }}>
        <h1>🍕 Pizza Delivery Marketplace</h1>
        <div>Status: {isConnected ? '🟢 Connected' : '🔴 Disconnected'}</div>
      </div>
      
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '20px', marginBottom: '30px' }}>
        <SupplierPanel orders={orders} />
        <CustomerPanel orders={orders} />
        <DispatchPanel orders={orders} />
      </div>

      <OrdersPanel orders={orders} />
    </div>
  )
}

export default App
