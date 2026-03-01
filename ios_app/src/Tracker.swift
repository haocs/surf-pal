import Vision
import Combine
import CoreGraphics

// Re-using the BoundingBox from Detector.swift

enum TrackingMode: String, CaseIterable, Identifiable {
    case auto = "Auto"
    case select = "Select"

    var id: String { rawValue }
}

struct LostTrackingEvent: Identifiable {
    let id = UUID()
    let message: String
}

class Tracker: ObservableObject {
    @Published var mode: TrackingMode = .auto
    @Published var isTracking = false
    @Published var trackedBox: BoundingBox?

    // Debug info
    @Published var trackID: String = ""
    @Published var currentActivity: Activity = .unknown
    @Published var classifierSignals = ClassifierSignals()
    @Published var lostEvent: LostTrackingEvent?

    private var sequenceRequestHandler = VNSequenceRequestHandler()
    private var lastObservation: VNDetectedObjectObservation?
    private let activityClassifier = ActivityClassifier()
    private var frameSize = CGSize(width: 1, height: 1)

    // Manual tracking settings
    private let manualMinConfidence: VNConfidence = 0.10

    // Auto mode settings
    private let autoLostFrameTolerance = 12
    private let autoIouThreshold: CGFloat = 0.08
    private let autoContinuityWeight: CGFloat = 0.70
    private let autoConfidenceWeight: CGFloat = 0.30
    private var autoLostFrames = 0

    private func runOnMain(_ block: @escaping () -> Void) {
        if Thread.isMainThread {
            block()
        } else {
            DispatchQueue.main.async(execute: block)
        }
    }

    private func publishTrackingUpdate(
        rect: CGRect,
        confidence: VNConfidence,
        forcedTrackID: String? = nil
    ) {
        runOnMain {
            self.autoLostFrames = 0
            self.isTracking = true
            if let forcedTrackID = forcedTrackID {
                self.trackID = forcedTrackID
            } else if self.trackID.isEmpty {
                self.trackID = String(format: "ID:%04d", Int.random(in: 1000...9999))
            }

            self.trackedBox = BoundingBox(rect: rect, confidence: confidence)
            self.currentActivity = self.activityClassifier.update(targetRect: rect, frameSize: self.frameSize)
            self.classifierSignals = self.activityClassifier.signals
        }
    }

    private func resetTrackingState() {
        isTracking = false
        trackedBox = nil
        trackID = ""
        lastObservation = nil
        sequenceRequestHandler = VNSequenceRequestHandler()
        autoLostFrames = 0
        activityClassifier.reset()
        currentActivity = .unknown
        classifierSignals = activityClassifier.signals
    }

    private func publishLostTracking(message: String) {
        runOnMain {
            self.resetTrackingState()
            self.lostEvent = LostTrackingEvent(message: message)
        }
    }

    func clearLostEvent() {
        runOnMain {
            self.lostEvent = nil
        }
    }

    func setMode(_ newMode: TrackingMode) {
        guard mode != newMode else { return }
        runOnMain {
            self.mode = newMode
            self.resetTrackingState()
            self.lostEvent = nil
        }
    }

    func startTracking(targetRect: CGRect, in pixelBuffer: CVPixelBuffer) {
        guard mode == .select else { return }
        let manualID = String(format: "ID:%04d", Int.random(in: 1000...9999))

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
        clearLostEvent()
        publishTrackingUpdate(rect: targetRect, confidence: 1.0, forcedTrackID: manualID)
    }

    func updateAutoTracking(with detections: [BoundingBox], frameSize: CGSize) {
        guard mode == .auto else { return }
        self.frameSize = frameSize

        guard !detections.isEmpty else {
            handleAutoMissingTarget()
            return
        }

        guard let next = selectAutoTarget(from: detections) else {
            handleAutoMissingTarget()
            return
        }

        clearLostEvent()
        publishTrackingUpdate(
            rect: next.rect,
            confidence: next.confidence,
            forcedTrackID: "AUTO"
        )
    }

    func stopTracking() {
        runOnMain {
            self.resetTrackingState()
            self.lostEvent = nil
        }
    }

    func updateTracking(with pixelBuffer: CVPixelBuffer) {
        guard mode == .select else { return }
        guard let observation = lastObservation else { return }

        let request = VNTrackObjectRequest(detectedObjectObservation: observation) { [weak self] request, error in
            guard let self = self else { return }

            if let result = request.results?.first as? VNDetectedObjectObservation {
                if result.confidence < self.manualMinConfidence {
                    self.publishLostTracking(message: "Tracking lost. Tap surfer to reselect.")
                    return
                }

                self.lastObservation = result

                // Convert back from Vision coordinates (Y inverted)
                let rect = result.boundingBox
                let normalizedRect = CGRect(x: rect.origin.x,
                                            y: 1 - rect.origin.y - rect.height,
                                            width: rect.width,
                                            height: rect.height)

                self.publishTrackingUpdate(rect: normalizedRect, confidence: result.confidence)
            } else {
                // Tracking lost
                self.publishLostTracking(message: "Tracking lost. Tap surfer to reselect.")
            }
        }

        // request.trackingLevel = .accurate // .fast or .accurate

        do {
            try sequenceRequestHandler.perform([request], on: pixelBuffer)
        } catch {
            print("Tracking failed: \(error)")
            publishLostTracking(message: "Tracking lost. Tap surfer to reselect.")
        }
    }

    private func handleAutoMissingTarget() {
        guard isTracking else { return }
        autoLostFrames += 1
        if autoLostFrames > autoLostFrameTolerance {
            publishLostTracking(message: "Auto tracking lost. Reacquiring...")
        }
    }

    private func selectAutoTarget(from detections: [BoundingBox]) -> BoundingBox? {
        guard let previous = trackedBox else {
            return detections.max(by: { $0.confidence < $1.confidence })
        }

        let overlaps = detections.map { box in
            (box: box, overlap: iou(previous.rect, box.rect))
        }

        if let bestOverlap = overlaps.max(by: { $0.overlap < $1.overlap }),
           bestOverlap.overlap >= autoIouThreshold {
            return overlaps
                .map { pair in
                    let score =
                        autoContinuityWeight * pair.overlap
                        + autoConfidenceWeight * CGFloat(pair.box.confidence)
                    return (box: pair.box, score: score)
                }
                .max(by: { $0.score < $1.score })?
                .box
        }

        // If no overlap survives threshold, fall back to confidence with
        // a small proximity bias so we don't jump targets aggressively.
        return detections
            .map { box in
                let distance = normalizedCenterDistance(previous.rect, box.rect)
                let proximity = max(0.0, 1.0 - distance)
                let score = 0.75 * CGFloat(box.confidence) + 0.25 * proximity
                return (box: box, score: score)
            }
            .max(by: { $0.score < $1.score })?
            .box
    }

    private func iou(_ a: CGRect, _ b: CGRect) -> CGFloat {
        let intersection = a.intersection(b)
        if intersection.isNull || intersection.isEmpty {
            return 0.0
        }

        let interArea = intersection.width * intersection.height
        let unionArea = (a.width * a.height) + (b.width * b.height) - interArea
        if unionArea <= 0 { return 0.0 }
        return interArea / unionArea
    }

    private func normalizedCenterDistance(_ a: CGRect, _ b: CGRect) -> CGFloat {
        let dx = a.midX - b.midX
        let dy = a.midY - b.midY
        let distance = sqrt(dx * dx + dy * dy)
        // Max diagonal in normalized coordinate space is sqrt(2)
        return min(1.0, distance / 1.41421356)
    }
}
