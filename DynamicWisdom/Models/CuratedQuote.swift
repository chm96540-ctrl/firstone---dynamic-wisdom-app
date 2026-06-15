import Foundation

/// A quote that the engine surfaced for a specific day + time slot, along with
/// the user's vote on how applicable it actually was.
struct CuratedQuote: Identifiable, Codable, Hashable {
    enum DaySlot: String, Codable, CaseIterable, Identifiable {
        case morning
        case evening
        var id: String { rawValue }

        var title: String { rawValue.capitalized }

        var greeting: String {
            switch self {
            case .morning: return "Start of day"
            case .evening: return "End of day"
            }
        }

        var symbol: String {
            switch self {
            case .morning: return "sunrise.fill"
            case .evening: return "moon.stars.fill"
            }
        }
    }

    enum Vote: String, Codable {
        case up
        case down
        case none
    }

    var id: UUID = UUID()
    var quoteID: String
    var quoteText: String
    var quoteAuthor: String
    var themes: [Theme]
    var slot: DaySlot
    /// The day this was curated for (normalized to start of day).
    var day: Date
    var createdAt: Date = Date()
    var vote: Vote = .none
    /// Snapshot of the life-event notes that influenced this pick, for context.
    var basedOnEventNotes: [String] = []

    /// Calendar day key like "2026-06-14" for grouping / de-duping.
    var dayKey: String {
        CuratedQuote.dayKeyFormatter.string(from: day)
    }

    static let dayKeyFormatter: DateFormatter = {
        let f = DateFormatter()
        f.calendar = Calendar(identifier: .gregorian)
        f.locale = Locale(identifier: "en_US_POSIX")
        f.dateFormat = "yyyy-MM-dd"
        return f
    }()
}
