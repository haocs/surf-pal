import SwiftUI
import Combine

class VirtualCameraman: ObservableObject {
    @Published var scale: CGFloat = 1.0
    @Published var offsetX: CGFloat = 0.0
    @Published var offsetY: CGFloat = 0.0
    
    // EMA smoothing factors
    private let alphaScale: CGFloat = 0.05
    private let alphaPan: CGFloat = 0.1
    
    // Current smoothed targets in normalized coordinates
    private var currentCx: CGFloat = 0.5
    private var currentCy: CGFloat = 0.5
    private var currentScale: CGFloat = 1.0
    
    func reset() {
        // Smoothly return to 1x zoom, centered
        update(targetBox: nil, activity: .unknown, screenSize: CGSize(width: 1, height: 1))
    }
    
    func update(targetBox: BoundingBox?, activity: Activity, screenSize: CGSize) {
        let targetCx: CGFloat
        let targetCy: CGFloat
        let targetScale: CGFloat
        
        if let box = targetBox {
            // Target center in normalized coords
            targetCx = box.rect.midX
            targetCy = box.rect.midY
            
            // Base scale based on box size (aim to keep box at ~25% of screen height)
            let boxHeight = box.rect.height
            let boxWidth = box.rect.width
            let baseScale = max(1.0, min(5.0, 0.25 / max(boxHeight, boxWidth * 0.5)))
            
            // Adjust scale based on activity
            switch activity {
            case .riding:
                // Zoom in more aggressively during riding
                targetScale = baseScale * 1.5
            case .paddling:
                // Zoom out to show more context during paddling
                targetScale = max(1.0, baseScale * 0.7)
            case .sitting, .unknown:
                targetScale = baseScale
            }
        } else {
            // Return to center and 1x scale if no target
            targetCx = 0.5
            targetCy = 0.5
            targetScale = 1.0
        }
        
        // Clamp total scale
        let clampedScale = max(1.0, min(6.0, targetScale))
        
        // Apply EMA smoothing
        currentCx = (1 - alphaPan) * currentCx + alphaPan * targetCx
        currentCy = (1 - alphaPan) * currentCy + alphaPan * targetCy
        currentScale = (1 - alphaScale) * currentScale + alphaScale * clampedScale
        
        // Set the published properties for SwiftUI
        // Offset = -Scale * (Target - Center) * Screen Dimension
        DispatchQueue.main.async {
            self.scale = self.currentScale
            self.offsetX = -self.currentScale * (self.currentCx - 0.5) * screenSize.width
            self.offsetY = -self.currentScale * (self.currentCy - 0.5) * screenSize.height
        }
    }
}
