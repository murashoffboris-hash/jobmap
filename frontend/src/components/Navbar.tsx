import { NavLink, Link } from "react-router-dom";
import { useAuthStore } from "@/store/auth";
import { useAuthBootstrap } from "@/hooks/useAuth";

export default function Navbar(): JSX.Element {
  useAuthBootstrap();
  const user = useAuthStore((s) => s.user);
  const status = useAuthStore((s) => s.status);
  const logout = useAuthStore((s) => s.logout);

  return (
    <header className="navbar">
      <Link to="/" className="navbar__brand">
        🗺️ JobMap
      </Link>
      <nav className="navbar__links" aria-label="Основная навигация">
        <NavLink
          to="/"
          end
          className={({ isActive }) =>
            "navbar__link" + (isActive ? " navbar__link--active" : "")
          }
        >
          Карта
        </NavLink>
        <NavLink
          to="/vacancies"
          className={({ isActive }) =>
            "navbar__link" + (isActive ? " navbar__link--active" : "")
          }
        >
          Вакансии
        </NavLink>
        {user ? (
          <>
            <span className="navbar__link muted">{user.email}</span>
            <button
              type="button"
              className="btn"
              onClick={() => {
                void logout();
              }}
            >
              Выйти
            </button>
          </>
        ) : (
          <>
            <NavLink
              to="/login"
              className={({ isActive }) =>
                "navbar__link" + (isActive ? " navbar__link--active" : "")
              }
            >
              Вход
            </NavLink>
            <NavLink to="/register" className="btn btn--primary">
              Регистрация
            </NavLink>
          </>
        )}
        {status === "loading" && <span className="spinner" aria-label="загрузка" />}
      </nav>
    </header>
  );
}
