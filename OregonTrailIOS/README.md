# OregonTrailIOS

Native SwiftUI scaffold for the Oregon Trail terminal game.

## What is included

- Setup flow: leader name, profession, departure month
- Core gameplay loop: travel, rest, hunt, pace/rations changes
- Random trail events: illness, weather, wagon breakdown, robbery/animals
- Landmark progression with optional fort shop prompt
- In-app store to buy supplies
- Win/lose state and score

## Open in Xcode

1. Install [XcodeGen](https://github.com/yonaskolb/XcodeGen) if needed.
2. Generate project files from this directory:

```bash
cd /Users/brandonlines/Documents/Oregon Trail/OregonTrailIOS
xcodegen generate
```

3. Open `OregonTrailIOS.xcodeproj` in Xcode.
4. Select an iOS Simulator and run.

## Notes

- This is a clean SwiftUI port scaffold of your Python game loop, not a pixel-perfect feature parity port.
- UI and systems are organized so additional mechanics and polish can be layered in quickly.
