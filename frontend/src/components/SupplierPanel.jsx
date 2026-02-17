import { useState } from 'react'

function SupplierPanel({ orders }) {
  const [form, setForm] = useState({
    supplier_name: '',
    pizza_name: '',
    supplier_price: '',
    markup_percentage: '30'
  })
  const [responseForm, setResponseForm] = useState({
    orderId: '',
    notes: '',
    estimatedTime: '30'
  })

  const pendingOrders = orders.filter(e => e.order.status === 'pending_supplier')

  const handleSubmit = async (e) => {
    e.preventDefault()
    
    try {
      console.log('Submitting order:', form)
      
      const response = await fetch('http://localhost:8000/api/orders', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...form,
          supplier_price: parseFloat(form.supplier_price),
          markup_percentage: parseFloat(form.markup_percentage)
        })
      })
      
      if (!response.ok) {
        const error = await response.text()
        console.error('Failed to create order:', error)
        alert('Failed to create order: ' + error)
        return
      }
      
      const result = await response.json()
      console.log('Order created:', result)
      
      setForm({ supplier_name: '', pizza_name: '', supplier_price: '', markup_percentage: '30' })
    } catch (error) {
      console.error('Error creating order:', error)
      alert('Error: ' + error.message)
    }
  }

  const handleResponse = async (accept) => {
    await fetch(`http://localhost:8000/api/orders/${responseForm.orderId}/supplier-respond?accept=${accept}&notes=${encodeURIComponent(responseForm.notes)}&estimated_time=${responseForm.estimatedTime}`, {
      method: 'POST'
    })
    
    setResponseForm({ orderId: '', notes: '', estimatedTime: '30' })
  }

  return (
    <div style={{ border: '2px solid #ff6b35', borderRadius: '8px', padding: '20px', backgroundColor: '#fff5f2' }}>
      <h2>🏪 Supplier</h2>
      
      <h3 style={{ marginTop: '0' }}>Create Order</h3>
      <form onSubmit={handleSubmit}>
        <div style={{ marginBottom: '8px' }}>
          <input
            type="text"
            placeholder="Supplier Name"
            value={form.supplier_name}
            onChange={(e) => setForm({...form, supplier_name: e.target.value})}
            required
            style={{ width: '100%', padding: '6px', boxSizing: 'border-box', fontSize: '13px' }}
          />
        </div>
        <div style={{ marginBottom: '8px' }}>
          <input
            type="text"
            placeholder="Pizza Name"
            value={form.pizza_name}
            onChange={(e) => setForm({...form, pizza_name: e.target.value})}
            required
            style={{ width: '100%', padding: '6px', boxSizing: 'border-box', fontSize: '13px' }}
          />
        </div>
        <div style={{ marginBottom: '8px', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '5px' }}>
          <input
            type="number"
            step="0.01"
            placeholder="Price ($)"
            value={form.supplier_price}
            onChange={(e) => setForm({...form, supplier_price: e.target.value})}
            required
            style={{ padding: '6px', fontSize: '13px' }}
          />
          <input
            type="number"
            placeholder="Markup %"
            value={form.markup_percentage}
            onChange={(e) => setForm({...form, markup_percentage: e.target.value})}
            required
            style={{ padding: '6px', fontSize: '13px' }}
          />
        </div>
        <button type="submit" style={{ width: '100%', padding: '8px', backgroundColor: '#ff6b35', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer', fontSize: '13px' }}>
          Create Order
        </button>
      </form>

      <hr style={{ margin: '20px 0', border: 'none', borderTop: '1px solid #ddd' }} />

      <h3>Pending Orders ({pendingOrders.length})</h3>
      {pendingOrders.length === 0 ? (
        <p style={{ color: '#666', fontSize: '13px' }}>No pending orders</p>
      ) : (
        <div>
          <select
            value={responseForm.orderId}
            onChange={(e) => setResponseForm({...responseForm, orderId: e.target.value})}
            style={{ width: '100%', padding: '6px', marginBottom: '8px', fontSize: '13px' }}
          >
            <option value="">Select Order</option>
            {pendingOrders.map(e => (
              <option key={e.order.id} value={e.order.id}>
                {e.order.pizza_name} - ${e.order.supplier_price}
              </option>
            ))}
          </select>
          {responseForm.orderId && (
            <>
              <input
                type="text"
                placeholder="Notes (optional)"
                value={responseForm.notes}
                onChange={(e) => setResponseForm({...responseForm, notes: e.target.value})}
                style={{ width: '100%', padding: '6px', marginBottom: '8px', fontSize: '13px' }}
              />
              <input
                type="number"
                placeholder="Est. Time (min)"
                value={responseForm.estimatedTime}
                onChange={(e) => setResponseForm({...responseForm, estimatedTime: e.target.value})}
                style={{ width: '100%', padding: '6px', marginBottom: '8px', fontSize: '13px' }}
              />
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '5px' }}>
                <button onClick={() => handleResponse(true)} style={{ padding: '8px', backgroundColor: '#10b981', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer', fontSize: '13px' }}>
                  Accept
                </button>
                <button onClick={() => handleResponse(false)} style={{ padding: '8px', backgroundColor: '#ef4444', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer', fontSize: '13px' }}>
                  Reject
                </button>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  )
}

export default SupplierPanel
