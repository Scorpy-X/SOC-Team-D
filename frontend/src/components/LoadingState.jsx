export default function LoadingState({ message }) {
  return (
    <div className="loading-page">
      <div className="loading-card card">
        <div className="loading-spinner" aria-hidden="true" />
        <h2>Preparing recommendation</h2>
        <p>{message}</p>
      </div>
    </div>
  );
}
