import Vision
import CoreML
import Combine

struct BoundingBox: Identifiable {
    let id = UUID()
    let rect: CGRect
    let confidence: Float
}

class Detector: ObservableObject {
    @Published var detectedBoxes: [BoundingBox] = []
    
    private var visionModel: VNCoreMLModel?
    private var request: VNCoreMLRequest?
    private let processingQueue = DispatchQueue(label: "detector.queue", qos: .userInitiated)
    private var isProcessing = false
    
    init() {
        setupModel()
    }
    
    private func setupModel() {
        do {
            // NOTE: The user must add yolov8n.mlpackage to the Xcode target for this to load
            let configuration = MLModelConfiguration()
            configuration.computeUnits = .all
            
            // The generated model class will be named yolov8n
            let yoloModel = try yolov8n(configuration: configuration)
            self.visionModel = try VNCoreMLModel(for: yoloModel.model)
            
            self.request = VNCoreMLRequest(model: self.visionModel!) { [weak self] request, error in
                self?.processResults(request: request, error: error)
            }
            // YOLO requires images scaled appropriately. Vision handles this.
            self.request?.imageCropAndScaleOption = .scaleFill
            
        } catch {
            print("Failed to initialize Vision ML model: \(error)")
        }
    }
    
    func processFrame(_ pixelBuffer: CVPixelBuffer) {
        // Drop frames if we are currently busy inferring to avoid memory buildup
        guard !isProcessing, let request = self.request else { return }
        isProcessing = true
        
        processingQueue.async {
            let handler = VNImageRequestHandler(cvPixelBuffer: pixelBuffer, orientation: .up, options: [:])
            do {
                try handler.perform([request])
            } catch {
                print("Failed to perform detection: \(error)")
                self.isProcessing = false
            }
        }
    }
    
    private func processResults(request: VNRequest, error: Error?) {
        guard let results = request.results as? [VNRecognizedObjectObservation] else {
            DispatchQueue.main.async {
                self.detectedBoxes = []
                self.isProcessing = false
            }
            return
        }
        
        // Filter for "person" class (YOLO class 0)
        let personObservations = results.filter { observation in
            guard let topLabel = observation.labels.first else { return false }
            return topLabel.identifier == "person" || topLabel.identifier == "0"
        }
        
        let newBoxes = personObservations.map { obs in
            // Vision returns bounding boxes in normalized coordinates (0.0 - 1.0)
            // with origin at bottom-left. We flip the Y axis for SwiftUI overlay.
            let flippedY = 1.0 - obs.boundingBox.origin.y - obs.boundingBox.size.height
            let normalizedRect = CGRect(x: obs.boundingBox.origin.x,
                                        y: flippedY,
                                        width: obs.boundingBox.size.width,
                                        height: obs.boundingBox.size.height)
            return BoundingBox(rect: normalizedRect, confidence: obs.confidence)
        }
        
        DispatchQueue.main.async {
            self.detectedBoxes = newBoxes
            self.isProcessing = false
        }
    }
}
