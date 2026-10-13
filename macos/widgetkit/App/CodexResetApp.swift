import SwiftUI
import WidgetKit

@main
struct CodexResetApp: App {
    var body: some Scene {
        WindowGroup("Codex Reset") {
            VStack(alignment: .leading, spacing: 18) {
                Label("Codex Reset 桌面小组件", systemImage: "square.grid.2x2")
                    .font(.title2.bold())
                Text("在桌面空白处右键，选择“编辑小组件”，搜索 Codex Reset，然后添加中号小组件。")
                Text("玻璃背景、圆角和着色由 macOS 统一处理，跟随系统小组件的外观设置。")
                    .foregroundStyle(.secondary)
                Text("小组件会请求约每 30 分钟更新；实际时间由系统调度。网络失败时保留上次数据。")
                    .font(.callout).foregroundStyle(.secondary)
                HStack {
                    Button("请求刷新小组件") { WidgetCenter.shared.reloadAllTimelines() }
                    Link("查看完整预告", destination: URL(string: "https://willcodexreset.com")!)
                }
            }
            .padding(28).frame(width: 440)
            .onOpenURL { _ in WidgetCenter.shared.reloadAllTimelines() }
        }.windowResizability(.contentSize)
    }
}
