import Foundation
import CoreGraphics

// Enum mirroring Python
enum Activity: String {
    case riding = "RIDING"
    case paddling = "PADDLING"
    case sitting = "SITTING"
    case unknown = "UNKNOWN"
}

// Structure mirroring Python ClassifierSignals
struct ClassifierSignals {
    var totalSpeed: CGFloat = 0.0
    var vertSpeed: CGFloat = 0.0
    var areaCV: CGFloat = 0.0
    var avgAR: CGFloat = 0.0
    var historyCount: Int = 0
}

class ActivityClassifier {
    // Tuning Constants
    private let ridingSpeedThreshold: CGFloat = 6.0
    private let verticalRidingThreshold: CGFloat = 4.0
    private let paddlingSpeedThreshold: CGFloat = 2.0
    private let moderateSpeedThreshold: CGFloat = 3.5
    private let areaVarianceThreshold: CGFloat = 0.05
    private let standingAspectRatio: CGFloat = 0.55
    private let historyLength: Int = 10
    private let ridingHoldFrames: Int = 15
    
    // History Buffers
    private var cxHistory: [CGFloat] = []
    private var cyHistory: [CGFloat] = []
    private var arHistory: [CGFloat] = []
    private var areaHistory: [CGFloat] = []
    
    private(set) var currentActivity: Activity = .unknown
    private(set) var signals = ClassifierSignals()
    private var ridingHoldCounter: Int = 0
    
    func reset() {
        cxHistory.removeAll()
        cyHistory.removeAll()
        arHistory.removeAll()
        areaHistory.removeAll()
        currentActivity = .unknown
        ridingHoldCounter = 0
        signals = ClassifierSignals()
    }
    
    func update(targetRect: CGRect?, frameSize: CGSize) -> Activity {
        guard let rect = targetRect else {
            tickHold()
            return currentActivity
        }
        
        // Convert normalized rect to absolute pixels for velocity calculations
        let cx = rect.midX * frameSize.width
        let cy = rect.midY * frameSize.height
        let boxW = rect.width * frameSize.width
        let boxH = max(rect.height * frameSize.height, 1.0)
        let area = boxW * boxH
        
        appendHistory(&cxHistory, val: cx)
        appendHistory(&cyHistory, val: cy)
        appendHistory(&arHistory, val: boxW / boxH)
        appendHistory(&areaHistory, val: area)
        
        // Need at least 2 points to compute frame-to-frame motion.
        if cxHistory.count < 2 {
            signals.historyCount = cxHistory.count
            return .unknown
        }
        
        currentActivity = classify()
        return currentActivity
    }
    
    private func appendHistory(_ array: inout [CGFloat], val: CGFloat) {
        array.append(val)
        if array.count > historyLength {
            array.removeFirst()
        }
    }
    
    private func tickHold() {
        if ridingHoldCounter > 0 {
            ridingHoldCounter -= 1
        }
    }
    
    private func classify() -> Activity {
        let n = cxHistory.count
        
        // 2D Speed
        var speeds2D: [CGFloat] = []
        for i in 1..<n {
            let dx = cxHistory[i] - cxHistory[i-1]
            let dy = cyHistory[i] - cyHistory[i-1]
            speeds2D.append(sqrt(dx*dx + dy*dy))
        }
        let totalSpeed = speeds2D.isEmpty ? 0.0 : speeds2D.reduce(0, +) / CGFloat(speeds2D.count)
        
        // Vertical Speed
        var vertSpeeds: [CGFloat] = []
        for i in 1..<n {
            vertSpeeds.append(abs(cyHistory[i] - cyHistory[i-1]))
        }
        let vertSpeed = vertSpeeds.isEmpty ? 0.0 : vertSpeeds.reduce(0, +) / CGFloat(vertSpeeds.count)
        
        // Area Variance (CV = std / mean)
        let meanArea = areaHistory.reduce(0, +) / CGFloat(areaHistory.count)
        var areaVar: CGFloat = 0.0
        if meanArea > 0 {
            let variance = areaHistory.reduce(0) { $0 + pow($1 - meanArea, 2) } / CGFloat(areaHistory.count)
            areaVar = sqrt(variance) / meanArea
        }
        
        // Aspect Ratio
        let avgAR = arHistory.reduce(0, +) / CGFloat(arHistory.count)
        
        // Update Signals struct
        signals = ClassifierSignals(
            totalSpeed: totalSpeed,
            vertSpeed: vertSpeed,
            areaCV: areaVar,
            avgAR: avgAR,
            historyCount: n
        )
        
        // Rules
        if totalSpeed >= ridingSpeedThreshold {
            ridingHoldCounter = ridingHoldFrames
            return .riding
        }
        
        if vertSpeed >= verticalRidingThreshold {
            ridingHoldCounter = ridingHoldFrames
            return .riding
        }
        
        if totalSpeed >= moderateSpeedThreshold && areaVar >= areaVarianceThreshold {
            ridingHoldCounter = ridingHoldFrames
            return .riding
        }
        
        if ridingHoldCounter > 0 {
            ridingHoldCounter -= 1
            return .riding
        }
        
        if totalSpeed >= paddlingSpeedThreshold {
            return .paddling
        }
        
        return .sitting
    }
}
