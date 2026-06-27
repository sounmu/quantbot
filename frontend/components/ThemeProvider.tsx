"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";

type Theme = "light" | "dark";

type ThemeContextValue = {
  theme: Theme;
  toggle: () => void;
};

const ThemeContext = createContext<ThemeContextValue>({
  theme: "light",
  toggle: () => {}
});

// layout의 인라인 스크립트가 첫 페인트 전에 .dark 클래스를 이미 설정한다.
// 여기서는 그 상태를 React state로 끌어와 토글/차트 색상에 동기화한다.
function readInitialTheme(): Theme {
  if (typeof document === "undefined") {
    return "light";
  }
  return document.documentElement.classList.contains("dark") ? "dark" : "light";
}

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setTheme] = useState<Theme>("light");

  // 마운트 시 실제 DOM 클래스(스크립트가 적용한 값)와 동기화
  useEffect(() => {
    setTheme(readInitialTheme());
  }, []);

  useEffect(() => {
    const root = document.documentElement;
    root.classList.toggle("dark", theme === "dark");
    try {
      localStorage.setItem("theme", theme);
    } catch {
      // localStorage 접근 불가(프라이빗 모드 등) — 무시
    }
  }, [theme]);

  const toggle = useCallback(() => {
    setTheme((current) => (current === "dark" ? "light" : "dark"));
  }, []);

  return <ThemeContext.Provider value={{ theme, toggle }}>{children}</ThemeContext.Provider>;
}

export function useTheme() {
  return useContext(ThemeContext);
}

// recharts용 테마 인지 팔레트. 속성(stroke/fill)은 CSS 변수가 안 먹으므로 실제 색을 고른다.
export function useChartPalette() {
  const { theme } = useTheme();
  const dark = theme === "dark";
  return {
    line: dark ? "#7c84ff" : "#4f46e5",
    grid: dark ? "#23272f" : "#eef0f3",
    axis: dark ? "#2c313b" : "#e6e8ec",
    tick: dark ? "#8b929e" : "#9aa1ab",
    tooltip: {
      borderRadius: 10,
      border: `1px solid ${dark ? "#2c313b" : "#e6e8ec"}`,
      backgroundColor: dark ? "#14161c" : "#ffffff",
      color: dark ? "#f3f5f8" : "#16181d",
      boxShadow: dark ? "0 6px 20px rgba(0, 0, 0, 0.45)" : "0 6px 20px rgba(20, 22, 28, 0.10)",
      fontSize: 12,
      padding: "8px 10px"
    } as const
  };
}
