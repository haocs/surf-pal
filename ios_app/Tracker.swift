import Vision
import CoreLocation
import Combine

// Re-using the BoundingBox from Detector.swift

class Tracker: ObservableObject {
    @Published var isTracking = false
    @Published var trackedBox: BoundingBox?
    
    // Debug info
    @Published var trackID: String = ""
    @Published var currentActivity: Activity = .unknown
    @Published var classifierSignals = ClassifierSignals()
    
    private var sequenceRequestHandler = VNSequenceRequestHandler()
    private var lastObservation: VNDetectedObjectObservation?
    private let activityClassifier = ActivityClassifier()
    private var frameSize = CGSize(width: 1, height: 1)
    
    func startTracking(targetRect: CGRect, in pixelBuffer: CVPixelBuffer) {
        self.isTracking = true
        // Assign a pseudo-random ID for this tracking session
        self.trackID = String(format: "ID:%04d", Int.random(in: 1000...9999))
        self.activityClassifier.reset()
        
        let width = CGFloat(CVPixelBufferGetWidth(pixelBuffer))
        let height = CGFloat(CVPixelBufferGetHeight(pixelBuffer))
        self.frameSize = CGSize(width: width, height: height)
        
        // Create an observation from the normalized rect
        // the Y coordinates in Vision are inverted (0 is bottom)
        let visionRect = CGRect(x: targetRect.origin.x,
                                y: 1 - targetRect.origin.y - targetRect.height,
                                width: targetRect.width,
                                height: targetRect.height)
        
        lastObservation = VNDetectedObjectObservation(boundingBox: visionRect)
        
        // Create initial box and perform one round of classification
        self.trackedBox = BoundingBox(rect: targetRect, confidence: 1.0)
        self.currentActivity = activityClassifier.update(targetRect: targetRect, frameSize: self.frameSize)
        self.classifierSignals = activityClassifier.signals
    }
    
    func stopTracking() {
        self.isTracking = false
        self.trackedBox = nil
        self.trackID = ""
        self.lastObservation = nil
        self.sequenceRequestHandler = VNSequenceRequestHandler()
        self.activityClassifier.reset()
        self.currentActivity = .unknown
    }
    
    func updateTracking(with pixelBuffer: CVPixelBuffer) {
        guard let observation = lastObservation else { return }
        
        let request = VNTrackObjectRequest(detectedObjectObservation: observation) { [weak self] request, error in
            guard let self = self else { return }
            
            if let result = request.results?.first as? VNDetectedObjectObservation {
                self.lastObservation = result
                
                // Convert back from Vision coordinates (Y inverted)
                let rect = result.boundingBox
                let normalizedRect = CGRect(x: rect.origin.x,
                                            y: 1 - rect.origin.y - rect.height,
                                            width: rect.width,
                                            height: rect.height)
                
                DispatchQueue.main.async {
                    self.trackedBox = BoundingBox(rect: normalizedRect, confidence: result.confidence)
                    self.currentActivity = self.activityClassifier.update(targetRect: normalizedRect, frameSize: self.frameSize)
                    self.classifierSignals = self.activityClassifier.signals
                }
            } else {
                // Tracking lost
                DispatchQueue.main.async {
                    self.stopTracking()
                }
            }
        }
        
        // request.trackingLevel = .accurate // .fast or .accurate
        
        do {
            try sequenceRequestHandler.perform([request], on: pixelBuffer)
        } catch {
            print("Tracking failed: \(error)")
        }
    }
}
