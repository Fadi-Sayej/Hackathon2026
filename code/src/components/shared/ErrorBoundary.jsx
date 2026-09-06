import { Component } from 'react'

export class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, message: '' }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, message: error?.message ?? 'Unknown error' }
  }

  componentDidCatch(error, info) {
    if (typeof console !== 'undefined') {
      console.error('SmartShelf render error:', error, info)
    }
  }

  handleRetry = () => {
    this.setState({ hasError: false, message: '' })
  }

  render() {
    if (!this.state.hasError) return this.props.children

    return (
      <section className="panel" role="alert">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">Demo recovery</p>
            <h2>Something didn't render correctly</h2>
            <p className="muted" style={{ marginTop: '0.5rem' }}>
              {this.state.message}
            </p>
          </div>
        </div>
        <p style={{ marginTop: '0.75rem' }}>
          The rest of the app is still safe. Click below to clear the failed view and continue.
        </p>
        <button className="btn btn-primary" onClick={this.handleRetry} type="button" style={{ marginTop: '1rem' }}>
          Retry view
        </button>
      </section>
    )
  }
}
