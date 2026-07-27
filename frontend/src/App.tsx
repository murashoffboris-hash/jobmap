import { Routes, Route, Navigate } from "react-router-dom";
import Header from "@/components/Header";
import ProtectedRoute from "@/components/ProtectedRoute";
import OfflineBanner from "@/components/OfflineBanner";
import ReloadPrompt from "@/components/ReloadPrompt";
import HomePage from "@/pages/HomePage";
import LoginPage from "@/pages/LoginPage";
import RegisterPage from "@/pages/RegisterPage";
import VacancyListPage from "@/pages/VacancyListPage";
import VacancyDetailPage from "@/pages/VacancyDetailPage";
import NotFoundPage from "@/pages/NotFoundPage";
import ProfilePage from "@/pages/ProfilePage";
import VacancyCreatePage from "@/pages/VacancyCreatePage";
import ApplicationsPage from "@/pages/ApplicationsPage";

export default function App(): JSX.Element {
  return (
    <div className="flex min-h-screen flex-col">
      <Header />
      {/* Баннеры висят под sticky-хедером (top-16) — см. компоненты. */}
      <OfflineBanner />
      <ReloadPrompt />
      <main className="flex flex-1 flex-col">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/vacancies" element={<VacancyListPage />} />
          <Route
            path="/vacancies/new"
            element={
              <ProtectedRoute>
                <VacancyCreatePage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/vacancies/:id"
            element={
              <ProtectedRoute>
                <VacancyDetailPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/profile"
            element={
              <ProtectedRoute>
                <ProfilePage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/applications"
            element={
              <ProtectedRoute>
                <ApplicationsPage />
              </ProtectedRoute>
            }
          />
          <Route path="/404" element={<NotFoundPage />} />
          <Route path="*" element={<Navigate to="/404" replace />} />
        </Routes>
      </main>
    </div>
  );
}
