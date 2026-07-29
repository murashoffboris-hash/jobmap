import { useEffect, useRef, useState, forwardRef } from "react";
import { Link, NavLink, useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import {
  LogOut,
  Map as MapIcon,
  Menu,
  Moon,
  PlusCircle,
  Sun,
  User as UserIcon,
  Briefcase,
  FileText,
  X,
  Sparkles,
} from "lucide-react";
import { useAuthStore } from "@/store/auth";
import { useThemeStore } from "@/store/theme";
import { useAuthBootstrap } from "@/hooks/useAuth";
import Avatar from "@/components/Avatar";
import Button from "@/components/Button";
import { cn } from "@/utils/cn";

/**
 * Адаптивный Header:
 *  — Логотип JobMap слева.
 *  — Центральные ссылки (Карта / Вакансии).
 *  — Справа: theme toggle + (для гостя) Войти/Регистрация;
 *    для залогиненного — аватар с выпадающим меню.
 *  — На мобильных ссылки сворачиваются в боковую шторку.
 */
export default function Header(): JSX.Element {
  useAuthBootstrap();

  const user = useAuthStore((s) => s.user);
  const status = useAuthStore((s) => s.status);
  const logout = useAuthStore((s) => s.logout);

  const theme = useThemeStore((s) => s.theme);
  const toggleTheme = useThemeStore((s) => s.toggle);

  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  const menuRef = useRef<HTMLDivElement | null>(null);

  // Закрытие выпадающего меню по клику вне и по Escape.
  useEffect(() => {
    if (!menuOpen) return;
    function onClick(e: MouseEvent): void {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
      }
    }
    function onKey(e: KeyboardEvent): void {
      if (e.key === "Escape") setMenuOpen(false);
    }
    document.addEventListener("mousedown", onClick);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onClick);
      document.removeEventListener("keydown", onKey);
    };
  }, [menuOpen]);

  // Блокируем скролл body при открытой мобильной шторке.
  useEffect(() => {
    if (mobileOpen) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [mobileOpen]);

  async function handleLogout(): Promise<void> {
    setMenuOpen(false);
    await logout();
    navigate("/", { replace: true });
  }

  return (
    <header
      className={cn(
        "sticky top-0 z-40 w-full border-b border-ink-200/60 bg-white/80 backdrop-blur-md",
        "dark:border-ink-800 dark:bg-ink-950/80",
      )}
    >
      <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-2 px-4 py-2 sm:px-6 md:h-16 md:flex-nowrap md:py-0">
        <Link
          to="/"
          className="group flex items-center gap-2 text-base font-semibold tracking-tight text-ink-900 dark:text-ink-50 shrink-0"
        >
          <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-brand-500 to-brand-700 text-white shadow-soft transition-transform group-hover:scale-105">
            <Sparkles size={18} aria-hidden="true" />
          </span>
          <span>JobMap</span>
        </Link>

        {/* Desktop nav */}
        <nav className="ml-6 hidden items-center gap-1 md:flex" aria-label="Основная навигация">
          <HeaderNavLink to="/" icon={<MapIcon size={16} />}>
            Карта
          </HeaderNavLink>
          <HeaderNavLink to="/vacancies" icon={<Briefcase size={16} />}>
            Вакансии
          </HeaderNavLink>
          {user && (user.role === "employer" || user.role === "admin") && (
            <HeaderNavLink to="/vacancies/new" icon={<PlusCircle size={16} />}>
              Создать
            </HeaderNavLink>
          )}
        </nav>

        <div className="ml-auto flex items-center gap-2">
          <button
            type="button"
            onClick={toggleTheme}
            className="btn-ghost h-10 w-10 p-0"
            aria-label={theme === "dark" ? "Включить светлую тему" : "Включить тёмную тему"}
            title={theme === "dark" ? "Светлая тема" : "Тёмная тема"}
          >
            {theme === "dark" ? <Sun size={18} /> : <Moon size={18} />}
          </button>

          {status === "loading" && !user && (
            <span
              className="h-4 w-4 animate-spin rounded-full border-2 border-ink-300 border-t-brand-500 dark:border-ink-600"
              aria-label="загрузка"
            />
          )}

          <div className="hidden md:flex md:items-center md:gap-2">
            {user ? <UserMenu
              ref={menuRef}
              open={menuOpen}
              onToggle={() => setMenuOpen((v) => !v)}
              onClose={() => setMenuOpen(false)}
              onLogout={handleLogout}
              name={user.full_name}
              email={user.email}
              role={user.role}
            /> : <GuestActions />}
          </div>

          {/* Mobile: show auth buttons inline + hamburger for full nav */}
          <div className="flex items-center gap-2 md:hidden">
            {user ? (
              <button
                type="button"
                onClick={() => setMobileOpen(true)}
                className="btn-ghost flex items-center gap-1.5 px-3"
              >
                <Avatar name={user.full_name} email={user.email} size="sm" />
                <span className="text-sm font-medium max-w-[100px] truncate">
                  {user.full_name?.trim() || user.email.split("@")[0] || "Профиль"}
                </span>
              </button>
            ) : (
              <GuestActions />
            )}
            <button
              type="button"
              onClick={() => setMobileOpen(true)}
              className="btn-ghost h-10 w-10 p-0"
              aria-label="Открыть меню"
            >
              <Menu size={20} />
            </button>
          </div>
        </div>
      </div>

      {/* Мобильная шторка */}
      <AnimatePresence>
        {mobileOpen && (
          <>
            <motion.div
              key="backdrop"
              className="fixed inset-0 z-40 bg-ink-900/40 backdrop-blur-sm md:hidden"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setMobileOpen(false)}
            />
            <motion.aside
              key="drawer"
              role="dialog"
              aria-modal="true"
              className={cn(
                "fixed right-0 top-0 z-50 flex h-full w-72 max-w-[85vw] flex-col gap-4 p-5 shadow-2xl md:hidden",
                "bg-white dark:bg-ink-900",
              )}
              initial={{ x: "100%" }}
              animate={{ x: 0 }}
              exit={{ x: "100%" }}
              transition={{ type: "spring", stiffness: 280, damping: 30 }}
            >
              <div className="flex items-center justify-between">
                <span className="text-sm font-semibold uppercase tracking-wide muted">
                  Меню
                </span>
                <button
                  type="button"
                  onClick={() => setMobileOpen(false)}
                  className="btn-ghost h-9 w-9 p-0"
                  aria-label="Закрыть меню"
                >
                  <X size={18} />
                </button>
              </div>

              {user && (
                <div className="flex items-center gap-3 rounded-xl border border-ink-200 p-3 dark:border-ink-800">
                  <Avatar name={user.full_name} email={user.email} size="md" />
                  <div className="min-w-0">
                    <div className="truncate text-sm font-semibold">
                      {user.full_name || user.email}
                    </div>
                    <div className="truncate text-xs muted">{user.email}</div>
                  </div>
                </div>
              )}

              <nav className="flex flex-col gap-1" aria-label="Мобильная навигация">
                <MobileNavLink to="/" icon={<MapIcon size={16} />} onClick={() => setMobileOpen(false)}>
                  Карта
                </MobileNavLink>
                <MobileNavLink to="/vacancies" icon={<Briefcase size={16} />} onClick={() => setMobileOpen(false)}>
                  Вакансии
                </MobileNavLink>
                {user && (
                  <>
                    <MobileNavLink to="/profile" icon={<UserIcon size={16} />} onClick={() => setMobileOpen(false)}>
                      Профиль
                    </MobileNavLink>
                    <MobileNavLink to="/vacancies?mine=1" icon={<Briefcase size={16} />} onClick={() => setMobileOpen(false)}>
                      Мои вакансии
                    </MobileNavLink>
                    <MobileNavLink to="/applications" icon={<FileText size={16} />} onClick={() => setMobileOpen(false)}>
                      Мои отклики
                    </MobileNavLink>
                    {(user.role === "employer" || user.role === "admin") && (
                      <MobileNavLink to="/vacancies/new" icon={<PlusCircle size={16} />} onClick={() => setMobileOpen(false)}>
                        Создать вакансию
                      </MobileNavLink>
                    )}
                  </>
                )}
              </nav>

              <div className="mt-auto flex flex-col gap-2">
                {user ? (
                  <Button variant="outline" leftIcon={<LogOut size={16} />} onClick={handleLogout}>
                    Выйти
                  </Button>
                ) : (
                  <>
                    <Button
                      variant="outline"
                      onClick={() => {
                        setMobileOpen(false);
                        navigate("/login");
                      }}
                    >
                      Войти
                    </Button>
                    <Button
                      onClick={() => {
                        setMobileOpen(false);
                        navigate("/register");
                      }}
                    >
                      Регистрация
                    </Button>
                  </>
                )}
              </div>
            </motion.aside>
          </>
        )}
      </AnimatePresence>
    </header>
  );
}

interface HeaderNavLinkProps {
  to: string;
  icon: React.ReactNode;
  children: React.ReactNode;
}
function HeaderNavLink({ to, icon, children }: HeaderNavLinkProps): JSX.Element {
  return (
    <NavLink
      to={to}
      end={to === "/"}
      className={({ isActive }) =>
        cn(
          "inline-flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
          isActive
            ? "bg-brand-50 text-brand-700 dark:bg-brand-500/10 dark:text-brand-300"
            : "text-ink-600 hover:bg-ink-100 hover:text-ink-900 dark:text-ink-300 dark:hover:bg-ink-800 dark:hover:text-ink-50",
        )
      }
    >
      {icon}
      <span>{children}</span>
    </NavLink>
  );
}

interface MobileNavLinkProps {
  to: string;
  icon: React.ReactNode;
  children: React.ReactNode;
  onClick: () => void;
}
function MobileNavLink({ to, icon, children, onClick }: MobileNavLinkProps): JSX.Element {
  return (
    <NavLink
      to={to}
      end={to === "/"}
      onClick={onClick}
      className={({ isActive }) =>
        cn(
          "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
          isActive
            ? "bg-brand-50 text-brand-700 dark:bg-brand-500/10 dark:text-brand-300"
            : "text-ink-700 hover:bg-ink-100 dark:text-ink-200 dark:hover:bg-ink-800",
        )
      }
    >
      {icon}
      <span>{children}</span>
    </NavLink>
  );
}

function GuestActions(): JSX.Element {
  const navigate = useNavigate();
  return (
    <>
      <button
        type="button"
        onClick={() => navigate("/login")}
        className="btn-ghost px-3 py-2 text-sm"
      >
        Войти
      </button>
      <button
        type="button"
        onClick={() => navigate("/register")}
        className="btn-primary"
      >
        Регистрация
      </button>
    </>
  );
}

interface UserMenuProps {
  open: boolean;
  onToggle: () => void;
  onClose: () => void;
  onLogout: () => void;
  name: string | null;
  email: string;
  role: string;
}

const UserMenu = forwardRef<HTMLDivElement, UserMenuProps>(function UserMenu(
  { open, onToggle, onClose, onLogout, name, email, role },
  ref,
) {
  const display = name?.trim() || email.split("@")[0] || "Пользователь";
  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        onClick={onToggle}
        aria-haspopup="menu"
        aria-expanded={open}
        className={cn(
          "flex items-center gap-2 rounded-full p-1 pr-3 transition-colors",
          "hover:bg-ink-100 dark:hover:bg-ink-800",
        )}
      >
        <Avatar name={name} email={email} size="sm" ring />
        <span className="hidden text-sm font-medium text-ink-700 dark:text-ink-200 lg:inline">
          {display}
        </span>
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            role="menu"
            initial={{ opacity: 0, y: -4, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -4, scale: 0.98 }}
            transition={{ duration: 0.14 }}
            className={cn(
              "absolute right-0 top-full z-50 mt-2 w-64 overflow-hidden rounded-xl border shadow-xl",
              "border-ink-200 bg-white dark:border-ink-800 dark:bg-ink-900",
            )}
          >
            <div className="border-b border-ink-100 p-3 dark:border-ink-800">
              <div className="flex items-center gap-3">
                <Avatar name={name} email={email} size="md" />
                <div className="min-w-0">
                  <div className="truncate text-sm font-semibold">
                    {name?.trim() || "Без имени"}
                  </div>
                  <div className="truncate text-xs muted">{email}</div>
                </div>
              </div>
              <div className="mt-2">
                <span className="chip">{roleLabel(role)}</span>
              </div>
            </div>

            <MenuLink to="/profile" icon={<UserIcon size={16} />} onClick={onClose}>
              Профиль
            </MenuLink>
            <MenuLink to="/vacancies?mine=1" icon={<Briefcase size={16} />} onClick={onClose}>
              Мои вакансии
            </MenuLink>
            <MenuLink to="/applications" icon={<FileText size={16} />} onClick={onClose}>
              Мои отклики
            </MenuLink>
            {(role === "employer" || role === "admin") && (
              <MenuLink to="/vacancies/new" icon={<PlusCircle size={16} />} onClick={onClose}>
                Создать вакансию
              </MenuLink>
            )}

            <button
              type="button"
              role="menuitem"
              onClick={onLogout}
              className={cn(
                "flex w-full items-center gap-2 px-4 py-2.5 text-sm transition-colors",
                "text-red-600 hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-500/10",
              )}
            >
              <LogOut size={16} />
              <span>Выйти</span>
            </button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
});

interface MenuLinkProps {
  to: string;
  icon: React.ReactNode;
  children: React.ReactNode;
  onClick: () => void;
}
function MenuLink({ to, icon, children, onClick }: MenuLinkProps): JSX.Element {
  return (
    <NavLink
      to={to}
      role="menuitem"
      onClick={onClick}
      className={({ isActive }) =>
        cn(
          "flex items-center gap-2 px-4 py-2.5 text-sm transition-colors",
          isActive
            ? "bg-ink-50 text-brand-700 dark:bg-ink-800 dark:text-brand-300"
            : "text-ink-700 hover:bg-ink-50 dark:text-ink-200 dark:hover:bg-ink-800",
        )
      }
    >
      {icon}
      <span>{children}</span>
    </NavLink>
  );
}

function roleLabel(role: string): string {
  switch (role) {
    case "user":
      return "Соискатель";
    case "employer":
      return "Работодатель";
    case "admin":
      return "Администратор";
    default:
      return role;
  }
}
