import Foundation

/// Picks the most applicable quote for a given day + slot, based on the user's
/// recent life events and the feedback they've given through votes.
///
/// Scoring intuition:
///  - Build a weighted theme profile from recent events (newer events weigh more).
///  - Score each candidate quote by how well its themes overlap that profile.
///  - Nudge scores by what the user has historically up/down-voted (learned bias).
///  - Prefer quotes that fit the slot (morning = energizing, evening = reflective).
///  - Penalize quotes shown recently so the feed stays fresh.
struct CurationEngine {

    /// How many days of history feed the theme profile.
    private let lookbackDays: Int = 10
    /// Half-life (in days) for event recency weighting.
    private let recencyHalfLife: Double = 3.0

    /// Pick a quote for `slot` on `day`.
    /// - Parameters:
    ///   - library: all available quotes.
    ///   - events: the user's logged life events.
    ///   - themeBias: learned per-theme multiplier from past votes (1.0 = neutral).
    ///   - recentlyShownIDs: quote IDs surfaced recently (to avoid repeats).
    func pick(slot: CuratedQuote.DaySlot,
              day: Date,
              library: [Quote],
              events: [LifeEvent],
              themeBias: [Theme: Double],
              recentlyShownIDs: Set<String>) -> (quote: Quote, themes: [Theme], eventNotes: [String])? {

        guard !library.isEmpty else { return nil }

        let profile = themeProfile(events: events, asOf: day)
        let topEventNotes = recentEventNotes(events: events, asOf: day, limit: 3)

        var best: Quote?
        var bestScore = -Double.greatestFiniteMagnitude

        for quote in library {
            var score = baseScore(for: quote, profile: profile, themeBias: themeBias)

            // Slot fit.
            score += slotBonus(quote: quote, slot: slot)

            // Freshness: discourage repeats, but never hard-exclude.
            if recentlyShownIDs.contains(quote.id) {
                score -= 5.0
            }

            // Tiny deterministic jitter keyed by id+day so ties break stably
            // but vary across days.
            score += jitter(quoteID: quote.id, day: day, slot: slot)

            if score > bestScore {
                bestScore = score
                best = quote
            }
        }

        guard let chosen = best else { return nil }
        let matchingThemes = chosen.themes.filter { (profile[$0] ?? 0) > 0 }
        return (chosen, matchingThemes.isEmpty ? chosen.themes : matchingThemes, topEventNotes)
    }

    // MARK: - Scoring pieces

    /// Weighted theme profile from recent events.
    func themeProfile(events: [LifeEvent], asOf day: Date) -> [Theme: Double] {
        var profile: [Theme: Double] = [:]
        let cal = Calendar.current
        for event in events {
            let days = daysBetween(event.date, day, calendar: cal)
            guard days >= 0, days <= Double(lookbackDays) else { continue }
            let weight = pow(0.5, days / recencyHalfLife)
            for theme in event.themes {
                profile[theme, default: 0] += weight
            }
        }
        return profile
    }

    private func baseScore(for quote: Quote,
                           profile: [Theme: Double],
                           themeBias: [Theme: Double]) -> Double {
        guard !profile.isEmpty else {
            // No events yet: lean on learned bias only, otherwise neutral.
            return quote.themes.reduce(0) { $0 + ((themeBias[$1] ?? 1.0) - 1.0) }
        }
        var score = 0.0
        for theme in quote.themes {
            let relevance = profile[theme] ?? 0
            let bias = themeBias[theme] ?? 1.0
            score += relevance * bias
        }
        // Reward quotes that concentrate on relevant themes rather than diluting.
        if !quote.themes.isEmpty {
            score /= sqrt(Double(quote.themes.count))
        }
        return score
    }

    private func slotBonus(quote: Quote, slot: CuratedQuote.DaySlot) -> Double {
        switch (quote.slot, slot) {
        case (.morning, .morning), (.evening, .evening):
            return 1.5
        case (.any, _):
            return 0.5
        default:
            return 0
        }
    }

    private func jitter(quoteID: String, day: Date, slot: CuratedQuote.DaySlot) -> Double {
        var hasher = Hasher()
        hasher.combine(quoteID)
        hasher.combine(CuratedQuote.dayKeyFormatter.string(from: day))
        hasher.combine(slot.rawValue)
        let h = abs(hasher.finalize())
        return Double(h % 1000) / 1000.0 * 0.4 // 0...0.4
    }

    private func recentEventNotes(events: [LifeEvent], asOf day: Date, limit: Int) -> [String] {
        events
            .filter { $0.date <= day.addingTimeInterval(86_400) }
            .sorted { $0.date > $1.date }
            .prefix(limit)
            .map { $0.note }
    }

    private func daysBetween(_ a: Date, _ b: Date, calendar: Calendar) -> Double {
        b.timeIntervalSince(a) / 86_400.0
    }
}

/// Learns per-theme preference multipliers from the user's voting history.
/// An up-vote on a quote raises the weight of its themes; a down-vote lowers it.
enum ThemeBiasLearner {
    static func bias(from curated: [CuratedQuote]) -> [Theme: Double] {
        var up: [Theme: Int] = [:]
        var down: [Theme: Int] = [:]
        for item in curated {
            switch item.vote {
            case .up: item.themes.forEach { up[$0, default: 0] += 1 }
            case .down: item.themes.forEach { down[$0, default: 0] += 1 }
            case .none: break
            }
        }
        var bias: [Theme: Double] = [:]
        for theme in Theme.allCases {
            let u = Double(up[theme] ?? 0)
            let d = Double(down[theme] ?? 0)
            // Laplace-smoothed signal in roughly [0.5, 1.7].
            let score = (u + 1.0) / (d + 1.0)
            bias[theme] = min(1.7, max(0.5, score))
        }
        return bias
    }
}
