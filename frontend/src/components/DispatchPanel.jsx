import { useState } from 'react'

function DispatchPanel({ orders }) {
  const [selectedOrder, setSelectedOrder] = useState('')
  const [driverName, setDriverName] = useState('')

  const readyOrders = orders.filter(e => e.order.status === 'ready')

  const handleDispatch = async (e) => {
    e.preventDefault()
    
    await fetch(`http://localhost:8000/api/orders/${selectedOrder}/dispatch?driver_name=${encodeURIComponent(driverName)}`, {
      method: 'POST'
    })
    
    setSelectedOrder('')
    setDriverName('')
  }

  return (
    <div style={{ border: '2px solid #a78bfa', borderRadius: '8px', padding: '20px', backgroundColor: '#f5f3ff' }}>
      <h2>🚗 Dispatch</h2>
      
      <h3 style={{ marginTop: '0' }}>Ready for Delivery ({readyOrders.length})</h3>
      {readyOrders.length === 0 ? (
        <p style={{ color: '#666', fontSize: '13px' }}>No orders ready</p>
      ) : (
        <form onSubmit={handleDispatch}>
          <div style={{ marginBottom: '8px' }}>
            <select
              value={selectedOrder}
              onChange={(e) => setSelectedOrder(e.target.value)}
              required
              style={{ width: '100%', padding: '6px', boxSizing: 'border-box', fontSize: '13px' }}
            >
              <option value="">Select Order</option>
              {readyOrders.map(e => (
                <option key={e.order.id} value={e.order.id}>
                  {e.order.pizza_name} → {e.order.delivery_address}
                </option>
              ))}
            </select>
          </div>
          <div style={{ marginBottom: '8px' }}>
            <input
              type="text"
              placeholder="Driver Name"
              value={driverName}
              onChange={(e) => setDriverName(e.target.value)}
              required
              style={{ width: '100%', padding: '6px', boxSizing: 'border-box', fontSize: '13px' }}
            />
          </div>
          <button type="submit" style={{ width: '100%', padding: '8px', backgroundColor: '#a78bfa', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer', fontSize: '13px' }}>
            Dispatch Order
          </button>
        </form>
      )}
    </div>
  )
}

export default DispatchPanel
