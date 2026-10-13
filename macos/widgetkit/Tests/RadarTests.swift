import Foundation
@main
struct RadarTests {
    static func main() throws {
        let bytes = Data(#"{"code":0,"data":{"probability24h":89,"probability48h":99,"timeline":[{"resetConfirmed":true,"time":"2026-10-08T03:00:00.000Z"},{"resetConfirmed":true,"time":"2026-10-07T03:00:00Z"},{"resetConfirmed":false,"time":"2026-10-09T03:00:00Z"}],"tiboRelevantPosts":[{"detail":"预告"}]}}"#.utf8)
        let radar = try RadarService.decode(bytes)
        precondition(radar.probability24h == 89 && radar.probability48h == 99)
        precondition(radar.lastReset == Radar.date("2026-10-08T03:00:00Z"))
        precondition(radar.preview == "预告")
        precondition(Radar.date("invalid") == nil)
        for json in [#"{"code":1,"data":{}}"#, #"{"code":0,"data":null}"#, "garbage"] {
            do { _ = try RadarService.decode(Data(json.utf8)); fatalError("Accepted invalid payload") }
            catch { }
        }
        let empty = try RadarService.decode(Data(#"{"code":0,"data":{}}"#.utf8))
        precondition(empty.lastReset == nil && empty.preview.isEmpty && empty.probability24h == nil)
        let roundTrip = try JSONDecoder().decode(Radar.self, from: JSONEncoder().encode(radar))
        precondition(roundTrip.lastReset == radar.lastReset)
        print("WidgetKit data checks passed")
    }
}
