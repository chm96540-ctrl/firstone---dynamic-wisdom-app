import Foundation

/// Turns free-text life-event notes into a set of `Theme`s using a keyword
/// lexicon. Intentionally simple and fully on-device (no network, no ML model)
/// so it works offline and is easy to reason about / extend.
enum ThemeMatcher {

    /// Keywords (and stems) that map to each theme. Matching is case-insensitive
    /// and stem-based (substring on word boundaries), so "working", "worked",
    /// and "works" all hit the "work" stem.
    static let lexicon: [Theme: [String]] = [
        .motivation:   ["motivat", "drive", "ambiti", "goal", "dream", "inspir", "push", "hustle"],
        .resilience:   ["resilien", "bounce", "tough", "hard time", "struggl", "endure", "survive", "setback"],
        .gratitude:    ["grateful", "gratitude", "thank", "blessed", "appreciat", "lucky"],
        .love:         ["love", "partner", "wife", "husband", "girlfriend", "boyfriend", "crush", "date", "marri", "romance"],
        .loss:         ["loss", "lost", "grief", "griev", "passed away", "death", "died", "funeral", "miss "],
        .change:       ["change", "transition", "moving", "moved", "new job", "switch", "shift", "different", "starting over"],
        .growth:       ["grow", "learn", "improv", "better", "progress", "develop", "skill", "habit"],
        .work:         ["work", "job", "career", "boss", "meeting", "project", "deadline", "office", "client", "promotion", "interview"],
        .stress:       ["stress", "anxious", "anxiety", "overwhelm", "pressure", "burnout", "tense", "worried", "panic"],
        .calm:         ["calm", "peace", "relax", "breath", "meditat", "quiet", "still", "ease"],
        .courage:      ["courage", "brave", "afraid", "fear", "scared", "risk", "bold", "nervous"],
        .beginnings:   ["start", "begin", "first day", "new ", "launch", "fresh", "kick off", "embark"],
        .reflection:   ["reflect", "think about", "looking back", "ponder", "journal", "review", "lesson"],
        .perseverance: ["persever", "keep going", "persist", "don't give up", "grind", "consistent", "discipline"],
        .failure:      ["fail", "mistake", "messed up", "rejected", "rejection", "didn't work", "flopped", "screwed up"],
        .success:      ["success", "won", "win ", "achiev", "accomplish", "nailed", "landed", "milestone", "passed"],
        .relationships:["friend", "family", "mom", "dad", "parent", "sibling", "brother", "sister", "kid", "child", "argument", "fight with"],
        .health:       ["health", "sick", "ill", "gym", "exercise", "run", "workout", "sleep", "tired", "doctor", "injur", "diet"],
        .uncertainty:  ["uncertain", "confus", "don't know", "unsure", "lost ", "doubt", "questioning", "crossroad"],
        .hope:         ["hope", "optimis", "looking forward", "excited", "bright", "future", "faith", "believe"],
        .focus:        ["focus", "concentrat", "distract", "priorit", "deep work", "attention"],
        .rest:         ["rest", "break", "vacation", "weekend", "recharge", "nap", "day off", "unwind"]
    ]

    /// Extract distinct themes implied by a note's text.
    static func themes(in text: String) -> [Theme] {
        let haystack = text.lowercased()
        guard !haystack.isEmpty else { return [] }

        var matched: [Theme] = []
        for theme in Theme.allCases {
            guard let keywords = lexicon[theme] else { continue }
            if keywords.contains(where: { haystack.contains($0) }) {
                matched.append(theme)
            }
        }
        return matched
    }

    /// Themes for a note combined with the mood's implied themes (deduplicated).
    static func themes(forNote note: String, mood: LifeEvent.Mood) -> [Theme] {
        var set = Set(themes(in: note))
        mood.impliedThemes.forEach { set.insert($0) }
        // Always keep at least one theme so an event is never "unmatchable".
        if set.isEmpty { set.insert(.reflection) }
        return Array(set)
    }
}
