import { useState } from "react";
import HomePage from "./pages/HomePage";
import RecommendationSummaryPage from "./pages/RecommendationSummaryPage";
import ResultsPage from "./pages/ResultsPage";
import LoadingState from "./components/LoadingState";
import { submitInvestorProfile } from "./services/api";

const HOME_SCREEN = "home";
const LOADING_SCREEN = "loading";
const SUMMARY_SCREEN = "summary";
const BREAKDOWN_SCREEN = "breakdown";

export default function App() {
  const [currentScreen, setCurrentScreen] = useState(HOME_SCREEN);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [submittedProfile, setSubmittedProfile] = useState(null);
  const [recommendation, setRecommendation] = useState(null);

  async function handleProfileSubmit(profile) {
    setSubmittedProfile(profile);
    setError("");
    setLoading(true);
    setCurrentScreen(LOADING_SCREEN);

    try {
      const result = await submitInvestorProfile(profile);
      setRecommendation(result);
      setCurrentScreen(SUMMARY_SCREEN);
    } catch (submissionError) {
      setRecommendation(null);
      setCurrentScreen(HOME_SCREEN);
      setError(
        submissionError instanceof Error
          ? submissionError.message
          : "Something went wrong while generating the recommendation."
      );
    } finally {
      setLoading(false);
    }
  }

  function handleStartOver() {
    setCurrentScreen(HOME_SCREEN);
    setLoading(false);
    setError("");
    setRecommendation(null);
  }

  function handleViewBreakdown() {
    setCurrentScreen(BREAKDOWN_SCREEN);
  }

  function handleBackToSummary() {
    setCurrentScreen(SUMMARY_SCREEN);
  }

  return (
    <div className="app-shell">
      {currentScreen === HOME_SCREEN && (
        <HomePage
          error={error}
          initialValues={submittedProfile}
          onSubmit={handleProfileSubmit}
        />
      )}

      {currentScreen === LOADING_SCREEN && (
        <LoadingState
          message={
            loading
              ? "Building a mocked advisory recommendation..."
              : "Loading..."
          }
        />
      )}

      {currentScreen === SUMMARY_SCREEN && recommendation && (
        <RecommendationSummaryPage
          recommendation={recommendation}
          submittedProfile={submittedProfile}
          onViewBreakdown={handleViewBreakdown}
          onStartOver={handleStartOver}
        />
      )}

      {currentScreen === BREAKDOWN_SCREEN && recommendation && (
        <ResultsPage
          recommendation={recommendation}
          submittedProfile={submittedProfile}
          onBackToSummary={handleBackToSummary}
          onStartOver={handleStartOver}
        />
      )}
    </div>
  );
}
