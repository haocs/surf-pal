import Vision
import CoreLocation
import Combine

// Re-using the BoundingBox from Detector.swift

class Tracker: ObservableObject {
    @Published var trackedBox: BoundingBox?
    @Published var isTracking = false
    
    private var sequenceRequestHandler = VNSequenceRequestHandler()
    private var trackRequest: VNTrackObjectRequest?
    
    func startTracking(targetRect: CGRect, in frame: CVPixelBuffer) {
        // Create an observation from the user-selected rect
        // Remember to flip the Y coordinate back to Vision's coordinate space (origin bottom-left)
        let visionY = 1.0 - targetRect.origin.y - targetRect.size.height
        let visionRect = CGRect(x: targetRect.origin.x,
                                y: visionY,
                                width: targetRect.size.width,
                                height: targetRect.size.height)
        
        let observation = VNDetectedObjectObservation(boundingBox: visionRect)
        
        self.trackRequest = VNTrackObjectRequest(detectedObjectObservation: observation) { [weak self] request, error in
            self?.handleTrackResult(request: request, error: error)
        }
        // Force high accuracy tracking (slower but better for our use case)
        self.trackRequest?.trackingLevel = .accurate
        
        do {
            try sequenceRequestHandler.perform([self.trackRequest!], on: frame, orientation: .up)
            
            DispatchQueue.main.async {
                self.isTracking = true
            }
        } catch {
            print("Failed to start tracking sequence: \(error)")
        }
    }
    
    func updateTracking(with frame: CVPixelBuffer) {
        guard isTracking, let request = trackRequest else { return }
        
        do {
            try sequenceRequestHandler.perform([request], on: frame, orientation: .up)
        } catch {
            print("Tracking update failed: \(error)")
            stopTracking()
        }
    }
    
    func stopTracking() {
        DispatchQueue.main.async {
            self.isTracking = false
            self.trackedBox = nil
            self.trackRequest = nil
        }
    }
    
    private func handleTrackResult(request: VNRequest, error: Error?) {
        guard let results = request.results as? [VNObservation],
              let observation = results.first as? VNDetectedObjectObservation else {
            stopTracking()
            return
        }
        
        // If confidence drops too low, we lost the target
        if observation.confidence < 0.3 {
            stopTracking()
            return
        }
        
        // Convert back to SwiftUI coordinate space (top-left origin)
        let flippedY = 1.0 - observation.boundingBox.origin.y - observation.boundingBox.size.height
        let normalizedRect = CGRect(x: observation.boundingBox.origin.x,
                                    y: flippedY,
                                    width: observation.boundingBox.size.width,
                                    height: observation.boundingBox.size.height)
        
        let box = BoundingBox(rect: normalizedRect, confidence: observation.confidence)
        
        DispatchQueue.main.async {
            self.trackedBox = box
            
            // Re-create the request for the next frame using the new observation
            self.trackRequest = VNTrackObjectRequest(detectedObjectObservation: observation, completionHandler: self.handleTrackResult)
            self.trackRequest?.trackingLevel = .accurate
        }
    }
}
