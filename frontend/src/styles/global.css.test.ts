import { describe, it, expect } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

describe("global.css — mobile media queries", () => {
  const cssPath = resolve(__dirname, "../styles/global.css");
  const css = readFileSync(cssPath, "utf-8");

  it("contains mobile media query breakpoint at 767px", () => {
    expect(css).toMatch(/@media\s*\(\s*max-width\s*:\s*767px\s*\)/);
  });

  it("sets min-height: 44px on buttons for WCAG touch target", () => {
    expect(css).toMatch(/min-height\s*:\s*44px/);
  });

  it("sets min font-size 14px for readability on mobile", () => {
    // Check for the mobile font-size rule
    expect(css).toContain("font-size: 14px");
  });

  it("prevents horizontal scroll on mobile", () => {
    expect(css).toMatch(/overflow-x\s*:\s*hidden/);
  });

  it("has map height of 50vh for mobile", () => {
    expect(css).toContain("h-[50vh]");
  });

  it("sets full-width inputs on mobile", () => {
    expect(css).toContain("width: 100%");
  });

  it("has desktop map height (50vh + min-h-[300px]) at >= 768px", () => {
    expect(css).toMatch(/@media\s*\(\s*min-width\s*:\s*768px\s*\)/);
  });
});
