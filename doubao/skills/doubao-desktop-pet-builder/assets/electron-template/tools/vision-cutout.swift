import AppKit
import CoreImage
import Foundation
import ImageIO
import UniformTypeIdentifiers
import Vision

enum CutoutError: Error, CustomStringConvertible {
    case invalidArguments
    case cannotLoadImage(String)
    case noForeground(String)
    case cannotCreateImage(String)
    case cannotWriteImage(String)

    var description: String {
        switch self {
        case .invalidArguments:
            return "Usage: vision-cutout <input-file> <output-file>"
        case .cannotLoadImage(let name):
            return "Cannot load image: \(name)"
        case .noForeground(let name):
            return "No foreground subject found: \(name)"
        case .cannotCreateImage(let name):
            return "Cannot create masked image: \(name)"
        case .cannotWriteImage(let name):
            return "Cannot write image: \(name)"
        }
    }
}

@available(macOS 14.0, *)
func cutOutImage(inputURL: URL, outputURL: URL) throws {
    guard let source = CGImageSourceCreateWithURL(inputURL as CFURL, nil),
          let image = CGImageSourceCreateImageAtIndex(source, 0, nil) else {
        throw CutoutError.cannotLoadImage(inputURL.lastPathComponent)
    }

    let request = VNGenerateForegroundInstanceMaskRequest()
    let handler = VNImageRequestHandler(cgImage: image)
    try handler.perform([request])

    guard let observation = request.results?.first,
          !observation.allInstances.isEmpty else {
        throw CutoutError.noForeground(inputURL.lastPathComponent)
    }

    let maskedBuffer = try observation.generateMaskedImage(
        ofInstances: observation.allInstances,
        from: handler,
        croppedToInstancesExtent: false
    )

    let ciImage = CIImage(cvPixelBuffer: maskedBuffer)
    let context = CIContext(options: [.useSoftwareRenderer: false])
    guard let outputImage = context.createCGImage(ciImage, from: ciImage.extent),
          let destination = CGImageDestinationCreateWithURL(
            outputURL as CFURL,
            UTType.png.identifier as CFString,
            1,
            nil
          ) else {
        throw CutoutError.cannotCreateImage(inputURL.lastPathComponent)
    }

    CGImageDestinationAddImage(destination, outputImage, nil)
    guard CGImageDestinationFinalize(destination) else {
        throw CutoutError.cannotWriteImage(inputURL.lastPathComponent)
    }
}

func main() throws {
    guard CommandLine.arguments.count == 3 else {
        throw CutoutError.invalidArguments
    }

    guard #available(macOS 14.0, *) else {
        fputs("Apple Vision foreground cutout requires macOS 14 or later.\n", stderr)
        exit(2)
    }

    let inputURL = URL(fileURLWithPath: CommandLine.arguments[1])
    let outputURL = URL(fileURLWithPath: CommandLine.arguments[2])
    try FileManager.default.createDirectory(
        at: outputURL.deletingLastPathComponent(),
        withIntermediateDirectories: true
    )
    try cutOutImage(inputURL: inputURL, outputURL: outputURL)
}

do {
    try main()
} catch {
    fputs("\(error)\n", stderr)
    exit(1)
}
