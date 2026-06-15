import Foundation
import SwiftUI

/// The single source of truth for the app. Owns life events, curated quotes,
/// the quote library, and orchestrates the curation engine + persistence.
@MainActor
final class AppStore: ObservableObject {

    @Published private(set) var lifeEvents: [LifeEvent] = []
    @Published private(set) var curated: [CuratedQuote] = []
    @Published var settings: AppSettings

    let library: [Quote]
    private let engine = CurationEngine()

    private let eventsStore = JSONStore<[LifeEvent]>(filename: "life_events.json")
    private let curatedStore = JSONStore<[CuratedQuote]>(filename: "curated_quotes.json")
    private let settingsStore = JSONStore<AppSettings>(filename: "settings.json")

    init(library: [Quote] = QuoteLibrary.load()) {
        self.library = library
        self.lifeEvents = eventsStore.load() ?? []
        self.curated = curatedStore.load() ?? []
        self.settings = settingsStore.load() ?? .default
    }

    // MARK: - Derived

    /// Learned per-theme bias from voting history.
    var themeBias: [Theme: Double] {
        ThemeBiasLearner.bias(from: curated)
    }

    /// Curated quotes for a specific calendar day, keyed by slot.
    func curatedQuotes(for day: Date) -> [CuratedQuote.DaySlot: CuratedQuote] {
        let key = CuratedQuote.dayKeyFormatter.string(from: Calendar.current.startOfDay(for: day))
        var result: [CuratedQuote.DaySlot: CuratedQuote] = [:]
        for item in curated where item.dayKey == key {
            result[item.slot] = item
        }
        return result
    }

    /// Stats for the insights screen.
    var voteStats: (up: Int, down: Int, total: Int) {
        let up = curated.filter { $0.vote == .up }.count
        let down = curated.filter { $0.vote == .down }.count
        return (up, down, curated.count)
    }

    // MARK: - Life events

    func addLifeEvent(note: String, mood: LifeEvent.Mood, date: Date = Date()) {
        let trimmed = note.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return }
        let themes = ThemeMatcher.themes(forNote: trimmed, mood: mood)
        let event = LifeEvent(date: date, note: trimmed, mood: mood, themes: themes)
        lifeEvents.append(event)
        lifeEvents.sort { $0.date > $1.date }
        eventsStore.save(lifeEvents)
        // A fresh event can change today's picks — recompute (without clobbering votes).
        refreshCuration(for: Date())
    }

    func deleteLifeEvents(at offsets: IndexSet) {
        lifeEvents.remove(atOffsets: offsets)
        eventsStore.save(lifeEvents)
    }

    func deleteLifeEvent(_ event: LifeEvent) {
        lifeEvents.removeAll { $0.id == event.id }
        eventsStore.save(lifeEvents)
    }

    // MARK: - Curation

    /// Ensure both slots for `day` have a curated quote. Re-picks a slot only if
    /// it hasn't been voted on yet (so we never overwrite the user's feedback).
    func refreshCuration(for day: Date) {
        let startOfDay = Calendar.current.startOfDay(for: day)
        let existing = curatedQuotes(for: startOfDay)
        let bias = themeBias

        for slot in CuratedQuote.DaySlot.allCases {
            if let current = existing[slot], current.vote != .none {
                continue // respect votes
            }
            let recent = recentlyShownIDs(excludingDay: startOfDay)
            guard let result = engine.pick(slot: slot,
                                           day: startOfDay,
                                           library: library,
                                           events: lifeEvents,
                                           themeBias: bias,
                                           recentlyShownIDs: recent) else { continue }

            let item = CuratedQuote(quoteID: result.quote.id,
                                    quoteText: result.quote.text,
                                    quoteAuthor: result.quote.author,
                                    themes: result.themes,
                                    slot: slot,
                                    day: startOfDay,
                                    basedOnEventNotes: result.eventNotes)

            if let existingItem = existing[slot] {
                replace(existingItem, with: item)
            } else {
                curated.append(item)
            }
        }
        curatedStore.save(curated)
    }

    /// Force a brand-new pick for a slot, ignoring any prior pick/vote.
    func reroll(slot: CuratedQuote.DaySlot, day: Date) {
        let startOfDay = Calendar.current.startOfDay(for: day)
        let recent = recentlyShownIDs(excludingDay: startOfDay)
            .union(curatedQuotes(for: startOfDay).values.map { $0.quoteID })
        guard let result = engine.pick(slot: slot,
                                       day: startOfDay,
                                       library: library,
                                       events: lifeEvents,
                                       themeBias: themeBias,
                                       recentlyShownIDs: recent) else { return }
        let item = CuratedQuote(quoteID: result.quote.id,
                                quoteText: result.quote.text,
                                quoteAuthor: result.quote.author,
                                themes: result.themes,
                                slot: slot,
                                day: startOfDay,
                                basedOnEventNotes: result.eventNotes)
        if let existing = curatedQuotes(for: startOfDay)[slot] {
            replace(existing, with: item)
        } else {
            curated.append(item)
        }
        curatedStore.save(curated)
    }

    // MARK: - Voting

    func vote(_ vote: CuratedQuote.Vote, on item: CuratedQuote) {
        guard let idx = curated.firstIndex(where: { $0.id == item.id }) else { return }
        // Tapping the same vote again clears it (toggle).
        curated[idx].vote = (curated[idx].vote == vote) ? .none : vote
        curatedStore.save(curated)
        objectWillChange.send()
    }

    // MARK: - Settings

    func updateSettings(_ new: AppSettings) {
        settings = new
        settingsStore.save(new)
    }

    // MARK: - Helpers

    private func replace(_ old: CuratedQuote, with new: CuratedQuote) {
        if let idx = curated.firstIndex(where: { $0.id == old.id }) {
            var updated = new
            updated.id = old.id // keep identity stable
            curated[idx] = updated
        }
    }

    private func recentlyShownIDs(excludingDay day: Date, days: Int = 5) -> Set<String> {
        let key = CuratedQuote.dayKeyFormatter.string(from: day)
        let cutoff = Calendar.current.date(byAdding: .day, value: -days, to: day) ?? day
        return Set(curated
            .filter { $0.day >= cutoff && $0.dayKey != key }
            .map { $0.quoteID })
    }
}

/// User-configurable settings, persisted to disk.
struct AppSettings: Codable, Equatable {
    var notificationsEnabled: Bool
    var morningHour: Int   // 0-23
    var morningMinute: Int
    var eveningHour: Int
    var eveningMinute: Int

    static let `default` = AppSettings(
        notificationsEnabled: false,
        morningHour: 8, morningMinute: 0,
        eveningHour: 21, eveningMinute: 0
    )
}
