import AVFoundation
import Vision
import CoreImage
import Combine
import PhotosUI

class CameraManager: NSObject, ObservableObject {
    @Published var currentFrame: CVPixelBuffer?
    @Published var isRecording = false
    
    // Configurable state
    var isDebugModeEnabled: Bool = false
    var currentTrackedBox: BoundingBox? = nil
    var currentDetectedBoxes: [BoundingBox] = []
    var currentTrackID: String = ""
    var currentActivity: Activity = .unknown
    var currentZoomScale: CGFloat = 1.0
    var currentSignals = ClassifierSignals()
    
    // Capture state
    private let captureSession = AVCaptureSession()
    private let videoOutput = AVCaptureVideoDataOutput()
    private let sessionQueue = DispatchQueue(label: "camera.session.queue")
    private var currentCameraPosition: AVCaptureDevice.Position = .back
    
    // Recording state (Asset Writer)
    private var assetWriter: AVAssetWriter?
    private var videoInput: AVAssetWriterInput?
    private var pixelBufferAdaptor: AVAssetWriterInputPixelBufferAdaptor?
    private var recordingURL: URL?
    private var isAssetWriterReady = false
    private var sessionAtSourceTime: CMTime?
    
    override init() {
        super.init()
        UIDevice.current.beginGeneratingDeviceOrientationNotifications()
        setupDeviceOrientationObserver()
        setupCamera()
    }
    
    private func setupDeviceOrientationObserver() {
        NotificationCenter.default.addObserver(self, selector: #selector(handleOrientationChange), name: UIDevice.orientationDidChangeNotification, object: nil)
    }
    
    @objc private func handleOrientationChange() {
        sessionQueue.async {
            self.updateVideoOrientation()
        }
    }
    
    private func updateVideoOrientation() {
        guard let connection = videoOutput.connection(with: .video) else { return }
        let orientation = UIDevice.current.orientation
        
        let videoOrientation: AVCaptureVideoOrientation
        let rotationAngle: CGFloat
        
        switch orientation {
        case .portrait:
            videoOrientation = .portrait
            rotationAngle = 90
        case .portraitUpsideDown:
            videoOrientation = .portraitUpsideDown
            rotationAngle = 270
        case .landscapeLeft:
            videoOrientation = .landscapeRight // Phone rotated left (side button up) -> Video Right
            rotationAngle = 0
        case .landscapeRight:
            videoOrientation = .landscapeLeft // Phone rotated right (side button down) -> Video Left
            rotationAngle = 180
        case .faceUp, .faceDown, .unknown:
            return 
        @unknown default:
            return
        }
        
        if connection.isVideoOrientationSupported {
            connection.videoOrientation = videoOrientation
        }
        if #available(iOS 17.0, macOS 14.0, *) {
            if connection.isVideoRotationAngleSupported(rotationAngle) {
                connection.videoRotationAngle = rotationAngle
            }
        }
    }
    
    private func setupCamera() {
        sessionQueue.async {
            self.captureSession.beginConfiguration()
            self.addInput(for: self.currentCameraPosition)
            
            // Set up pixel buffer output
            self.videoOutput.setSampleBufferDelegate(self, queue: DispatchQueue(label: "camera.video.data.queue"))
            self.videoOutput.alwaysDiscardsLateVideoFrames = true
            self.videoOutput.videoSettings = [kCVPixelBufferPixelFormatTypeKey as String: Int(kCVPixelFormatType_32BGRA)]
            
            if self.captureSession.canAddOutput(self.videoOutput) {
                self.captureSession.addOutput(self.videoOutput)
            }
            self.captureSession.commitConfiguration()
            self.updateVideoOrientation()
        }
    }
    
    private func addInput(for position: AVCaptureDevice.Position) {
        for input in captureSession.inputs {
            captureSession.removeInput(input)
        }
        
        guard let device = AVCaptureDevice.default(.builtInWideAngleCamera, for: .video, position: position) else { return }
        
        do {
            let videoInput = try AVCaptureDeviceInput(device: device)
            if captureSession.canAddInput(videoInput) {
                captureSession.addInput(videoInput)
            }
        } catch {
            print("Failed configuring camera input: \(error)")
        }
    }
    
    func flipCamera() {
        sessionQueue.async {
            self.captureSession.beginConfiguration()
            self.currentCameraPosition = self.currentCameraPosition == .back ? .front : .back
            self.addInput(for: self.currentCameraPosition)
            self.captureSession.commitConfiguration()
            self.updateVideoOrientation()
        }
    }
    
    func start() {
        sessionQueue.async {
            if !self.captureSession.isRunning {
                self.captureSession.startRunning()
            }
        }
    }
    
    func stop() {
        sessionQueue.async {
            if self.captureSession.isRunning {
                self.captureSession.stopRunning()
            }
        }
    }
    
    // MARK: - Asset Writer Methods
    
    func toggleRecording() {
        sessionQueue.async {
            if self.isRecording {
                self.stopAssetWriter()
            } else {
                self.startAssetWriter()
            }
        }
    }
    
    private func startAssetWriter() {
        let tempDir = FileManager.default.temporaryDirectory
        let fileUrl = tempDir.appendingPathComponent(UUID().uuidString + ".mp4")
        self.recordingURL = fileUrl
        
        do {
            assetWriter = try AVAssetWriter(outputURL: fileUrl, fileType: .mp4)
            
            // Determine dimensions based on current device orientation
            let orientation = UIDevice.current.orientation
            let isLandscape = orientation == .landscapeLeft || orientation == .landscapeRight
            
            let width = isLandscape ? 1920 : 1080
            let height = isLandscape ? 1080 : 1920
            
            let videoSettings: [String: Any] = [
                AVVideoCodecKey: AVVideoCodecType.h264,
                AVVideoWidthKey: width,
                AVVideoHeightKey: height
            ]
            
            videoInput = AVAssetWriterInput(mediaType: .video, outputSettings: videoSettings)
            videoInput?.expectsMediaDataInRealTime = true
            
            let sourcePixelBufferAttributes: [String: Any] = [
                kCVPixelBufferPixelFormatTypeKey as String: Int(kCVPixelFormatType_32BGRA),
                kCVPixelBufferWidthKey as String: width,
                kCVPixelBufferHeightKey as String: height
            ]
            
            pixelBufferAdaptor = AVAssetWriterInputPixelBufferAdaptor(
                assetWriterInput: videoInput!,
                sourcePixelBufferAttributes: sourcePixelBufferAttributes
            )
            
            if assetWriter!.canAdd(videoInput!) {
                assetWriter!.add(videoInput!)
            }
            
            assetWriter!.startWriting()
            isAssetWriterReady = true
            sessionAtSourceTime = nil
            
            DispatchQueue.main.async { self.isRecording = true }
        } catch {
            print("Failed to initialize AVAssetWriter: \(error)")
        }
    }
    
    private func stopAssetWriter() {
        self.isAssetWriterReady = false
        self.videoInput?.markAsFinished()
        self.assetWriter?.finishWriting {
            if self.assetWriter?.status == .completed, let url = self.recordingURL {
                // Save to photos library
                PHPhotoLibrary.shared().performChanges({
                    PHAssetChangeRequest.creationRequestForAssetFromVideo(atFileURL: url)
                }) { saved, error in
                    if saved {
                        print("Video successfully saved to Photos.")
                    } else if let error = error {
                        print("Error saving video: \(error)")
                    }
                    try? FileManager.default.removeItem(at: url)
                }
            } else {
                print("Asset writer failed with status: \(String(describing: self.assetWriter?.status))")
            }
            self.assetWriter = nil
            self.videoInput = nil
            self.pixelBufferAdaptor = nil
            
            DispatchQueue.main.async { self.isRecording = false }
        }
    }
}

extension CameraManager: AVCaptureVideoDataOutputSampleBufferDelegate {
    func captureOutput(_ output: AVCaptureOutput, didOutput sampleBuffer: CMSampleBuffer, from connection: AVCaptureConnection) {
        guard let pixelBuffer = CMSampleBufferGetImageBuffer(sampleBuffer) else { return }
        
        // 1. Send the raw frame to the UI and processing pipeline
        DispatchQueue.main.async {
            self.currentFrame = pixelBuffer
        }
        
        // 2. If recording, burn debug HUD if enabled, and append to AssetWriter
        if self.isAssetWriterReady, let writer = self.assetWriter, let input = self.videoInput, input.isReadyForMoreMediaData, let adaptor = self.pixelBufferAdaptor {
            let timestamp = CMSampleBufferGetPresentationTimeStamp(sampleBuffer)
            
            if self.sessionAtSourceTime == nil {
                writer.startSession(atSourceTime: timestamp)
                self.sessionAtSourceTime = timestamp
            }
            
            var bufferToWrite = pixelBuffer
            
            if self.isDebugModeEnabled {
                // Draw shapes on a copied buffer
                if let debugBuffer = HUDOverlay.drawDebugHUD(
                    on: pixelBuffer,
                    trackedBox: currentTrackedBox,
                    detectedBoxes: currentDetectedBoxes,
                    trackID: currentTrackID,
                    activity: currentActivity,
                    zoomScale: currentZoomScale,
                    signals: currentSignals) {
                    bufferToWrite = debugBuffer
                }
            }
            
            adaptor.append(bufferToWrite, withPresentationTime: timestamp)
        }
    }
}
