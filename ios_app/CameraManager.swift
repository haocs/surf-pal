import AVFoundation
import Vision
import CoreImage
import Combine
import PhotosUI

class CameraManager: NSObject, ObservableObject {
    @Published var currentFrame: CVPixelBuffer?
    @Published var isRecording = false
    
    private let captureSession = AVCaptureSession()
    private let videoOutput = AVCaptureVideoDataOutput()
    private let movieOutput = AVCaptureMovieFileOutput()
    private let sessionQueue = DispatchQueue(label: "camera.session.queue")
    
    private var currentCameraPosition: AVCaptureDevice.Position = .back
    
    override init() {
        super.init()
        setupCamera()
    }
    
    private func setupCamera() {
        sessionQueue.async {
            self.captureSession.beginConfiguration()
            
            // Set up input
            self.addInput(for: self.currentCameraPosition)
            
            // Set up pixel buffer output
            self.videoOutput.setSampleBufferDelegate(self, queue: DispatchQueue(label: "camera.video.data.queue"))
            self.videoOutput.alwaysDiscardsLateVideoFrames = true
            self.videoOutput.videoSettings = [kCVPixelBufferPixelFormatTypeKey as String: Int(kCVPixelFormatType_32BGRA)]
            
            if self.captureSession.canAddOutput(self.videoOutput) {
                self.captureSession.addOutput(self.videoOutput)
            }
            // Fix orientation for pixel buffer
            if let connection = self.videoOutput.connection(with: .video) {
                if #available(iOS 17.0, macOS 14.0, *) {
                    connection.videoRotationAngle = 90
                } else {
                    connection.videoOrientation = .portrait
                }
            }
            
            // Set up movie file output
            if self.captureSession.canAddOutput(self.movieOutput) {
                self.captureSession.addOutput(self.movieOutput)
            }
            
            self.captureSession.commitConfiguration()
        }
    }
    
    private func addInput(for position: AVCaptureDevice.Position) {
        // Remove existing inputs
        for input in captureSession.inputs {
            captureSession.removeInput(input)
        }
        
        guard let device = AVCaptureDevice.default(.builtInWideAngleCamera, for: .video, position: position) else {
            print("Failed to get camera device")
            return
        }
        
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
            
            // Fix connection orientation after adding new input
            if let connection = self.videoOutput.connection(with: .video) {
                if #available(iOS 17.0, macOS 14.0, *) {
                    connection.videoRotationAngle = 90
                } else {
                    connection.videoOrientation = .portrait
                }
            }
            self.captureSession.commitConfiguration()
        }
    }
    
    func toggleRecording() {
        sessionQueue.async {
            if self.movieOutput.isRecording {
                self.movieOutput.stopRecording()
                DispatchQueue.main.async { self.isRecording = false }
            } else {
                let tempDir = FileManager.default.temporaryDirectory
                let fileUrl = tempDir.appendingPathComponent(UUID().uuidString + ".mp4")
                
                // Ensure proper orientation for the recorded file
                if let connection = self.movieOutput.connection(with: .video) {
                    if #available(iOS 17.0, macOS 14.0, *) {
                        connection.videoRotationAngle = 90
                    } else {
                        connection.videoOrientation = .portrait
                    }
                }
                
                self.movieOutput.startRecording(to: fileUrl, recordingDelegate: self)
                DispatchQueue.main.async { self.isRecording = true }
            }
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
}

extension CameraManager: AVCaptureVideoDataOutputSampleBufferDelegate {
    func captureOutput(_ output: AVCaptureOutput, didOutput sampleBuffer: CMSampleBuffer, from connection: AVCaptureConnection) {
        guard let pixelBuffer = CMSampleBufferGetImageBuffer(sampleBuffer) else { return }
        
        DispatchQueue.main.async {
            self.currentFrame = pixelBuffer
        }
    }
}

extension CameraManager: AVCaptureFileOutputRecordingDelegate {
    func fileOutput(_ output: AVCaptureFileOutput, didFinishRecordingTo outputFileURL: URL, from connections: [AVCaptureConnection], error: Error?) {
        if let error = error {
            print("Error recording movie: \(error)")
            return
        }
        
        // Save to photos library
        PHPhotoLibrary.shared().performChanges({
            PHAssetChangeRequest.creationRequestForAssetFromVideo(atFileURL: outputFileURL)
        }) { saved, error in
            if saved {
                print("Video successfully saved to Photos.")
            } else if let error = error {
                print("Error saving video: \(error)")
            }
            // Cleanup temp file
            try? FileManager.default.removeItem(at: outputFileURL)
        }
    }
}
