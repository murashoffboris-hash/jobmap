import { Link } from "react-router-dom";

export default function NotFoundPage(): JSX.Element {
  return (
    <div className="page">
      <h1 className="page__title">404</h1>
      <p className="muted">Страница не найдена.</p>
      <p>
        <Link to="/" className="btn">
          На главную
        </Link>
      </p>
    </div>
  );
}
