# Signing Assets

Put signing assets here before cloud packaging or local Android release builds.

Recommended structure:
- `android/release.keystore`
- `ios/` for iOS certificate assets if you later package iOS

Current placeholders in `src/manifest.json`:
- `keystore`: `src/static/certs/android/release.keystore`
- `password`: `CHANGE_ME`
- `aliasname`: `excellent-release`

Do not commit real passwords or production certificates into public repositories.
