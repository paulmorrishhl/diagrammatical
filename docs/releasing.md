# Release and local development

The intended first release is `0.1.0`, matching the plugin, marketplace and package manifests.
Follow `RELEASE_CHECKLIST.md`; do not update screenshots automatically in CI. Local acceptance must
install from the local marketplace rather than relying only on `--plugin-dir`.

Reviewed visual baselines are platform-sensitive and are captured on macOS/arm64. GitHub visual
regression jobs therefore use the matching `macos-15` runner family. A maintainer must inspect and
explicitly update baselines locally; CI never accepts or rewrites changed screenshots.

No release command in this repository pushes, tags, publishes or creates a GitHub release. Those
external actions require explicit maintainer authorisation after every required v1 audit item passes.
