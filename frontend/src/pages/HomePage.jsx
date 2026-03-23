import ProfileForm from "../components/ProfileForm";

export default function HomePage({ error, initialValues, onSubmit }) {
  return (
    <main className="page">
      <header className="hero">
        <span className="eyebrow">Generation One Frontend</span>
        <h1>Mock advisory profiling flow</h1>
        <p>
          This frontend collects investor profile inputs, validates them on the
          client, submits through a service layer, and shows a mocked
          recommendation result that can later be replaced by a real backend
          response.
        </p>
      </header>

      {error ? (
        <div className="error-banner" role="alert">
          {error}
        </div>
      ) : null}

      <ProfileForm initialValues={initialValues} onSubmit={onSubmit} />
    </main>
  );
}
