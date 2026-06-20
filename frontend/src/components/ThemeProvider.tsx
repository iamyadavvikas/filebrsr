"use client";

import { createContext, useContext, useEffect, useState } from "react";

type Theme = "light" | "dark";

const ThemeContext = createContext<{
  theme: Theme;
  toggleTheme: () => void;
}>({ theme: "light", toggleTheme: () => {} });

export function useTheme() {
  return useContext(ThemeContext);
}

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setTheme] = useState<Theme>("light");
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    // Dark mode disabled — always force light theme.
    // const stored = localStorage.getItem("theme") as Theme | null;
    // const initial = stored || "light";
    const initial: Theme = "light";
    setTheme(initial);
    // document.documentElement.classList.toggle("dark", initial === "dark");
    document.documentElement.classList.remove("dark");
    setMounted(true);
  }, []);

  const toggleTheme = () => {
    // Dark mode disabled — toggle is a no-op, theme stays light.
    // const next = theme === "light" ? "dark" : "light";
    // setTheme(next);
    // localStorage.setItem("theme", next);
    // document.documentElement.classList.toggle("dark", next === "dark");
    setTheme("light");
    document.documentElement.classList.remove("dark");
  };

  if (!mounted) return <>{children}</>;

  return (
    <ThemeContext.Provider value={{ theme, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}
