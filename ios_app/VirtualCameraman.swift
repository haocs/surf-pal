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
        update(targetBox: nil, screenSize: CGSize(width: 1, height: 1))
    }
    
    func update(targetBox: BoundingBox?, screenSize: CGSize) {
        let targetCx: CGFloat
        let targetCy: CGFloat
        let targetScale: CGFloat
        
        if let box = targetBox {
            // Target center in normalized coords
            targetCx = box.rect.midX
            targetCy = box.rect.midY
            
            // Calculate scale: we want the max dimension of the box to take up ~30% of the screen
            let maxDim = max(box.rect.width, box.rect.height)
            targetScale = max(1.0, min(4.0, 0.3 / maxDim))
        } else {
            // Return to center and 1x scale if no target
            targetCx = 0.5
            targetCy = 0.5
            targetScale = 1.0
        }
        
        // Apply EMA smoothing
        currentCx = (1 - alphaPan) * currentCx + alphaPan * targetCx
        currentCy = (1 - alphaPan) * currentCy + alphaPan * targetCy
        currentScale = (1 - alphaScale) * currentScale + alphaScale * targetScale
        
        // Set the published properties for SwiftUI
        // Offset = -Scale * (Target - Center) * Screen Dimension
        DispatchQueue.main.async {
            self.scale = self.currentScale
            self.offsetX = -self.currentScale * (self.currentCx - 0.5) * screenSize.width
            self.offsetY = -self.currentScale * (self.currentCy - 0.5) * screenSize.height
        }
    }
}
