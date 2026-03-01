import Foundation
import CoreGraphics
import CoreVideo
import UIKit

class HUDOverlay {
    
    // Draw the debug info onto a copy of the pixel buffer
    static func drawDebugHUD(on pixelBuffer: CVPixelBuffer,
                             trackedBox: BoundingBox?,
                             detectedBoxes: [BoundingBox],
                             trackID: String,
                             activity: Activity,
                             zoomScale: CGFloat,
                             signals: ClassifierSignals) -> CVPixelBuffer? {
        
        let width = CVPixelBufferGetWidth(pixelBuffer)
        let height = CVPixelBufferGetHeight(pixelBuffer)
        
        // We must create a copy of the pixel buffer because the original is often read-only from the camera
        guard let outputBuffer = pixelBuffer.copy() else { return nil }
        
        CVPixelBufferLockBaseAddress(outputBuffer, .init(rawValue: 0))
        defer { CVPixelBufferUnlockBaseAddress(outputBuffer, .init(rawValue: 0)) }
        
        // Create CGContext
        let colorSpace = CGColorSpaceCreateDeviceRGB()
        guard let context = CGContext(data: CVPixelBufferGetBaseAddress(outputBuffer),
                                      width: width,
                                      height: height,
                                      bitsPerComponent: 8,
                                      bytesPerRow: CVPixelBufferGetBytesPerRow(outputBuffer),
                                      space: colorSpace,
                                      bitmapInfo: CGImageAlphaInfo.premultipliedFirst.rawValue | CGBitmapInfo.byteOrder32Little.rawValue) else {
            return outputBuffer
        }
        
        // UIGraphicsPushContext allows us to use high-level UIKit drawing (like NSString.draw)
        // directly onto the CVPixelBuffer context without worrying about CoreText mirroring issues.
        UIGraphicsPushContext(context)
        defer { UIGraphicsPopContext() }
        
        context.setLineWidth(4.0)
        
        // Draw the target bounding box (Green) OR detected boxes (Red)
        if let box = trackedBox {
            let rect = CGRect(x: box.rect.origin.x * CGFloat(width),
                              y: box.rect.origin.y * CGFloat(height),
                              width: box.rect.width * CGFloat(width),
                              height: box.rect.height * CGFloat(height))
            
            context.setStrokeColor(UIColor.green.cgColor)
            context.stroke(rect)
            
            // Draw Target ID above the box
            let textAttributes: [NSAttributedString.Key: Any] = [
                .font: UIFont.boldSystemFont(ofSize: 24),
                .foregroundColor: UIColor.green
            ]
            let idString = NSAttributedString(string: trackID, attributes: textAttributes)
            drawText(text: idString, at: CGPoint(x: rect.origin.x, y: max(0, rect.origin.y - 30)))
            
        } else {
            // Not tracking, draw DETECTED boxes in Red
            context.setStrokeColor(UIColor.red.cgColor)
            let textAttributes: [NSAttributedString.Key: Any] = [
                .font: UIFont.boldSystemFont(ofSize: 24),
                .foregroundColor: UIColor.red
            ]
            
            for box in detectedBoxes {
                let rect = CGRect(x: box.rect.origin.x * CGFloat(width),
                                  y: box.rect.origin.y * CGFloat(height),
                                  width: box.rect.width * CGFloat(width),
                                  height: box.rect.height * CGFloat(height))
                context.stroke(rect)
                
                let confString = NSAttributedString(string: String(format: "Person %.2f", box.confidence), attributes: textAttributes)
                drawText(text: confString, at: CGPoint(x: rect.origin.x, y: max(0, rect.origin.y - 30)))
            }
        }
        
        // Draw the top-left HUD if we are tracking (or even if we are not, show zero'd out states)
        let hudText = """
        STATE: \(activity.rawValue)
        ZOOM: \(String(format: "%.2fx", zoomScale))
        
        --- SIGNALS ---
        SPD: \(String(format: "%.1f", signals.totalSpeed)) px/f
        V-SPD: \(String(format: "%.1f", signals.vertSpeed)) px/f
        VAR: \(String(format: "%.3f", signals.areaCV))
        AR: \(String(format: "%.2f", signals.avgAR))
        """
        
        let hudAttributes: [NSAttributedString.Key: Any] = [
            .font: UIFont.monospacedSystemFont(ofSize: 20, weight: .bold),
            .foregroundColor: UIColor.yellow
        ]
        
        let hudString = NSAttributedString(string: hudText, attributes: hudAttributes)
        drawText(text: hudString, at: CGPoint(x: 20, y: 50))
        
        return outputBuffer
    }
    
    private static func drawText(text: NSAttributedString, at point: CGPoint) {
        let size = text.size()
        let textRect = CGRect(origin: point, size: size)
        
        // Draw black background for readability
        let ctx = UIGraphicsGetCurrentContext()
        ctx?.saveGState()
        
        // Slightly larger background for better contrast
        ctx?.setFillColor(UIColor.black.withAlphaComponent(0.6).cgColor)
        ctx?.fill(textRect.insetBy(dx: -8, dy: -8))
        
        text.draw(at: point)
        ctx?.restoreGState()
    }
}

// Helper to copy a CVPixelBuffer
extension CVPixelBuffer {
    func copy() -> CVPixelBuffer? {
        let width = CVPixelBufferGetWidth(self)
        let height = CVPixelBufferGetHeight(self)
        let format = CVPixelBufferGetPixelFormatType(self)
        
        var pixelBufferCopy: CVPixelBuffer?
        let status = CVPixelBufferCreate(nil, width, height, format, nil, &pixelBufferCopy)
        
        guard status == kCVReturnSuccess, let copy = pixelBufferCopy else { return nil }
        
        CVPixelBufferLockBaseAddress(self, .readOnly)
        CVPixelBufferLockBaseAddress(copy, [])
        
        let baseAddress = CVPixelBufferGetBaseAddress(self)
        let copyBaseAddress = CVPixelBufferGetBaseAddress(copy)
        let bytesPerRow = CVPixelBufferGetBytesPerRow(self)
        
        memcpy(copyBaseAddress, baseAddress, height * bytesPerRow)
        
        CVPixelBufferUnlockBaseAddress(copy, [])
        CVPixelBufferUnlockBaseAddress(self, .readOnly)
        
        return copy
    }
}
