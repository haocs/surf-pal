import SwiftUI

struct ContentView: View {
    @StateObject private var cameraManager = CameraManager()
    @StateObject private var detector = Detector()
    @StateObject private var tracker = Tracker()
    @StateObject private var virtualCameraman = VirtualCameraman()
    
    @State private var isDebugMode = false
    
    var body: some View {
        GeometryReader { geometry in
            ZStack {
                // 1. Scalable Background (Video + Boxes)
                ZStack {
                    if let frame = cameraManager.currentFrame {
                        FrameView(pixelBuffer: frame)
                            .onChange(of: frame, perform: { newFrame in
                                if tracker.isTracking {
                                    tracker.updateTracking(with: newFrame)
                                } else {
                                    detector.processFrame(newFrame)
                                }
                            })
                            .frame(width: geometry.size.width, height: geometry.size.height)
                            .clipped()
                    } else {
                        Color.black
                        Text("Initializing Camera...")
                            .foregroundColor(.white)
                    }
                    
                    // Bounding Boxes Layer
                    if tracker.isTracking {
                        if let box = tracker.trackedBox {
                            BoundingBoxView(
                                normalizedRect: box.rect,
                                screenSize: geometry.size,
                                color: .green,
                                label: "TRACKING (\(String(format: "%.2f", box.confidence)))"
                            )
                        }
                    } else {
                        ForEach(detector.detectedBoxes, id: \.id) { box in
                            BoundingBoxView(
                                normalizedRect: box.rect,
                                screenSize: geometry.size,
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
                        }
                    }
                }
                // Apply the digital pan and zoom
                .scaleEffect(virtualCameraman.scale)
                .offset(x: virtualCameraman.offsetX, y: virtualCameraman.offsetY)
                
                // 2. Static UI Controls Overlay
                VStack {
                    // Top Bar
                    HStack {
                        Spacer()
                        Toggle("Debug", isOn: $isDebugMode)
                            .toggleStyle(SwitchToggleStyle(tint: .yellow))
                            .labelsHidden()
                            .padding()
                            .background(Color.black.opacity(0.6))
                            .cornerRadius(10)
                            .padding()
                            .onChange(of: isDebugMode, perform: { newVal in
                                cameraManager.isDebugModeEnabled = newVal
                            })
                    }
                    
                    if isDebugMode && tracker.isTracking {
                        VStack(alignment: .leading) {
                            Text("ID: \(tracker.trackID)")
                            Text("STATE: \(tracker.currentActivity.rawValue)")
                            Text("ZOOM: \(String(format: "%.2fx", virtualCameraman.scale))")
                            Divider().background(Color.white)
                            Text("SPD: \(String(format: "%.1f", tracker.classifierSignals.totalSpeed))")
                            Text("V-SPD: \(String(format: "%.1f", tracker.classifierSignals.vertSpeed))")
                            Text("VAR: \(String(format: "%.3f", tracker.classifierSignals.areaCV))")
                            Text("AR: \(String(format: "%.2f", tracker.classifierSignals.avgAR))")
                        }
                        .font(.caption.monospaced())
                        .foregroundColor(.yellow)
                        .padding()
                        .background(Color.black.opacity(0.6))
                        .cornerRadius(8)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .padding(.horizontal)
                    }
                    
                    if !tracker.isTracking {
                        Text("Tap a person to start tracking")
                            .padding()
                            .background(Color.black.opacity(0.6))
                            .foregroundColor(.white)
                            .cornerRadius(10)
                            .padding(.top, 50)
                    }
                    
                    Spacer()
                    
                    // Bottom Control Bar
                    HStack(spacing: 40) {
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
                        
                        if tracker.isTracking {
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
                        } else {
                            Color.clear.frame(width: 50, height: 50)
                        }
                    }
                    .padding(.bottom, 40)
                }
            }
            .ignoresSafeArea()
            // Route state from Tracker/VC down to CameraManager whenever it changes
            // so that CameraManager has the latest frame values to burn into the video
            .onChange(of: tracker.trackedBox?.id, perform: { newId in
                virtualCameraman.update(targetBox: tracker.trackedBox, screenSize: geometry.size)
                
                cameraManager.currentTrackedBox = tracker.trackedBox
                cameraManager.currentTrackID = tracker.trackID
                cameraManager.currentActivity = tracker.currentActivity
                cameraManager.currentSignals = tracker.classifierSignals
                cameraManager.currentZoomScale = virtualCameraman.scale
            })
            .onChange(of: detector.detectedBoxes.first?.id, perform: { _ in
                cameraManager.currentDetectedBoxes = detector.detectedBoxes
            })
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
