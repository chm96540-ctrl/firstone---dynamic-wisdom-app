import Foundation

/// A moment the user logs about what's going on in their life.
/// The free-text `note` is run through `ThemeMatcher` to derive `themes`, which
/// is how the curation engine decides which quotes are relevant.
struct LifeEvent: Identifiable, Codable, Hashable {
    enum Mood: String, Codable, CaseIterable, Identifiable {
        case great, good, neutral, low, rough
        var id: String { rawValue }

        var emoji: String {
            switch self {
            case .great: return "🤩"
            case .good: return "🙂"
            case .neutral: return "😐"
            case .low: return "😔"
            case .rough: return "😣"
            }
        }

        var label: String { rawValue.capitalized }

        /// Themes implied by the mood itself, layered on top of keyword matches.
        var impliedThemes: [Theme] {
            switch self {
            case .great: return [.gratitude, .success, .hope]
            case .good: return [.hope, .calm]
            case .neutral: return [.reflection]
            case .low: return [.resilience, .hope, .rest]
            case .rough: return [.resilience, .courage, .calm]
            }
        }
    }

    var id: UUID = UUID()
    var date: Date = Date()
    var note: String
    var mood: Mood
    /// Themes derived from `note` + `mood` at save time (cached for fast scoring).
    var themes: [Theme]

    init(id: UUID = UUID(),
         date: Date = Date(),
         note: String,
         mood: Mood,
         themes: [Theme]) {
        self.id = id
        self.date = date
        self.note = note
        self.mood = mood
        self.themes = themes
    }
}
