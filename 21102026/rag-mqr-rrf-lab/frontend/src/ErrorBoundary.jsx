import React from "react";

export default class ErrorBoundary extends React.Component {
  state = { error: null };

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, info) {
    console.error("RAG UI rendering failed", error, info.componentStack);
  }

  render() {
    if (!this.state.error) return this.props.children;
    return (
      <div className="panel error-box" role="alert">
        <strong>Unable to display this response</strong>
        <span>{this.state.error.message || String(this.state.error)}</span>
        <button className="btn" onClick={() => this.setState({ error: null })}>Reset this view</button>
      </div>
    );
  }
}
