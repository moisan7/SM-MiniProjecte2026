"use client";

import { Component, ReactNode } from "react";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  message: string;
}

export default class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, message: "" };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, message: error.message };
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback ?? (
        <div role="alert" className="mt-4 p-4 bg-red-50 text-red-700 rounded-xl border border-red-200 text-sm">
          <strong>Error al mostrar el resultado.</strong> Prueba a seleccionar otro elemento del historial o genera una nueva imagen.
          <button
            className="ml-4 underline text-red-600 hover:text-red-800"
            onClick={() => this.setState({ hasError: false, message: "" })}
          >
            Reintentar
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
