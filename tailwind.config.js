/** @type {import('tailwindcss').Config} */
module.exports = {
    content: [
        "./main.py",
        "./src/**/*.py",
    ],
    theme: {
        extend: {},
    },
    plugins: [require("daisyui")],
    daisyui: {
        themes: ["light", "dark"],
    },
};
