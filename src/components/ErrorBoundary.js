import React from 'react';

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true };
  }

  componentDidCatch(error, errorInfo) {
    this.setState({
      error: error,
      errorInfo: errorInfo
    });
    console.error('Error caught by boundary:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: '20px', border: '1px solid #ff6b6b', margin: '10px', borderRadius: '8px', backgroundColor: '#fff5f5' }}>
          <h2 style={{ color: '#e53e3e' }}>Something went wrong with this component.</h2>
          <details style={{ whiteSpace: 'pre-wrap', marginTop: '10px' }}>
            <summary style={{ cursor: 'pointer', fontWeight: 'bold' }}>Error Details</summary>
            {this.state.error && this.state.error.toString()}
            <br />
            {this.state.errorInfo?.componentStack}
          </details>
          <button 
            onClick={() => this.setState({ hasError: false, error: null, errorInfo: null })}
            style={{ 
              marginTop: '10px', 
              padding: '8px 16px', 
              backgroundColor: '#3182ce',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer'
            }}
          >
            Try Again
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
