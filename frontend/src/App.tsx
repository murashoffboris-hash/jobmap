import { Routes, Route, Navigate } from "react-router-dom";
import Navbar from "./components/Navbar";
import HomePage from "./pages/HomePage";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import VacancyListPage from "./pages/VacancyListPage";
import VacancyDetailPage from "./pages/VacancyDetailPage";
import NotFoundPage from "./pages/NotFoundPage";

export default function App(): JSX.Element {
  return (
    <div className="app">
      <Navbar />
      <main className="app__main">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/vacancies" element={<VacancyListPage />} />
          <Route path="/vacancies/:id" element={<VacancyDetailPage />} />
          <Route path="/404" element={<NotFoundPage />} />
          <Route path="*" element={<Navigate to="/404" replace />} />
        </Routes>
      </main>
    </div>
  );
}
