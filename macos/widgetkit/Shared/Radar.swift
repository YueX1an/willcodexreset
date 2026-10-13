import Foundation

struct Radar: Codable {
    let probability24h: Int?
    let probability48h: Int?
    let verdict: String?
    let updatedAt: String?
    let timeline: [ResetEvent]?
    let tiboRelevantPosts: [Post]?
    struct ResetEvent: Codable { let time: String?; let resetConfirmed: Bool? }
    struct Post: Codable { let detail: String? }
    var lastReset: Date? {
        (timeline ?? []).filter { $0.resetConfirmed == true }.compactMap { Self.date($0.time) }.max()
    }
    var preview: String { tiboRelevantPosts?.first?.detail ?? "" }
    static func date(_ text: String?) -> Date? {
        guard let text else { return nil }
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        if let date = formatter.date(from: text) { return date }
        formatter.formatOptions = [.withInternetDateTime]
        return formatter.date(from: text)
    }
    static let sample = Radar(probability24h: 12, probability48h: 28, verdict: "low", updatedAt: nil,
                              timeline: nil, tiboRelevantPosts: [.init(detail: "等待下一次重置预告")])
}
struct RadarEnvelope: Decodable { let code: Int; let data: Radar? }

enum RadarService {
    static func decode(_ bytes: Data) throws -> Radar {
        let payload = try JSONDecoder().decode(RadarEnvelope.self, from: bytes)
        guard payload.code == 0, let radar = payload.data else { throw URLError(.cannotParseResponse) }
        return radar
    }
    static func fetch() async throws -> Radar {
        let url = URL(string: "https://willcodexreset.com/api/reset-radar")!
        var request = URLRequest(url: url, timeoutInterval: 12)
        request.setValue("codex-reset-widgetkit/1.0", forHTTPHeaderField: "User-Agent")
        let (bytes, response) = try await URLSession.shared.data(for: request)
        guard let http = response as? HTTPURLResponse, (200..<300).contains(http.statusCode) else {
            throw URLError(.badServerResponse)
        }
        return try decode(bytes)
    }
}
// The extension owns this cache inside its sandbox; no account or app group is needed.
enum RadarCache {
    private static var file: URL? {
        FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first?
            .appendingPathComponent("CodexReset", isDirectory: true).appendingPathComponent("radar.json")
    }
    static func load() -> Radar? {
        guard let file, let bytes = try? Data(contentsOf: file) else { return nil }
        return try? JSONDecoder().decode(Radar.self, from: bytes)
    }
    static func save(_ radar: Radar) {
        guard let file, let bytes = try? JSONEncoder().encode(radar) else { return }
        try? FileManager.default.createDirectory(at: file.deletingLastPathComponent(), withIntermediateDirectories: true)
        try? bytes.write(to: file, options: .atomic)
    }
}
