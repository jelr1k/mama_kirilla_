import React from 'react';

export class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('UI Render Error caught by ErrorBoundary:', error, errorInfo);
  }

  componentDidUpdate(prevProps) {
    if (prevProps.resetKey !== this.props.resetKey && this.state.hasError) {
      this.setState({ hasError: false, error: null });
    }
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="page standard-page">
          <div className="page-container" style={{ textAlign: 'center', marginTop: '60px' }}>
            <h2 style={{ color: '#ef4444', marginBottom: '12px' }}>Ошибка отображения раздела</h2>
            <p style={{ color: '#94a3b8', fontSize: '14px', marginBottom: '16px' }}>
              Произошла ошибка при рендеринге вкладки. Другие разделы продолжают работать.
            </p>
            <pre
              style={{
                background: 'rgba(0,0,0,0.5)',
                padding: '16px',
                borderRadius: '8px',
                color: '#fca5a5',
                fontSize: '13px',
                textAlign: 'left',
                overflowX: 'auto',
                maxHeight: '200px',
                margin: '0 auto',
                maxWidth: '600px',
              }}
            >
              {this.state.error?.toString()}
            </pre>
            <button
              className="primary-action-btn"
              onClick={() => this.setState({ hasError: false, error: null })}
              style={{ margin: '20px auto 0', display: 'inline-flex' }}
            >
              <span>Попробовать снова</span>
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
