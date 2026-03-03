.PHONY: generate sync-model build-sim

generate:
	./scripts/generate_project.sh

sync-model:
	./scripts/sync_model.sh

build-sim: generate
	xcodebuild -project SurfPal.xcodeproj -scheme SurfPal -destination "platform=iOS Simulator,name=iPhone 16" build
