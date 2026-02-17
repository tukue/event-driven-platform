import { useState } from 'react'

function CustomerPanel({ orders }) {
  const [selectedOrder, setSelectedOrder] = useState('')
  const [customerName, setCustomerName] = useState('')
  const [deliveryAddress, setDeliveryAddress] = useState('')

  const availableOrders = orders.filter(e => e.order.status === 'supplier_accepted')

  const handleAccept = async (e) => {
    e.preventDefault()
    
    await fetch(`http://localhost:8000/api/orders/${selectedOrder}/customer-accept?customer_name=${encodeURIComponent(customerName)}&delivery_address=${encodeURIComponent(deliveryAddress)}`, {
      method: 'POST'
    })
    
    setSelectedOrder('')
    setCustomerName('')
    setDeliveryAddress('')
  }

  const selectedOrderData = orders.find(e => e.order.id === selectedOrder)

  return (
    <div style={{ border: '2px solid #4ecdc4', borderRadius: '8px', padding: '20px', backgroundColor: '#f0fffe' }}>
      <h2>👤 Customer</h2>
      
      <h3 style={{ marginTop: '0' }}>Available Orders ({availableOrders.length})</h3>
      {availableOrders.length === 0 ? (
        <p style={{ color: '#666', fontSize: '13px' }}>No orders available</p>
      ) : (
        <form onSubmit={handleAccept}>
          <div style={{ marginBottom: '8px' }}>
            <select
              value={selectedOrder}
              onChange={(e) => setSelectedOrder(e.target.value)}
              required
              style={{ width: '100%', padding: '6px', boxSizing: 'border-box', fontSize: '13px' }}
            >
              <option value="">Select Order</option>
              {availableOrders.map(e => (
                <option key={e.order.id} value={e.order.id}>
                  {e.order.pizza_name} - ${e.order.supplier_price} ({e.order.supplier_name})
                </option>
              ))}
            </select>
          </div>
          {selectedOrderData && (
            <div style={{ padding: '8px', backgroundColor: '#e0f7f7', borderRadius: '4px', marginBottom: '8px', fontSize: '12px' }}>
              <div><strong>Base:</strong> ${selectedOrderData.order.supplier_price}</div>
              <div><strong>Markup:</strong> {selectedOrderData.order.markup_percentage}%</div>
              <div><strong>Your Price:</strong> ${(selectedOrderData.order.supplier_price * (1 + selectedOrderData.order.markup_percentage / 100)).toFixed(2)}</div>
              {selectedOrderData.order.estimated_delivery_time && (
                <div><strong>Est. Time:</strong> {selectedOrderData.order.estimated_delivery_time} min</div>
              )}
              {selectedOrderData.order.supplier_notes && (
                <div><strong>Notes:</strong> {selectedOrderData.order.supplier_notes}</div>
              )}
            </div>
          )}
          <div style={{ marginBottom: '8px' }}>
            <input
              type="text"
              placeholder="Your Name"
              value={customerName}
              onChange={(e) => setCustomerName(e.target.value)}
              required
              style={{ width: '100%', padding: '6px', boxSizing: 'border-box', fontSize: '13px' }}
            />
          </div>
          <div style={{ marginBottom: '8px' }}>
            <input
              type="text"
              placeholder="Delivery Address"
              value={deliveryAddress}
              onChange={(e) => setDeliveryAddress(e.target.value)}
              required
              style={{ width: '100%', padding: '6px', boxSizing: 'border-box', fontSize: '13px' }}
            />
          </div>
          <button type="submit" style={{ width: '100%', padding: '8px', backgroundColor: '#4ecdc4', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer', fontSize: '13px' }}>
            Accept Order
          </button>
        </form>
      )}
    </div>
  )
}

export default CustomerPanel
