# App Assets Checklist

Before building Android or iOS packages, prepare these assets and then wire them into `src/manifest.json`.

Recommended assets:
- App icon set
- Splash screen background image
- Splash center logo
- Store submission icon
- Android signing keystore

Recommended package metadata to confirm before release:
- Android package name: `com.excellent.mall`
- App scheme: `excellent`
- DCloud appid
- WeChat mini program appid
- Signing certificate path and password

Suggested locations:
- Icons: `src/static/icons/`
- Certificates: `src/static/certs/android/`
