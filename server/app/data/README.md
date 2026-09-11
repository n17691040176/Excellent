`city_regions.json` is derived from the project's existing
`province-city-china` package, version 8.5.8 (declared license: MIT),
`dist/level.json`. It uses the same normalization as
`admin-web/src/utils/region-options.js` and the mobile shipping-address picker:
municipalities use the province name as the city name.

Source project: https://github.com/uiwjs/province-city-china

When upgrading the address dataset, regenerate this province/city subset and
verify the admin and mobile pickers together. Existing seat names are not
automatically rewritten because they are historical order/ledger identifiers.
