import AppKit
import Foundation

private let cardSize = NSSize(width: 340, height: 164)
private let endpoint = URL(string: "https://willcodexreset.com/api/reset-radar")!

struct RadarResponse: Decodable {
    let code: Int
    let data: RadarData?
}
struct RadarData: Decodable {
    let probability24h: Int?
    let probability48h: Int?
    let verdict: String?
    let updatedAt: String?
    let timeline: [ResetEvent]?
    let tiboRelevantPosts: [Post]?
}
struct ResetEvent: Decodable {
    let time: String?
    let resetConfirmed: Bool?
}
struct Post: Decodable { let detail: String? }

func isoDate(_ value: String?) -> Date? {
    guard let value else { return nil }
    let parser = ISO8601DateFormatter()
    parser.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
    if let date = parser.date(from: value) { return date }
    parser.formatOptions = [.withInternetDateTime]
    return parser.date(from: value)
}
func formatted(_ date: Date, _ pattern: String) -> String {
    let formatter = DateFormatter()
    formatter.locale = Locale(identifier: "en_US_POSIX")
    formatter.dateFormat = pattern
    return formatter.string(from: date)
}
func latestReset(_ data: RadarData) -> Date? {
    (data.timeline ?? []).filter { $0.resetConfirmed == true }
        .compactMap { isoDate($0.time) }.max()
}
func probabilityColor(_ value: Int) -> NSColor {
    value >= 70 ? .systemRed : value >= 30 ? .systemOrange : .systemGreen
}
func verdictColor(_ value: String) -> NSColor {
    switch value.lowercased() {
    case "elevated", "high", "severe": return .systemRed
    case "moderate", "medium": return .systemOrange
    case "low", "calm", "quiet": return .systemGreen
    default: return .secondaryLabelColor
    }
}

final class CardView: NSView {
    var refreshAction: (() -> Void)?
    override var isFlipped: Bool { true }
    override func mouseDown(with event: NSEvent) {
        if event.clickCount == 2 { refreshAction?() }
        else { window?.performDrag(with: event) }
    }
}

final class AppDelegate: NSObject, NSApplicationDelegate, NSWindowDelegate {
    private var panel: NSPanel!
    private var statusItem: NSStatusItem!
    private var pinButton: NSButton!
    private var timer: Timer?
    private var request: URLSessionDataTask?
    private var pinned = UserDefaults.standard.bool(forKey: "pinned")
    private var labels: [String: NSTextField] = [:]
    private var visibilityItem: NSMenuItem!
    private var pinItem: NSMenuItem!

    func applicationDidFinishLaunching(_ notification: Notification) {
        NSApp.setActivationPolicy(.accessory)
        buildPanel()
        buildMenu()
        if CommandLine.arguments.contains("--layout-test") {
            let bounds = NSRect(origin: .zero, size: cardSize)
            precondition(labels.values.allSatisfy { bounds.contains($0.frame) })
            let fields = Array(labels.values)
            for a in fields.indices {
                for b in fields.indices where b > a {
                    precondition(!fields[a].frame.intersects(fields[b].frame), "Labels overlap")
                }
            }
            precondition(panel.frame.size == cardSize)
            print("macOS layout checks passed (340 × 164)")
            NSApp.terminate(nil)
            return
        }
        panel.orderFrontRegardless()
        refresh()
        timer = Timer.scheduledTimer(withTimeInterval: 600, repeats: true) { [weak self] _ in
            self?.refresh()
        }
    }

    private func label(_ key: String, _ text: String, _ x: CGFloat, _ y: CGFloat,
                       _ width: CGFloat, _ size: CGFloat = 12,
                       _ color: NSColor = .labelColor, bold: Bool = false) -> NSTextField {
        let field = NSTextField(labelWithString: text)
        field.frame = NSRect(x: x, y: y, width: width, height: size + 8)
        field.font = .systemFont(ofSize: size, weight: bold ? .semibold : .regular)
        field.textColor = color
        field.lineBreakMode = .byTruncatingTail
        field.maximumNumberOfLines = 1
        field.isSelectable = false
        labels[key] = field
        return field
    }

    private func buildPanel() {
        panel = NSPanel(contentRect: NSRect(origin: .zero, size: cardSize),
                        styleMask: [.borderless, .nonactivatingPanel], backing: .buffered, defer: false)
        panel.title = "Codex Reset"
        panel.isOpaque = false
        panel.backgroundColor = .clear
        // Match the translucent, pale-on-wallpaper desktop widget treatment.
        panel.appearance = NSAppearance(named: .darkAqua)
        panel.hasShadow = true
        panel.hidesOnDeactivate = false
        panel.isReleasedWhenClosed = false
        panel.collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary]
        panel.delegate = self
        let content = CardView(frame: NSRect(origin: .zero, size: cardSize))
        content.refreshAction = { [weak self] in self?.refresh() }
        // The system renders live glass without capturing the desktop.
        if #available(macOS 26.0, *), ProcessInfo.processInfo.environment["CODEX_WIDGET_GLASS"] != "frosted" {
            let glass = NSGlassEffectView(frame: content.frame)
            glass.style = .clear
            glass.tintColor = NSColor.black.withAlphaComponent(0.12)
            glass.cornerRadius = 28
            glass.contentView = content
            panel.contentView = glass
        } else {
            let glass = NSVisualEffectView(frame: content.frame)
            glass.material = .hudWindow
            glass.blendingMode = .behindWindow
            glass.state = .active
            glass.wantsLayer = true
            glass.layer?.cornerRadius = 28
            glass.layer?.masksToBounds = true
            glass.addSubview(content)
            panel.contentView = glass
        }
        let fields = [
            label("title", "CODEX RESET", 18, 13, 150, 12, .labelColor, bold: true),
            label("status", "● 连接中", 175, 14, 62, 10, .secondaryLabelColor),
            label("footer", "--:--", 241, 14, 47, 10, .secondaryLabelColor),
            label("24label", "未来 24h", 18, 36, 140, 10, .secondaryLabelColor),
            label("48label", "未来 48h", 182, 36, 140, 10, .secondaryLabelColor),
            label("p24", "—", 18, 54, 140, 28, bold: true),
            label("p48", "—", 182, 54, 140, 28, bold: true),
            label("verdict", "加载中…", 18, 91, 304, 12, bold: true),
            label("lastLabel", "上次重置", 18, 112, 70, 11, .secondaryLabelColor),
            label("last", "—", 90, 112, 232, 11),
            label("previewLabel", "预告", 18, 134, 70, 11, .secondaryLabelColor),
            label("preview", "—", 90, 134, 232, 11)
        ]
        fields.forEach { content.addSubview($0) }
        labels["footer"]?.alignment = .right
        labels["footer"]?.toolTip = "每 10 分钟自动更新；双击卡片立即刷新"
        pinButton = NSButton(frame: NSRect(x: 297, y: 7, width: 28, height: 28))
        pinButton.isBordered = false
        pinButton.target = self
        pinButton.action = #selector(togglePin)
        pinButton.setAccessibilityLabel("置顶 / 取消置顶")
        content.addSubview(pinButton)
        applyPin()
        positionPanel()
    }

    private func positionPanel() {
        if let saved = UserDefaults.standard.string(forKey: "position") {
            let origin = NSPointFromString(saved)
            let frame = NSRect(origin: origin, size: cardSize)
            if NSScreen.screens.contains(where: { $0.visibleFrame.contains(frame) }) {
                panel.setFrameOrigin(origin)
                return
            }
        }
        let screen = NSScreen.main?.visibleFrame ?? NSRect(x: 0, y: 0, width: 1440, height: 900)
        panel.setFrameOrigin(NSPoint(x: screen.maxX - cardSize.width - 28,
                                     y: screen.maxY - cardSize.height - 28))
    }
    func windowDidMove(_ notification: Notification) {
        UserDefaults.standard.set(NSStringFromPoint(panel.frame.origin), forKey: "position")
    }
    private func menuItem(_ title: String, _ action: Selector) -> NSMenuItem {
        let item = NSMenuItem(title: title, action: action, keyEquivalent: "")
        item.target = self
        return item
    }
    private func buildMenu() {
        let menu = NSMenu()
        visibilityItem = menuItem("隐藏浮窗", #selector(toggleVisible))
        pinItem = menuItem("置顶浮窗", #selector(togglePin))
        pinItem.state = pinned ? .on : .off
        menu.addItem(visibilityItem)
        menu.addItem(pinItem)
        menu.addItem(menuItem("立即刷新", #selector(refresh)))
        menu.addItem(.separator())
        menu.addItem(menuItem("退出 Codex Reset", #selector(quit)))
        panel.contentView?.menu = menu
        // Attach to the actual content so right-clicks anywhere on the card work.
        if #available(macOS 26.0, *), let glass = panel.contentView as? NSGlassEffectView {
            glass.contentView?.menu = menu
        } else { panel.contentView?.subviews.first?.menu = menu }
        statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.squareLength)
        statusItem.button?.image = NSImage(systemSymbolName: "arrow.clockwise.circle", accessibilityDescription: "Codex Reset")
        statusItem.button?.toolTip = "Codex Reset"
        statusItem.menu = menu
    }
    @objc private func toggleVisible() {
        if panel.isVisible { panel.orderOut(nil) } else { panel.orderFrontRegardless() }
        visibilityItem.title = panel.isVisible ? "隐藏浮窗" : "显示浮窗"
    }
    @objc private func togglePin() {
        pinned.toggle()
        UserDefaults.standard.set(pinned, forKey: "pinned")
        applyPin()
        pinItem?.state = pinned ? .on : .off
    }
    private func applyPin() {
        panel.level = pinned ? .floating : .normal
        pinButton.image = NSImage(systemSymbolName: pinned ? "pin.fill" : "pin", accessibilityDescription: "置顶")
        pinButton.contentTintColor = pinned ? .systemBlue : .secondaryLabelColor
        pinButton.toolTip = pinned ? "取消置顶" : "置顶浮窗"
    }
    @objc private func quit() { NSApp.terminate(nil) }

    @objc private func refresh() {
        guard request == nil else { return }
        labels["status"]?.stringValue = "● 更新中"
        labels["status"]?.textColor = .secondaryLabelColor
        var urlRequest = URLRequest(url: endpoint, timeoutInterval: 15)
        urlRequest.setValue("codex-reset-widget-macos/1.0", forHTTPHeaderField: "User-Agent")
        request = URLSession.shared.dataTask(with: urlRequest) { [weak self] bytes, response, error in
            var result: RadarData?
            if error == nil, let http = response as? HTTPURLResponse, (200..<300).contains(http.statusCode),
               let bytes, let payload = try? JSONDecoder().decode(RadarResponse.self, from: bytes), payload.code == 0 {
                result = payload.data
            }
            let loaded = result
            DispatchQueue.main.async {
                guard let self else { return }
                self.request = nil
                if let loaded { self.render(loaded) }
                else {
                    self.labels["status"]?.stringValue = "● 离线"
                    self.labels["status"]?.textColor = .systemOrange
                    self.labels["footer"]?.stringValue = formatted(Date(), "HH:mm")
                    self.labels["footer"]?.toolTip = "更新失败；保留上次数据，双击重试"
                    self.labels["footer"]?.textColor = .systemOrange
                }
            }
        }
        request?.resume()
    }
    private func render(_ data: RadarData) {
        for (key, value) in [("p24", data.probability24h ?? 0), ("p48", data.probability48h ?? 0)] {
            labels[key]?.stringValue = "\(value)%"
            labels[key]?.textColor = .labelColor
            labels[key]?.toolTip = value >= 70 ? "重置概率较高" : value >= 30 ? "重置概率中等" : "重置概率较低"
        }
        let verdict = (data.verdict ?? "").trimmingCharacters(in: .whitespacesAndNewlines)
        labels["verdict"]?.stringValue = verdict.isEmpty ? "—" : verdict.uppercased()
        labels["verdict"]?.textColor = .labelColor
        if let last = latestReset(data) {
            let days = Int(floor(Date().timeIntervalSince(last) / 86400))
            labels["last"]?.stringValue = "\(formatted(last, "yyyy-MM-dd"))（\(days)天前）"
        } else { labels["last"]?.stringValue = "—" }
        let preview = data.tiboRelevantPosts?.first?.detail ?? ""
        labels["previewLabel"]?.stringValue = preview.isEmpty ? "" : "预告"
        labels["preview"]?.stringValue = preview
        labels["preview"]?.toolTip = preview
        labels["status"]?.stringValue = "● 实时"
        labels["status"]?.textColor = .systemGreen
        let updated = isoDate(data.updatedAt).map { formatted($0, "HH:mm") } ?? "--:--"
        labels["footer"]?.stringValue = updated
        labels["footer"]?.toolTip = "上次更新 \(updated)；双击卡片立即刷新"
        labels["footer"]?.textColor = .secondaryLabelColor
    }
    func applicationWillTerminate(_ notification: Notification) {
        timer?.invalidate()
        request?.cancel()
    }
}

if CommandLine.arguments.contains("--self-test") {
    let sample = #"{"code":0,"data":{"probability24h":89,"probability48h":99,"verdict":"elevated","updatedAt":"2026-10-13T04:53:51.024Z","timeline":[{"time":"2026-10-07T03:00:00Z","resetConfirmed":true},{"time":"2026-10-10T03:00:00.000Z","resetConfirmed":false},{"time":"2026-10-08T03:00:00.000Z","resetConfirmed":true}],"tiboRelevantPosts":[{"detail":"Global reset"}]}}"#
    let payload = try JSONDecoder().decode(RadarResponse.self, from: Data(sample.utf8))
    precondition(payload.code == 0 && payload.data?.probability24h == 89)
    precondition(latestReset(payload.data!) == isoDate("2026-10-08T03:00:00Z"))
    precondition(isoDate(payload.data?.updatedAt) != nil)
    precondition(isoDate("invalid") == nil)
    let empty = try JSONDecoder().decode(RadarResponse.self, from: Data(#"{"code":0,"data":{}}"#.utf8))
    precondition(latestReset(empty.data!) == nil)
    precondition(probabilityColor(29) == .systemGreen)
    precondition(probabilityColor(30) == .systemOrange)
    precondition(probabilityColor(70) == .systemRed)
    precondition(verdictColor("ELEVATED") == .systemRed)
    print("macOS data checks passed")
} else {
    let app = NSApplication.shared
    let delegate = AppDelegate()
    app.delegate = delegate
    app.run()
}
