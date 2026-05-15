import { Component, type ReactNode } from "react";

interface Props { children: ReactNode; }
interface State { hasError: boolean; }

export default class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError(): State {
    return { hasError: true };
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="error-fallback">
          <strong>Something went wrong</strong>
          <span>Please refresh the page and try again.</span>
        </div>
      );
    }
    return this.props.children;
  }
}
