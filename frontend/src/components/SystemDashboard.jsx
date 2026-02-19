import { useState, useEffect, useCallback, useRef } from 'react';
import PropTypes from 'prop-types';
import { API_BASE_URL } from '../config/api';
import useWebSocket from '../hooks/useWebSocket';
import './SystemDashboard.css';

// Subcomponent: Statistics Card
const StatCard = ({ icon, label, value, color, trend }) => (
  <div className="stat-card" style={{ borderLeftColor: color }}>
    <div className="stat-card__icon" style={{ color }}>
      {icon}
    </div>
    <div className="stat-card__content">
      <div className="stat-card__label">{label}</div>
      <div className="stat-card__value">{value}</div>
      {trend && <div className="stat-card__trend">{trend}</div>}
    </div>
  </div>
);

StatCard.propTypes = {
  icon: PropTypes.string.isRequired,
  label: PropTypes.string.isRequired,
  value: PropTypes.oneOfType([PropTypes.string, PropTypes.number]).isRequired,
  color: PropTypes.string.isRequired,
  trend: PropTypes.string,
};

// Subcomponent: Order Item
const OrderItem = ({ order }) => (
  <div className="order-item">
    <div className="order-item__header">
      <span className="order-item__id">#{order.id?.slice(0, 8)}</span>
      <span className="order-item__pizza">{order.pizza_name}</span>
    </div>
    <div className="order-item__details">
      <span className="order-item__supplier">🏪 {order.supplier_name}</span>
      {order.customer_name && (
        <span className="order-item__customer">👤 {order.customer_name}</span>
      )}
      {order.driver_name && (
        <span className="order-item__driver">🚗 {order.driver_name}</span>
      )}
    </div>
    {order.delivery_address && (
      <div className="order-item__address">📍 {order.delivery_address}</div>
    )}
  </div>
);

OrderItem.propTypes = {
  order: PropTypes.shape({
    id: PropTypes.string,
    pizza_name: PropTypes.string,
    supplier_name: PropTypes.string,
    customer_name: PropTypes.string,
    driver_name: PropTypes.string,
    delivery_address: PropTypes.string,
  }).isRequired,
};

// Subcomponent: Collapsible Status Section
const StatusSection = ({ status, orders, icon, color }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  const statusLabels = {
    pending_supplier: 'Pending Supplier',
    supplier_accepted: 'Supplier Accepted',
    customer_accepted: 'Customer Accepted',
    preparing: 'Preparing',
    ready: 'Ready for Pickup',
    dispatched: 'Dispatched',
    in_transit: 'In Transit',
    delivered: 'Delivered',
    cancelled: 'Cancelled',
  };

  if (!orders || orders.length === 0) return null;

  return (
    <div className="status-section">
      <button
        className="status-section__header"
        onClick={() => setIsExpanded(!isExpanded)}
        style={{ borderLeftColor: color }}
      >
        <div className="status-section__title">
          <span className="status-section__icon">{icon}</span>
          <span className="status-section__label">
            {statusLabels[status] || status}
          </span>
          <span className="status-section__count">{orders.length}</span>
        </div>
        <span className="status-section__toggle">
          {isExpanded ? '▼' : '▶'}
        </span>
      </button>
      
      {isExpanded && (
        <div className="status-section__content">
          {orders.map((order) => (
            <OrderItem key={order.id} order={order} />
          ))}
        </div>
      )}
    </div>
  );
};

StatusSection.propTypes = {
  status: PropTypes.string.isRequired,
  orders: PropTypes.array.isRequired,
  icon: PropTypes.string.isRequired,
  color: PropTypes.string.isRequired,
};

// Subcomponent: Driver Card
const DriverCard = ({ driver }) => {
  const statusIcons = {
    dispatched: '📦',
    in_transit: '🚗',
  };

  const statusLabels = {
    dispatched: 'Picking up',
    in_transit: 'Delivering',
  };

  return (
    <div className="driver-card-item">
      <div className="driver-card-item__avatar">👤</div>
      <div className="driver-card-item__info">
        <div className="driver-card-item__name">{driver.driver_name}</div>
        <div className="driver-card-item__status">
          {statusIcons[driver.status]} {statusLabels[driver.status]}
        </div>
        {driver.order_id && (
          <div className="driver-card-item__order">
            Order #{driver.order_id.slice(0, 8)}
          </div>
        )}
      </div>
      <div className={`driver-card-item__indicator driver-card-item__indicator--${driver.status}`} />
    </div>
  );
};

DriverCard.propTypes = {
  driver: PropTypes.shape({
    driver_name: PropTypes.string.isRequired,
    status: PropTypes.string.isRequired,
    order_id: PropTypes.string,
  }).isRequired,
};

// Subcomponent: Loading State
const LoadingState = () => (
  <div className="dashboard-loading">
    <div className="loading-spinner" />
    <p>Loading system state...</p>
  </div>
);

// Subcomponent: Error State
const ErrorState = ({ message, onRetry }) => (
  <div className="dashboard-error">
    <p>⚠️ {message}</p>
    <button onClick={onRetry} className="button button--primary">
      Retry
    </button>
  </div>
);

ErrorState.propTypes = {
  message: PropTypes.string.isRequired,
  onRetry: PropTypes.func.isRequired,
};

// Main Component
const SystemDashboard = () => {
  const [systemState, setSystemState] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [notification, setNotification] = useState(null);
  
  // Use ref to track notification timeout and prevent memory leaks
  const notificationTimeoutRef = useRef(null);

  // Show notification helper with cleanup
  const showNotification = useCallback((message, type = 'info') => {
    // Clear any existing timeout to prevent memory leaks
    if (notificationTimeoutRef.current) {
      clearTimeout(notificationTimeoutRef.current);
    }
    
    setNotification({ message, type });
    
    // Set new timeout and store reference
    notificationTimeoutRef.current = setTimeout(() => {
      setNotification(null);
      notificationTimeoutRef.current = null;
    }, 3000);
  }, []);

  // Cleanup notification timeout on unmount
  useEffect(() => {
    return () => {
      if (notificationTimeoutRef.current) {
        clearTimeout(notificationTimeoutRef.current);
      }
    };
  }, []);

  // Wrap fetchSystemState with useCallback to prevent stale closures
  const fetchSystemState = useCallback(async () => {
    try {
      setError(null);
      
      const response = await fetch(`${API_BASE_URL}/api/state`);
      
      if (!response.ok) {
        throw new Error('Failed to fetch system state');
      }
      
      const data = await response.json();
      setSystemState(data);
      setLastUpdated(new Date());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  // WebSocket callback wrapped with useCallback to prevent stale closures
  const handleWebSocketMessage = useCallback((event) => {
    // Refetch system state on any order event
    if (event.event_type?.startsWith('order.')) {
      fetchSystemState();
      
      // Show notification for important events
      const eventMessages = {
        'order.created': '📝 New order created',
        'order.dispatched': '📦 Order dispatched',
        'order.in_transit': '🚗 Order in transit',
        'order.delivered': '🎉 Order delivered',
      };
      
      const message = eventMessages[event.event_type];
      if (message) {
        showNotification(message, 'success');
      }
    }
  }, [fetchSystemState, showNotification]);

  const { isConnected } = useWebSocket(handleWebSocketMessage);

  // Initial fetch
  useEffect(() => {
    fetchSystemState();
  }, [fetchSystemState]);

  // Auto-refresh every 5 seconds with proper dependency
  useEffect(() => {
    const interval = setInterval(() => {
      if (!loading) {
        fetchSystemState();
      }
    }, 5000);

    return () => clearInterval(interval);
  }, [loading, fetchSystemState]);

  if (loading && !systemState) {
    return <LoadingState />;
  }

  if (error && !systemState) {
    return <ErrorState message={error} onRetry={fetchSystemState} />;
  }

  const stats = systemState?.statistics || {};
  const ordersByStatus = systemState?.orders_by_status || {};
  const activeDrivers = systemState?.active_drivers || [];

  // Status configuration for rendering
  const statusConfig = [
    { key: 'pending_supplier', icon: '⏳', color: '#8b5cf6' },
    { key: 'supplier_accepted', icon: '✅', color: '#10b981' },
    { key: 'customer_accepted', icon: '🤝', color: '#3b82f6' },
    { key: 'preparing', icon: '👨‍🍳', color: '#f59e0b' },
    { key: 'ready', icon: '🍕', color: '#10b981' },
    { key: 'dispatched', icon: '📦', color: '#8b5cf6' },
    { key: 'in_transit', icon: '🚗', color: '#f59e0b' },
    { key: 'delivered', icon: '🎉', color: '#10b981' },
    { key: 'cancelled', icon: '❌', color: '#ef4444' },
  ];

  return (
    <div className="system-dashboard">
      {/* Notification Toast */}
      {notification && (
        <div className={`notification notification--${notification.type}`}>
          {notification.message}
        </div>
      )}

      {/* Header */}
      <div className="dashboard-header">
        <h1 className="dashboard-title">📊 System Dashboard</h1>
        <div className="dashboard-status">
          <span className={`status-indicator ${isConnected ? 'status--connected' : 'status--disconnected'}`}>
            {isConnected ? '🟢 Live' : '⚪ Offline'}
          </span>
          {lastUpdated && (
            <span className="last-updated">
              Updated {lastUpdated.toLocaleTimeString()}
            </span>
          )}
        </div>
      </div>

      {/* Statistics Cards */}
      <div className="stats-grid">
        <StatCard
          icon="📦"
          label="Total Orders"
          value={stats.total_orders || 0}
          color="#3b82f6"
        />
        <StatCard
          icon="🚚"
          label="Active Deliveries"
          value={stats.active_deliveries || 0}
          color="#f59e0b"
        />
        <StatCard
          icon="✅"
          label="Completed Today"
          value={stats.completed_today || 0}
          color="#10b981"
        />
        <StatCard
          icon="⏳"
          label="Pending Supplier"
          value={stats.pending_supplier || 0}
          color="#8b5cf6"
        />
      </div>

      {/* Status Breakdown */}
      <div className="status-breakdown">
        <h2 className="section-title">Order Status Breakdown</h2>
        <div className="status-grid">
          <div className="status-item">
            <span className="status-label">👨‍🍳 Preparing</span>
            <span className="status-value">{stats.preparing || 0}</span>
          </div>
          <div className="status-item">
            <span className="status-label">🍕 Ready</span>
            <span className="status-value">{stats.ready || 0}</span>
          </div>
          <div className="status-item">
            <span className="status-label">📦 Dispatched</span>
            <span className="status-value">{stats.dispatched || 0}</span>
          </div>
          <div className="status-item">
            <span className="status-label">🚗 In Transit</span>
            <span className="status-value">{stats.in_transit || 0}</span>
          </div>
          <div className="status-item">
            <span className="status-label">🎉 Delivered</span>
            <span className="status-value">{stats.delivered || 0}</span>
          </div>
        </div>
      </div>

      {/* Orders by Status */}
      <div className="orders-section">
        <h2 className="section-title">Orders by Status</h2>
        <div className="status-sections">
          {statusConfig.map((config) => (
            <StatusSection
              key={config.key}
              status={config.key}
              orders={ordersByStatus[config.key] || []}
              icon={config.icon}
              color={config.color}
            />
          ))}
        </div>
        {Object.keys(ordersByStatus).length === 0 && (
          <p className="empty-state">No orders yet</p>
        )}
      </div>

      {/* Active Drivers */}
      <div className="drivers-section">
        <h2 className="section-title">Active Drivers ({activeDrivers.length})</h2>
        {activeDrivers.length > 0 ? (
          <div className="drivers-grid">
            {activeDrivers.map((driver, index) => (
              <DriverCard key={`${driver.driver_name}-${index}`} driver={driver} />
            ))}
          </div>
        ) : (
          <p className="empty-state">No active drivers</p>
        )}
      </div>
    </div>
  );
};

export default SystemDashboard;
