import { createRoot } from "react-dom/client";
import { Component, ReactNode, ErrorInfo } from "react";
import App from "./App.tsx";
import "./index.css";

class ErrorBoundary extends Component<{ children: ReactNode }, { error: Error | null }> {
  state = { error: null };
  static getDerivedStateFromError(error: Error) { return { error }; }
  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("React crash:", error, info);
  }
  render() {
    if (this.state.error) {
      const err = this.state.error as Error;
      return (
        <div style={{ padding: 32, fontFamily: "monospace", background: "#fee", color: "#c00", borderRadius: 8, margin: 16 }}>
          <h2>Error de aplicación</h2>
          <pre style={{ whiteSpace: "pre-wrap", fontSize: 13 }}>{err.message}{"\n"}{err.stack}</pre>
        </div>
      );
    }
    return this.props.children;
  }
}

createRoot(document.getElementById("root")!).render(
  <ErrorBoundary>
    <App />
  </ErrorBoundary>
);
