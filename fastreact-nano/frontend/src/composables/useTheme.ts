/**
 * Theme composable
 */

import { ref, onMounted } from "vue";

export type Theme = "light" | "dark" | "auto";

const THEME_KEY = "fastreact-theme";

export function useTheme() {
  const theme = ref<Theme>("auto");
  const isDark = ref(false);

  function applyTheme(value: Theme) {
    let actualTheme: "light" | "dark";

    if (value === "auto") {
      actualTheme = window.matchMedia("(prefers-color-scheme: dark)").matches
        ? "dark"
        : "light";
    } else {
      actualTheme = value;
    }

    isDark.value = actualTheme === "dark";

    if (actualTheme === "dark") {
      document.documentElement.classList.add("dark");
    } else {
      document.documentElement.classList.remove("dark");
    }
  }

  function setTheme(value: Theme) {
    theme.value = value;
    localStorage.setItem(THEME_KEY, value);
    applyTheme(value);
  }

  function toggleTheme() {
    if (theme.value === "light") {
      setTheme("dark");
    } else if (theme.value === "dark") {
      setTheme("light");
    } else {
      setTheme("light");
    }
  }

  onMounted(() => {
    // Load saved theme
    const saved = localStorage.getItem(THEME_KEY) as Theme | null;
    if (saved) {
      theme.value = saved;
    }

    applyTheme(theme.value);

    // Listen for system theme changes
    const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
    mediaQuery.addEventListener("change", () => {
      if (theme.value === "auto") {
        applyTheme("auto");
      }
    });
  });

  return {
    theme,
    isDark,
    setTheme,
    toggleTheme,
  };
}
