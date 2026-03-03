# Surf-Pal iOS App (No Copy-Paste Setup)

This folder is now project-driven with XcodeGen, so you do not need to manually drag files into a new Xcode app.

## One-time prerequisites

1. Install Xcode.
2. Install XcodeGen:
   - `brew install xcodegen`

## Generate the project

From repo root:

```bash
cd ios_app
make generate
```

This does all of the following:

1. Verifies `models/yolov8n.mlpackage` exists.
2. Copies it into `ios_app/Resources/yolov8n.mlpackage`.
3. Generates `ios_app/SurfPal.xcodeproj` from `ios_app/project.yml`.
4. Build phase compiles and embeds `yolov8n.mlmodelc` into the app bundle automatically.

If the model is missing, generate it first from repo root:

```bash
python3 models/export_coreml.py
```

To explicitly copy the model into app resources:

```bash
cd ios_app
make sync-model
```

## Build from terminal (optional)

```bash
cd ios_app
make build-sim
```

## Run on device

1. Open `ios_app/SurfPal.xcodeproj`.
2. Select your iPhone as the run destination.
3. Press Run.
4. Accept camera and photo-library permissions.

## Important notes

- Source files for the app target are under `ios_app/src/`.
- `ios_app/generated/yolov8n.swift` is only for local terminal type-checking and is not included in the app target.
- CoreML model packaging is managed via `ios_app/scripts/sync_model.sh`.
