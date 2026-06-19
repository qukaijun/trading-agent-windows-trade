import { Component, type ReactNode } from "react";

interface Props { children: ReactNode; }
interface State { error: Error | null; }

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };
  static getDerivedStateFromError(error: Error) { return { error }; }
  render() {
    if (this.state.error) {
      return (
        <div style={{padding:40,fontFamily:"monospace",color:"red",background:"#fff",minHeight:"100vh"}}>
          <h1 style={{fontSize:24,marginBottom:12}}>⚠ React Render Error</h1>
          <pre style={{whiteSpace:"pre-wrap",fontSize:14,lineHeight:1.6}}>{this.state.error.message}{"\n\n"}{this.state.error.stack}</pre>
        </div>
      );
    }
    return this.props.children;
  }
}
