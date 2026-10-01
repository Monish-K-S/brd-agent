import { Component, type ReactNode } from "react";
import { Link } from "react-router-dom";

type ErrorBoundaryProps = {
  children: ReactNode;
};

type ErrorBoundaryState = {
  hasError: boolean;
};

export class ErrorBoundary extends Component<
  ErrorBoundaryProps,
  ErrorBoundaryState
> {
  state: ErrorBoundaryState = { hasError: false };

  static getDerivedStateFromError(): ErrorBoundaryState {
    return { hasError: true };
  }

  componentDidCatch(error: unknown): void {
    console.error("Uncaught UI error:", error);
  }

  private handleRetry = (): void => {
    this.setState({ hasError: false });
  };

  render(): ReactNode {
    if (!this.state.hasError) {
      return this.props.children;
    }

    return (
      <main className="relative flex min-h-screen flex-col items-center bg-canvas px-4 py-24 text-center text-ink sm:px-8">
        <div className="mx-auto w-full max-w-xl">
          <span
            aria-hidden="true"
            className="mx-auto mb-8 block size-2 rounded-full bg-signal"
          />

          <h1 className="font-display text-h1 leading-[1.1] font-normal text-ink">
            Something went wrong.
          </h1>

          <p className="mx-auto mt-4 max-w-md text-base leading-7 text-steel">
            This part of the app crashed. Your work is saved — try again or
            head back home.
          </p>

          <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
            <button
              type="button"
              onClick={this.handleRetry}
              className="press inline-flex min-h-11 cursor-pointer items-center rounded-full bg-primary px-6 py-[11px] text-sm font-semibold text-surface transition-colors duration-200 hover:bg-primary-deep active:bg-primary-deep"
            >
              Try again
            </button>

            <Link
              to="/"
              className="press inline-flex min-h-11 items-center rounded-full border border-ink/25 bg-transparent px-6 py-[11px] text-sm font-semibold text-ink transition-colors duration-200 hover:border-ink/50 hover:bg-soft"
            >
              Back to home
            </Link>
          </div>
        </div>
      </main>
    );
  }
}
