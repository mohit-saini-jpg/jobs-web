# Tailwind build for resume-maker.html

The previous version of `resume-maker.html` loaded Tailwind via
`https://cdn.tailwindcss.com`, which prints a "should not be used in
production" warning to the browser console.

We now ship a precompiled, minified Tailwind CSS file at
`../resume-maker.tailwind.css`, generated from the classes used in
`resume-maker.html` plus the custom tokens (brand palette, soft/card
shadows, pulseSoft keyframes) declared in `tailwind.config.js`.

## Regenerate after editing resume-maker.html

```bash
cd .tailwind-build
npx --yes tailwindcss@3 -c tailwind.config.js -i input.css -o ../resume-maker.tailwind.css --minify
```

Commit the updated `resume-maker.tailwind.css` alongside your HTML changes.
