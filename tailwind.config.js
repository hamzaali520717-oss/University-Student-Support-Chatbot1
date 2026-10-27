/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./templates/**/*.html",
    "./apps/**/templates/**/*.html",
    "./node_modules/flowbite/**/*.js",
  ],
  // Classes built as Python strings (apps/portal/forms.py's
  // PASSWORD_INPUT_CLASSES) never appear literally in a scanned .html/.js
  // file, so the content scanner above can't find them - safelist them
  // explicitly instead of duplicating the class name into a template just to
  // be "seen".
  safelist: ["pr-10"],
  theme: {
    extend: {
      colors: {
        // Modern editorial academic palette: deep green is the dominant,
        // safe-contrast workhorse (text/buttons/nav); accent orange is a
        // spark used sparingly (badges, hovers, borders, hero CTAs) since
        // it does not clear 4.5:1 on white at body-text size.
        brand: {
          DEFAULT: "#1d4e42",
          50: "#f2f8f6",
          100: "#ddefe8",
          500: "#1d4e42",
          600: "#173f36",
          700: "#12302a",
        },
        accent: {
          DEFAULT: "#d97a3c",
          50: "#fdf1e7",
          500: "#d97a3c",
          600: "#c2622a",
          700: "#9c4a1f",
        },
      },
      fontFamily: {
        // Fraunces: soft, high-contrast display serif carrying the
        // editorial/academic personality. Work Sans: humanist body face,
        // also used (small-caps, tracked-out) for kicker/eyebrow labels.
        display: ["\"Fraunces\"", "serif"],
        body: ["\"Work Sans\"", "sans-serif"],
      },
    },
  },
  plugins: [require("flowbite/plugin")],
};
