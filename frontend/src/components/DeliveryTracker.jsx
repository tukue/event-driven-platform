import { useState, useEffect, useCallback } from 'react';
import PropTypes from 'prop-types';
import { API_BASE_URL, API_ENDPOINTS } from '../config/api';
import useWebSocket from '../hooks/useWebSocket';
import './DeliveryTracker.css';

// Subcomponents
const ProgressStep = ({ icon, label, time, status }) => (
  <div className={`step step--${status}`}>
    <div className="step__icon">{icon}</div>
    <div className="step__label">{label}</div>
    {time && (
      <div className="step__time">
        {new Date(time).toLocaleTimeString()}
      </div>
    )}
  </div>
);

ProgressStep.propTypes = {
  icon: PropTypes.string.isRequired,
  label: PropTypes.string.isRequired,
  time: PropTypes.string,
  status: PropTypes.oneOf(['completed', 'active', 'pending']).isRequired,
};

const ProgressConnector = ({ isCompleted }) => (
  <div className={`connector ${isCompleted ? 'connector--completed' : 'connector--pending'}`} />
);

ProgressConnector.propTypes = {
  isCompleted: PropTypes.bool.isRequired,
};

const DriverCard = ({ driverName, currentStatus }) => {
  const getStatusText = () => {
    switch (currentStatus) {
      case 'dispatched':
        return '📍 Picking up order';
      case 'in_transit':
        return '🚗 On the way';
      case 'delivered':
        return '✅ Delivered';
      default:
        return '';
    }
  };

  return (
    <div className="driver-card">
      <h3 className="driver-card__title">Driver Information</h3>
      <div className="driver-card__info">
        <div className="driver-card__avatar">👤</div>
        <div className="driver-card__details">
          <div className="driver-card__name">{driverName}</div>
          <div className="driver-card__status">{getStatusText()}</div>
        </div>
      </div>
    </div>
  );
};

DriverCard.propTypes = {
  driverName: PropTypes.string.isRequired,
  currentStatus: PropTypes.string.isRequired,
};

const ETACard = ({ estimatedArrival, countdown }) => (
  <div className="eta-card">
    <div className="eta-card__icon">⏱️</div>
    <div className="eta-card__content">
      <div className="eta-card__label">Estimated Arrival</div>
      <div className="eta-card__time">
        {new Date(estimatedArrival).toLocaleTimeString([], {
          hour: '2-digit',
          minute: '2-digit',
        })}
      </div>
      {countdown && <div className="eta-card__countdown">{countdown}</div>}
    </div>
  </div>
);

ETACard.propTypes = {
  estimatedArrival: PropTypes.string.isRequired,
  countdown: PropTypes.string,
};

const DeliveredCard = ({ deliveredAt }) => (
  <div className="delivered-card">
    <div className="delivered-card__icon">🎉</div>
    <div className="delivered-card__text">Order Delivered!</div>
    <div className="delivered-card__time">
      Delivered at {new Date(deliveredAt).toLocaleTimeString()}
    </div>
  </div>
);

DeliveredCard.propTypes = {
  deliveredAt: PropTypes.string.isRequired,
};

const LoadingState = () => (
  <div className="loading">
    <div className="loading__spinner" />
    <p>Loading delivery information...</p>
  </div>
);

const ErrorState = ({ message, onClose }) => (
  <div className="error">
    <p>⚠️ {message}</p>
    <button onClick={onClose} className="button">
      Close
    </button>
  </div>
);

ErrorState.propTypes = {
  message: PropTypes.string.isRequired,
  onClose: PropTypes.func.isRequired,
};

// Custom hook for countdown timer
const useCountdown = (estimatedArrival, isDelivered) => {
  const [countdown, setCountdown] = useState('');

  useEffect(() => {
    if (!estimatedArrival || isDelivered) {
      return;
    }

    const updateCountdown = () => {
      const now = new Date();
      const eta = new Date(estimatedArrival);
      const diff = eta - now;

      if (diff <= 0) {
        setCountdown('Arriving now');
        return;
      }

      const minutes = Math.floor(diff / 60000);
      const seconds = Math.floor((diff % 60000) / 1000);

      if (minutes > 60) {
        const hours = Math.floor(minutes / 60);
        const mins = minutes % 60;
        setCountdown(`${hours}h ${mins}m`);
      } else if (minutes > 0) {
        setCountdown(`${minutes} minute${minutes !== 1 ? 's' : ''}`);
      } else {
        setCountdown(`${seconds} second${seconds !== 1 ? 's' : ''}`);
      }
    };

    updateCountdown();
    const interval = setInterval(updateCountdown, 1000);

    return () => clearInterval(interval);
  }, [estimatedArrival, isDelivered]);

  return countdown;
};

// Helper function to determine step status
const getStepStatus = (stepName, currentStatus) => {
  const statusOrder = ['dispatched', 'in_transit', 'delivered'];
  const currentIndex = statusOrder.indexOf(currentStatus);
  const stepIndex = statusOrder.indexOf(stepName);

  if (stepIndex < currentIndex) return 'completed';
  if (stepIndex === currentIndex) return 'active';
  return 'pending';
};

// Main component
const DeliveryTracker = ({ orderId, onClose }) => {
  const [deliveryInfo, setDeliveryInfo] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const countdown = useCountdown(
    deliveryInfo?.estimated_arrival,
    deliveryInfo?.current_status === 'delivered'
  );

  // Wrap fetchDeliveryInfo with useCallback to prevent stale closures
  const fetchDeliveryInfo = useCallback(async () => {
    if (!orderId) return;
    
    try {
      setLoading(true);
      setError(null);

      const response = await fetch(`${API_BASE_URL}${API_ENDPOINTS.delivery(orderId)}`);

      if (!response.ok) {
        if (response.status === 404) {
          throw new Error('Order not found');
        } else if (response.status === 400) {
          const data = await response.json();
          throw new Error(data.detail || 'Order not yet dispatched');
        }
        throw new Error('Failed to fetch delivery information');
      }

      const data = await response.json();
      setDeliveryInfo(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [orderId]);

  // WebSocket integration for real-time updates with useCallback to prevent stale closures
  const handleWebSocketMessage = useCallback((event) => {
    // Only update if this event is for the current order
    if (event.order?.id === orderId) {
      // Refetch delivery info when order status changes
      if (
        event.event_type === 'order.dispatched' ||
        event.event_type === 'order.in_transit' ||
        event.event_type === 'order.delivered'
      ) {
        fetchDeliveryInfo();
      }
    }
  }, [orderId, fetchDeliveryInfo]);

  const { isConnected } = useWebSocket(handleWebSocketMessage);

  // Initial fetch
  useEffect(() => {
    if (!orderId) return;
    fetchDeliveryInfo();
  }, [orderId, fetchDeliveryInfo]);

  if (!orderId) return null;

  return (
    <div className="delivery-tracker-overlay" onClick={onClose}>
      <div className="delivery-tracker" onClick={(e) => e.stopPropagation()}>
        <div className="delivery-tracker__header">
          <h2 className="delivery-tracker__title">Delivery Tracker</h2>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span style={{ fontSize: '12px', color: isConnected ? '#4caf50' : '#999' }}>
              {isConnected ? '🟢 Live' : '⚪ Offline'}
            </span>
            <button
              onClick={onClose}
              className="delivery-tracker__close"
              aria-label="Close"
            >
              ×
            </button>
          </div>
        </div>

        {loading && <LoadingState />}

        {error && <ErrorState message={error} onClose={onClose} />}

        {deliveryInfo && !loading && !error && (
          <div className="delivery-tracker__content">
            <p className="delivery-tracker__order-id">
              Order #{orderId.slice(0, 8)}
            </p>

            {/* Progress Stepper */}
            <div className="progress-stepper">
              <ProgressStep
                icon="📦"
                label="Dispatched"
                time={deliveryInfo.timeline.dispatched_at}
                status={getStepStatus('dispatched', deliveryInfo.current_status)}
              />

              <ProgressConnector
                isCompleted={
                  deliveryInfo.current_status === 'in_transit' ||
                  deliveryInfo.current_status === 'delivered'
                }
              />

              <ProgressStep
                icon="🚚"
                label="In Transit"
                time={deliveryInfo.timeline.in_transit_at}
                status={getStepStatus('in_transit', deliveryInfo.current_status)}
              />

              <ProgressConnector
                isCompleted={deliveryInfo.current_status === 'delivered'}
              />

              <ProgressStep
                icon="✅"
                label="Delivered"
                time={deliveryInfo.timeline.delivered_at}
                status={getStepStatus('delivered', deliveryInfo.current_status)}
              />
            </div>

            {/* Driver Information */}
            <DriverCard
              driverName={deliveryInfo.driver_name}
              currentStatus={deliveryInfo.current_status}
            />

            {/* ETA or Delivered Status */}
            {deliveryInfo.current_status !== 'delivered' &&
              deliveryInfo.estimated_arrival && (
                <ETACard
                  estimatedArrival={deliveryInfo.estimated_arrival}
                  countdown={countdown}
                />
              )}

            {deliveryInfo.current_status === 'delivered' && (
              <DeliveredCard deliveredAt={deliveryInfo.timeline.delivered_at} />
            )}
          </div>
        )}
      </div>
    </div>
  );
};

DeliveryTracker.propTypes = {
  orderId: PropTypes.string,
  onClose: PropTypes.func.isRequired,
};

export default DeliveryTracker;
