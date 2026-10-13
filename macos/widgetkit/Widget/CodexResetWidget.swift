import SwiftUI
import WidgetKit

struct RadarEntry: TimelineEntry {
    let date: Date
    let radar: Radar?
    var offline = false
}
struct RadarProvider: TimelineProvider {
    func placeholder(in context: Context) -> RadarEntry { RadarEntry(date: .now, radar: .sample) }
    func getSnapshot(in context: Context, completion: @escaping (RadarEntry) -> Void) {
        if context.isPreview { completion(placeholder(in: context)); return }
        load(completion)
    }
    func getTimeline(in context: Context, completion: @escaping (Timeline<RadarEntry>) -> Void) {
        load { entry in
            completion(Timeline(entries: [entry], policy: .after(entry.date.addingTimeInterval(1800))))
        }
    }
    private func load(_ completion: @escaping (RadarEntry) -> Void) {
        Task {
            do {
                let radar = try await RadarService.fetch()
                RadarCache.save(radar)
                completion(RadarEntry(date: .now, radar: radar))
            } catch {
                completion(RadarEntry(date: .now, radar: RadarCache.load(), offline: true))
            }
        }
    }
}
struct RadarWidgetView: View {
    let entry: RadarEntry
    @Environment(\.widgetFamily) private var family
    private var radar: Radar? { entry.radar }
    private var updated: String {
        guard let date = Radar.date(radar?.updatedAt) else { return "--:--" }
        return date.formatted(.dateTime.hour(.twoDigits(amPM: .omitted)).minute(.twoDigits))
    }
    var body: some View {
        VStack(alignment: .leading, spacing: 7) {
            HStack(spacing: 4) {
                Text("CODEX RESET").font(.system(size: 12, weight: .semibold))
                Spacer(minLength: 4)
                if family != .systemSmall {
                    Text(entry.offline ? "离线" : "更新 \(updated)")
                        .font(.system(size: 10)).foregroundStyle(.secondary)
                }
            }
            HStack(alignment: .top, spacing: 18) {
                probability("未来 24h", radar?.probability24h)
                probability("未来 48h", radar?.probability48h)
            }
            Text(radar?.verdict?.uppercased() ?? (entry.offline ? "连接失败" : "等待更新"))
                .font(.system(size: 12, weight: .semibold)).lineLimit(1)
            if family != .systemSmall {
                HStack(spacing: 10) {
                    Text("上次重置").foregroundStyle(.secondary)
                    if let last = radar?.lastReset {
                        let days = Int(floor(entry.date.timeIntervalSince(last) / 86400))
                        Text("\(last.formatted(.dateTime.year().month(.twoDigits).day(.twoDigits)))（\(days)天前）")
                    } else { Text("—") }
                }.font(.system(size: 11)).lineLimit(1)
                if let preview = radar?.preview, !preview.isEmpty {
                    HStack(spacing: 10) {
                        Text("预告").foregroundStyle(.secondary)
                        Text(preview).lineLimit(family == .systemLarge ? 4 : 1)
                    }.font(.system(size: 11))
                }
            } else {
                Text(entry.offline ? "离线 · 保留上次数据" : "更新 \(updated)")
                    .font(.system(size: 10)).foregroundStyle(.secondary)
            }
            if family == .systemLarge { Spacer(minLength: 0) }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
        // WidgetKit supplies the radius, shadow, wallpaper treatment and tinted/clear appearance.
        .containerBackground(.background, for: .widget)
        .widgetURL(URL(string: "codexreset://show"))
    }
    private func probability(_ title: String, _ value: Int?) -> some View {
        VStack(alignment: .leading, spacing: 1) {
            Text(title).font(.system(size: 10)).foregroundStyle(.secondary)
            Text(value.map { "\($0)%" } ?? "—")
                .font(.system(size: family == .systemSmall ? 25 : 30, weight: .medium))
                .minimumScaleFactor(0.65).lineLimit(1).monospacedDigit()
        }.frame(maxWidth: .infinity, alignment: .leading)
    }
}
@main
struct CodexResetWidget: Widget {
    let kind = "CodexResetRadar"
    var body: some WidgetConfiguration {
        StaticConfiguration(kind: kind, provider: RadarProvider()) { entry in RadarWidgetView(entry: entry) }
            .configurationDisplayName("Codex Reset")
            .description("查看未来 24 / 48 小时重置概率、上次重置和预告。")
            .supportedFamilies([.systemSmall, .systemMedium, .systemLarge])
    }
}
