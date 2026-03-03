import Vision
import CoreML
import Combine
import ImageIO
import Foundation

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

    private func failLoudly(_ message: String) -> Never {
        fatalError("SurfPal Detector Fatal: \(message)")
    }
    
    private func setupModel() {
        // NOTE: yolov8n.mlpackage must be included in target resources.
        let configuration = MLModelConfiguration()
        configuration.computeUnits = .all

        do {
            let model = try loadModel(configuration: configuration)
            let visionModel = try VNCoreMLModel(for: model)
            self.visionModel = visionModel

            let request = VNCoreMLRequest(model: visionModel) { [weak self] request, error in
                self?.processResults(request: request, error: error)
            }
            // YOLO requires images scaled appropriately. Vision handles this.
            request.imageCropAndScaleOption = .scaleFill
            self.request = request
        } catch {
            failLoudly("Failed to initialize Vision/CoreML model: \(error)")
        }
    }

    private func loadModel(configuration: MLModelConfiguration) throws -> MLModel {
        // Preferred path: Xcode-compiled model in bundle.
        if let compiledURL = Bundle.main.url(forResource: "yolov8n", withExtension: "mlmodelc") {
            return try MLModel(contentsOf: compiledURL, configuration: configuration)
        }

        // Fallback path: raw package in bundle (compile at runtime).
        if let packageURL = Bundle.main.url(forResource: "yolov8n", withExtension: "mlpackage") {
            let compiledURL = try MLModel.compileModel(at: packageURL)
            return try MLModel(contentsOf: compiledURL, configuration: configuration)
        }

        // Robust fallback: walk bundle in case model is nested in a folder reference.
        if let compiledURL = findModelRecursively(extension: "mlmodelc") {
            return try MLModel(contentsOf: compiledURL, configuration: configuration)
        }
        if let packageURL = findModelRecursively(extension: "mlpackage") {
            let compiledURL = try MLModel.compileModel(at: packageURL)
            return try MLModel(contentsOf: compiledURL, configuration: configuration)
        }

        failLoudly(
            "Missing required model in app bundle. Expected yolov8n.mlmodelc or yolov8n.mlpackage. " +
            "Run `cd ios_app && make sync-model && make generate`, then rebuild."
        )
    }

    private func findModelRecursively(extension ext: String) -> URL? {
        guard let resourceRoot = Bundle.main.resourceURL else { return nil }
        let fm = FileManager.default
        guard let enumerator = fm.enumerator(
            at: resourceRoot,
            includingPropertiesForKeys: nil,
            options: [.skipsHiddenFiles]
        ) else { return nil }

        for case let url as URL in enumerator {
            let basename = url.deletingPathExtension().lastPathComponent.lowercased()
            if basename == "yolov8n" && url.pathExtension.lowercased() == ext.lowercased() {
                return url
            }
        }
        return nil
    }
    
    func processFrame(
        _ pixelBuffer: CVPixelBuffer,
        orientation: CGImagePropertyOrientation = .up
    ) {
        // Drop frames if we are currently busy inferring to avoid memory buildup
        guard !isProcessing else { return }
        guard let request = self.request else {
            failLoudly("Detector request is nil while processing frames.")
        }
        isProcessing = true
        
        processingQueue.async {
            let handler = VNImageRequestHandler(
                cvPixelBuffer: pixelBuffer,
                orientation: orientation,
                options: [:]
            )
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
