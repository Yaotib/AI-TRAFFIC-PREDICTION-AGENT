# Wayline (React)

    npm install
    npm run dev

Add ?locfail to the address to simulate "location unavailable".
Add ?routefail to simulate "route info unavailable" (Try again then works).

- src/HomeScreen.jsx  home screen (Where to?, suggestions, start point)
- src/MapScreen.jsx   route screen: map, bottom sheet, Details
- src/MapSvg.jsx      the illustrative map and route lines
- src/routes.js       sample route data and the recommendation logic
- src/App.jsx         switches between home and route screens
