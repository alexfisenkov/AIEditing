// Text on frames via Apple Vision (macOS). Usage: swift vision_ocr.swift <image>...
// Prints one JSON object per recognised line:
// {"image": <index>, "text": ..., "x","y","w","h": pixels, top-left origin, "conf": 0..1}
import Foundation
import Vision
import AppKit

func emit(_ obj: [String: Any]) {
    if let data = try? JSONSerialization.data(withJSONObject: obj),
       let line = String(data: data, encoding: .utf8) {
        print(line)
    }
}

for (index, path) in CommandLine.arguments.dropFirst().enumerated() {
    guard let image = NSImage(contentsOfFile: path),
          let cg = image.cgImage(forProposedRect: nil, context: nil, hints: nil) else {
        FileHandle.standardError.write("cannot read \(path)\n".data(using: .utf8)!)
        continue
    }
    let request = VNRecognizeTextRequest()
    request.recognitionLevel = .accurate
    request.usesLanguageCorrection = false
    let wanted = ["ru-RU", "en-US"]
    if let supported = try? request.supportedRecognitionLanguages() {
        request.recognitionLanguages = wanted.filter { supported.contains($0) }
    }
    let handler = VNImageRequestHandler(cgImage: cg, options: [:])
    try? handler.perform([request])
    for observation in request.results ?? [] {
        guard let best = observation.topCandidates(1).first else { continue }
        let box = observation.boundingBox
        let W = Double(cg.width), H = Double(cg.height)
        emit(["image": index, "text": best.string, "conf": Double(best.confidence),
              "x": Double(box.minX) * W, "y": (1 - Double(box.maxY)) * H,
              "w": Double(box.width) * W, "h": Double(box.height) * H])
    }
}
