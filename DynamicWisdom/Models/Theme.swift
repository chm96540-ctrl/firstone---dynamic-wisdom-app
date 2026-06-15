import Foundation

/// The emotional / situational dimensions used to connect life events to quotes.
/// Both quotes (in `quotes.json`) and life events (via keyword extraction) are
/// tagged with these themes, and the curation engine matches on the overlap.
enum Theme: String, CaseIterable, Codable, Identifiable, Hashable {
    case motivation
    case resilience
    case gratitude
    case love
    case loss
    case change
    case growth
    case work
    case stress
    case calm
    case courage
    case beginnings
    case reflection
    case perseverance
    case failure
    case success
    case relationships
    case health
    case uncertainty
    case hope
    case focus
    case rest

    var id: String { rawValue }

    /// Human-readable label for display.
    var title: String {
        rawValue.prefix(1).uppercased() + rawValue.dropFirst()
    }

    /// A representative SF Symbol for the theme.
    var symbol: String {
        switch self {
        case .motivation: return "flame"
        case .resilience: return "shield"
        case .gratitude: return "hands.sparkles"
        case .love: return "heart"
        case .loss: return "cloud.rain"
        case .change: return "arrow.triangle.2.circlepath"
        case .growth: return "leaf"
        case .work: return "briefcase"
        case .stress: return "bolt.heart"
        case .calm: return "wind"
        case .courage: return "figure.stand"
        case .beginnings: return "sunrise"
        case .reflection: return "moon.stars"
        case .perseverance: return "figure.run"
        case .failure: return "arrow.uturn.up"
        case .success: return "trophy"
        case .relationships: return "person.2"
        case .health: return "cross.case"
        case .uncertainty: return "questionmark.circle"
        case .hope: return "sparkles"
        case .focus: return "scope"
        case .rest: return "bed.double"
        }
    }
}
