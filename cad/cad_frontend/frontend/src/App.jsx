import { useEffect, useRef } from 'react'
import { DxfViewer } from 'dxf-viewer'

function App() {
  const containerRef = useRef(null)

  useEffect(() => {
    const viewer = new DxfViewer(containerRef.current, {
      autoResize: true,
      colorCorrection: true,
      fonts: [
        'https://fonts.gstatic.com/s/roboto/v30/KFOmCnqEu92Fr1Mu4mxK.woff2',
      ]
    })

    viewer.Load({ url: '/도면1.dxf' })
      .catch(console.error)

    return () => viewer.Destroy()
  }, [])

  return (
    <div
      ref={containerRef}
      style={{ width: '100vw', height: '100vh', background: '#1a1a1a' }}
    />
  )
}

export default App