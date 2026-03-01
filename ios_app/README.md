# Surf-Pal iOS Native App setup

This directory contains the Swift source code and Apple CoreML model to build the Surf-Pal app natively on iOS.

## Step 1: Create the Xcode Project
1. Open Xcode and select **Create a new Xcode project**.
2. Select **iOS** -> **App**, then click Next.
3. Fill in the product details:
   - **Product Name:** `SurfPal`
   - **Interface:** SwiftUI
   - **Language:** Swift
4. Choose a location to save your project and click Create.

## Step 2: Import the Source Files
1. Open a Finder window to this `ios_app` directory.
2. In Xcode, delete the default `ContentView.swift` file from the Project Navigator (left sidebar).
3. Drag the following files from Finder into your Xcode Project Navigator:
   - `CameraManager.swift`
   - `Detector.swift`
   - `Tracker.swift`
   - `VirtualCameraman.swift`
   - `ContentView.swift`
4. When the dialog appears, make sure **Copy items if needed** is checked, and click Finish.

## Step 3: Import the Machine Learning Model
1. If you haven't already, generate the Apple CoreML model from the PyTorch weights:
   - Open a terminal and navigate to the `models/` folder in this repository.
   - Run `python3 export_coreml.py`.
   - This will download the YOLOv8 weights and generate a `yolov8n.mlpackage` folder.
2. Locate the generated `yolov8n.mlpackage` file inside the `models/` directory.
3. Drag it into the Xcode Project Navigator, just like the Swift files. Make sure **Copy items if needed** is checked.
4. **CRITICAL STEP:** Click on `yolov8n.mlpackage` in the Xcode Project Navigator. Then look at the right sidebar (File Inspector). Under the **Target Membership** section, make sure the checkbox next to your app name (`SurfPal`) is **CHECKED**. Xcode will generate the necessary Swift code in the background.

## Step 4: Configure the Info.plist Permissions
Because this app uses the camera to track and the photo library to save videos, you must ask the user for permission. If you don't do this, the app will instantly crash on launch.

1. Click on your project name at the very top of the Project Navigator.
2. Under "Targets", select your app (`SurfPal`).
3. Go to the **Info** tab at the top.
4. Hover over any item in the Custom iOS Target Properties list and click the **+** button to add a new row.
5. Add the Camera permission:
   - **Key:** `Privacy - Camera Usage Description` (Raw key: `NSCameraUsageDescription`)
   - **Value:** `Surf-Pal needs access to the camera to track surfers.`
6. Click **+** again to add the Photo Library permission:
   - **Key:** `Privacy - Photo Library Additions Usage Description` (Raw key: `NSPhotoLibraryAddUsageDescription`)
   - **Value:** `Surf-Pal needs access to the photo library to save your tracking videos.`

## Step 5: Build and Run
1. Plug an iPhone into your Mac (the iOS Simulator doesn't support the camera).
2. Select your actual device from the run destinations drop-down menu at the very top of Xcode.
3. Press **Cmd + R** (or click the Play button) to build and run the app. Accept the camera permissions when prompted.
