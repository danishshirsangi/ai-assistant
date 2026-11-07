import AVFoundation
import CoreMedia
import Foundation
import ScreenCaptureKit

final class Recorder: NSObject, SCStreamOutput, SCStreamDelegate {
    private let writer: AVAssetWriter
    private let input: AVAssetWriterInput
    private var stream: SCStream?
    private var receivedAudioBuffers = 0
    private var appendedAudioBuffers = 0

    init(url: URL) throws {
        writer = try AVAssetWriter(outputURL: url, fileType: .m4a)
        input = AVAssetWriterInput(mediaType: .audio, outputSettings: [
            AVFormatIDKey: kAudioFormatMPEG4AAC,
            AVSampleRateKey: 48000,
            AVNumberOfChannelsKey: 2,
            AVEncoderBitRateKey: 64000
        ])
        input.expectsMediaDataInRealTime = true
        super.init()
        guard writer.canAdd(input) else {
            throw NSError(domain: "InterviewCopilot", code: 1,
                          userInfo: [NSLocalizedDescriptionKey: "Cannot add audio input"])
        }
        writer.add(input)
    }

    func start() async throws {
        let content = try await SCShareableContent.excludingDesktopWindows(
            false, onScreenWindowsOnly: false
        )
        guard let display = content.displays.first else {
            throw NSError(domain: "InterviewCopilot", code: 2,
                          userInfo: [NSLocalizedDescriptionKey: "No display found"])
        }
        let filter = SCContentFilter(display: display, excludingWindows: [])
        let config = SCStreamConfiguration()
        config.width = 2
        config.height = 2
        config.capturesAudio = true
        config.sampleRate = 48000
        config.channelCount = 2
        config.excludesCurrentProcessAudio = false
        let capture = SCStream(filter: filter, configuration: config, delegate: self)
        try capture.addStreamOutput(
            self, type: .audio,
            sampleHandlerQueue: DispatchQueue(label: "copilot.system-audio")
        )
        writer.startWriting()
        writer.startSession(atSourceTime: .zero)
        stream = capture
        try await capture.startCapture()
    }

    func stop() async throws {
        if let stream { try await stream.stopCapture() }
        input.markAsFinished()
        await withCheckedContinuation { continuation in
            writer.finishWriting { continuation.resume() }
        }
        guard writer.status == .completed else {
            throw writer.error ?? NSError(domain: "InterviewCopilot", code: 3,
                userInfo: [NSLocalizedDescriptionKey: "Could not finish audio file"])
        }
        guard receivedAudioBuffers > 0, appendedAudioBuffers > 0 else {
            throw NSError(domain: "InterviewCopilot", code: 4,
                userInfo: [NSLocalizedDescriptionKey:
                    "ScreenCaptureKit received no writable system-audio samples. Check macOS Screen & System Audio Recording permission and ensure Google Meet audio is playing through this Mac."])
        }
    }

    func stream(_ stream: SCStream, didOutputSampleBuffer sampleBuffer: CMSampleBuffer,
                of outputType: SCStreamOutputType) {
        guard outputType == .audio, CMSampleBufferIsValid(sampleBuffer) else { return }
        receivedAudioBuffers += 1
        guard input.isReadyForMoreMediaData else { return }
        if input.append(sampleBuffer) {
            appendedAudioBuffers += 1
        } else if let error = writer.error {
            fputs("Audio writer append failed: \\(error.localizedDescription)\\n", stderr)
        }
    }
}

@main
struct CaptureMain {
    static func main() async {
        guard CommandLine.arguments.count > 1 else {
            fputs("Usage: system_audio_capture output.m4a\n", stderr)
            exit(2)
        }
        do {
            let recorder = try Recorder(url: URL(fileURLWithPath: CommandLine.arguments[1]))
            try await recorder.start()
            print("READY")
            fflush(stdout)
            _ = readLine()
            try await recorder.stop()
        } catch {
            fputs(String(describing: error) + "\n", stderr)
            exit(1)
        }
    }
}
