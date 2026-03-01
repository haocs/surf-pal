import Foundation
import CoreGraphics
import CoreVideo
import UIKit

class HUDOverlay {
    
    // Draw the debug info onto a copy of the pixel buffer
    static func drawDebugHUD(on pixelBuffer: CVPixelBuffer,
                             trackedBox: BoundingBox?,
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
        
        // Setup drawing config
        context.setLineWidth(4.0)
        let textAttributes: [NSAttributedString.Key: Any] = [
            .font: UIFont.boldSystemFont(ofSize: 24),
            .foregroundColor: UIColor.green
        ]
        
        // Draw the target bounding box
        if let box = trackedBox {
            let rect = CGRect(x: box.rect.origin.x * CGFloat(width),
                              y: box.rect.origin.y * CGFloat(height),
                              width: box.rect.width * CGFloat(width),
                              height: box.rect.height * CGFloat(height))
            
            context.setStrokeColor(UIColor.green.cgColor)
            context.stroke(rect)
            
            // Draw Target ID above the box
            let idString = NSAttributedString(string: trackID, attributes: textAttributes)
            drawText(context: context, text: idString, at: CGPoint(x: rect.origin.x, y: max(0, rect.origin.y - 30)))
        }
        
        // Draw the top-left HUD
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
        drawText(context: context, text: hudString, at: CGPoint(x: 20, y: 50))
        
        return outputBuffer
    }
    
    private static func drawText(context: CGContext, text: NSAttributedString, at point: CGPoint) {
        // CoreGraphics has origin at bottom-left, so we must flip the text matrix
        context.saveGState()
        
        context.translateBy(x: 0, y: CGFloat(context.height))
        context.scaleBy(x: 1.0, y: -1.0)
        
        let framesetter = CTFramesetterCreateWithAttributedString(text)
        let size = CTFramesetterSuggestFrameSizeWithConstraints(framesetter, CFRangeMake(0,0), nil, CGSize(width: 800, height: 800), nil)
        
        // Since we flipped the context, we must also flip the y coordinate
        let textRect = CGRect(x: point.x, y: CGFloat(context.height) - point.y - size.height, width: size.width, height: size.height)
        
        // Draw black background for readability
        context.setFillColor(UIColor.black.withAlphaComponent(0.6).cgColor)
        context.fill(textRect.insetBy(dx: -5, dy: -5))
        
        let path = CGPath(rect: textRect, transform: nil)
        let frame = CTFramesetterCreateFrame(framesetter, CFRangeMake(0, 0), path, nil)
        
        CTFrameDraw(frame, context)
        context.restoreGState()
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
