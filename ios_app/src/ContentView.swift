import SwiftUI

struct ContentView: View {
    @StateObject private var cameraManager = CameraManager()
    @StateObject private var detector = Detector()
    @StateObject private var tracker = Tracker()
    @StateObject private var virtualCameraman = VirtualCameraman()
    
    @State private var isDebugMode = false
    @State private var lastLostEventID: UUID?
    
    var body: some View {
        GeometryReader { geometry in
            ZStack {
                // 1. Scalable Background (Video + Boxes)
                ZStack {
                    if let frame = cameraManager.currentFrame {
                        let frameW = CGFloat(CVPixelBufferGetWidth(frame))
                        let frameH = CGFloat(CVPixelBufferGetHeight(frame))
                        
                        // Creates a container that maintains the exact video aspect ratio
                        // but perfectly fills the device screen layout
                        Color.clear
                            .aspectRatio(frameW / frameH, contentMode: .fill)
                            .overlay(
                                GeometryReader { innerGeo in
                                    ZStack {
                                        FrameView(pixelBuffer: frame)
                                            .frame(width: innerGeo.size.width, height: innerGeo.size.height)
                                            .onChange(of: frame, perform: { newFrame in
                                                // Select mode: run Vision box tracker after user tap.
                                                // Auto mode: run detector continuously and let Tracker
                                                // lock onto the best candidate from detections.
                                                if tracker.mode == .select && tracker.isTracking {
                                                    tracker.updateTracking(with: newFrame)
                                                } else {
                                                    detector.processFrame(newFrame)
                                                }

                                                // UPDATE ZOOM CONTROLLER EVERY FRAME
                                                virtualCameraman.update(
                                                    targetBox: tracker.trackedBox,
                                                    activity: tracker.currentActivity,
                                                    screenSize: innerGeo.size
                                                )
                                            })
                                        
                                        // Bounding Boxes Layer
                                        // Uses the perfectly aligned inner geometry size
                                        if tracker.isTracking {
                                            if let box = tracker.trackedBox {
                                                BoundingBoxView(
                                                    normalizedRect: box.rect,
                                                    screenSize: innerGeo.size,
                                                    color: .green,
                                                    label: "TRACKING (\(String(format: "%.2f", box.confidence)))"
                                                )
                                            }
                                        } else {
                                            ForEach(detector.detectedBoxes, id: \.id) { box in
                                                if tracker.mode == .select {
                                                    BoundingBoxView(
                                                        normalizedRect: box.rect,
                                                        screenSize: innerGeo.size,
                                                        color: .red,
                                                        label: "Person (\(String(format: "%.2f", box.confidence)))"
                                                    )
                                                    .contentShape(Rectangle())
                                                    .onTapGesture {
                                                        // User selected a target to track
                                                        if let currentFrame = cameraManager.currentFrame {
                                                            tracker.startTracking(targetRect: box.rect, in: currentFrame)
                                                        }
                                                    }
                                                } else {
                                                    BoundingBoxView(
                                                        normalizedRect: box.rect,
                                                        screenSize: innerGeo.size,
                                                        color: .red,
                                                        label: "Person (\(String(format: "%.2f", box.confidence)))"
                                                    )
                                                }
                                            }
                                        }
                                    }
                                }
                            )
                            .frame(width: geometry.size.width, height: geometry.size.height)
                            .clipped()
                            
                    } else {
                        Color.black
                        Text("Initializing Camera...")
                            .foregroundColor(.white)
                    }
                }
                // Apply the digital pan and zoom
                .scaleEffect(virtualCameraman.scale)
                .offset(x: virtualCameraman.offsetX, y: virtualCameraman.offsetY)
                
                // 2. Static UI Controls Overlay
                VStack {
                    VStack(spacing: 10) {
                        Picker("Tracking Mode", selection: Binding(
                            get: { tracker.mode },
                            set: { newMode in
                                tracker.setMode(newMode)
                                virtualCameraman.reset()
                            }
                        )) {
                            ForEach(TrackingMode.allCases) { mode in
                                Text(mode.rawValue).tag(mode)
                            }
                        }
                        .pickerStyle(.segmented)
                        .padding(10)
                        .background(Color.black.opacity(0.6))
                        .cornerRadius(12)

                        if let lostMessage = tracker.lostEvent?.message {
                            Text(lostMessage)
                                .padding(.horizontal, 12)
                                .padding(.vertical, 8)
                                .background(Color.red.opacity(0.85))
                                .foregroundColor(.white)
                                .cornerRadius(10)
                        }

                        if tracker.mode == .select && !tracker.isTracking {
                            Text("Select mode: tap a surfer to start tracking")
                                .padding()
                                .background(Color.black.opacity(0.6))
                                .foregroundColor(.white)
                                .cornerRadius(10)
                        } else if tracker.mode == .auto && !tracker.isTracking {
                            Text("Auto mode: scanning for surfer")
                            .padding()
                            .background(Color.black.opacity(0.6))
                            .foregroundColor(.white)
                            .cornerRadius(10)
                        }
                    }
                    .padding(.top, geometry.safeAreaInsets.top + 12)
                    .padding(.horizontal)
                    
                    Spacer()
                    
                    Spacer()
                    
                    if isDebugMode {
                        VStack(alignment: .leading, spacing: 2) {
                            if tracker.isTracking {
                                Text("ID: \(tracker.trackID)")
                                Text("MODE: \(tracker.mode.rawValue.uppercased())")
                                Text("ACT: \(tracker.currentActivity.rawValue.lowercased())")
                                Text("SPD: \(String(format: "%.1f", tracker.classifierSignals.totalSpeed))")
                                Text("HIST: \(tracker.classifierSignals.historyCount)")
                            } else {
                                Text("STATUS: DETECTING")
                                Text("MODE: \(tracker.mode.rawValue.uppercased())")
                                Text("COUNT: \(detector.detectedBoxes.count)")
                            }
                            Text("ZOOM: \(String(format: "%.2fx", virtualCameraman.scale))")
                        }
                        .font(.system(.caption, design: .monospaced))
                        .foregroundColor(.yellow)
                        .padding(8)
                        .background(Color.black.opacity(0.6))
                        .cornerRadius(8)
                        .padding(.horizontal)
                        .padding(.bottom, 10)
                    }
                    
                    // Bottom Control Bar
                    HStack(spacing: 40) {
                        // Flip Camera
                        Button(action: {
                            cameraManager.flipCamera()
                        }) {
                            Image(systemName: "arrow.triangle.2.circlepath.camera.fill")
                                .font(.title2)
                                .foregroundColor(.white)
                                .frame(width: 50, height: 50)
                                .background(Color.black.opacity(0.5))
                                .clipShape(Circle())
                        }
                        
                        // Record
                        Button(action: {
                            cameraManager.toggleRecording()
                        }) {
                            ZStack {
                                Circle()
                                    .stroke(Color.white, lineWidth: 4)
                                    .frame(width: 75, height: 75)
                                
                                if cameraManager.isRecording {
                                    RoundedRectangle(cornerRadius: 8)
                                        .fill(Color.red)
                                        .frame(width: 35, height: 35)
                                } else {
                                    Circle()
                                        .fill(Color.red)
                                        .frame(width: 65, height: 65)
                                }
                            }
                        }
                        
                        // Action / Debug Column
                        VStack(spacing: 12) {
                            if tracker.mode == .select && tracker.isTracking {
                                Button(action: {
                                    tracker.stopTracking()
                                    virtualCameraman.reset()
                                }) {
                                    Image(systemName: "xmark")
                                        .font(.title2)
                                        .foregroundColor(.white)
                                        .frame(width: 50, height: 50)
                                        .background(Color.red.opacity(0.8))
                                        .clipShape(Circle())
                                }
                            }
                            
                            // Always show Debug Toggle
                            VStack(spacing: 2) {
                                Text("DEBUG")
                                    .font(.system(size: 8, weight: .bold))
                                    .foregroundColor(.white)
                                Toggle("", isOn: $isDebugMode)
                                    .toggleStyle(SwitchToggleStyle(tint: .yellow))
                                    .labelsHidden()
                                    .scaleEffect(0.8)
                            }
                            .frame(width: 50, height: 50)
                            .background(Color.black.opacity(0.5))
                            .clipShape(Circle())
                            .onChange(of: isDebugMode, perform: { newVal in
                                cameraManager.isDebugModeEnabled = newVal
                            })
                        }
                    }
                    .padding(.bottom, 30)
                }
            }
            .ignoresSafeArea()
            // Keep debug HUD state in CameraManager synchronized to
            // the source-of-truth publishers instead of frame-loop snapshots.
            .onReceive(tracker.$trackedBox) { newBox in
                cameraManager.currentTrackedBox = newBox
            }
            .onReceive(tracker.$trackID) { newTrackID in
                cameraManager.currentTrackID = newTrackID
            }
            .onReceive(tracker.$currentActivity) { newActivity in
                cameraManager.currentActivity = newActivity
            }
            .onReceive(tracker.$classifierSignals) { newSignals in
                cameraManager.currentSignals = newSignals
            }
            .onReceive(detector.$detectedBoxes) { newBoxes in
                cameraManager.currentDetectedBoxes = newBoxes

                // Auto mode lock logic runs on detector output.
                if tracker.mode == .auto, let frame = cameraManager.currentFrame {
                    let frameSize = CGSize(
                        width: CGFloat(CVPixelBufferGetWidth(frame)),
                        height: CGFloat(CVPixelBufferGetHeight(frame))
                    )
                    tracker.updateAutoTracking(with: newBoxes, frameSize: frameSize)
                }
            }
            .onReceive(virtualCameraman.$scale) { newScale in
                cameraManager.currentZoomScale = newScale
            }
            .onReceive(tracker.$lostEvent) { event in
                guard let event = event else { return }
                lastLostEventID = event.id
                let currentID = event.id
                DispatchQueue.main.asyncAfter(deadline: .now() + 2.5) {
                    if lastLostEventID == currentID {
                        tracker.clearLostEvent()
                    }
                }
            }
        }
        .onAppear {
            cameraManager.start()
        }
        .onDisappear {
            cameraManager.stop()
        }
    }
}

// Minimal view to display the CVPixelBuffer
struct FrameView: View {
    let pixelBuffer: CVPixelBuffer
    
    var body: some View {
        let ciImage = CIImage(cvPixelBuffer: pixelBuffer)
        let context = CIContext()
        guard let cgImage = context.createCGImage(ciImage, from: ciImage.extent) else {
            return AnyView(Color.black)
        }
        return AnyView(
             Image(decorative: cgImage, scale: 1.0, orientation: .up)
                .resizable()
                .scaledToFill()
        )
    }
}

// Wrapper to draw the box on top of the video
struct BoundingBoxView: View {
    let normalizedRect: CGRect
    let screenSize: CGSize
    let color: Color
    let label: String
    
    var body: some View {
        let absoluteFrame = CGRect(
            x: normalizedRect.origin.x * screenSize.width,
            y: normalizedRect.origin.y * screenSize.height,
            width: normalizedRect.width * screenSize.width,
            height: normalizedRect.height * screenSize.height
        )
        
        ZStack(alignment: .topLeading) {
            Rectangle()
                .path(in: absoluteFrame)
                .stroke(color, lineWidth: 3.0)
            
            Text(label)
                .font(.caption)
                .bold()
                .foregroundColor(.white)
                .padding(4)
                .background(color)
                .position(x: absoluteFrame.minX + (absoluteFrame.width / 2.0),
                          y: absoluteFrame.minY - 10)
        }
    }
}
