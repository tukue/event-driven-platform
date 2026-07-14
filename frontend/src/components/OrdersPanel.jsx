import { useState } from 'react'

const statusColors = {
  created: '#ffd93d',
  pending_source: '#ffd93d',
  source_accepted: '#6bcf7f',
  source_rejected: '#ef4444',
  buyer_accepted: '#10b981',
  preparing: '#ff9a3c',
  ready: '#4ecdc4',
  dispatched: '#a78bfa',
  in_transit: '#8b5cf6',
  delivered: '#10b981',
  cancelled: '#9ca3af'
}

const statusEmojis = {
  created: '📝',
  pending_source: '⏳',
  source_accepted: '✅',
  source_rejected: '❌',
  buyer_accepted: '🤝',
  preparing: '👨‍🍳',
  ready: '📦',
  dispatched: '📦',
  in_transit: '🚗',
  delivered: '🎉',
  cancelled: '🚫'
}

function OrdersPanel({ orders, onTrackDelivery }) {
  const updateStatus = async (orderId, status) => {
    await fetch(`http://localhost:8000/api/orders/${orderId}/status?status=${status}`, {
      method: 'POST'
    })
  }

  return (
    <div style={{ border: '2px solid #ddd', borderRadius: '8px', padding: '20px' }}>
      <h2>📦 All Orders</h2>
      <div style={{ display: 'grid', gap: '15px' }}>
        {orders.length === 0 ? (
          <p style={{ color: '#666' }}>No orders yet</p>
        ) : (
          orders.map((event) => (
            <div key={event.order.id} style={{ 
              border: '1px solid #ddd', 
              borderRadius: '8px', 
              padding: '15px',
              backgroundColor: '#fff'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
                <div style={{ flex: 1 }}>
                  <h3 style={{ margin: '0 0 10px 0' }}>{event.order.item_name}</h3>
                  <p style={{ margin: '5px 0' }}>
                    <strong>Source:</strong> {event.order.source_name} | 
                    <strong> Base Price:</strong> ${event.order.source_price}
                  </p>
                  {event.order.buyer_name && (
                    <>
                      <p style={{ margin: '5px 0' }}>
                        <strong>Buyer:</strong> {event.order.buyer_name}
                      </p>
                      <p style={{ margin: '5px 0' }}>
                        <strong>Delivery:</strong> {event.order.delivery_address}
                      </p>
                      <p style={{ margin: '5px 0' }}>
                        <strong>Buyer Price:</strong> ${event.order.buyer_price} 
                        <span style={{ color: '#10b981', marginLeft: '5px' }}>
                          (+{event.order.markup_percentage}%)
                        </span>
                      </p>
                    </>
                  )}
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div style={{ 
                    display: 'inline-block',
                    padding: '5px 15px', 
                    borderRadius: '20px', 
                    backgroundColor: statusColors[event.order.status],
                    color: '#000',
                    fontWeight: 'bold',
                    marginBottom: '10px'
                  }}>
                    {statusEmojis[event.order.status]} {event.order.status}
                  </div>
                  
                  {/* Track Delivery button for dispatched, in_transit, and delivered orders */}
                  {['dispatched', 'in_transit', 'delivered'].includes(event.order.status) && (
                    <button 
                      onClick={() => onTrackDelivery(event.order.id)}
                      style={{ 
                        padding: '8px 15px', 
                        fontSize: '13px',
                        backgroundColor: '#8b5cf6',
                        color: 'white',
                        border: 'none',
                        borderRadius: '5px',
                        cursor: 'pointer',
                        marginBottom: '5px',
                        width: '100%'
                      }}
                    >
                      🚚 Track Delivery
                    </button>
                  )}
                  
                  {!['delivered', 'cancelled', 'source_rejected', 'created', 'pending_source', 'source_accepted'].includes(event.order.status) && (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '5px' }}>
                      {event.order.status === 'buyer_accepted' && (
                        <button onClick={() => updateStatus(event.order.id, 'preparing')} style={{ padding: '5px 10px', fontSize: '12px' }}>
                          Start Preparing
                        </button>
                      )}
                      {event.order.status === 'preparing' && (
                        <button onClick={() => updateStatus(event.order.id, 'ready')} style={{ padding: '5px 10px', fontSize: '12px' }}>
                          Mark Ready
                        </button>
                      )}
                      {event.order.status === 'dispatched' && (
                        <button onClick={() => updateStatus(event.order.id, 'in_transit')} style={{ padding: '5px 10px', fontSize: '12px' }}>
                          In Transit
                        </button>
                      )}
                      {event.order.status === 'in_transit' && (
                        <button onClick={() => updateStatus(event.order.id, 'delivered')} style={{ padding: '5px 10px', fontSize: '12px' }}>
                          Mark Delivered
                        </button>
                      )}
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}

export default OrdersPanel
