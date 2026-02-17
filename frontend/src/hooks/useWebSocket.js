import { useEffect, useRef, useState } from 'react'

const useWebSocket = (onMessage) => {
  const ws = useRef(null)
  const [isConnected, setIsConnected] = useState(false)

  useEffect(() => {
    const connect = () => {
      ws.current = new WebSocket('ws://localhost:8000/ws')

      ws.current.onopen = () => setIsConnected(true)
      ws.current.onclose = () => {
        setIsConnected(false)
        setTimeout(connect, 3000)
      }
      ws.current.onmessage = (event) => {
        const data = JSON.parse(event.data)
        onMessage(data)
      }
    }

    connect()
    return () => ws.current?.close()
  }, [])

  return { isConnected }
}

export default useWebSocket
